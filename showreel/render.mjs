// Frame-exact renderer: drives index.html in headless Chromium, one frame at a
// time, and pipes PNGs into ffmpeg. Splits the timeline across parallel workers.
//
//   node render.mjs                       -> out/video.mp4 (no audio)
//   node render.mjs --stills 0.5,3,6      -> out/stills/*.png
//   options: --samples 6 (motion-blur sub-frames) --workers 4 --fps 60
import { createRequire } from 'node:module';
import { spawn, execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const require = createRequire(import.meta.url);
const globalRoot = execFileSync('npm', ['root', '-g']).toString().trim();
const { chromium } = require(path.join(globalRoot, 'playwright'));

const dir = path.dirname(fileURLToPath(import.meta.url));
const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => (v.startsWith('--') ? [...a, [v.slice(2), arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : true]] : a), []));
const FPS = +(args.fps || 60), DUR = 15, SAMPLES = +(args.samples || 6), WORKERS = +(args.workers || 4);
const out = path.join(dir, 'out');
mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ args: ['--disable-gpu-vsync', '--force-color-profile=srgb'] });
async function page() {
  const p = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await p.goto(pathToFileURL(path.join(dir, 'index.html')).href + '?capture');
  await p.waitForFunction(() => window.READY === true);
  return p;
}
const grab = p => p.locator('#c').screenshot({ type: 'png', animations: 'disabled' });

if (args.stills) {
  const p = await page();
  mkdirSync(path.join(out, 'stills'), { recursive: true });
  for (const t of String(args.stills).split(',').map(Number)) {
    await p.evaluate(([t, s]) => window.drawFrame(t, s), [t, SAMPLES]);
    writeFileSync(path.join(out, 'stills', `t${t.toFixed(2).padStart(5, '0')}.png`), await grab(p));
  }
  await browser.close();
  process.exit(0);
}

const total = Math.round(FPS * DUR);
const per = Math.ceil(total / WORKERS);
const segs = [];
const started = Date.now();
let done = 0;
await Promise.all([...Array(WORKERS)].map(async (_, w) => {
  const a = w * per, b = Math.min(total, a + per);
  const seg = path.join(out, `seg${w}.mp4`); segs.push([w, seg]);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', seg], { stdio: ['pipe', 'inherit', 'inherit'] });
  const p = await page();
  for (let f = a; f < b; f++) {
    await p.evaluate(([t, s]) => window.drawFrame(t, s), [f / FPS, SAMPLES]);
    const buf = await grab(p);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (++done % 60 === 0) console.log(`${done}/${total} frames  ${((Date.now() - started) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end();
  await new Promise((res, rej) => ff.on('close', c => (c ? rej(new Error('ffmpeg ' + c)) : res())));
}));
await browser.close();

segs.sort((x, y) => x[0] - y[0]);
const list = path.join(out, 'segs.txt');
writeFileSync(list, segs.map(([, s]) => `file '${s}'`).join('\n'));
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', path.join(out, 'video.mp4')]);
for (const [, s] of segs) rmSync(s); rmSync(list);
console.log(`video.mp4 done in ${((Date.now() - started) / 1000).toFixed(0)}s`);

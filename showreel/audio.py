"""Original soundtrack for the showreel, synthesized from scratch with numpy.

128 BPM, 8 bars, A minor. Every hit is scored to an on-screen event
(see the timings in index.html). Writes out/soundtrack.wav (48 kHz, stereo).
"""
import os
import wave

import numpy as np

SR = 48000
BPM = 128
B = 60 / BPM
BAR = 4 * B
DUR = 15.0
N = int(SR * DUR)
rng = np.random.default_rng(11)

mix = np.zeros((N, 2))
send = np.zeros((N, 2))  # reverb bus


def t_(sec):
    return np.arange(int(sec * SR)) / SR


def hz(note):
    """MIDI note -> Hz."""
    return 440.0 * 2 ** ((note - 69) / 12)


def place(sig, at, gain=1.0, pan=0.0, rev=0.0):
    """Drop a mono or stereo one-shot onto the timeline."""
    if sig.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        sig = np.stack([sig * l, sig * r], axis=1) * np.sqrt(2)
    i = int(round(at * SR))
    if i >= N:
        return
    j = min(N, i + len(sig))
    s = sig[: j - i] * gain
    if i < 0:
        s, i = s[-i:], 0
    mix[i:j] += s
    send[i:j] += s * rev


def fft_filter(x, lo=None, hi=None):
    """Static brick-ish band filter with soft edges, done in the frequency domain."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if lo:
        g *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    if hi:
        g *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * g, len(x))


def sweep_lp(x, f0, f1):
    """One-pole low-pass whose cutoff glides exponentially from f0 to f1."""
    n = len(x)
    fc = f0 * (f1 / f0) ** (np.arange(n) / n)
    a = 1 - np.exp(-2 * np.pi * fc / SR)
    y = np.empty(n)
    acc = 0.0
    for k in range(n):
        acc += a[k] * (x[k] - acc)
        y[k] = acc
    return y


def saw(freq, t, harmonics=12, bright=0.25):
    out = np.zeros_like(t)
    for k in range(1, harmonics + 1):
        if freq * k > SR / 2.2:
            break
        out += np.sin(2 * np.pi * freq * k * t) / k * np.exp(-(k - 1) * bright)
    return out


# ---------------------------------------------------------------- one-shots
def kick():
    t = t_(0.42)
    f = 46 + 120 * np.exp(-t * 38)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 6.5)
    click = fft_filter(rng.standard_normal(len(t)), lo=2000) * np.exp(-t * 400) * 0.25
    return np.tanh((body + click) * 1.6)


def clap():
    t = t_(0.35)
    n = rng.standard_normal(len(t))
    env = np.exp(-t * 22)
    for d in (0.0, 0.011, 0.022):
        env = env + (t >= d) * np.exp(-np.maximum(t - d, 0) * 180) * 0.8
    return fft_filter(n * env, lo=900, hi=5000) * 0.9


def hat(open_=False):
    t = t_(0.3 if open_ else 0.07)
    return fft_filter(rng.standard_normal(len(t)), lo=7500) * np.exp(-t * (14 if open_ else 70)) * 0.5


def blip(note, dur=0.22):
    t = t_(dur)
    f = hz(note) * (1 + 0.5 * np.exp(-t * 60))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + 0.25 * np.sin(2 * ph)) * np.exp(-t * 16)


def pluck(note, dur=0.3):
    t = t_(dur)
    return saw(hz(note), t, 8, 0.6) * np.exp(-t * 14) * 0.8


def whoosh(dur, up=True):
    n = rng.standard_normal(int(dur * SR))
    y = sweep_lp(n, 300 if up else 6000, 6000 if up else 300)
    t = np.linspace(0, 1, len(y))
    env = np.sin(np.pi * t) ** 2 if up else (1 - t) ** 2
    return y * env


def riser(dur):
    t = t_(dur)
    k = t / dur
    noise = sweep_lp(rng.standard_normal(len(t)), 200, 9000) * k ** 2
    f = 180 * (16 ** k)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * k ** 3 * 0.25
    return noise + tone


def impact(dur=1.6):
    t = t_(dur)
    f = 32 + 60 * np.exp(-t * 9)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.6)
    boom = fft_filter(rng.standard_normal(len(t)), hi=500) * np.exp(-t * 6) * 0.8
    crash = fft_filter(rng.standard_normal(len(t)), lo=4000) * np.exp(-t * 2.4) * 0.35
    return np.tanh((sub * 1.3 + boom + crash) * 1.3)


def bell(note, dur=2.4):
    t = t_(dur)
    f = hz(note)
    idx = 3.0 * np.exp(-t * 4)
    return np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * 3.5 * t)) * np.exp(-t * 2.2)


def glitch(dur):
    t = t_(dur)
    steps = (t / (B / 8)).astype(int)
    f = 200 * 2 ** (rng.integers(0, 24, steps.max() + 1)[steps] / 12)
    sq = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR))
    gate = (np.floor(t / (B / 16)) % 2 == 0).astype(float)
    crushed = np.round(sq * gate * 4) / 4
    return crushed * 0.35 + fft_filter(rng.standard_normal(len(t)), lo=3000) * gate * 0.25


# ---------------------------------------------------------------- harmony
A2, F2, C3, G2 = 45, 41, 48, 43
CHORDS = [  # (bass root, pad voicing) per bar
    (A2, [57, 60, 64, 71]),  # Am(add9)
    (F2, [57, 60, 65, 69]),  # F
    (C3, [55, 60, 64, 67]),  # C
    (G2, [55, 59, 62, 67]),  # G
    (A2, [57, 60, 64, 69]),  # Am
    (F2, [57, 60, 65, 72]),  # F
    (G2, [55, 59, 62, 71]),  # G
    (A2, [57, 60, 64, 71]),  # Am(add9)
]

# pad: filter opens over the intro, sits under the drop, blooms at the end
t = np.arange(N) / SR
pad = np.zeros(N)
bright = np.interp(t, [0, BAR, BAR + 0.01, 7 * BAR, DUR], [1.4, 0.35, 0.55, 0.45, 0.3])
for bar, (_, notes) in enumerate(CHORDS):
    a, b = bar * BAR, (bar + 1) * BAR + (0.6 if bar == 7 else 0.05)
    i, j = int(a * SR), min(N, int(b * SR))
    tt = t[i:j] - a
    env = np.minimum(1, tt / 0.04) * np.minimum(1, (b - a - tt) / 0.05 + 0.0)
    seg = np.zeros(j - i)
    for n in notes:
        for det in (-0.12, 0.0, 0.12):
            f = hz(n + det)
            for k in range(1, 9):
                seg += np.sin(2 * np.pi * f * k * tt + k * det * 9) / k * np.exp(-(k - 1) * bright[i:j])
    pad[i:j] += seg * env
pad *= 0.035
pan_lfo = 0.3 * np.sin(2 * np.pi * 0.25 * t)
mix[:, 0] += pad * (1 - pan_lfo)
mix[:, 1] += pad * (1 + pan_lfo)
send[:, 0] += pad * 0.6
send[:, 1] += pad * 0.6

# ---------------------------------------------------------------- drums + bass (bars 1..6)
K, CL, HC, HO = kick(), clap(), hat(), hat(True)
drop, stop = BAR, 7 * BAR
duck = np.ones(N)
beat = drop
while beat < stop - 1e-6:
    place(K, beat, 0.95)
    i = int(beat * SR)
    d = np.arange(min(N - i, int(B * SR))) / SR
    duck[i:i + len(d)] = np.minimum(duck[i:i + len(d)], 1 - 0.85 * np.exp(-d * 11))
    n = round((beat - drop) / B)
    if n % 2 == 1:
        place(CL, beat, 0.55, rev=0.25)
    if beat >= 2 * BAR:
        place(HC, beat + B / 2, 0.45, pan=0.35)
        if n % 4 == 3:
            place(HO, beat + B / 2, 0.35, pan=-0.3)
    if 2 * BAR <= beat < 3 * BAR or 5 * BAR <= beat < 6 * BAR:  # 16th hats in the busy bars
        for s in (0.25, 0.75):
            place(HC, beat + s * B, 0.22, pan=-0.4)
    beat += B

bass = np.zeros(N)
for bar in range(1, 7):
    root = CHORDS[bar][0]
    for e in range(8):
        a = bar * BAR + e * B / 2
        tt = t_(B / 2)
        note = root + (12 if e in (3, 7) else 0)
        env = np.exp(-tt * 5) * 0.8 + 0.2
        sig = saw(hz(note), tt, 14, 0.42) * env * np.minimum(1, tt / 0.004) * np.minimum(1, (B / 2 - tt) / 0.006)
        i = int(a * SR)
        bass[i:i + len(sig)] += sig[: max(0, min(len(sig), N - i))]
bass = np.tanh(bass * 1.4) * 0.28 * duck
mix += bass[:, None]
mix[:, 0] *= 1  # (pad/bass already mono-centred)

# ---------------------------------------------------------------- scene-scored sound design
# S1 intro: dot pop, anticipation tick, line zip, title hit, riser into the drop
place(blip(81, 0.25), 0.04, 0.5, rev=0.4)
place(blip(76, 0.08), B * 0.45, 0.25)
place(whoosh(0.3), B * 0.72 - 0.05, 0.6, pan=-0.2)
place(impact(1.2), 2 * B, 0.55, rev=0.3)
place(bell(69, 1.2), 2 * B, 0.12, rev=0.5)
place(riser(BAR - 2 * B - 0.05), 2 * B + 0.05, 0.45)

# S2: a pitched pop on every shape morph
for k, n in enumerate([72, 76, 79, 84]):
    place(blip(n), BAR + k * B, 0.38, pan=(-0.4, 0.4, -0.2, 0.2)[k], rev=0.35)

# transitions: each cut gets its own swoosh
for k, pre in {1: .34, 2: .24, 4: .28, 5: .26, 7: .34}.items():
    place(whoosh(pre + 0.12), k * BAR - pre, 0.5, pan=0.3 if k % 2 else -0.3)

# S3: kinetic type hits + stutter on FEEL
for k in range(4):
    place(blip(64 + k * 3, 0.12), 2 * BAR + k * B, 0.3)
place(glitch(B * 0.6), 2 * BAR + 3 * B + 0.2, 0.45)
place(glitch(0.3), 3 * BAR - 0.16, 0.5)

# S4: reverse swell into the particle explosion
tEx = 3 * BAR + 1.2 * B
place(whoosh(0.45)[::-1] * 0.8, tEx - 0.45, 0.8)
place(impact(1.4), tEx, 0.8, rev=0.35)
for i in range(10):  # sparkle as particles land in the word
    place(blip(84 + (i * 5) % 12, 0.1), tEx + 0.15 + i * 0.045, 0.08, pan=(i % 5 - 2) / 2.5, rev=0.5)

# S5: soft ticks as bars grow, plus the data swap
for i in range(7):
    place(blip(72 + i, 0.06), 4 * BAR + 0.15 + i * 0.045, 0.12, pan=(i - 3) / 4)
for i in range(7):
    place(blip(79 - i, 0.06), 4 * BAR + 2 * B + i * 0.035, 0.12, pan=(3 - i) / 4)

# S6: arpeggio + long riser into the fly-through, impact on the flash
arp = [57, 64, 69, 72, 76, 72, 69, 64]
for i in range(16):
    a = 5 * BAR + i * B / 4
    if a >= 6 * BAR - 0.05:
        break
    place(pluck(arp[i % 8] + (12 if i >= 8 else 0)), a, 0.18, pan=(-0.5, 0.5)[i % 2], rev=0.4)
place(riser(6 * BAR - (5 * BAR + 1.2 * B)), 5 * BAR + 1.2 * B, 0.6)
place(impact(1.5), 6 * BAR, 0.75, rev=0.35)

# S7: clacks as each tile wave ripples out
for k in range(4):
    for i in range(6):
        place(hat(), 6 * BAR + k * B + i * 0.035, 0.18 * (1 - i / 7), pan=(i / 3 - 1) * (1 if k % 2 else -1))

# S8: final hit, merge chime, signature chord
place(impact(1.8), 7 * BAR, 0.7, rev=0.3)
for i, n in enumerate([69, 76, 81, 83]):
    place(bell(n, 2.0), 7 * BAR + B + i * 0.06, 0.13, pan=(i - 1.5) / 2, rev=0.6)
place(blip(93, 0.3), 7 * BAR + 2 * B, 0.12, rev=0.6)

# ---------------------------------------------------------------- reverb (FFT convolution)
ir_len = int(1.6 * SR)
ti = np.arange(ir_len) / SR
ir = np.stack([rng.standard_normal(ir_len), rng.standard_normal(ir_len)], 1) * np.exp(-ti / 0.32)[:, None]
ir[:, 0] = fft_filter(ir[:, 0], hi=7000)
ir[:, 1] = fft_filter(ir[:, 1], hi=7000)
ir /= np.sqrt((ir ** 2).sum(0))
L = N + ir_len
for c in range(2):
    wet = np.fft.irfft(np.fft.rfft(send[:, c], L) * np.fft.rfft(ir[:, c], L), L)[:N]
    mix[:, c] += wet * 0.5

# ---------------------------------------------------------------- master
mix = fft_filter(mix[:, 0], lo=25)[:, None] * [1, 0] + fft_filter(mix[:, 1], lo=25)[:, None] * [0, 1]
mix = np.tanh(mix * 1.15)
mix /= np.abs(mix).max() / 0.89
fade = np.ones(N)
fade[:480] = np.linspace(0, 1, 480)
fade[-int(0.35 * SR):] = np.linspace(1, 0, int(0.35 * SR)) ** 1.5
mix *= fade[:, None]

os.makedirs(os.path.join(os.path.dirname(__file__), 'out'), exist_ok=True)
path = os.path.join(os.path.dirname(__file__), 'out', 'soundtrack.wav')
with wave.open(path, 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes())
print('wrote', path, f'{N / SR:.2f}s peak', f'{np.abs(mix).max():.2f}')

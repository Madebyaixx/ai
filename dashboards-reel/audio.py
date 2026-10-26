"""Original soundtrack + UI sound design for the Claude Dashboards explainer.

120 BPM, 28 s, F major / D minor. Every UI sound is placed on the exact
on-screen event in index.html. Writes out/soundtrack.wav (48 kHz stereo).
"""
import os
import wave

import numpy as np

SR = 48000
B = 0.5
BAR = 4 * B
DUR = 28.0
N = int(SR * DUR)
rng = np.random.default_rng(5)
mix = np.zeros((N, 2))
send = np.zeros((N, 2))


def t_(sec):
    return np.arange(int(sec * SR)) / SR


def hz(note):
    return 440.0 * 2 ** ((note - 69) / 12)


def place(sig, at, gain=1.0, pan=0.0, rev=0.0):
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    sig = np.stack([sig * l, sig * r], axis=1) * np.sqrt(2)
    i = int(round(at * SR))
    if i >= N:
        return
    j = min(N, i + len(sig))
    mix[i:j] += sig[: j - i] * gain
    send[i:j] += sig[: j - i] * gain * rev


def band(x, lo=None, hi=None):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if lo:
        g *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    if hi:
        g *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * g, len(x))


def sweep_lp(x, f0, f1):
    fc = f0 * (f1 / f0) ** (np.arange(len(x)) / len(x))
    a = 1 - np.exp(-2 * np.pi * fc / SR)
    y = np.empty(len(x))
    acc = 0.0
    for k in range(len(x)):
        acc += a[k] * (x[k] - acc)
        y[k] = acc
    return y


def tone(freq, t, harmonics=8, bright=0.5):
    out = np.zeros_like(t)
    for k in range(1, harmonics + 1):
        if freq * k < SR / 2.2:
            out += np.sin(2 * np.pi * freq * k * t) / k * np.exp(-(k - 1) * bright)
    return out


# ------------------------------------------------------------------ one-shots
def kick():
    t = t_(0.35)
    f = 50 + 90 * np.exp(-t * 40)
    return np.tanh(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8) * 1.5)


def hat():
    t = t_(0.06)
    return band(rng.standard_normal(len(t)), lo=8000) * np.exp(-t * 80) * 0.5


def snap():
    t = t_(0.2)
    return band(rng.standard_normal(len(t)), lo=1200, hi=6000) * np.exp(-t * 30)


def key_click():
    t = t_(0.03)
    return band(rng.standard_normal(len(t)), lo=2500, hi=9000) * np.exp(-t * 250) * 0.6


def pop(note, dur=0.18):
    t = t_(dur)
    f = hz(note) * (1 + 0.35 * np.exp(-t * 70))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + 0.2 * np.sin(2 * ph)) * np.exp(-t * 18)


def tick():
    t = t_(0.025)
    return np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 300)


def whoosh(dur, up=True):
    y = sweep_lp(rng.standard_normal(int(dur * SR)), 300 if up else 5000, 5000 if up else 300)
    k = np.linspace(0, 1, len(y))
    return y * np.sin(np.pi * k) ** 2


def bell(note, dur=2.0):
    t = t_(dur)
    f = hz(note)
    return np.sin(2 * np.pi * f * t + 2.2 * np.exp(-t * 5) * np.sin(2 * np.pi * f * 3.5 * t)) * np.exp(-t * 2.5)


def boom(dur=1.2):
    t = t_(dur)
    f = 36 + 50 * np.exp(-t * 10)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.5)
    air = band(rng.standard_normal(len(t)), lo=3000) * np.exp(-t * 4) * 0.15
    return np.tanh((sub + air) * 1.3)


# ------------------------------------------------------------------ harmony
CHORDS = [(41, [57, 60, 64, 65]), (45, [57, 60, 64, 67]), (38, [57, 60, 62, 65]), (48, [55, 60, 64, 67])]  # Fmaj7 Am7 Dm7 C
t = np.arange(N) / SR
pad = np.zeros(N)
bright = np.interp(t, [0, 3, 3.01, 25.5, DUR], [1.2, 0.7, 0.8, 0.6, 0.5])
nbars = int(np.ceil(DUR / BAR))
for bar in range(nbars):
    notes = CHORDS[bar % 4][1]
    a = bar * BAR
    i, j = int(a * SR), min(N, int((a + BAR + 0.05) * SR))
    tt = t[i:j] - a
    env = np.minimum(1, tt / 0.08) * np.minimum(1, (BAR + 0.05 - tt) / 0.08)
    seg = np.zeros(j - i)
    for n in notes:
        for det in (-0.08, 0.08):
            f = hz(n + det)
            for k in range(1, 7):
                seg += np.sin(2 * np.pi * f * k * tt + det * k * 11) / k * np.exp(-(k - 1) * bright[i:j])
    pad[i:j] += seg * env
pad *= 0.03
mix += pad[:, None]
send += pad[:, None] * 0.5

# drums + bass: groove from the prompt scene to the outro
K, HT, SN = kick(), hat(), snap()
duck = np.ones(N)
beat = 3.0
while beat < 25.5 - 1e-6:
    place(K, beat, 0.7)
    i = int(beat * SR)
    d = np.arange(min(N - i, int(B * SR))) / SR
    duck[i:i + len(d)] = np.minimum(duck[i:i + len(d)], 1 - 0.7 * np.exp(-d * 10))
    place(HT, beat + B / 2, 0.35, pan=0.3)
    if beat >= 7.0 and round((beat - 3.0) / B) % 2 == 1:
        place(SN, beat, 0.3, rev=0.3)
    beat += B
bass = np.zeros(N)
for bar in range(1, 13):
    root = CHORDS[bar % 4][0]
    for e in range(4):
        a = bar * BAR + e * B + B / 2  # off-beat bass
        if a < 3.0 or a >= 25.5:
            continue
        tt = t_(B / 2)
        sig = tone(hz(root + 12), tt, 10, 0.55) * np.exp(-tt * 6) * np.minimum(1, tt / 0.004)
        i = int(a * SR)
        bass[i:i + len(sig)] += sig[: max(0, min(len(sig), N - i))]
mix += (np.tanh(bass * 1.3) * 0.22 * duck)[:, None]

# ------------------------------------------------------------------ UI sound design
# hook: a hit per headline line, swoosh on the wipe
for at, n in ((0.05, 72), (0.35, 65), (1.0, 69), (1.5, 72)):
    place(pop(n, 0.3), at, 0.35, rev=0.4)
place(boom(), 1.5, 0.5, rev=0.2)
place(whoosh(0.5), 2.5, 0.45)
# prompt: typing, send, loader
msg_len = 68
for c in range(msg_len):
    place(key_click(), 3.55 + c * (2.05 / msg_len) + rng.uniform(-0.008, 0.008), 0.25, pan=rng.uniform(-0.3, 0.3))
place(pop(79, 0.25), 5.85, 0.4, rev=0.3)
place(whoosh(0.35), 5.88, 0.3)
for i in range(4):
    place(pop(84 + (0, 3, 7, 10)[i], 0.15), 6.05 + i * 0.22, 0.12, pan=(i - 1.5) / 2, rev=0.5)
# build: card morph, tiles, bars, line draw
place(whoosh(0.5), 6.95, 0.35)
for i in range(3):
    place(pop(72 + i * 4), 7.65 + i * 0.12, 0.3, pan=(i - 1) / 2, rev=0.3)
for i in range(4):
    place(pop(84 - i * 2, 0.1), 8.2 + i * 0.1, 0.15, pan=(i - 1.5) / 3)
for i in range(16):
    place(tick(), 8.6 + i * 0.075, 0.12, pan=-0.6 + i * 0.08)
place(bell(81, 1.2), 9.8, 0.12, rev=0.5)
# connectors: zoom out, chips pop in, data pulses
place(whoosh(0.6), 11.5, 0.35)
for i in range(7):
    place(pop(76 + (0, 2, 4, 7, 9, 12, 14)[i], 0.14), 11.95 + i * 0.09, 0.22, pan=(i - 3) / 4, rev=0.3)
place(whoosh(0.6), 14.4, 0.3)
# live: clock fast-forward ticks, refresh chime
for i in range(20):
    place(tick(), 15.3 + i * 0.05, 0.1, pan=0.4)
place(bell(84, 1.4), 16.3, 0.15, rev=0.5)
place(pop(88, 0.2), 16.3, 0.2)
# inspect: tap, sheet up, code lines, explain, answer
place(pop(67, 0.12), 19.15, 0.35)
place(whoosh(0.4), 19.35, 0.3)
for i in range(5):
    place(tick(), 19.8 + i * 0.1, 0.15)
place(pop(74, 0.12), 20.75, 0.3)
for c in range(30):
    place(key_click(), 20.9 + c * 0.023, 0.1)
place(whoosh(0.35, up=False), 21.85, 0.25)
# share: tap, viewers arrive
place(pop(72, 0.15), 22.7, 0.35)
for i in range(3):
    place(pop(79 + i * 3, 0.2), 23.0 + i * 0.12, 0.25, pan=(i - 1) / 1.5, rev=0.4)
# outro: hit + chord + chime
place(boom(1.6), 25.5, 0.6, rev=0.3)
for i, n in enumerate((65, 72, 76, 81)):
    place(bell(n, 2.4), 25.6 + i * 0.07, 0.12, pan=(i - 1.5) / 2, rev=0.6)

# ------------------------------------------------------------------ reverb + master
ir_len = int(1.4 * SR)
ti = np.arange(ir_len) / SR
L = N + ir_len
for c in range(2):
    ir = band(rng.standard_normal(ir_len) * np.exp(-ti / 0.3), hi=7000)
    ir /= np.sqrt((ir ** 2).sum())
    mix[:, c] += np.fft.irfft(np.fft.rfft(send[:, c], L) * np.fft.rfft(ir, L), L)[:N] * 0.5
for c in range(2):
    mix[:, c] = band(mix[:, c], lo=25)
mix = np.tanh(mix * 1.1)
mix /= np.abs(mix).max() / 0.89
fade = np.ones(N)
fade[:480] = np.linspace(0, 1, 480)
fade[-int(0.5 * SR):] = np.linspace(1, 0, int(0.5 * SR)) ** 1.5
mix *= fade[:, None]

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(out, exist_ok=True)
with wave.open(os.path.join(out, 'soundtrack.wav'), 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes())
print(f'wrote out/soundtrack.wav {N / SR:.2f}s')

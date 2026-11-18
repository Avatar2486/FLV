"""
FLV sound library: every sound effect and score bed is synthesised from scratch with numpy,
so there is nothing to license. 48 kHz mono float arrays in -1..1.

    from sound_library import RATE, sfx, music
    sfx("heart_single")              # one lub-dub
    music("drone_night", t0, seconds)   # score bed starting at absolute time t0 (continuous across cuts)
"""
import numpy as np

RATE = 48000
_rng = np.random.default_rng(7)


# ------------------------------------------------------------------ building blocks
def t_axis(seconds, t0=0.0):
    return t0 + np.arange(int(seconds * RATE)) / RATE


def env(seconds, attack=0.005, decay=0.2, hold=0.0):
    t = t_axis(seconds)
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    d = np.where(t < attack + hold, 1.0, np.exp(-(t - attack - hold) / max(decay, 1e-4)))
    return a * d


def noise(seconds):
    return _rng.standard_normal(int(seconds * RATE))


def band(x, lo=None, hi=None):
    """FFT band filter (brick-wall with soft edges)."""
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / RATE)
    mask = np.ones_like(f)
    if lo:
        mask *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    if hi:
        mask *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(spec * mask, len(x))


def reverb(x, seconds=1.2, mix=0.3, bright=4000):
    ir = band(noise(seconds), hi=bright) * np.exp(-t_axis(seconds) * 6 / seconds)
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    n = len(x) + len(ir)
    wet = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)
    out = np.zeros(n)
    out[:len(x)] += x * (1 - mix)
    return out + wet * mix


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak


def sine(freq, seconds, t0=0.0):
    return np.sin(2 * np.pi * freq * t_axis(seconds, t0))


def place(dst, src, start):
    s = int(start * RATE)
    if s >= len(dst) or s + len(src) <= 0:
        return dst
    a, b = max(0, s), min(len(dst), s + len(src))
    dst[a:b] += src[a - s:b - s]
    return dst


def layer(*parts):
    """Sum sounds of different lengths (shorter ones are padded with silence)."""
    out = np.zeros(max(len(x) for x in parts))
    for x in parts:
        out[:len(x)] += x
    return out


def series(make, times, seconds):
    out = np.zeros(int(seconds * RATE))
    for t in times:
        place(out, make(), t)
    return out


# ------------------------------------------------------------------ effects
def heart(muffled=False):
    def thump(f, amp):
        n = 0.22
        body = sine(f, n) * env(n, 0.004, 0.06) + sine(f * 0.5, n) * env(n, 0.006, 0.09) * 0.7
        return amp * (body + band(noise(n), hi=180) * env(n, 0.002, 0.03) * 0.4)
    x = np.zeros(int(0.5 * RATE))
    place(x, thump(62, 1.0), 0)
    place(x, thump(52, 0.75), 0.17)
    return norm(band(x, hi=110 if muffled else 400), 0.95)


def tick(freq=3200, decay=0.004):
    n = 0.03
    return norm(band(noise(n), lo=1500) * env(n, 0.0005, decay) + sine(freq, n) * env(n, 0.0005, decay) * 0.5)


def tock():
    n = 0.08
    return norm(band(noise(n), lo=400, hi=3000) * env(n, 0.001, 0.012) + sine(900, n) * env(n, 0.001, 0.02))


def bell(fundamental=220, seconds=4.0, bright=1.0):
    partials = [(0.5, 0.6), (1, 1.0), (1.19, 0.5), (1.56, 0.35), (2.0, 0.4), (2.66, 0.25 * bright), (3.01, 0.2 * bright)]
    x = sum(a * sine(fundamental * r, seconds) * env(seconds, 0.003, seconds / (1.5 + 2 * r)) for r, a in partials)
    return norm(reverb(x, 2.5, 0.35))


def creak(seconds=1.4, base=180, spread=140):
    t = t_axis(seconds)
    f = base + spread * np.sin(2 * np.pi * 0.7 * t) + 40 * np.sin(2 * np.pi * 7 * t)
    phase = 2 * np.pi * np.cumsum(f) / RATE
    saw = 2 * ((phase / (2 * np.pi)) % 1) - 1
    grain = (np.sin(2 * np.pi * 31 * t) > 0.2) * 0.6 + 0.4
    x = band(saw * grain, lo=300, hi=2500) * env(seconds, 0.1, seconds * 0.6, seconds * 0.3)
    return norm(reverb(x, 0.6, 0.2))


def squeal(seconds=0.8, f0=1500, f1=900):
    t = t_axis(seconds)
    f = f0 + (f1 - f0) * t / seconds + 30 * np.sin(2 * np.pi * 23 * t)
    phase = 2 * np.pi * np.cumsum(f) / RATE
    x = np.sin(phase) + 0.4 * np.sin(2 * phase) + 0.2 * band(noise(seconds), lo=2000)
    return norm(x * env(seconds, 0.05, seconds * 0.5, seconds * 0.3))


def thud(f=70, seconds=0.5, click=0.4):
    body = sine(f, seconds) * env(seconds, 0.003, 0.09) + sine(f * 1.6, seconds) * env(seconds, 0.003, 0.05) * 0.4
    return norm(body + band(noise(seconds), lo=200, hi=3000) * env(seconds, 0.001, 0.015) * click)


def scrape(seconds=2.0, lo=300, hi=3500, chatter=18):
    t = t_axis(seconds)
    grain = 0.55 + 0.45 * np.sign(np.sin(2 * np.pi * chatter * t + 3 * np.sin(2 * np.pi * 1.3 * t)))
    return norm(band(noise(seconds), lo=lo, hi=hi) * grain * env(seconds, 0.05, seconds * 0.4, seconds * 0.5))


def clinks(times, seconds, base=2600):
    def one():
        n = 0.25
        return sum(a * sine(base * r, n) * env(n, 0.0005, 0.05 / r) for r, a in ((1, 1), (1.58, 0.6), (2.37, 0.4)))
    return norm(series(one, times, seconds))


def steps(count, spacing=0.55, heavy=1.0):
    seconds = count * spacing + 0.6
    return norm(series(lambda: thud(85 - 20 * heavy, 0.35, 0.5 * heavy) * (0.85 + 0.3 * _rng.random()),
                       [i * spacing + _rng.uniform(-0.03, 0.03) for i in range(count)], seconds))


def voice_burst(f=180, seconds=0.7, formants=(700, 1200), glide=0.0, rough=0.3):
    t = t_axis(seconds)
    freq = f * (1 + glide * t / seconds) * (1 + 0.02 * np.sin(2 * np.pi * 6 * t))
    phase = 2 * np.pi * np.cumsum(freq) / RATE
    saw = 2 * ((phase / (2 * np.pi)) % 1) - 1
    x = sum(band(saw, lo=fm * 0.7, hi=fm * 1.3) for fm in formants) + rough * band(noise(seconds), lo=800, hi=5000)
    return norm(x * env(seconds, 0.02, seconds * 0.5, seconds * 0.35))


def wind(seconds, t0=0.0):
    t = t_axis(seconds, t0)
    swell = 0.55 + 0.45 * np.sin(2 * np.pi * 0.11 * t + 1.3) * np.sin(2 * np.pi * 0.037 * t)
    return norm(band(noise(seconds), lo=120, hi=900) * swell) * 0.8


def chirp():
    n = 0.35
    x = np.zeros(int(n * RATE))
    for k in range(3):
        m = 0.05
        place(x, sine(4600, m) * env(m, 0.005, 0.02) * (np.sin(2 * np.pi * 60 * t_axis(m)) > 0), k * 0.08)
    return norm(x)


def scratch(seconds=1.6):
    return norm(series(lambda: band(noise(0.04), lo=2500, hi=8000) * env(0.04, 0.001, 0.01),
                       sorted(_rng.uniform(0, seconds - 0.1, 22)), seconds)) * 0.7


def ringing(seconds=6.0):
    t = t_axis(seconds)
    return norm((sine(7400, seconds) + 0.4 * sine(3150, seconds)) * np.clip(t / 2.5, 0, 1)) * 0.5


def sting(low=True, seconds=3.0):
    t = t_axis(seconds)
    if low:
        f = 41 + 14 * t / seconds
        phase = 2 * np.pi * np.cumsum(f) / RATE
        x = band(2 * ((phase / (2 * np.pi)) % 1) - 1, hi=400) + 0.5 * np.sin(phase * 2)
    else:
        x = sine(1200, seconds) + sine(1271, seconds) + sine(1349, seconds) + 0.4 * band(noise(seconds), lo=3000)
    return norm(reverb(x * np.clip(t / (seconds * 0.6), 0, 1) * env(seconds, 0.01, 0.6, seconds * 0.65), 2.0, 0.4))


_FX = {
    "heart_single": lambda: heart(),
    "boom": lambda: norm(reverb(sine(40, 4) * env(4, 0.01, 1.2) + band(noise(4), hi=300) * env(4, 0.005, 0.4), 3, 0.5)),
    "cricket": lambda: series(chirp, [0, 0.6], 1.2),
    "mouse": lambda: scratch(),
    "wind_gust": lambda: wind(3.5) * env(3.5, 1.2, 1.5, 0.6),
    "cup_clink": lambda: clinks([0, 0.12], 0.6),
    "cup_rattle": lambda: clinks(sorted(_rng.uniform(0, 1.3, 9)), 1.6, 3100) * 0.6,
    "steps_wood": lambda: steps(8, 0.6),
    "steps_group": lambda: norm(steps(9, 0.5) + np.pad(steps(8, 0.57), (int(0.21 * RATE), 0))[:len(steps(9, 0.5))]),
    "steps_heavy": lambda: steps(10, 0.7, heavy=1.6),
    "coin": lambda: clinks([0, 0.09, 0.15, 0.31], 0.9, 3900),
    "sting_low": lambda: sting(True, 3.5),
    "sting_high": lambda: sting(False, 2.5),
    "door_creak_soft": lambda: creak(2.0, 160, 90) * 0.7,
    "watch_tick_loud": lambda: series(lambda: tick(4200, 0.003), [i * 0.2 for i in range(30)], 6.0),
    "latch": lambda: norm(series(lambda: tick(2100, 0.008), [0, 0.18, 0.21], 0.5)),
    "hinge_tiny": lambda: squeal(0.35, 2400, 1800) * 0.5,
    "clock_chime": lambda: bell(660, 3.0, 1.2) * 0.6,
    "clock_strike": lambda: bell(330, 3.5),
    "bell_toll": lambda: bell(110, 7.0, 0.7),
    "chuckle": lambda: norm(series(lambda: voice_burst(140, 0.12, (500, 1500), 0, 0.8), [0, 0.2, 0.38], 0.7)) * 0.5,
    "bed_creak": lambda: creak(0.9, 110, 60),
    "clink": lambda: clinks([0], 0.4, 2900),
    "deathwatch": lambda: series(lambda: tick(1600, 0.006), [i * 0.085 for i in range(6)], 0.7),
    "groan": lambda: voice_burst(92, 2.2, (450, 900), -0.15, 0.25) * 0.7,
    "lantern_open": lambda: norm(clinks([0], 0.6, 1800) + band(noise(0.6), lo=500, hi=4000) * env(0.6, 0.01, 0.15)),
    "yell": lambda: voice_burst(190, 0.9, (750, 1250, 2500), 0.25, 0.5),
    "shriek": lambda: voice_burst(520, 1.0, (1100, 2300, 3400), 0.35, 0.4),
    "bed_drag": lambda: norm(scrape(2.2, 120, 900, 9) + np.pad(thud(45, 1.0, 0.8), (int(2.0 * RATE), 0))[:int(2.2 * RATE)]),
    "work_muffled": lambda: band(series(lambda: thud(60, 0.4, 0.3), [0, 0.9, 1.5, 2.6, 3.1], 3.6), hi=500),
    "nail_squeal": lambda: squeal(0.9),
    "hammer_muffled": lambda: band(thud(70, 0.4, 0.6), hi=700),
    "knock3": lambda: norm(reverb(series(lambda: thud(110, 0.3, 0.9), [0, 0.38, 0.76], 1.2), 1.0, 0.35)),
    "door_open": lambda: norm(layer(creak(1.6, 140, 80), tick(2000, 0.01))),
    "chair_place": lambda: norm(thud(95, 0.4, 0.7) + scrape(0.4, 400, 3000, 30) * 0.3),
    "ringing": lambda: ringing(),
    "laugh_group": lambda: norm(layer(*[series(lambda f=f: voice_burst(f, 0.13, (650, 1100), 0, 0.6),
                                               [d + i * 0.19 for i in range(5)], 1.6)
                                        for f, d in ((130, 0.0), (165, 0.07), (115, 0.12))])) * 0.6,
    "chair_scrape": lambda: scrape(2.6, 250, 4500, 22),
    "stomp": lambda: thud(48, 0.8, 1.0),
}


def sfx(name):
    return _FX[name]().astype(np.float32)


def loop(name, seconds, t0=0.0):
    """Sounds that run under a whole shot."""
    if name == "wind_loop":
        return wind(seconds, t0).astype(np.float32)
    if name == "watch_tick_loop":
        return series(lambda: tick(4200, 0.003) * 0.6, np.arange(0, seconds, 0.2), seconds).astype(np.float32)
    if name == "clock_tick_loop":
        return series(tock, np.arange(0, seconds, 1.0), seconds).astype(np.float32)
    if name == "clock_tick_fast":
        return series(tock, np.arange(0, seconds, 0.125), seconds).astype(np.float32)
    if name == "deathwatch_loop":
        times = [g + i * 0.085 for g in np.arange(0.5, seconds, 2.3) for i in range(5)]
        return (series(lambda: tick(1600, 0.006), times, seconds) * 0.6).astype(np.float32)
    raise KeyError(name)


LOOPS = {"wind_loop", "watch_tick_loop", "clock_tick_loop", "clock_tick_fast", "deathwatch_loop"}


# ------------------------------------------------------------------ score
def music(cue, t0, seconds):
    """Score bed from absolute time t0, so the same cue continues seamlessly across cuts."""
    n = int(seconds * RATE)
    if cue == "silence" or n == 0:
        return np.zeros(n, np.float32)
    t = t_axis(seconds, t0)
    slow = 0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t)
    if cue == "drone_low":
        x = (np.sin(2 * np.pi * 55 * t) + np.sin(2 * np.pi * 55.35 * t) + 0.5 * np.sin(2 * np.pi * 110.2 * t)) * slow
        x += 0.15 * np.sin(2 * np.pi * 164.8 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * t))
        level = 0.16
    elif cue == "drone_night":
        x = (np.sin(2 * np.pi * 49 * t) + np.sin(2 * np.pi * 49.3 * t)) * slow
        x += 0.06 * (np.sin(2 * np.pi * 1046.5 * t) + np.sin(2 * np.pi * 1108.7 * t)) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.03 * t))
        level = 0.17
    elif cue == "drone_rise":
        x = (np.sin(2 * np.pi * 55 * t) + np.sin(2 * np.pi * 58.27 * t) + 0.4 * np.sin(2 * np.pi * 116.5 * t)) * slow
        level = 0.2
    elif cue == "drone_tension":
        pulse = 0.7 + 0.3 * np.sin(2 * np.pi * 0.9 * t) ** 8
        x = (np.sin(2 * np.pi * 55 * t) + 0.7 * np.sin(2 * np.pi * 77.78 * t) + 0.5 * np.sin(2 * np.pi * 82.4 * t)) * pulse
        x += 0.05 * np.sin(2 * np.pi * 1318.5 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.2 * t))
        level = 0.2
    else:
        raise KeyError(cue)
    return (x * level).astype(np.float32)

"""Bande-son synthétisée de l'épisode 1 (musique d'ambiance + bruitages), calée sur la voix."""
import os, sys, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
from timeline import Words

SR = 48000
WD = Words(os.path.join(HERE, "audio", "words.json"))
T = WD.at
DUR = WD.end + 2.0
rng = np.random.default_rng(617)
N = int(DUR * SR)
L = np.zeros(N, np.float32)
R = np.zeros(N, np.float32)


def tt(d):
    return np.arange(int(d * SR), dtype=np.float32) / SR


def band(x, lo=None, hi=None):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if lo:
        m *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    if hi:
        m *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * m, len(x)).astype(np.float32)


def env(n, a=0.005, r=0.2):
    e = np.ones(n, np.float32)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr and nr < n:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def put(sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N:
        return
    s = sig[: N - i] * gain
    L[i:i + len(s)] += s * (1 - max(0, pan))
    R[i:i + len(s)] += s * (1 + min(0, pan))


def noise(d):
    return rng.standard_normal(int(d * SR)).astype(np.float32)


def brown(d):
    b = np.cumsum(noise(d)) / 50
    return band(b - b.mean(), lo=20)


# ---------------------------------------------------------------- éléments
def boom(d=2.2, f0=90, f1=28):
    t = tt(d)
    f = f1 + (f0 - f1) * np.exp(-t * 6)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 2.2)
    s += band(noise(d), hi=400) * np.exp(-t * 18) * 0.5
    return s * env(len(t), 0.002, 0.3)


def stinger(d=3.0):
    t = tt(d)
    s = np.zeros_like(t)
    for f in (207.6, 220.0, 311.1, 329.6, 466.2, 493.9):
        saw = 2 * ((t * f) % 1) - 1
        s += band(saw, hi=2500) * 0.12
    s *= np.exp(-t * 1.3)
    return s * env(len(t), 0.01, 0.4) + boom(d) * 0.8


def riser(d=2.0):
    t = tt(d)
    k = t / d
    n = noise(d)
    out = band(n, lo=300, hi=6000) * (k ** 2.5) * 0.5
    f = 80 + 600 * k ** 2
    out += np.sin(2 * np.pi * np.cumsum(f) / SR) * k ** 2 * 0.25
    return out


def whoosh(d=0.6):
    t = tt(d)
    return band(noise(d), lo=400, hi=5000) * np.sin(np.pi * t / d) ** 2 * 0.5


def heartbeat(bpm):
    def thump(f=48, d=0.18):
        t = tt(d)
        return np.sin(2 * np.pi * f * t) * np.exp(-t * 26) + band(noise(d), hi=200) * np.exp(-t * 60) * 0.3
    s = np.zeros(int(60 / bpm * SR), np.float32)
    a = thump()
    s[:len(a)] += a
    b = thump(44) * 0.7
    o = int(0.24 * SR)
    s[o:o + len(b)] += b[:len(s) - o]
    return s


def knock():
    d = 0.25
    t = tt(d)
    s = np.sin(2 * np.pi * 140 * t) * np.exp(-t * 35) * 0.9
    for f, k in ((1850, 60), (2650, 80), (980, 50)):
        s += np.sin(2 * np.pi * f * t) * np.exp(-t * k) * 0.18
    s += band(noise(d), lo=800, hi=6000) * np.exp(-t * 120) * 0.4
    return s


def buzz(d=0.42):
    t = tt(d)
    sq = np.sign(np.sin(2 * np.pi * 172 * t)) * 0.5 + np.sin(2 * np.pi * 344 * t) * 0.3
    return band(sq, hi=1800) * env(len(t), 0.01, 0.05) * (0.8 + 0.2 * np.sin(2 * np.pi * 9 * t))


def creak(d=2.8):
    """Grincement métal (frottement saccadé) de la poignée qui tourne lentement."""
    n = int(d * SR)
    s = np.zeros(n, np.float32)
    t = 0.0
    while t < d - 0.05:
        rate = 34 + 26 * np.sin(t * 2.1) + rng.uniform(-6, 6)
        i = int(t * SR)
        s[i] += rng.uniform(0.6, 1.0)
        t += 1 / rate
    out = np.zeros(n, np.float32)
    for f, q in ((920, 90), (1730, 120), (2640, 160)):
        k = tt(0.05)
        ir = np.sin(2 * np.pi * f * k) * np.exp(-k * q)
        out += np.convolve(s, ir, "same").astype(np.float32)
    out *= env(n, 0.2, 0.3) * 0.5
    c = knock() * 0.25  # clic du pêne
    out[-len(c):] += c
    return out


def ding():
    d = 1.6
    t = tt(d)
    s = np.zeros_like(t)
    for f0, t0 in ((659.3, 0.0), (523.3, 0.42)):
        i = int(t0 * SR)
        k = t[: len(t) - i]
        s[i:] += (np.sin(2 * np.pi * f0 * k) + 0.3 * np.sin(2 * np.pi * f0 * 2.01 * k)) * np.exp(-k * 3.2) * 0.35
    return s


def rewind(d=1.0):
    t = tt(d)
    f = 3000 - 2200 * (t / d)
    s = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.3 * np.sin(2 * np.pi * 23 * t))) / SR) * 0.15
    s += band(noise(d), lo=1500, hi=9000) * 0.25
    return s * env(len(t), 0.02, 0.1)


def step():
    d = 0.12
    t = tt(d)
    return band(noise(d), lo=120, hi=2500) * np.exp(-t * 45) + np.sin(2 * np.pi * 70 * t) * np.exp(-t * 40) * 0.6


def tick():
    d = 0.06
    t = tt(d)
    return band(noise(d), lo=2000, hi=8000) * np.exp(-t * 160) * 0.6 + np.sin(2 * np.pi * 1500 * t) * np.exp(-t * 120) * 0.2


# ---------------------------------------------------------------- partition
t_rw, t_en, t_frz = T("mais", 1), T("en"), T("immobilisés")
t_30, t_noirs, t_dir = T("trente"), T("noirs"), T("et", 2)
t_shop, t_cest, t_thomas1 = T("emma", 3), T("c'est"), T("thomas", 1)
t_pourtant, t_th2, t_soudain = T("pourtant"), T("thomas", 2), T("soudain")
t_msg, t_emma4, t_poign, t_deux = T("message"), T("emma", 4), T("poignée"), T("deux")
t_q, t_end = T("et", 3), WD.end

# 1) Drone continu (nappe grave) avec intensité qui évolue
t = tt(DUR)
drone = (np.sin(2 * np.pi * 43.65 * t) * 0.5 + np.sin(2 * np.pi * 43.9 * t) * 0.4 + np.sin(2 * np.pi * 65.4 * t) * 0.25
         + np.sin(2 * np.pi * 87.3 * t + np.sin(t * 0.3) * 2) * 0.12)
drone += band(brown(DUR), hi=180) * 0.6
inten = np.interp(t, [0, 5, t_rw, t_en, t_frz, t_30, t_noirs, t_cest, t_pourtant, t_th2, t_emma4, t_deux, t_q, DUR],
                  [0.5, 0.45, 0.3, 0.25, 0.55, 0.65, 0.9, 0.7, 0.35, 0.7, 0.8, 1.0, 0.55, 0.4]).astype(np.float32)
put(drone * inten * 0.32, 0)
# nappe aiguë dissonante qui monte
pad = (np.sin(2 * np.pi * 622.3 * t) + np.sin(2 * np.pi * 659.3 * t)) * 0.03
pad_env = np.interp(t, [0, t_noirs - 2, t_noirs, t_shop, t_emma4, t_deux, t_deux + 2, DUR], [0, 0, 0.6, 0.2, 0.5, 1.0, 0.2, 0.15]).astype(np.float32)
put(pad * pad_env, 0, pan=0.2)

# 2) Ouverture : coups sur la vitre + impact titre
put(boom(), 0.05, 0.9)
for k in (0.30, 0.62, 0.94, 2.4, 2.72):
    put(knock(), k, 0.8, pan=0.15)

# 3) Rembobinage + ville vivante, puis gel brutal + acouphène
put(rewind(), t_rw, 0.7)
amb_d = t_frz - t_rw
amb = band(brown(amb_d), hi=400) * 1.2 + band(noise(amb_d), lo=500, hi=3000) * 0.04
for c in np.arange(0.5, amb_d - 1, 1.7):  # voitures qui passent
    w = whoosh(1.6) * 0.6
    i = int(c * SR)
    amb[i:i + len(w)] += w[: len(amb) - i]
amb *= env(len(amb), 0.6, 0.02)
put(amb * 0.5, t_rw + 0.6)
put(boom(1.8, 60, 25), t_frz, 0.8)
ring = np.sin(2 * np.pi * 7400 * tt(5)) * np.exp(-tt(5) * 0.6) * 0.035
put(ring, t_frz, pan=-0.1)

# 4) Cœur qui bat pendant la marche d'Emma et Adam, accélère à la reprise
tb = T("seules")
while tb < t_noirs:
    bpm = 72 if tb < t_30 else 72 + (tb - t_30) * 14
    hb = heartbeat(bpm)
    put(hb, tb, 0.55)
    tb += 60 / bpm
put(riser(t_noirs - (t_30 + 1.0)), t_30 + 1.0, 0.6)
put(stinger(), t_noirs - 0.05, 0.75)
put(whoosh(0.8), t_dir - 0.4, 0.6)
put(boom(2.5, 70, 30), t_dir, 0.5)

# 5) Course vers la supérette, carillon de la porte
for k in np.arange(t_shop + 0.1, t_cest - 0.7, 0.27):
    put(step(), k, 0.35, pan=np.clip((k - t_shop) / 3 - 0.5, -0.6, 0.6))
put(ding(), t_cest - 0.6, 0.45)

# 6) Thomas frappe à la vitre
for k in [T("frappé") + i * 0.32 for i in range(3)] + [T("demandait") + i * 0.3 for i in range(3)] + [T("d'ouvrir") + 0.5 + i * 0.3 for i in range(2)]:
    put(knock(), k, 0.9, pan=0.1)
put(stinger(2.5), t_thomas1 - 0.05, 0.55)

# 7) Flash-back cimetière : pluie
rain = band(noise(t_th2 - t_pourtant), lo=1500, hi=9000) * 0.12
put(rain * env(len(rain), 0.3, 0.3), t_pourtant)
put(whoosh(0.7), t_pourtant - 0.35, 0.5)

# 8) Téléphone
tb = T("vibré") - 0.6
put(buzz(), tb, 0.8)
put(buzz(), tb + 0.75, 0.8)
put(tick() * 2, t_msg - 0.15, 0.6)

# 9) Réserve : néon qui grésille, grincement de la poignée
hum_d = t_deux - t_emma4
th = tt(hum_d)
hum = (np.sin(2 * np.pi * 100 * th) * 0.4 + np.sin(2 * np.pi * 200 * th) * 0.2 + np.sign(np.sin(2 * np.pi * 100 * th)) * 0.05)
hum *= (0.6 + 0.4 * (rng.random(len(th)) > 0.002)).astype(np.float32)
put(hum * env(len(th), 0.3, 0.1) * 0.06, t_emma4)
put(creak(t_deux - t_poign - 0.15), t_poign, 0.7, pan=0.1)
put(riser(t_deux - t_poign), t_poign, 0.5)

# 10) « Deux Thomas » : impact, puis tic-tac pendant la question
put(stinger(3.5), t_deux - 0.03, 1.0)
for k in np.arange(t_q, t_end + 1.5, 1.0):
    put(tick(), k, 0.7)
put(boom(2.0), t_end - 0.4, 0.7)

mix = np.stack([L, R], -1)
mix /= max(1e-6, np.abs(mix).max()) / 0.9
out = os.path.join(HERE, "audio", "music_sfx.wav")
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("bande-son ->", out, f"{DUR:.1f}s")

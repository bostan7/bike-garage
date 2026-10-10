"""Synthesizes the game UI sounds as small WAV files (16-bit mono 44.1 kHz), no downloads.

They copy the WebAudio sounds of the approved prototype (design/prototype/template.html):
  whoosh    filtered noise, band-pass sweep 400 -> 2400 Hz, 0.35 s   (mode change)
  tick      1500 Hz square, 50 ms, quiet                           (menu move)
  confirm   two triangle notes 660 Hz then 990 Hz                  (hold-to-confirm done)
  hold      rising saw 300 -> 900 Hz, 0.6 s, quiet                  (while holding a button)
  light_on  low square thunk at 100 Hz, 0.28 s                      (intro light switching on;
            the app plays it at rate 0.8..1.2 to get the prototype's 80..120 Hz)

Run from anywhere (standard library only):
    python design/sounds/make_sounds.py
Output: android/app/src/main/res/raw/<name>.wav
"""
import math
import os
import random
import struct
import wave

RATE = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "android", "app", "src", "main", "res", "raw")


def env_exp(t, dur, start=1.0, end=0.0001, attack=0.003):
    """WebAudio-style exponential ramp to ~0 over `dur`, with a tiny linear attack against clicks."""
    if t >= dur:
        return 0.0
    g = start * (end / start) ** (t / dur)
    if t < attack:
        g *= t / attack
    return g


def osc(kind, phase, freq):
    """Band-limited oscillator (additive) so high notes don't alias. `phase` in cycles."""
    nyq = RATE / 2
    if kind == "sine":
        return math.sin(2 * math.pi * phase)
    harmonics = max(1, int(nyq / max(freq, 1)))
    s = 0.0
    if kind == "square":
        for k in range(1, harmonics + 1, 2):
            s += math.sin(2 * math.pi * k * phase) / k
        return s * 4 / math.pi
    if kind == "saw":
        for k in range(1, harmonics + 1):
            s += math.sin(2 * math.pi * k * phase) / k * (-1) ** (k + 1)
        return s * 2 / math.pi
    if kind == "triangle":
        for i, k in enumerate(range(1, harmonics + 1, 2)):
            s += (-1) ** i * math.sin(2 * math.pi * k * phase) / (k * k)
        return s * 8 / (math.pi ** 2)
    raise ValueError(kind)


def tone(freq, dur, kind, vol, slide=None):
    """Like the prototype's tone(): optional exponential frequency slide, exponential gain decay."""
    n = int(dur * RATE)
    out, phase = [], 0.0
    for i in range(n):
        t = i / RATE
        f = freq * (slide / freq) ** (t / dur) if slide else freq
        phase += f / RATE
        out.append(osc(kind, phase, f) * env_exp(t, dur, vol))
    return out


def mix(a, b, offset_s):
    off = int(offset_s * RATE)
    out = a + [0.0] * max(0, off + len(b) - len(a))
    for i, v in enumerate(b):
        out[off + i] += v
    return out


def whoosh(dur=0.35, vol=0.9):
    """White noise fading linearly, through a band-pass (RBJ biquad, Q ~1) swept 400 -> 2400 Hz in 0.3 s."""
    rnd = random.Random(980)
    n = int(dur * RATE)
    x1 = x2 = y1 = y2 = 0.0
    q = 1.0
    out = []
    for i in range(n):
        t = i / RATE
        f0 = 400 * (2400 / 400) ** min(1.0, t / 0.3)
        w0 = 2 * math.pi * f0 / RATE
        alpha = math.sin(w0) / (2 * q)
        b0, b2 = alpha, -alpha
        a0, a1, a2 = 1 + alpha, -2 * math.cos(w0), 1 - alpha
        x = (rnd.random() * 2 - 1) * (1 - i / n)
        y = (b0 * x + b2 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1, y2, y1 = x1, x, y1, y
        out.append(y)
    peak = max(abs(v) for v in out) or 1
    fade = int(0.004 * RATE)
    return [v / peak * vol * (min(1, i / fade)) for i, v in enumerate(out)]


def save(name, samples):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v)) * 32767)) for v in samples))
    print(f"{name:9s} {len(samples) / RATE:5.2f} s  {os.path.getsize(path) / 1024:5.1f} kB")
    return os.path.getsize(path)


if __name__ == "__main__":
    # Levels follow the prototype's relative gains (tick 0.025, hold 0.02 quiet; confirm 0.07; thunk 0.05; whoosh 0.12),
    # scaled up so the loudest sound peaks near full scale. SoundPool plays them at volume 1.
    total = 0
    total += save("whoosh", whoosh(0.35, 0.85))
    total += save("tick", tone(1500, 0.05, "square", 0.28))
    total += save("confirm", mix(tone(660, 0.12, "triangle", 0.75), tone(990, 0.18, "triangle", 0.75), 0.09))
    total += save("hold", tone(300, 0.6, "saw", 0.22, slide=900))
    total += save("light_on", tone(100, 0.28, "square", 0.55))
    print(f"total     {total / 1024:.1f} kB")

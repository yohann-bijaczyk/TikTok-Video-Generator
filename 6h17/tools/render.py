"""Moteur de rendu des épisodes 6H17.

  python tools/render.py ep01                 -> rendu complet (build/video.mp4, sans son)
  python tools/render.py ep01 --stills 3,12.5 -> images de contrôle (build/stills/)
  python tools/render.py ep01 --from 30 --to 40

Conçu pour rester léger : 1 image en mémoire à la fois, encodage matériel
VideoToolbox (le CPU reste libre), décors mis en cache une seule fois.
"""
import argparse, importlib.util, math, os, random, subprocess, sys, time
import numpy as np
from PIL import Image, ImageDraw

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import gfx
from gfx import W, H, SW, SH, font, text_sprite, pill, ease_out

FPS = 30


def load_episode(ep_dir):
    sys.path.insert(0, ep_dir)
    spec = importlib.util.spec_from_file_location("episode", os.path.join(ep_dir, "episode.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- plans de remplacement (images / clips IA)
class StillSource:
    def __init__(self, path):
        im = Image.open(path).convert("RGB")
        s = max(SW / im.width, SH / im.height)
        im = im.resize((math.ceil(im.width * s), math.ceil(im.height * s)), Image.LANCZOS)
        x, y = (im.width - SW) // 2, (im.height - SH) // 2
        self.im = im.crop((x, y, x + SW, y + SH))

    def frame(self, t):
        return self.im


class ClipSource:
    """Lit un clip vidéo image par image via ffmpeg (aucun chargement complet en RAM)."""
    def __init__(self, path, t0):
        self.path, self.t0, self.proc, self.last, self.n = path, t0, None, None, 0

    def _open(self):
        vf = f"scale={SW}:{SH}:force_original_aspect_ratio=increase,crop={SW}:{SH},fps={FPS}"
        self.proc = subprocess.Popen(["ffmpeg", "-v", "error", "-threads", "2", "-i", self.path, "-vf", vf,
                                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)

    def frame(self, t):
        want = int((t - self.t0) * FPS)
        if self.proc is None:
            self._open()
        while self.n <= want:
            buf = self.proc.stdout.read(SW * SH * 3)
            if len(buf) < SW * SH * 3:  # fin du clip : on boucle
                self.proc.kill(); self._open(); continue
            self.last = Image.frombuffer("RGB", (SW, SH), buf)
            self.n += 1
        return self.last


def apply_overrides(ep_dir, scenes):
    sd = os.path.join(ep_dir, "scenes")
    for s in scenes:
        for ext in ("mp4", "mov", "jpg", "jpeg", "png", "webp"):
            p = os.path.join(sd, f"{s['id']}.{ext}")
            if os.path.exists(p):
                src = ClipSource(p, s["t"]) if ext in ("mp4", "mov") else StillSource(p)
                s["fn"] = src.frame
                s["override"] = p
                print(f"  ↳ {s['id']} remplacé par {os.path.basename(p)}")
                break


# ---------------------------------------------------------------- sous-titres
def build_chunks(words, maxw=2, maxc=12):
    out, cur = [], []
    for i, w in enumerate(words):
        txt = w["w"].replace("’", "'").upper().replace("6 H 17", "6H17")
        gap = w["s"] - words[i - 1]["e"] if i else 0
        if cur and (len(cur) >= maxw or sum(len(c["t"]) for c in cur) + len(txt) > maxc or gap > 0.22):
            out.append(cur); cur = []
        cur.append(dict(t=txt, s=w["s"], e=w["e"]))
    if cur:
        out.append(cur)
    chunks = []
    for i, c in enumerate(out):
        s, e = c[0]["s"], c[-1]["e"]
        nxt = out[i + 1][0]["s"] if i + 1 < len(out) else e + 0.6
        end = nxt if nxt - e < 0.5 else e + 0.3
        chunks.append(dict(words=[x["t"] for x in c], s=s, e=end))
    return chunks


class Captions:
    def __init__(self, chunks, keywords):
        self.chunks, self.kw, self.cache = chunks, keywords, {}
        self.f = font("impact", 138)

    def sprite(self, idx):
        if idx in self.cache:
            return self.cache[idx]
        parts = []
        for w in self.chunks[idx]["words"]:
            key = w.strip(",;:!?«»\"")
            red = key in self.kw or key.rstrip(".") in self.kw
            parts.append(text_sprite(w, self.f, fill=(255, 52, 46) if red else (255, 255, 255), stroke=10, shadow=9))
        gap = -44
        wd = sum(p.width for p in parts) + gap * (len(parts) - 1)
        hd = max(p.height for p in parts)
        im = Image.new("RGBA", (wd, hd), (0, 0, 0, 0))
        x = 0
        for p in parts:
            im.alpha_composite(p, (x, (hd - p.height) // 2)); x += p.width + gap
        if im.width > 860:
            s = 860 / im.width
            im = im.resize((860, int(im.height * s)), Image.LANCZOS)
        self.cache[idx] = im
        return im

    def draw(self, img, t, y):
        for i, c in enumerate(self.chunks):
            if c["s"] <= t < c["e"]:
                spr = self.sprite(i)
                dt = t - c["s"]
                sc = 1.0 + 0.16 * (1 - ease_out(dt / 0.12)) if dt < 0.12 else 1.0
                gfx.paste_center(img, spr, W / 2 - 20, y, scale=sc)
                return


# ---------------------------------------------------------------- HUD / titre / étiquettes
class Hud:
    def __init__(self, ep):
        self.ep, self.cache = ep, {}
        self.mono = font("mono", 44)
        self.small = font("mono", 30)
        b1 = text_sprite(ep.SERIES, font("impact", 54), fill=(255, 255, 255), pad=0)
        b2 = text_sprite(f"ÉPISODE {ep.EPISODE}", font("din", 46), fill=(255, 255, 255), pad=0)
        badge = Image.new("RGBA", (b1.width + b2.width + 70, 74), (0, 0, 0, 0))
        d = ImageDraw.Draw(badge)
        d.rectangle([0, 0, b1.width + 28, 73], fill=(220, 30, 30, 255))
        badge.alpha_composite(b1, (14, (74 - b1.height) // 2))
        d.rectangle([b1.width + 28, 0, badge.width - 1, 73], fill=(0, 0, 0, 170))
        badge.alpha_composite(b2, (b1.width + 48, (74 - b2.height) // 2 + 3))
        self.badge = badge

    def spr(self, key, fn):
        if key not in self.cache:
            self.cache[key] = fn()
        return self.cache[key]

    def draw(self, img, t, loc):
        clk = self.ep.story_clock(t)
        hh, mm, ss = int(clk // 3600), int(clk % 3600 // 60), int(clk % 60)
        txt = f"{hh:02d}:{mm:02d}:{ss:02d}"
        c = self.spr(("c", txt), lambda: text_sprite(txt, self.mono, fill=(240, 240, 240, 235), stroke=2, stroke_fill=(0, 0, 0, 160)))
        l = self.spr(("l", loc), lambda: text_sprite(loc, self.small, fill=(200, 200, 205, 220), stroke=2, stroke_fill=(0, 0, 0, 160))) if loc else None
        tw = c.width + (l.width + 20 if l else 0) + 34
        x = (W - tw) // 2 - 20
        d = ImageDraw.Draw(img)
        if int(t * 2) % 2 == 0:
            d.ellipse([x, 196, x + 20, 216], fill=(255, 40, 40))
        img.paste(c, (x + 34, 206 - c.height // 2), c)
        if l:
            img.paste(l, (x + 34 + c.width + 20, 208 - l.height // 2), l)
        if t > 2.8:
            a = min(1.0, (t - 2.8) / 0.4)
            gfx.paste_center(img, self.badge, W / 2 - 20, 290, alpha=a)


class Title:
    def __init__(self, ep):
        self.big = text_sprite(ep.SERIES, font("impact", 330), fill=(230, 30, 30), stroke=6, shadow=14)
        self.ep = text_sprite(f"É P I S O D E   {ep.EPISODE}", font("din", 74), fill=(255, 255, 255), stroke=3, shadow=6)
        self.sub = text_sprite(ep.EP_TITLE, font("din", 56), fill=(200, 200, 200), stroke=3, shadow=6)

    def draw(self, img, t):
        if t > 2.9:
            return
        a = min(1.0, t / 0.2) * (1 - max(0.0, (t - 2.55) / 0.35))
        jit = (random.uniform(-14, 14) if (t < 0.45 or 1.3 < t < 1.38) else 0)
        sc = 1.0 + 0.04 * t
        gfx.paste_center(img, self.big, W / 2 - 20 + jit, 600, alpha=a, scale=sc)
        gfx.paste_center(img, self.ep, W / 2 - 20, 820, alpha=a)
        gfx.paste_center(img, self.sub, W / 2 - 20, 900, alpha=a * 0.9)


class Tags:
    def __init__(self):
        self.cache = {}
        self.f = font("mono", 36)

    def draw(self, img, t, tags, s_end):
        for text, t0, (fx, fy) in tags or []:
            if t0 <= t < s_end:
                if text not in self.cache:
                    self.cache[text] = pill(text, self.f, bg=(255, 176, 32), fg=(10, 10, 10))
                dt = t - t0
                sc = 1.0 + 0.25 * (1 - ease_out(dt / 0.15)) if dt < 0.15 else 1.0
                gfx.paste_center(img, self.cache[text], fx * W, fy * H, scale=sc)


# ---------------------------------------------------------------- effets image
class FX:
    def __init__(self):
        rng = np.random.default_rng(1)
        n = gfx.smooth_noise((W + 800) // 4, H // 4, 70, seed=3)
        fog = Image.fromarray((n * 255).astype(np.uint8)).resize((W + 800, H), Image.BICUBIC)
        self.fog = np.asarray(fog)
        yy = np.linspace(0, 1, H, dtype=np.float32)
        self.fog_h = (0.35 + 0.65 * np.exp(-((yy - 0.62) / 0.3) ** 2))[:, None].astype(np.float32)
        self.fog_col = np.array([92, 102, 120], np.float32)
        yv, xv = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.hypot((xv - W / 2) / (W * 0.62), (yv - H * 0.5) / (H * 0.6))
        self.vig = np.clip(1 - 0.62 * r ** 2.4, 0.18, 1).astype(np.float32)[..., None]
        self.grain = [np.clip(rng.normal(0, 7.5, (H, W)), -24, 24).astype(np.float32)[..., None] for _ in range(4)]
        x = np.arange(256, dtype=np.float32) / 255
        s = x + 0.18 * (x - 0.5) * (1 - np.abs(2 * x - 1))  # courbe en S douce
        s = np.clip(s, 0, 1)
        self.lut = {
            "cold": np.stack([np.clip(255 * (s ** 1.12) * 0.90, 0, 255), np.clip(255 * (s ** 1.04) * 0.97, 0, 255),
                              np.clip(255 * s * 1.04 + 6, 0, 255)], -1).astype(np.uint8),
            "flashback": np.stack([np.clip(255 * s * 1.02 + 8, 0, 255), np.clip(255 * s * 0.98 + 6, 0, 255),
                                   np.clip(255 * s * 0.90, 0, 255)], -1).astype(np.uint8),
        }
        self.drift_seed = rng.random(6) * 10

    def process(self, img, t, frame_i, sc, glitch_k, cut_flash):
        a = np.asarray(img, dtype=np.float32)
        if sc.get("grade") == "flashback":
            g = a.mean(axis=2, keepdims=True)
            a = g + (a - g) * 0.12
            a = a * 1.08
        dens = sc.get("fog", 0.0)
        if dens > 0:
            off = int(t * 38) % 800
            fa = self.fog[:, off:off + W].astype(np.float32) * (dens / 255.0) * self.fog_h
            a += (self.fog_col - a) * fa[..., None]
        fl = 1.0
        fk = sc.get("flicker", 0.0)
        if fk and random.random() < 0.18:
            fl = 1 - fk * random.random()
        fl *= 1 + 0.55 * cut_flash
        a *= self.vig * fl
        a += self.grain[frame_i % 4]
        out = a.clip(0, 255).astype(np.uint8)
        lut = self.lut["flashback" if sc.get("grade") == "flashback" else "cold"]
        out = np.stack([lut[out[..., c], c] for c in range(3)], -1)
        if glitch_k > 0.01:
            sh = int(4 + 22 * glitch_k)
            out[..., 0] = np.roll(out[..., 0], sh, axis=1)
            out[..., 2] = np.roll(out[..., 2], -sh, axis=1)
            for _ in range(int(3 + 8 * glitch_k)):
                y0 = random.randint(0, H - 40)
                hgt = random.randint(8, int(30 + 120 * glitch_k))
                out[y0:y0 + hgt] = np.roll(out[y0:y0 + hgt], random.randint(-int(90 * glitch_k), int(90 * glitch_k)), axis=1)
        return Image.fromarray(out, "RGB")


def camera(src, t, sc, fx):
    k = (t - sc["t"]) / max(0.01, sc["end"] - sc["t"])
    k = k * k * (3 - 2 * k) * 0.6 + k * 0.4
    z0, z1, c0, c1 = sc["cam"]
    z = max(1.03, z0 + (z1 - z0) * k)
    cx = (c0[0] + (c1[0] - c0[0]) * k) * SW
    cy = (c0[1] + (c1[1] - c0[1]) * k) * SH
    ds = fx.drift_seed
    cx += 5 * math.sin(t * 0.9 + ds[0]) + 3 * math.sin(t * 2.3 + ds[1])  # caméra à l'épaule
    cy += 5 * math.sin(t * 0.7 + ds[2]) + 3 * math.sin(t * 1.9 + ds[3])
    shake = sc.get("shake")
    if shake:
        amp = shake(t)
        cx += random.uniform(-amp, amp); cy += random.uniform(-amp, amp)
    w, h = SW / z, SH / z
    x0 = min(max(0, cx - w / 2), SW - w)
    y0 = min(max(0, cy - h / 2), SH - h)
    return src.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + w, y0 + h))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ep")
    ap.add_argument("--stills", default="")
    ap.add_argument("--from", dest="t0", type=float, default=0.0)
    ap.add_argument("--to", dest="t1", type=float, default=None)
    ap.add_argument("--bitrate", default="14M")
    args = ap.parse_args()
    ep_dir = os.path.abspath(args.ep if os.path.isdir(args.ep) else os.path.join(os.getcwd(), args.ep))
    ep = load_episode(ep_dir)
    scenes, END = ep.build_scenes()
    apply_overrides(ep_dir, scenes)
    caps = Captions(build_chunks(ep.WORDS.words), ep.KEYWORDS)
    hud, title, tags, fx = Hud(ep), Title(ep), Tags(), FX()
    build = os.path.join(ep_dir, "build")
    os.makedirs(build, exist_ok=True)

    def scene_at(t):
        for s in scenes:
            if s["t"] <= t < s["end"]:
                return s
        return scenes[-1]

    def render(t, i):
        random.seed(i * 7919)
        sc = scene_at(t)
        src = sc["fn"](t)
        img = camera(src, t, sc, fx)
        g = 0.0
        since = t - sc["t"]
        if since < 0.1 and sc["t"] > 0:
            g = 0.45 * (1 - since / 0.1)
        if "glitch" in sc:
            a, b = sc["glitch"]
            if a <= since < b:
                g = max(g, 0.9 * (1 - (since - a) / (b - a)) ** 0.5)
        flash = max(0.0, 1 - since / 0.08) if sc["t"] > 0 else 0.0
        img = fx.process(img, t, i, sc, g, flash)
        title.draw(img, t)
        hud.draw(img, t, sc.get("loc", ""))
        tags.draw(img, t, sc.get("tags"), sc["end"])
        if sc.get("captions", True):
            caps.draw(img, t, sc.get("cap_y", 1250))
        return img

    if args.stills:
        sd = os.path.join(build, "stills")
        os.makedirs(sd, exist_ok=True)
        for v in args.stills.split(","):
            t = float(v)
            render(t, int(t * FPS)).save(os.path.join(sd, f"t{t:06.2f}.jpg"), quality=85)
        print("stills ->", sd)
        return

    t1 = END if args.t1 is None else min(args.t1, END)
    n0, n1 = int(args.t0 * FPS), int(round(t1 * FPS))
    out = os.path.join(build, "video_noaudio.mp4")
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "h264_videotoolbox", "-b:v", args.bitrate,
                            "-maxrate", "20M", "-profile:v", "high", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
                           stdin=subprocess.PIPE)
    st = time.time()
    for i in range(n0, n1):
        enc.stdin.write(render(i / FPS, i).tobytes())
        if (i - n0) % 150 == 0:
            el = time.time() - st
            done = (i - n0 + 1) / (n1 - n0)
            print(f"  {i / FPS:6.2f}s  {done * 100:5.1f}%  écoulé {el:5.0f}s  reste ~{el / done - el:4.0f}s", flush=True)
    enc.stdin.close()
    enc.wait()
    print("vidéo ->", out, f"({n1 - n0} images, {time.time() - st:.0f}s)")


if __name__ == "__main__":
    main()

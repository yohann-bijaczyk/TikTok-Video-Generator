"""Primitives graphiques partagées par tous les épisodes (Pillow + numpy, faible empreinte)."""
import math
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

W, H = 1080, 1920          # sortie TikTok
SW, SH = 1188, 2112        # canevas de scène (10 % de marge pour les mouvements de caméra)

FONT_FILES = {
    "impact": "/System/Library/Fonts/Supplemental/Impact.ttf",
    "black": "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "din": "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
    "mono": "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
    "sf": "/System/Library/Fonts/SFNS.ttf",
}


@lru_cache(maxsize=64)
def font(name, size):
    return ImageFont.truetype(FONT_FILES[name], size)


def mix(a, b, k):
    k = max(0.0, min(1.0, k))
    return tuple(int(round(a[i] + (b[i] - a[i]) * k)) for i in range(3))


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def vgrad(w, h, stops):
    """Dégradé vertical. stops = [(pos 0..1, (r,g,b)), ...]"""
    ys = np.linspace(0, 1, h, dtype=np.float32)
    out = np.zeros((h, 3), np.float32)
    pos = [s[0] for s in stops]
    for c in range(3):
        out[:, c] = np.interp(ys, pos, [s[1][c] for s in stops])
    arr = np.repeat(out[:, None, :], w, axis=1)
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGB")


def smooth_noise(w, h, cell, seed=0, octaves=3):
    """Bruit fractal 0..1 (float32) par sur-échantillonnage de grilles aléatoires."""
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        c = max(2, int(cell / (2 ** o)))
        gw, gh = w // c + 3, h // c + 3
        g = (rng.random((gh, gw)) * 255).astype(np.uint8)
        im = Image.fromarray(g, "L").resize((gw * c, gh * c), Image.BICUBIC)
        acc += np.asarray(im, np.float32)[:h, :w] / 255.0 * amp
        tot += amp
        amp *= 0.5
    acc /= tot
    acc -= acc.min()
    acc /= max(1e-6, acc.max())
    return acc


@lru_cache(maxsize=8)
def glow_sprite(size=256, power=2.2):
    r = np.linspace(-1, 1, size, dtype=np.float32)
    xx, yy = np.meshgrid(r, r)
    d = np.sqrt(xx ** 2 + yy ** 2)
    a = np.clip(1 - d, 0, 1) ** power
    return Image.fromarray((a * 255).astype(np.uint8), "L")


def add_glow(img, cx, cy, rx, ry, color, strength=1.0, power=2.2):
    """Halo lumineux additif (lampadaires, néons, feux)."""
    rx, ry = int(max(2, rx)), int(max(2, ry))
    x0, y0 = int(cx - rx), int(cy - ry)
    x1, y1 = x0 + 2 * rx, y0 + 2 * ry
    if x1 <= 0 or y1 <= 0 or x0 >= img.width or y0 >= img.height:
        return
    m = glow_sprite(256, power).resize((2 * rx, 2 * ry), Image.BILINEAR)
    col = tuple(int(c * strength) for c in color)
    layer = Image.new("RGB", m.size, col)
    black = Image.new("RGB", m.size, (0, 0, 0))
    layer = Image.composite(layer, black, m)
    box = (max(0, x0), max(0, y0), min(img.width, x1), min(img.height, y1))
    crop_l = layer.crop((box[0] - x0, box[1] - y0, box[2] - x0, box[3] - y0))
    region = img.crop(box)
    img.paste(ImageChops.add(region, crop_l), box)


def rounded(draw, box, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)


# ---------------------------------------------------------------- personnages
def person(dr, x, y, hp, col, *, phase=0.0, stride=0.0, kind="adult", facing="back",
           eyes=None, skin=(150, 140, 135), hair=None, scarf=None, backpack=None,
           coat_len=0.36, lean=0.0, arm_up=None):
    """Silhouette humaine stylisée. y = pieds. eyes: None | 'black' | 'normal'."""
    h = hp
    child = kind == "child"
    head_r = (0.085 if child else 0.062) * h
    head_cy = y - h + head_r * 1.05
    lx = lean * h  # inclinaison (course)
    hair = hair or mix(col, (0, 0, 0), 0.3)
    sw = math.sin(phase) * stride
    hip_y = y - (0.44 if child else 0.47) * h
    # jambes
    for side in (-1, 1):
        lift = max(0.0, math.sin(phase + (0 if side < 0 else math.pi))) * 0.05 * h * stride
        fx = x + side * 0.05 * h + side * sw * 0.02 * h
        fy = y - lift
        hx = x + lx * 0.5 + side * 0.045 * h
        lw = 0.038 * h
        dr.polygon([(hx - lw, hip_y), (hx + lw, hip_y), (fx + lw * 0.7, fy), (fx - lw * 0.7, fy)], fill=col)
        dr.ellipse([fx - lw, fy - lw * 0.6, fx + lw * 1.1, fy + lw * 0.4], fill=mix(col, (0, 0, 0), 0.4))
    sh_y = head_cy + head_r + 0.035 * h
    hem_y = y - coat_len * h
    shw = (0.16 if child else 0.135) * h
    hmw = (0.14 if child else 0.125) * h
    sx = x + lx
    # bras
    for side in (-1, 1):
        ax = sx + side * shw * 0.95
        swing = -side * sw * 0.04 * h
        if arm_up is not None and side == arm_up[0]:
            ex, ey = arm_up[1], arm_up[2]
            dr.line([(ax, sh_y + 0.02 * h), (ex, ey)], fill=col, width=int(max(2, 0.07 * h)))
            continue
        ex = ax + side * 0.02 * h + swing
        ey = y - (0.5 if child else 0.52) * h
        aw = 0.032 * h
        dr.polygon([(ax - aw, sh_y), (ax + aw, sh_y), (ex + aw * 0.8, ey), (ex - aw * 0.8, ey)], fill=col)
    # torse / manteau
    dr.polygon([(sx - shw, sh_y + 0.025 * h), (sx + shw, sh_y + 0.025 * h), (x + hmw, hem_y), (x - hmw, hem_y)], fill=col)
    dr.ellipse([sx - shw, sh_y - 0.01 * h, sx - shw + 0.07 * h, sh_y + 0.06 * h], fill=col)
    dr.ellipse([sx + shw - 0.07 * h, sh_y - 0.01 * h, sx + shw, sh_y + 0.06 * h], fill=col)
    dr.rectangle([sx - shw * 0.6, sh_y - 0.005 * h, sx + shw * 0.6, sh_y + 0.05 * h], fill=col)
    if backpack and facing == "back":
        dr.rounded_rectangle([sx - shw * 0.7, sh_y + 0.04 * h, sx + shw * 0.7, sh_y + 0.27 * h], int(0.03 * h), fill=backpack)
    # cou + écharpe
    dr.rectangle([sx - head_r * 0.45, head_cy + head_r * 0.6, sx + head_r * 0.45, sh_y + 0.02 * h], fill=col)
    if scarf:
        dr.rounded_rectangle([sx - head_r * 1.1, sh_y - 0.025 * h, sx + head_r * 1.1, sh_y + 0.03 * h], int(head_r * 0.4), fill=scarf)
        if facing == "back":
            dr.polygon([(sx + head_r * 0.2, sh_y), (sx + head_r * 0.9, sh_y), (sx + head_r * 0.8, sh_y + 0.12 * h), (sx + head_r * 0.35, sh_y + 0.11 * h)], fill=scarf)
    # tête
    hx0, hy0 = sx - head_r, head_cy - head_r * 1.08
    hx1, hy1 = sx + head_r, head_cy + head_r * 1.08
    if facing == "back":
        dr.ellipse([hx0, hy0, hx1, hy1], fill=hair)
        if kind == "woman":
            dr.ellipse([sx - head_r * 0.45, hy0 - head_r * 0.35, sx + head_r * 0.45, hy0 + head_r * 0.5], fill=hair)
    else:
        dr.ellipse([hx0, hy0, hx1, hy1], fill=skin)
        dr.chord([hx0 - 1, hy0 - 1, hx1 + 1, hy1 * 0.0 + head_cy + head_r * 0.2], 180, 360, fill=hair)
        if eyes and head_r > 5:
            ey = head_cy + head_r * 0.18
            for side in (-1, 1):
                ex = sx + side * head_r * 0.38
                rx, ry = head_r * 0.22, head_r * 0.13
                if eyes == "black":
                    dr.ellipse([ex - rx, ey - ry, ex + rx, ey + ry], fill=(4, 4, 6))
                    if head_r > 14:
                        dr.ellipse([ex - rx * 0.5, ey - ry * 0.6, ex - rx * 0.1, ey - ry * 0.1], fill=(70, 70, 80))
                else:
                    dr.ellipse([ex - rx, ey - ry, ex + rx, ey + ry], fill=mix(skin, (230, 230, 230), 0.6))
                    dr.ellipse([ex - ry, ey - ry, ex + ry, ey + ry], fill=(20, 20, 20))


# ---------------------------------------------------------------- texte
def text_sprite(text, fnt, fill=(255, 255, 255), stroke=0, stroke_fill=(0, 0, 0), shadow=0, spacing=0, pad=None):
    """Rend un texte en RGBA avec contour/ombre portée. Renvoie Image RGBA."""
    pad = pad if pad is not None else stroke + shadow * 2 + 6
    if spacing:
        widths = [fnt.getbbox(ch)[2] - fnt.getbbox(ch)[0] if ch != " " else fnt.size * 0.3 for ch in text]
        tw = int(sum(widths) + spacing * (len(text) - 1))
    else:
        bb = fnt.getbbox(text, stroke_width=stroke)
        tw = bb[2] - bb[0]
    asc, desc = fnt.getmetrics()
    th = asc + desc + stroke * 2
    img = Image.new("RGBA", (tw + pad * 2 + stroke * 2, th + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def _draw(dd, ox, oy, col, scol):
        if spacing:
            cx = ox
            for ch, wch in zip(text, widths):
                dd.text((cx, oy), ch, font=fnt, fill=col, stroke_width=stroke, stroke_fill=scol)
                cx += wch + spacing
        else:
            bb = fnt.getbbox(text, stroke_width=stroke)
            dd.text((ox - bb[0] + stroke, oy), text, font=fnt, fill=col, stroke_width=stroke, stroke_fill=scol)

    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        _draw(ImageDraw.Draw(sh), pad, pad + shadow, (0, 0, 0, 200), (0, 0, 0, 200))
        sh = sh.filter(ImageFilter.GaussianBlur(shadow))
        img = Image.alpha_composite(img, sh)
        d = ImageDraw.Draw(img)
    _draw(d, pad, pad, fill, stroke_fill)
    return img


def pill(text, fnt, bg=(255, 59, 48), fg=(10, 10, 10), padx=22, pady=10, radius=None):
    bb = fnt.getbbox(text)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    w, h = tw + padx * 2, th + pady * 2
    img = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4, 4, 4 + w, 4 + h], radius if radius is not None else h // 2, fill=bg)
    d.text((4 + padx - bb[0], 4 + pady - bb[1]), text, font=fnt, fill=fg)
    return img


def paste_center(base, spr, cx, cy, alpha=1.0, scale=1.0):
    if scale != 1.0:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
    if alpha < 1.0:
        a = spr.getchannel("A").point(lambda v: int(v * alpha))
        spr = spr.copy()
        spr.putalpha(a)
    base.alpha_composite(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2))) if base.mode == "RGBA" \
        else base.paste(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)), spr)

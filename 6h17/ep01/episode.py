"""6H17 — Épisode 1 « Les Immobiles » : décors procéduraux, découpage et habillage.

Chaque plan peut être remplacé par une image ou un clip réaliste (IA ou tourné) :
déposez  ep01/scenes/<ID>.jpg|png|mp4  (ex. S09_vitre.jpg) et relancez le rendu.
"""
import math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageChops

import gfx
from gfx import SW, SH, W, H, mix, ease, ease_out, add_glow, person, font, text_sprite, pill, paste_center
from timeline import Words

HERE = os.path.dirname(os.path.abspath(__file__))
WORDS = Words(os.path.join(HERE, "audio", "words.json"))
T = WORDS.at

SERIES = "6H17"
EPISODE = 1
EP_TITLE = "LES IMMOBILES"

# Couleurs de continuité (voir bible/BIBLE.md)
EMMA_COAT, EMMA_SCARF, EMMA_HAIR = (112, 98, 80), (150, 22, 24), (38, 28, 24)
ADAM_HOODIE, ADAM_BAG = (34, 46, 74), (70, 70, 74)
THOMAS_COAT = (24, 30, 46)
FOG = (78, 88, 106)
RED = (235, 38, 38)

# ------------------------------------------------------------------ horloge HUD
T_FREEZE = T("immobilisés")
T_30 = T("trente")
T_RESTART = T("recommencé")


def story_clock(t):
    """Heure affichée dans le HUD (secondes depuis 06:00:00)."""
    base = 6 * 3600 + 17 * 60
    t_rw0, t_rw1 = T("mais", 1), T("en")
    if t < t_rw0:
        return base + t
    if t < t_rw0 + 1.0:  # rembobinage
        k = ease((t - t_rw0) / 1.0)
        return (base + t_rw0) + ((base - 40) - (base + t_rw0)) * k
    if t < T_30:
        return base - 40 + (t - t_rw0 - 1.0)
    if t < T_30 + 0.8:  # avance rapide « trente secondes plus tard »
        a = base - 40 + (T_30 - t_rw0 - 1.0)
        return a + (base - 8 - a) * ease((t - T_30) / 0.8)
    return base - 8 + (t - T_30 - 0.8)


# ------------------------------------------------------------------ rue (3D simple)
class Street:
    """Rue parisienne haussmannienne à l'aube, projetée en perspective."""
    cx, vy, f, camh = SW / 2, SH * 0.46, 1000.0, 1.7

    def __init__(self):
        self.rng = random.Random(617)
        self.bg = None
        r = self.rng
        self.people = []
        for i in range(64):
            side = r.choice((-1, 1))
            X = side * r.uniform(5.3, 7.4)
            Z0 = r.uniform(13, 95)
            if i < 22:  # sur le passage piéton
                X, Z0 = r.uniform(-4.4, 4.4), r.uniform(19.5, 23.5)
            elif i < 30:  # au bord de la chaussée, près de la caméra
                X, Z0 = side * r.uniform(3.6, 4.6), r.uniform(8, 16)
            self.people.append(dict(X=X, Z0=Z0, dir=r.choice((-1, 1)), sp=r.uniform(1.1, 1.6),
                                    h=r.uniform(1.58, 1.88), ph=r.uniform(0, 6.28), shade=r.uniform(0.75, 1.15),
                                    kind=r.choice(("adult", "adult", "woman")), turn=r.uniform(0, 0.8)))
        self.cars = []
        for lane, d in ((-2.6, 1), (2.6, -1)):
            z = 9.0 if lane < 0 else 16.0
            while z < 130:
                self.cars.append(dict(X=lane, Z0=z, dir=d, col=r.choice([(40, 44, 52), (70, 20, 22), (90, 92, 96), (22, 24, 30), (50, 58, 70)])))
                z += r.uniform(9, 16)

    def P(self, X, Y, Z):
        return self.cx + self.f * X / Z, self.vy + self.f * (self.camh - Y) / Z

    def fogk(self, Z):
        return 1 - math.exp(-Z / 42.0)

    def build(self):
        img = gfx.vgrad(SW, SH, [(0, (8, 11, 20)), (0.30, (22, 28, 42)), (0.46, (70, 80, 98)), (0.47, (40, 44, 52)), (1, (14, 15, 18))])
        d = ImageDraw.Draw(img)
        P, fk = self.P, self.fogk
        r = random.Random(5)
        # bâtiment au fond de la rue
        zf = 170
        bx0, by0 = P(-9, 22, zf)
        bx1, by1 = P(9, 0, zf)
        d.rectangle([bx0, by0, bx1, by1], fill=mix((50, 54, 64), FOG, fk(zf)))
        # chaussée / trottoirs
        for (x0, x1, col) in ((-8, -5, (46, 47, 52)), (5, 8, (46, 47, 52)), (-5, 5, (26, 27, 31))):
            pts = [P(x0, 0, 1.0), P(x1, 0, 1.0), P(x1, 0, zf), P(x0, 0, zf)]
            d.polygon(pts, fill=col)
        for X in (-5, 5):
            d.line([P(X, 0, 1.2), P(X, 0, zf)], fill=(70, 72, 78), width=3)
        z = 13.0
        while z < zf:  # pointillés centraux
            d.polygon([P(-0.08, 0, z), P(0.08, 0, z), P(0.08, 0, z + 3), P(-0.08, 0, z + 3)], fill=mix((150, 150, 140), FOG, fk(z)))
            z += 9
        for i in range(8):  # passage piéton
            x = -4.5 + i * 1.2
            d.polygon([P(x, 0, 20), P(x + 0.6, 0, 20), P(x + 0.6, 0, 23), P(x, 0, 23)], fill=(110, 112, 115))
        # immeubles
        for side in (-1, 1):
            X = 8 * side
            blocks, z = [], 2.0
            while z < zf - 5:
                L = r.uniform(12, 20)
                blocks.append((z, min(zf - 5, z + L), r.uniform(18, 23), r.uniform(-8, 8)))
                z += L
            for z0, z1, hb, tint in reversed(blocks):
                zm = (z0 + z1) / 2
                fkk = fk(zm)
                base = (58 + tint, 62 + tint, 72 + tint)
                d.polygon([P(X, 0, z0), P(X, hb, z0), P(X, hb, z1), P(X, 0, z1)], fill=mix(base, FOG, fkk))
                d.polygon([P(X, 0, z0), P(X, 4, z0), P(X, 4, z1), P(X, 0, z1)], fill=mix((26, 27, 32), FOG, fkk))
                # toit mansardé
                d.polygon([P(X, hb, z0), P(X * 1.2, hb + 3.5, z0), P(X * 1.2, hb + 3.5, z1), P(X, hb, z1)], fill=mix((34, 38, 48), FOG, fkk))
                # fenêtres
                for k in range(5):
                    yb = 5.0 + k * 3.1
                    if yb + 2 > hb:
                        break
                    zz = z0 + 1.0
                    while zz + 1.3 < z1:
                        lit = r.random() < 0.10
                        wc = r.choice([(255, 196, 120), (255, 214, 160), (190, 210, 255)]) if lit else (22, 26, 36)
                        wcol = mix(wc, FOG, fk(zz) * (0.6 if lit else 1.0))
                        d.polygon([P(X, yb, zz), P(X, yb + 1.9, zz), P(X, yb + 1.9, zz + 1.2), P(X, yb, zz + 1.2)], fill=wcol)
                        zz += 2.6
                    if k in (0, 3):  # balcons filants
                        d.polygon([P(X, yb - 0.15, z0), P(X, yb + 0.15, z0), P(X, yb + 0.15, z1), P(X, yb - 0.15, z1)], fill=mix((20, 22, 28), FOG, fkk))
                # vitrine éclairée de temps en temps
                if r.random() < 0.3:
                    zz = z0 + r.uniform(1, 4)
                    d.polygon([P(X, 0.4, zz), P(X, 3.2, zz), P(X, 3.2, zz + 4), P(X, 0.4, zz + 4)], fill=mix((120, 150, 160), FOG, fkk * 0.7))
        # lampadaires
        lamps = []
        for side in (-1, 1):
            for z in range(8, 150, 24):
                X = 6.3 * side
                zz = z + (12 if side > 0 else 0)
                p0, p1 = P(X, 0, zz), P(X, 5.6, zz)
                fkk = fk(zz)
                d.line([p0, p1], fill=mix((18, 18, 22), FOG, fkk), width=max(1, int(self.f * 0.14 / zz)))
                lamps.append((p1, p0, zz, fkk))
        for p1, p0, zz, fkk in sorted(lamps, key=lambda l: -l[2]):
            s = self.f / zz
            add_glow(img, p1[0], p1[1], s * 2.4, s * 2.4, (255, 160, 80), 0.9 * (1 - fkk * 0.6))
            add_glow(img, p1[0], p1[1], s * 0.35, s * 0.35, (255, 230, 190), 1.0 * (1 - fkk * 0.5))
            add_glow(img, p0[0], p0[1], s * 3.5, s * 0.8, (200, 120, 60), 0.35 * (1 - fkk))
            add_glow(img, p0[0], p0[1] + s * 1.6, s * 0.4, s * 2.2, (255, 150, 70), 0.25 * (1 - fkk))  # reflet sur sol mouillé
        self.bg = img

    # temps « monde » : la ville coule, puis se fige, puis repart vers la caméra
    def world_time(self, t):
        t0 = T("mais", 1)
        if t < t0 + 0.8:
            return 3.2 * max(0.0, (t0 + 0.8 - t)) / 0.8 + 0.0  # rembobinage
        return min(t, T_FREEZE) - (t0 + 0.8)

    def frame(self, t, emma=False, emma_run=False, focus=None):
        if self.bg is None:
            self.build()
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        P, fk = self.P, self.fogk
        tw = self.world_time(t)
        moving = t < T_FREEZE
        restart = max(0.0, t - T_RESTART)
        items = []
        for c in self.cars:
            span = 125.0
            Z = (c["Z0"] - 6 + c["dir"] * 5.0 * tw) % span + 6
            items.append((Z, "car", c))
        for p in self.people:
            if abs(p["X"]) < 4.7:
                Z = p["Z0"]
                X = max(-4.8, min(4.8, p["X"] + p["dir"] * p["sp"] * tw * 0.35))
            else:
                Z = (p["Z0"] - 5 + p["dir"] * p["sp"] * tw) % 95 + 5
                X = p["X"]
            if restart > 0:
                Z = max(3.5, Z - restart * (0.9 + p["turn"]) * (0.6 + 0.4 * math.sin(restart * 7 + p["ph"]) ** 2))
            items.append((Z, "p", (p, X)))
        for Z, kind, o in sorted(items, key=lambda i: -i[0]):
            if Z < 2.5:
                continue
            k = fk(Z)
            s = self.f / Z
            if kind == "car":
                c = o
                X = c["X"]
                x, yb = P(X, 0.25, Z)
                w = 1.8 * s
                hb = 0.75 * s
                body = mix(c["col"], FOG, k)
                d.rounded_rectangle([x - w / 2, yb - hb, x + w / 2, yb], int(0.12 * s), fill=body)
                d.polygon([(x - w * 0.4, yb - hb), (x + w * 0.4, yb - hb), (x + w * 0.32, yb - hb - 0.5 * s), (x - w * 0.32, yb - hb - 0.5 * s)], fill=mix((14, 16, 22), FOG, k))
                if s > 60:  # conducteur figé
                    d.ellipse([x - 0.16 * s, yb - hb - 0.42 * s, x + 0.05 * s, yb - hb - 0.12 * s], fill=mix((6, 6, 8), FOG, k))
                d.rectangle([x - w / 2 + 0.05 * s, yb - 0.02 * s, x - w * 0.3, yb + 0.25 * s], fill=(8, 8, 9))
                d.rectangle([x + w * 0.3, yb - 0.02 * s, x + w / 2 - 0.05 * s, yb + 0.25 * s], fill=(8, 8, 9))
                if c["dir"] > 0:  # feux arrière
                    for sx in (-1, 1):
                        lx = x + sx * w * 0.38
                        d.rectangle([lx - 0.12 * s, yb - hb * 0.7, lx + 0.12 * s, yb - hb * 0.5], fill=mix((255, 40, 30), FOG, k * 0.5))
                        add_glow(img, lx, yb - hb * 0.6, 0.9 * s, 0.6 * s, (255, 30, 20), 0.55 * (1 - k * 0.7))
                    add_glow(img, x, yb + 0.6 * s, 1.2 * s, 0.9 * s, (160, 20, 10), 0.25 * (1 - k))
                else:  # phares
                    for sx in (-1, 1):
                        lx = x + sx * w * 0.36
                        add_glow(img, lx, yb - hb * 0.55, 1.0 * s, 0.7 * s, (255, 240, 210), 0.8 * (1 - k * 0.6))
                    add_glow(img, x, yb + 1.0 * s, 1.6 * s, 1.4 * s, (200, 190, 160), 0.25 * (1 - k))
            else:
                p, X = o
                x, y = P(X, 0, Z)
                hp = p["h"] * s
                col = mix(tuple(int(v * p["shade"]) for v in (24, 26, 32)), FOG, k)
                face = restart > 0.4
                eyes = "black" if (face and t > T("noirs") - 0.3) else None
                skin = mix((168, 164, 160), FOG, k)
                ph = p["ph"] + tw * p["sp"] * 3.2 + (restart * 2.5 if restart else 0)
                person(d, x, y, hp, col, phase=ph, stride=0.9 if (moving or restart) else 0.6, kind=p["kind"],
                       facing="front" if face else "back", eyes=eyes, skin=skin, hair=mix((14, 13, 14), FOG, k))
        if emma:
            self.draw_family(img, d, t, run=emma_run)
        return img

    def draw_family(self, img, d, t, run=False):
        t0 = T("seules")
        walk = t < T_30
        prog = (min(t, T_30) - t0)
        Ze = 3.3 + prog * 0.35
        P = self.P
        xe, ye = P(-0.55, 0, Ze)
        xa, ya = P(0.35, 0, Ze + 0.2)
        se, sa = self.f / Ze, self.f / (Ze + 0.2)
        ph = prog * 5.5
        light = 1.0
        coat = tuple(int(c * light) for c in EMMA_COAT)
        # Adam d'abord (légèrement derrière), puis Emma qui lui tient la main
        person(d, xa, ya, 1.15 * sa, ADAM_HOODIE, phase=ph + 1.3, stride=0.9 if walk else 0.0, kind="child",
               backpack=ADAM_BAG, hair=(30, 24, 20))
        hand = (xa - 0.22 * sa, ya - 0.55 * sa)
        person(d, xe, ye, 1.68 * se, coat, phase=ph, stride=0.9 if walk else 0.0, kind="woman", scarf=EMMA_SCARF,
               hair=EMMA_HAIR, coat_len=0.30, arm_up=(1, hand[0], hand[1]))


# ------------------------------------------------------------------ vitrine vue de l'intérieur
class ShopGlass:
    def __init__(self):
        self.base = None
        self.knocks = sorted([0.30, 0.62, 0.94, 2.4, 2.72] + [T("frappé") + i * 0.32 for i in range(3)] +
                             [T("demandait") + i * 0.3 for i in range(3)] + [T("d'ouvrir") + 0.5 + i * 0.3 for i in range(2)])

    def _man(self, reveal):
        lay = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        cx = SW / 2 + 20
        # manteau / épaules
        d.polygon([(cx - 330, SH), (cx - 300, 1080), (cx - 170, 960), (cx + 170, 960), (cx + 300, 1080), (cx + 330, SH)], fill=THOMAS_COAT + (255,))
        d.polygon([(cx - 70, 960), (cx + 70, 960), (cx + 30, 1130), (cx - 30, 1130)], fill=(70, 72, 78, 255))  # pull gris
        d.polygon([(cx - 120, 960), (cx - 40, 960), (cx - 10, 1180), (cx - 110, 1060)], fill=(18, 22, 34, 255))  # revers
        d.polygon([(cx + 120, 960), (cx + 40, 960), (cx + 10, 1180), (cx + 110, 1060)], fill=(18, 22, 34, 255))
        # bras gauche (main à plat sur la vitre, côté gauche de l'image)
        d.line([(cx - 280, 1100), (cx - 330, 980), (cx - 300, 860)], fill=THOMAS_COAT + (255,), width=110, joint="curve")
        # bras droit (poing qui frappe)
        d.line([(cx + 280, 1100), (cx + 330, 1000), (cx + 300, 900)], fill=THOMAS_COAT + (255,), width=110, joint="curve")
        # cou
        d.rectangle([cx - 55, 860, cx + 55, 975], fill=(120, 118, 118, 255))
        # visage
        f = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        fd = ImageDraw.Draw(f)
        skin = (168, 165, 165)
        fd.ellipse([cx - 110, 630, cx + 110, 905], fill=skin + (255,))
        fd.ellipse([cx - 92, 810, cx + 92, 912], fill=(146, 142, 144, 255))  # barbe de 3 jours
        fd.ellipse([cx - 108, 610, cx + 108, 730], fill=(40, 30, 26, 255))  # cheveux
        fd.rectangle([cx - 108, 670, cx + 108, 690], fill=(40, 30, 26, 255))
        for s in (-1, 1):
            fd.ellipse([cx + s * 44 - 30, 742, cx + s * 44 + 30, 780], fill=(112, 104, 108, 255))  # orbites
            fd.ellipse([cx + s * 44 - 20, 752, cx + s * 44 + 20, 770], fill=(214, 210, 208, 255))
            fd.ellipse([cx + s * 44 - 9, 752, cx + s * 44 + 9, 770], fill=(30, 26, 24, 255))
            fd.ellipse([cx + s * 44 - 4, 754, cx + s * 44, 758], fill=(230, 230, 235, 255))
            fd.line([(cx + s * 44 - 30, 728), (cx + s * 44 + 26, 724 - s * 2)], fill=(44, 34, 30, 255), width=9)  # sourcils
        fd.polygon([(cx - 4, 770), (cx + 16, 840), (cx - 10, 842)], fill=(110, 105, 108, 255))
        fd.line([(cx - 35, 870), (cx + 35, 868)], fill=(70, 50, 52, 255), width=6)
        # ombre portée de la lumière du magasin (éclairage par le bas/devant)
        sh = Image.new("L", (SW, SH), 0)
        ImageDraw.Draw(sh).ellipse([cx - 20, 560, cx + 220, 960], fill=150)
        sh = sh.filter(ImageFilter.GaussianBlur(60))
        dark = Image.new("RGBA", (SW, SH), (5, 6, 10, 255))
        f2 = Image.composite(dark, f, sh)
        f2.putalpha(f.getchannel("A"))
        lay.alpha_composite(f2)
        # main à plat sur la vitre
        hx, hy = cx - 300, 820
        hd = ImageDraw.Draw(lay)
        palm = (156, 146, 142, 255)
        hd.ellipse([hx - 75, hy - 40, hx + 75, hy + 110], fill=palm)
        for i, (dx, ln) in enumerate(((-58, 120), (-20, 150), (18, 158), (55, 132))):
            hd.rounded_rectangle([hx + dx - 17, hy - ln, hx + dx + 17, hy + 10], 17, fill=palm)
        hd.rounded_rectangle([hx + 60, hy + 10, hx + 150, hy + 48], 19, fill=palm)
        f_soft = lay.filter(ImageFilter.GaussianBlur(2.6))  # à travers le verre embué
        lay = f_soft
        if reveal < 1:
            a = lay.getchannel("A")
            darkl = Image.new("RGBA", (SW, SH), (6, 8, 14, 255))
            lay = Image.blend(darkl, lay, 0.18 + 0.82 * reveal)
            lay.putalpha(a)
        return lay

    def _fist(self):
        s = Image.new("RGBA", (260, 260), (0, 0, 0, 0))
        d = ImageDraw.Draw(s)
        sk = (176, 168, 166, 255)
        d.rounded_rectangle([40, 50, 220, 210], 60, fill=sk)
        for i in range(4):
            d.ellipse([45 + i * 42, 40, 95 + i * 42, 92], fill=(186, 178, 176, 255))
            d.line([(70 + i * 42, 90), (70 + i * 42, 150)], fill=(140, 130, 130, 255), width=3)
        d.rounded_rectangle([30, 120, 120, 175], 26, fill=(160, 152, 150, 255))
        return s.filter(ImageFilter.GaussianBlur(2))

    def _outside(self):
        img = gfx.vgrad(SW, SH, [(0, (30, 38, 54)), (0.5, (66, 76, 94)), (1, (30, 33, 40))])
        d = ImageDraw.Draw(img)
        for i in range(7):  # façades lointaines
            x = i * 190 - 40
            d.rectangle([x, 300 + (i % 3) * 60, x + 170, 1300], fill=mix((40, 46, 60), FOG, 0.55))
        d.rectangle([0, 1300, SW, SH], fill=(28, 30, 36))
        add_glow(img, 180, 520, 260, 260, (255, 160, 80), 0.6)
        add_glow(img, 180, 520, 40, 40, (255, 230, 190), 1.0)
        add_glow(img, 1020, 650, 160, 160, (255, 160, 80), 0.4)
        return img

    def _glass_overlay(self):
        ov = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        # buée
        n = gfx.smooth_noise(SW // 4, SH // 4, 40, seed=9)
        yy = np.linspace(0.4, 1.0, SH // 4)[:, None]
        a = (n * 60 * yy + 10).clip(0, 255).astype(np.uint8)
        fog = Image.fromarray(a, "L").resize((SW, SH), Image.BICUBIC)
        clear = Image.new("L", (SW, SH), 0)
        cd = ImageDraw.Draw(clear)
        cd.ellipse([SW / 2 + 20 - 420, 620, SW / 2 + 20 - 180, 960], fill=255)  # zone essuyée par la main
        for i in range(9):
            x = SW / 2 - 380 + i * 22
            cd.line([(x, 900), (x + random.Random(i).randint(-6, 6), 1050 + i * 31 % 140)], fill=200, width=5)
        clear = clear.filter(ImageFilter.GaussianBlur(14))
        fog = ImageChops.subtract(fog, clear)
        ov.paste((200, 215, 225, 255), (0, 0), fog)
        d = ImageDraw.Draw(ov)
        # reflets diagonaux
        refl = Image.new("L", (SW, SH), 0)
        rd = ImageDraw.Draw(refl)
        rd.polygon([(700, 250), (820, 250), (300, 1850), (180, 1850)], fill=22)
        rd.polygon([(900, 250), (940, 250), (480, 1850), (440, 1850)], fill=16)
        refl = refl.filter(ImageFilter.GaussianBlur(25))
        ov = Image.alpha_composite(ov, Image.merge("RGBA", (*Image.new("RGB", (SW, SH), (230, 240, 255)).split(), refl)))
        # autocollant « OUVERT 24H/24 » vu à l'envers
        st = text_sprite("OUVERT 24H/24", font("din", 92), fill=(210, 40, 40, 235), pad=4)
        st = ImageOps.mirror(st)
        ov.alpha_composite(st, (int(SW / 2 - st.width / 2), 300))
        st2 = text_sprite("CB ACCEPTÉE — LIVRAISON", font("din", 42), fill=(230, 230, 230, 160), pad=4)
        ov.alpha_composite(ImageOps.mirror(st2), (int(SW / 2 - st2.width / 2), 410))
        return ov

    def _interior(self):
        it = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(it)
        frame = (34, 36, 40, 255)
        d.rectangle([0, 0, SW, 250], fill=(16, 18, 20, 255))  # plafond / linteau
        d.rectangle([0, 1850, SW, SH], fill=(12, 13, 15, 255))  # comptoir
        d.rectangle([0, 0, 110, SH], fill=frame)
        d.rectangle([SW - 110, 0, SW, SH], fill=frame)
        d.rectangle([0, 236, SW, 252], fill=(60, 62, 66, 255))
        d.rectangle([0, 1838, SW, 1854], fill=(60, 62, 66, 255))
        d.rectangle([110, 1160, SW - 110, 1190], fill=(80, 82, 86, 255))  # barre de poussée
        r = random.Random(3)
        for side in (0, 1):  # bouts de rayon avec produits
            x0 = 0 if side == 0 else SW - 150
            d.rectangle([x0, 600, x0 + 150, SH], fill=(20, 22, 26, 255))
            for row in range(9):
                y = 640 + row * 140
                d.rectangle([x0, y + 100, x0 + 150, y + 112], fill=(46, 48, 52, 255))
                x = x0 + 6
                while x < x0 + 140:
                    w = r.randint(16, 34)
                    hh = r.randint(50, 96)
                    c = r.choice([(150, 30, 30), (30, 80, 150), (200, 160, 40), (40, 120, 60), (180, 180, 180), (120, 40, 110)])
                    d.rectangle([x, y + 100 - hh, x + w, y + 100], fill=tuple(int(v * 0.45) for v in c) + (255,))
                    x += w + 3
        for i in range(5):  # objets sur le comptoir
            x = 200 + i * 180
            d.rectangle([x, 1790 - i % 2 * 40, x + 110, 1860], fill=(22, 22, 26, 255))
        d.rectangle([860, 1740, 960, 1860], fill=(30, 32, 36, 255))
        d.rectangle([872, 1752, 948, 1800], fill=(60, 120, 90, 255))  # TPE
        return it

    def build(self):
        out = self._outside()
        glass = self._glass_overlay()
        inter = self._interior()
        self.versions = {}
        for rv in (0.0, 1.0):
            b = out.convert("RGBA")
            b.alpha_composite(self._man(rv))
            self.versions[rv] = b
        self.glass, self.inter = glass, inter
        self.fist = self._fist()
        # néon du magasin qui éclaire le haut
        top = Image.new("RGB", (SW, SH), (0, 0, 0))
        add_glow(top, SW / 2, 120, 700, 240, (170, 230, 210), 0.5)
        self.toplight = top
        self.base = True

    def reveal_at(self, t):
        t0 = T("c'était")
        if t < t0:
            return 0.0
        # néon qui grésille puis révèle le visage
        dt = t - t0
        if dt < 0.5:
            return 1.0 if int(dt * 22) % 3 == 0 else 0.15
        return 1.0

    def contact(self, t):
        for k in self.knocks:
            if 0 <= t - k < 0.09:
                return 1.0 - (t - k) / 0.09
        return 0.0

    def shake(self, t):
        return self.contact(t) * 9

    def frame(self, t, force_reveal=None):
        if self.base is None:
            self.build()
        rv = self.reveal_at(t) if force_reveal is None else force_reveal
        if rv in self.versions:
            img = self.versions[rv].copy()
        else:
            img = Image.blend(self.versions[0.0], self.versions[1.0], rv)
        c = self.contact(t)
        fx, fy = SW / 2 + 20 + 300, 860 + (1 - c) * 26
        sc = 0.9 + 0.12 * c
        f = self.fist.resize((int(260 * sc), int(260 * sc)), Image.BILINEAR)
        img.alpha_composite(f, (int(fx - f.width / 2), int(fy - f.height / 2)))
        img.alpha_composite(self.glass)
        img.alpha_composite(self.inter)
        img = img.convert("RGB")
        return ImageChops.add(img, self.toplight)


# ------------------------------------------------------------------ œil qui devient noir
class Eye:
    def __init__(self):
        self.cache = {}
        self.t0, self.t1 = T("leurs"), T("noirs") + 0.15

    def _render(self, k):
        w, h = SW, SH
        cx, cy, a, b = SW / 2, 1010, 500, 240
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        u = (xx - cx) / a
        inside_u = np.abs(u) < 1
        uu = np.clip(1 - u ** 2, 0, 1)
        upper = cy - b * (uu ** 0.72) * (1 + 0.12 * u)
        lower = cy + b * 0.62 * (uu ** 0.9)
        m = ((yy > upper) & (yy < lower) & inside_u).astype(np.float32)
        mask = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
        # peau
        n1 = gfx.smooth_noise(w // 2, h // 2, 60, seed=21)
        n2 = gfx.smooth_noise(w // 2, h // 2, 6, seed=22, octaves=2)
        n = np.asarray(Image.fromarray(((n1 * 0.6 + n2 * 0.4) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255
        light = np.clip(1.15 - np.hypot((xx - cx * 0.6) / 900, (yy - cy * 0.75) / 1100), 0.2, 1.0)
        skin = np.stack([168 + 0 * n, 136 + 0 * n, 122 + 0 * n], -1) * (0.78 + 0.3 * n)[..., None] * light[..., None]
        # pli de la paupière et cernes
        crease = np.exp(-((yy - (upper - 70)) / 30) ** 2) * inside_u
        bag = np.exp(-((yy - (lower + 60)) / 45) ** 2) * inside_u
        skin *= (1 - 0.35 * crease - 0.25 * bag)[..., None]
        brow = np.exp(-((yy - (upper - 260 + 40 * u ** 2)) / 40) ** 2) * (np.abs(u) < 1.15)
        skin *= (1 - 0.7 * brow * (0.6 + 0.4 * n2.repeat(2, 0).repeat(2, 1)[:h, :w]))[..., None]
        # globe oculaire
        shade = (1 - 0.5 * np.abs(u) ** 2) * (1 - 0.55 * np.clip((upper + 80 - yy) / 80, 0, 1))
        sclera = np.stack([206 + 0 * u, 194 + 0 * u, 188 + 0 * u], -1) * shade[..., None]
        icx, icy, R = cx + 15, cy - 15, 195
        dist = np.hypot(xx - icx, yy - icy)
        ang = np.arctan2(yy - icy, xx - icx)
        rng = np.random.default_rng(4)
        sbase = np.convolve(rng.random(721), np.ones(3) / 3, "same")
        streak = np.interp((ang + np.pi) / (2 * np.pi) * 720, np.arange(721), sbase).astype(np.float32)
        irisc = np.stack([86 + 50 * streak, 66 + 34 * streak, 44 + 18 * streak], -1)
        irisc *= np.clip(1.25 - dist / R * 0.6, 0, 1.2)[..., None]
        limb = np.clip((dist - R * 0.88) / (R * 0.12), 0, 1)[..., None]
        irisc = irisc * (1 - 0.7 * limb)
        iris_m = np.clip((R - dist) / 3, 0, 1)[..., None]
        eye = sclera * (1 - iris_m) + irisc * shade[..., None] * iris_m
        pup = np.clip((72 - dist) / 3, 0, 1)[..., None]
        eye = eye * (1 - pup) + 5 * pup
        # encre noire qui envahit tout l'œil
        if k > 0:
            nz = np.interp((ang + np.pi) / (2 * np.pi) * 64, np.arange(65), np.r_[rng.random(64), 0])
            Rb = (72 + k * 620) * (1 + 0.28 * nz * (1 - k))
            ink = np.clip((Rb - dist) / 18, 0, 1)[..., None]
            eye = eye * (1 - ink) + np.array([6, 6, 9], np.float32) * ink
        # reflet humide
        for (sx, sy, sr, sa) in ((cx - 70, cy - 95, 46, 0.9), (cx + 90, cy + 40, 16, 0.5)):
            sp = np.clip(1 - np.hypot(xx - sx, yy - sy) / sr, 0, 1) ** 1.5
            eye = eye + (255 - eye) * (sp * sa)[..., None]
        out = skin * (1 - mask[..., None]) + eye * mask[..., None]
        img = Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img)
        r = random.Random(8)
        for i in range(70):  # cils
            uu_ = -0.95 + 1.9 * i / 69
            x0 = cx + uu_ * a
            y0 = cy - b * (max(0, 1 - uu_ ** 2) ** 0.72) * (1 + 0.12 * uu_)
            ln = r.uniform(60, 110) * (1 - 0.4 * abs(uu_))
            ang_ = -math.pi / 2 + uu_ * 0.9 + r.uniform(-0.1, 0.1)
            d.line([(x0, y0), (x0 + math.cos(ang_) * ln * 0.6, y0 + math.sin(ang_) * ln)], fill=(18, 14, 14), width=4)
        return img

    def frame(self, t):
        k = ease((t - self.t0 - 0.3) / (self.t1 - self.t0 - 0.3))
        q = round(k * 14) / 14
        if q not in self.cache:
            self.cache[q] = self._render(q)
        return self.cache[q]


# ------------------------------------------------------------------ foule qui fixe la caméra
class Crowd:
    def __init__(self):
        self.img = None

    def face(self, s, seed, depth):
        r = random.Random(seed)
        im = Image.new("RGBA", (int(s * 2.4), int(s * 3.2)), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        cx, cy = im.width / 2, s * 1.0
        coat = r.choice([(20, 22, 28), (34, 30, 28), (18, 26, 36), (40, 40, 44)])
        d.polygon([(cx - s * 1.15, im.height), (cx - s * 1.0, cy + s * 1.15), (cx + s * 1.0, cy + s * 1.15), (cx + s * 1.15, im.height)], fill=coat + (255,))
        d.rectangle([cx - s * 0.28, cy + s * 0.5, cx + s * 0.28, cy + s * 1.2], fill=(120, 116, 116, 255))
        skin = r.choice([(176, 168, 164), (150, 132, 120), (120, 98, 86), (182, 172, 166)])
        d.ellipse([cx - s * 0.5, cy - s * 0.66, cx + s * 0.5, cy + s * 0.7], fill=skin + (255,))
        hair = r.choice([(20, 16, 14), (60, 44, 30), (90, 86, 82), (30, 24, 20)])
        if r.random() < 0.4:  # cheveux longs
            d.ellipse([cx - s * 0.62, cy - s * 0.78, cx + s * 0.62, cy + s * 0.9], fill=hair + (255,))
            d.ellipse([cx - s * 0.46, cy - s * 0.5, cx + s * 0.46, cy + s * 0.7], fill=skin + (255,))
        d.chord([cx - s * 0.52, cy - s * 0.74, cx + s * 0.52, cy + s * 0.1], 180, 360, fill=hair + (255,))
        # ombrage
        sh = Image.new("L", im.size, 0)
        ImageDraw.Draw(sh).ellipse([cx - s * 0.1, cy - s * 0.9, cx + s * 1.1, cy + s * 1.1], fill=170)
        sh = sh.filter(ImageFilter.GaussianBlur(s * 0.3))
        im = Image.composite(Image.new("RGBA", im.size, (6, 6, 10, 255)), im, sh).copy()
        a0 = im.getchannel("A")
        d = ImageDraw.Draw(im)
        for side in (-1, 1):
            ex, ey = cx + side * s * 0.2, cy + s * 0.02
            d.ellipse([ex - s * 0.15, ey - s * 0.11, ex + s * 0.15, ey + s * 0.11], fill=(60, 50, 50, 255))
            d.ellipse([ex - s * 0.11, ey - s * 0.065, ex + s * 0.11, ey + s * 0.065], fill=(3, 3, 5, 255))
            d.ellipse([ex - s * 0.06, ey - s * 0.05, ex - s * 0.02, ey - s * 0.02], fill=(90, 90, 100, 255))
        d.line([(cx, cy + s * 0.08), (cx + s * 0.05, cy + s * 0.3)], fill=tuple(int(v * 0.7) for v in skin) + (255,), width=max(1, int(s * 0.04)))
        d.line([(cx - s * 0.13, cy + s * 0.44), (cx + s * 0.13, cy + s * 0.45)], fill=(60, 40, 40, 255), width=max(1, int(s * 0.03)))
        im.putalpha(a0)
        if depth > 0:
            fogl = Image.new("RGBA", im.size, FOG + (255,))
            im = Image.blend(im, fogl, depth)
            im.putalpha(a0)
            im = im.filter(ImageFilter.GaussianBlur(depth * 4))
        return im

    def build(self):
        img = gfx.vgrad(SW, SH, [(0, (10, 13, 22)), (0.45, (62, 72, 90)), (1, (18, 19, 24))])
        for x, y, r_ in ((150, 700, 300), (1050, 560, 260), (600, 400, 180)):
            add_glow(img, x, y, r_, r_, (255, 160, 80), 0.5)
        rows = [(110, 0.75, 820, 9), (170, 0.55, 980, 7), (260, 0.33, 1180, 5), (390, 0.12, 1460, 4), (560, 0.0, 1820, 3)]
        r = random.Random(11)
        k = 0
        for s, depth, y, n in rows:
            for i in range(n):
                x = (i + 0.5) / n * SW + r.uniform(-40, 40) + (s * 0.4 if n % 2 else 0)
                f = self.face(s, k, depth)
                img.paste(f, (int(x - f.width / 2), int(y - s)), f)
                k += 1
        self.img = img

    def frame(self, t):
        if self.img is None:
            self.build()
        return self.img


# ------------------------------------------------------------------ façade de la supérette
class ShopFront:
    def __init__(self):
        self.bg = None

    def build(self):
        img = gfx.vgrad(SW, SH, [(0, (10, 13, 22)), (0.5, (36, 42, 56)), (1, (16, 17, 20))])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, SW, 1020], fill=(44, 48, 58))
        r = random.Random(2)
        for row in range(4):
            for col in range(4):
                x, y = 80 + col * 280, 120 + row * 225
                lit = r.random() < 0.15
                d.rectangle([x, y, x + 150, y + 170], fill=(255, 196, 120) if lit else (20, 24, 34))
                d.rectangle([x - 10, y + 170, x + 160, y + 182], fill=(26, 28, 34))
        d.rectangle([0, 1020, SW, 1100], fill=(14, 40, 34))  # enseigne
        win = gfx.vgrad(880, 560, [(0, (180, 214, 204)), (1, (120, 150, 146))])
        wd = ImageDraw.Draw(win)
        for row in range(4):
            y = 60 + row * 130
            wd.rectangle([0, y + 90, 880, y + 100], fill=(70, 80, 80))
            x = 10
            while x < 860:
                w = r.randint(14, 40)
                hh = r.randint(40, 85)
                c = r.choice([(170, 40, 40), (40, 90, 170), (210, 170, 40), (50, 140, 70), (200, 200, 200)])
                wd.rectangle([x, y + 90 - hh, x + w, y + 90], fill=c)
                x += w + 4
        img.paste(win, (60, 1120))
        d.rectangle([700, 1120, 940, 1680], fill=(150, 186, 178))  # porte vitrée
        d.rectangle([700, 1120, 940, 1680], outline=(30, 34, 38), width=14)
        d.rectangle([40, 1100, 60, 1700], fill=(30, 34, 38))
        d.rectangle([940, 1100, 1140, 1700], fill=(40, 44, 50))
        d.rectangle([0, 1680, SW, 1720], fill=(60, 62, 66))  # bordure trottoir
        d.rectangle([0, 1720, SW, SH], fill=(30, 31, 35))
        refl = win.transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.32))
        img.paste(ImageChops.add(img.crop((60, 1720, 940, 2112)), refl.crop((0, 0, 880, 392))), (60, 1720))
        add_glow(img, 500, 1060, 560, 140, (120, 255, 200), 0.6)
        sign = text_sprite("SUPÉRETTE", font("din", 110), fill=(225, 255, 240), pad=4)
        img.paste(sign, (int(500 - sign.width / 2), 1010), sign)
        add_glow(img, 330, 1180, 170, 60, (255, 50, 40), 0.7)
        o = text_sprite("OUVERT 24/24", font("din", 54), fill=(255, 90, 80), pad=4)
        img.paste(o, (int(330 - o.width / 2), 1155), o)
        add_glow(img, 500, 1400, 700, 500, (140, 200, 190), 0.25)
        self.bg = img

    def frame(self, t):
        if self.bg is None:
            self.build()
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        t0 = T("emma", 3)
        p = (t - t0) / (T("c'est") - 0.4 - t0)
        # silhouettes aux yeux noirs qui approchent dans le brouillard, à gauche
        for i, (x0, sc) in enumerate(((-60, 0.55), (60, 0.62), (170, 0.5), (1120, 0.58))):
            x = x0 + (t - t0) * (14 if x0 < 600 else -10)
            person(d, x, 1700, 560 * sc, mix((22, 24, 30), FOG, 0.35), facing="front", eyes="black",
                   skin=mix((160, 156, 152), FOG, 0.35), phase=t * 3 + i, stride=0.4)
        if p < 1.0:
            xe = 80 + 760 * ease_out(max(0, p))
            ph = (t - t0) * 11
            person(d, xe - 90, 1990, 420, ADAM_HOODIE, kind="child", phase=ph + 1, stride=1.2, lean=0.05, backpack=ADAM_BAG)
            person(d, xe + 40, 2010, 620, EMMA_COAT, kind="woman", phase=ph, stride=1.2, lean=0.06,
                   scarf=EMMA_SCARF, hair=EMMA_HAIR, coat_len=0.3, arm_up=(-1, xe - 140, 1990 - 240))
        return img


# ------------------------------------------------------------------ enterrement (flash-back)
class Funeral:
    def __init__(self):
        self.bg = None
        self.rain = []

    def build(self):
        img = gfx.vgrad(SW, SH, [(0, (120, 124, 128)), (0.5, (150, 152, 154)), (0.55, (70, 72, 70)), (1, (36, 36, 34))])
        d = ImageDraw.Draw(img)
        r = random.Random(4)

        def branch(x, y, ang, ln, w, depth):
            if depth == 0 or ln < 6:
                return
            x2, y2 = x + math.cos(ang) * ln, y + math.sin(ang) * ln
            d.line([(x, y), (x2, y2)], fill=(60, 62, 64), width=max(1, int(w)))
            for _ in range(2):
                branch(x2, y2, ang + r.uniform(-0.6, 0.6), ln * r.uniform(0.6, 0.78), w * 0.68, depth - 1)

        branch(150, 1180, -math.pi / 2 - 0.1, 240, 26, 8)
        branch(1050, 1180, -math.pi / 2 + 0.15, 200, 20, 8)
        for i in range(14):  # tombes au loin
            x = i * 95 + r.randint(-20, 20)
            y = 1150 + r.randint(-10, 30)
            c = mix((90, 92, 92), (150, 152, 154), 0.5)
            if r.random() < 0.3:
                d.rectangle([x + 20, y - 110, x + 34, y], fill=c)
                d.rectangle([x, y - 85, x + 54, y - 72], fill=c)
            else:
                d.rounded_rectangle([x, y - 90, x + 60, y], 22, fill=c)
        # terre fraîche
        d.ellipse([60, 1560, 1130, 2000], fill=(52, 42, 34))
        d.ellipse([140, 1600, 1050, 1900], fill=(64, 52, 42))
        # stèle
        stone = gfx.smooth_noise(560, 760, 12, seed=7)
        st = Image.fromarray((40 + stone * 40).astype(np.uint8), "L").convert("RGB")
        m = Image.new("L", st.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, 560, 760], 120, fill=255)
        img.paste(st, (314, 900), m)
        sd = ImageDraw.Draw(img)
        for txt, sz, y in (("THOMAS", 110, 1010), ("1989 — 2026", 58, 1160), ("Mari et papa adoré", 46, 1250)):
            f = font("din", sz)
            bb = f.getbbox(txt)
            x = SW / 2 - (bb[2] - bb[0]) / 2
            sd.text((x + 2, y + 3), txt, font=f, fill=(120, 120, 118))
            sd.text((x, y), txt, font=f, fill=(18, 18, 18))
        for i in range(90):  # couronne de fleurs
            a = i / 90 * math.tau
            rr_ = 190 + r.uniform(-25, 25)
            x, y = SW / 2 + math.cos(a) * rr_, 1650 + math.sin(a) * rr_ * 0.38
            sd.ellipse([x - 30, y - 18, x + 30, y + 18], fill=(36, 60, 40))
        for i in range(70):
            a = r.uniform(0, math.tau)
            rr_ = 190 + r.uniform(-30, 30)
            x, y = SW / 2 + math.cos(a) * rr_, 1650 + math.sin(a) * rr_ * 0.38 - 6
            sd.ellipse([x - 17, y - 14, x + 17, y + 14], fill=(160, 26, 32) if r.random() < 0.7 else (225, 225, 215))
        self.bg = img
        rr = np.random.default_rng(3)
        for k in range(6):
            lay = Image.new("L", (SW, SH), 0)
            ld = ImageDraw.Draw(lay)
            for _ in range(260):
                x, y = rr.uniform(0, SW), rr.uniform(0, SH)
                ln = rr.uniform(40, 110)
                ld.line([(x, y), (x - ln * 0.15, y + ln)], fill=int(rr.uniform(40, 110)), width=2)
            self.rain.append(lay)

    def frame(self, t):
        if self.bg is None:
            self.build()
        lay = self.rain[int(t * 24) % len(self.rain)]
        return Image.composite(Image.new("RGB", (SW, SH), (210, 214, 220)), self.bg, lay)


# ------------------------------------------------------------------ téléphone
class Phone:
    def __init__(self):
        self.bg = None
        self.t_buzz = T("vibré") - 0.6
        self.t_msg = T("message") - 0.15

    def build(self):
        img = Image.new("RGB", (SW, SH), (8, 9, 12))
        r = random.Random(6)
        for _ in range(26):  # bokeh rayonnages
            x, y, rr = r.uniform(0, SW), r.uniform(0, SH), r.uniform(30, 110)
            add_glow(img, x, y, rr, rr, r.choice([(90, 40, 40), (40, 70, 110), (110, 100, 40), (60, 110, 90)]), 0.6, power=1.2)
        add_glow(img, SW / 2, SH * 0.5, 700, 900, (60, 90, 120), 0.35)
        self.bg = img
        self.wall = gfx.vgrad(560, 1180, [(0, (40, 30, 44)), (0.5, (90, 52, 48)), (1, (20, 18, 30))])
        wd = ImageDraw.Draw(self.wall)  # photo de couple floutée en fond d'écran
        person(wd, 230, 1180, 760, (16, 14, 20), facing="back", kind="woman", hair=(10, 8, 10))
        person(wd, 360, 1180, 840, (14, 12, 18), facing="back", hair=(10, 8, 10))
        self.wall = self.wall.filter(ImageFilter.GaussianBlur(16))

    def phone_img(self, t):
        pw, ph = 620, 1260
        im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, pw, ph], 96, fill=(18, 18, 20, 255))
        d.rounded_rectangle([3, 3, pw - 3, ph - 3], 94, outline=(70, 70, 76, 255), width=3)
        on = t >= self.t_buzz
        scr = Image.new("RGBA", (pw - 40, ph - 40), (0, 0, 0, 255))
        if on:
            scr.paste(self.wall.resize(scr.size), (0, 0))
            sd = ImageDraw.Draw(scr)
            sd.text((scr.width / 2, 120), "dimanche 8 novembre", font=font("sf", 34), fill=(235, 235, 240), anchor="mm")
            sd.text((scr.width / 2, 230), "6:17", font=font("sf", 170), fill=(245, 245, 250), anchor="mm")
            if t >= self.t_msg:
                k = ease_out((t - self.t_msg) / 0.35)
                y = 380 + (1 - k) * -60
                card = Image.new("RGBA", (scr.width - 40, 230), (0, 0, 0, 0))
                cd = ImageDraw.Draw(card)
                cd.rounded_rectangle([0, 0, card.width, card.height], 36, fill=(40, 40, 46, int(225 * k)))
                cd.rounded_rectangle([24, 26, 92, 94], 18, fill=(52, 199, 89, int(255 * k)))
                cd.ellipse([38, 40, 78, 74], fill=(255, 255, 255, int(255 * k)))
                cd.polygon([(44, 68), (40, 84), (56, 72)], fill=(255, 255, 255, int(255 * k)))
                cd.text((112, 30), "Thomas", font=font("sf", 36), fill=(255, 255, 255, int(255 * k)))
                cd.text((card.width - 24, 34), "maintenant", font=font("sf", 26), fill=(170, 170, 176, int(255 * k)), anchor="ra")
                msg1, msg2 = "N'ouvre surtout pas.", "Je suis caché dans la réserve."
                cd.text((112, 84), msg1, font=font("sf", 33), fill=(240, 240, 245, int(255 * k)))
                cd.text((112, 130), msg2, font=font("sf", 33), fill=(240, 240, 245, int(255 * k)))
                scr.alpha_composite(card, (20, int(y)))
        m = Image.new("L", scr.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, scr.width, scr.height], 76, fill=255)
        im.paste(scr, (20, 20), m)
        d.rounded_rectangle([pw / 2 - 90, 40, pw / 2 + 90, 92], 26, fill=(0, 0, 0, 255))
        return im

    def frame(self, t):
        if self.bg is None:
            self.build()
        img = self.bg.copy()
        buzz = 0.0
        for tb in (self.t_buzz, self.t_buzz + 0.75):
            if 0 <= t - tb < 0.45:
                buzz = 1.0
        ph = self.phone_img(t)
        ang = -5 + (math.sin(t * 90) * 1.6 if buzz else 0)
        ph = ph.rotate(ang, resample=Image.BICUBIC, expand=True)
        if t >= self.t_buzz:
            add_glow(img, SW / 2, SH * 0.5, 620, 900, (90, 70, 80), 0.5)
        x = SW / 2 - ph.width / 2 + (random.uniform(-6, 6) if buzz else 0)
        y = SH * 0.5 - ph.height / 2 + 60
        img.paste(ph, (int(x), int(y)), ph)
        d = ImageDraw.Draw(img)
        sk = (70, 60, 58)  # doigts
        d.rounded_rectangle([int(x) + 10, int(y) + 700, int(x) + 80, int(y) + 1000], 34, fill=sk)
        for i in range(3):
            d.rounded_rectangle([int(x) + ph.width - 70, int(y) + 560 + i * 120, int(x) + ph.width + 40, int(y) + 660 + i * 120], 40, fill=sk)
        return img


# ------------------------------------------------------------------ allée + porte de la réserve
class Aisle:
    def __init__(self):
        self.bg = None
        self.t_feet = T("magasin")

    def build(self):
        img = Image.new("RGB", (SW, SH), (10, 11, 13))
        d = ImageDraw.Draw(img)
        vx, vy = SW / 2, 980
        # mur du fond + porte
        bw, bh = 520, 640
        d.rectangle([vx - bw / 2, vy - bh * 0.62, vx + bw / 2, vy + bh * 0.38], fill=(64, 68, 66))
        self.door = (vx - 110, vy - 210, vx + 110, vy + 243)
        d.rectangle(self.door, fill=(92, 98, 96))
        d.rectangle(self.door, outline=(40, 42, 42), width=6)
        d.rectangle([vx + 66, vy + 10, vx + 98, vy + 22], fill=(170, 170, 170))
        sign = pill("RÉSERVE — PRIVÉ", font("din", 34), bg=(230, 230, 225), fg=(170, 20, 20), radius=4)
        img.paste(sign, (int(vx - sign.width / 2), int(vy - 300)), sign)
        # sol carrelé
        for (pts, col) in (([(0, SH), (SW, SH), (vx + bw / 2, vy + bh * 0.38), (vx - bw / 2, vy + bh * 0.38)], (54, 56, 56)),
                           ([(0, 0), (SW, 0), (vx + bw / 2, vy - bh * 0.62), (vx - bw / 2, vy - bh * 0.62)], (24, 25, 28))):
            d.polygon(pts, fill=col)
        for i in range(-8, 9):
            d.line([(vx + i * 30, vy + bh * 0.38), (SW / 2 + i * 260, SH)], fill=(40, 42, 42), width=2)
        for k in range(1, 12):
            z = 1 / (k * 0.35 + 0.0)
            y = vy + bh * 0.38 + (SH - vy - bh * 0.38) * (1 - 1 / (1 + k * 0.4))
            d.line([(0, y), (SW, y)], fill=(40, 42, 42), width=2)
        # rayonnages
        r = random.Random(12)
        for side in (-1, 1):
            xo = 0 if side < 0 else SW
            xi = vx + side * bw / 2
            d.polygon([(xo, -200), (xi, vy - bh * 0.62), (xi, vy + bh * 0.38), (xo, SH + 200)], fill=(26, 28, 32))
            for lv in range(7):
                fy0 = -200 + lv * 330
                fy1 = vy - bh * 0.62 + lv * (bh / 6.0)
                d.line([(xo, fy0 + 330), (xi, fy1 + bh / 6.0)], fill=(70, 72, 76), width=8)
                for j in range(26):  # produits
                    k = j / 26
                    x = xo + (xi - xo) * k
                    yb = (fy0 + 330) + ((fy1 + bh / 6.0) - (fy0 + 330)) * k
                    hh = (300 * (1 - k) + 40 * k) * r.uniform(0.4, 0.8)
                    ww = (90 * (1 - k) + 12 * k) * r.uniform(0.5, 0.9)
                    c = r.choice([(150, 30, 30), (30, 80, 150), (200, 160, 40), (40, 120, 60), (180, 180, 180)])
                    d.rectangle([x - ww / 2, yb - hh, x + ww / 2, yb], fill=tuple(int(v * (0.35 + 0.2 * k)) for v in c))
        # néons au plafond
        self.tubes = []
        for k in range(5):
            y = vy - bh * 0.62 - (vy - bh * 0.62) * (1 - 1 / (1 + k * 0.7)) * 0.9 - 10
            w = 60 + k * 120
            self.tubes.append((vx, y, w))
            d.rectangle([vx - w / 2, y - 6 - k * 3, vx + w / 2, y + 6 + k * 3], fill=(220, 240, 235))
        self.bg = img

    def frame(self, t):
        if self.bg is None:
            self.build()
        img = self.bg.copy()
        flick = (int(t * 17) % 7 != 0) and (int(t * 5.3) % 5 != 0)
        for i, (x, y, w) in enumerate(self.tubes):
            on = flick or i != 0
            if on:
                add_glow(img, x, y, w * 1.4, 120 + i * 30, (150, 210, 200), 0.35)
            else:
                ImageDraw.Draw(img).rectangle([x - w / 2, y - 6, x + w / 2, y + 6], fill=(40, 44, 44))
        x0, y0, x1, y1 = self.door
        d = ImageDraw.Draw(img)
        # filet de lumière sous la porte… et l'ombre de deux pieds
        d.rectangle([x0 + 6, y1 - 6, x1 - 6, y1 + 2], fill=(255, 220, 150))
        add_glow(img, (x0 + x1) / 2, y1, 200, 40, (255, 190, 110), 0.5)
        if t > self.t_feet:
            k = ease((t - self.t_feet) / 0.8)
            for fx in (-50, 25):
                d.rectangle([(x0 + x1) / 2 + fx, y1 - 7, (x0 + x1) / 2 + fx + 34 * k, y1 + 3], fill=(10, 8, 8))
        return img


class Handle:
    def __init__(self):
        self.bg = None
        self.t0 = T("poignée")
        self.t1 = T("deux") - 0.1

    def build(self):
        n = gfx.smooth_noise(SW, SH, 80, seed=31)
        n2 = gfx.smooth_noise(SW, SH, 4, seed=32, octaves=1)
        base = np.stack([82 + 0 * n, 90 + 0 * n, 86 + 0 * n], -1) * (0.8 + 0.25 * n + 0.08 * n2)[..., None]
        yy, xx = np.mgrid[0:SH, 0:SW]
        light = np.clip(1.2 - np.hypot(xx - 300, yy - 300) / 1800, 0.35, 1)
        img = Image.fromarray((base * light[..., None]).clip(0, 255).astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img)
        r = random.Random(1)
        for _ in range(60):  # rayures
            x, y = r.uniform(0, SW), r.uniform(0, SH)
            d.line([(x, y), (x + r.uniform(-80, 80), y + r.uniform(-20, 20))], fill=(120, 126, 122), width=1)
        px, py = 470, 1010
        plate = gfx.vgrad(150, 620, [(0, (190, 192, 196)), (0.5, (120, 122, 128)), (1, (70, 72, 76))])
        m = Image.new("L", plate.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, 150, 620], 30, fill=255)
        shp = Image.new("L", (SW, SH), 0)
        ImageDraw.Draw(shp).rounded_rectangle([px - 75 + 18, py - 180 + 22, px + 75 + 18, py + 440 + 22], 30, fill=160)
        img = Image.composite(Image.new("RGB", (SW, SH), (10, 10, 12)), img, shp.filter(ImageFilter.GaussianBlur(14)))
        img.paste(plate, (px - 75, py - 180), m)
        d = ImageDraw.Draw(img)
        d.ellipse([px - 20, py + 280, px + 20, py + 320], fill=(10, 10, 12))
        d.rectangle([px - 8, py + 305, px + 8, py + 350], fill=(10, 10, 12))
        d.ellipse([px - 70, py - 70, px + 70, py + 70], fill=(150, 152, 158))
        d.ellipse([px - 56, py - 56, px + 56, py + 56], fill=(110, 112, 118))
        self.bg = img
        self.pivot = (px, py)
        lev = Image.new("RGBA", (1000, 1000), (0, 0, 0, 0))
        g = gfx.vgrad(470, 96, [(0, (230, 232, 236)), (0.35, (170, 172, 178)), (1, (60, 62, 68))]).convert("RGBA")
        mm = Image.new("L", g.size, 0)
        ImageDraw.Draw(mm).rounded_rectangle([0, 0, 470, 96], 48, fill=255)
        lev.paste(g, (500 - 30, 500 - 48), mm)
        rose = Image.new("L", (1000, 1000), 0)
        ImageDraw.Draw(rose).ellipse([500 - 58, 500 - 58, 500 + 58, 500 + 58], fill=255)
        lev.paste((175, 177, 182, 255), (0, 0), rose)
        self.lever = lev
        sh = Image.new("RGBA", (1000, 1000), (0, 0, 0, 0))
        sh.paste((0, 0, 0, 170), (0, 0), lev.getchannel("A"))
        self.lshadow = sh.filter(ImageFilter.GaussianBlur(14))

    def angle(self, t):
        k = ease((t - self.t0) / (self.t1 - self.t0))
        jit = math.sin(t * 31) * 0.8 * (0 < k < 1)
        return -(40 * k + jit)

    def frame(self, t):
        if self.bg is None:
            self.build()
        img = self.bg.copy().convert("RGBA")
        a = self.angle(t)
        px, py = self.pivot
        sh = self.lshadow.rotate(a, resample=Image.BICUBIC, center=(500, 500))
        img.alpha_composite(sh, (px - 500 + 22, py - 500 + 28))
        lv = self.lever.rotate(a, resample=Image.BICUBIC, center=(500, 500))
        img.alpha_composite(lv, (px - 500, py - 500))
        img = img.convert("RGB")
        add_glow(img, px + 120, py - 40, 260, 120, (60, 70, 70), 0.3)
        return img


# ------------------------------------------------------------------ écran partagé + question
class Split:
    def __init__(self, glass, aisle):
        self.glass, self.aisle = glass, aisle

    def frame(self, t):
        top = self.glass.frame(t, force_reveal=1.0)
        bot = self.aisle.frame(t)
        img = Image.new("RGB", (SW, SH), (0, 0, 0))
        img.paste(top.crop((0, 250, SW, 1306)), (0, 0))
        x0, y0, x1, y1 = self.aisle.door
        cyc = (y0 + y1) / 2
        crop = bot.crop((int(SW / 2 - 300), int(cyc - 290), int(SW / 2 + 300), int(cyc + 290))).resize((SW, int(SH - 1056)), Image.BICUBIC)
        img.paste(crop, (0, 1056))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 1046, SW, 1066], fill=RED)
        add_glow(img, SW / 2, 1056, SW * 0.7, 60, (255, 40, 30), 0.6)
        for txt, y in (("DEHORS", 940), ("RÉSERVE", 1100)):
            p = pill(txt, font("mono", 40), bg=(255, 255, 255), fg=(10, 10, 10))
            img.paste(p, (90, y), p)
        return img


class Question:
    def __init__(self, glass, aisle):
        self.glass, self.aisle = glass, aisle
        self.bg = None
        self.tq, self.ta, self.tb = T("et", 3), T("a", 2), T("b", 1)
        self.tc, self.tn = T("écrivez"), T("suite")

    def build(self):
        g = self.glass.frame(10.0, force_reveal=1.0)
        self.bg = ImageChops.multiply(g.filter(ImageFilter.GaussianBlur(18)), Image.new("RGB", (SW, SH), (90, 90, 100)))
        ta = self.glass.frame(10.0, force_reveal=1.0).crop((150, 520, 1040, 1180)).resize((200, 148))
        door = self.aisle.frame(10.0).crop((SW // 2 - 240, 740, SW // 2 + 240, 1095)).resize((200, 148))
        self.thumbs = {"A": ta, "B": door}

    def option(self, letter, line1, line2, hi):
        w, h = 900, 250
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        col = RED if letter == "A" else (70, 140, 255)
        d.rounded_rectangle([0, 0, w, h], 34, fill=(12, 12, 16, 235), outline=col + (255,), width=6 if hi else 3)
        d.ellipse([30, 60, 160, 190], fill=col + (255,))
        f = font("impact", 96)
        d.text((95, 125), letter, font=f, fill=(255, 255, 255), anchor="mm")
        im.paste(self.thumbs[letter], (w - 230, 50))
        d.rectangle([w - 230, 50, w - 30, 198], outline=(255, 255, 255, 160), width=2)
        d.text((190, 72), line1, font=font("impact", 54), fill=(255, 255, 255))
        d.text((190, 140), line2, font=font("impact", 54), fill=(255, 255, 255))
        return im

    def frame(self, t):
        if self.bg is None:
            self.build()
        img = self.bg.copy().convert("RGBA")
        cx = SW / 2 - 30
        k = ease_out((t - self.tq) / 0.4)
        q1 = text_sprite("ET VOUS,", font("impact", 120), stroke=8, shadow=8)
        q2 = text_sprite("QUE FERIEZ-VOUS ?", font("impact", 120), fill=(255, 255, 255), stroke=8, shadow=8)
        paste_center(img, q1, cx, 560 - (1 - k) * 60, alpha=k)
        paste_center(img, q2, cx, 700 - (1 - k) * 60, alpha=k)
        for letter, t0, y, l1, l2 in (("A", self.ta, 960, "OUVRIR AU MARI", "QUI EST DEHORS"),
                                      ("B", self.tb, 1250, "ALLER VOIR CELUI", "DANS LA RÉSERVE")):
            if t >= t0 - 0.1:
                kk = ease_out((t - t0 + 0.1) / 0.3)
                hi = t0 <= t < t0 + 2.4
                pulse = 1 + (0.04 * math.sin((t - t0) * 12) * max(0, 1 - (t - t0) / 1.2) if hi else 0)
                paste_center(img, self.option(letter, l1, l2, hi), cx - (1 - kk) * 300, y, alpha=kk, scale=pulse)
        if t >= self.tc:
            kk = ease_out((t - self.tc) / 0.3)
            p = pill("ÉCRIVEZ  A  OU  B  EN COMMENTAIRE", font("din", 60), bg=(255, 255, 255), fg=(0, 0, 0), padx=34, pady=18)
            paste_center(img, p, cx, 1500, alpha=kk, scale=1 + 0.03 * math.sin(t * 7))
        if t >= self.tn:
            kk = ease_out((t - self.tn) / 0.3)
            p = text_sprite("LA SUITE DANS L'ÉPISODE 2", font("impact", 78), fill=RED + (255,), stroke=6, shadow=6)
            paste_center(img, p, cx, 1660, alpha=kk)
        return img.convert("RGB")


# ------------------------------------------------------------------ découpage
def build_scenes():
    street, glass, eye, crowd = Street(), ShopGlass(), Eye(), Crowd()
    front, fun, phone, aisle, handle = ShopFront(), Funeral(), Phone(), Aisle(), Handle()
    split, quest = Split(glass, aisle), Question(glass, aisle)
    END = WORDS.end + 1.9
    S = [
        # id, début, rendu, caméra (zoom0, zoom1, centre0, centre1), réglages
        dict(id="S01_vitre_hook", t=0.0, fn=glass.frame, cam=(1.05, 1.18, (0.5, 0.42), (0.5, 0.40)), fog=0.12, shake=glass.shake, loc="SUPÉRETTE · PARIS 11E"),
        dict(id="S02_rembobinage", t=T("mais", 1), fn=street.frame, cam=(1.25, 1.05, (0.5, 0.48), (0.5, 0.48)), fog=0.35, glitch=(0.0, 1.0), loc="PARIS 11E · RUE OBERKAMPF"),
        dict(id="S03_rue_figee", t=T("en"), fn=street.frame, cam=(1.0, 1.08, (0.5, 0.47), (0.5, 0.47)), fog=0.35, loc="PARIS 11E · RUE OBERKAMPF"),
        dict(id="S04_conducteurs", t=T("les", 2), fn=street.frame, cam=(2.1, 2.3, (0.36, 0.5), (0.37, 0.5)), fog=0.3, loc="PARIS 11E · RUE OBERKAMPF"),
        dict(id="S05_passants", t=T("les", 3), fn=street.frame, cam=(1.7, 1.95, (0.5, 0.5), (0.5, 0.49)), fog=0.3, loc="PARIS 11E · RUE OBERKAMPF"),
        dict(id="S06_emma_adam", t=T("seules"), fn=lambda t: street.frame(t, emma=True), cam=(1.0, 1.12, (0.5, 0.55), (0.5, 0.52)), fog=0.3, loc="PARIS 11E · RUE OBERKAMPF",
             tags=[("EMMA", T("emma", 2), (0.36, 0.43)), ("ADAM · 6 ANS", T("adam"), (0.63, 0.55))]),
        dict(id="S07_reprise", t=T_30, fn=lambda t: street.frame(t, emma=True), cam=(1.12, 1.3, (0.5, 0.52), (0.5, 0.5)), fog=0.35, glitch=(0.0, 0.5), loc="PARIS 11E · RUE OBERKAMPF",
             tags=[("+30 SECONDES", T_30, (0.5, 0.33))]),
        dict(id="S08_yeux_noirs", t=T("mais", 2), fn=eye.frame, cam=(1.0, 1.15, (0.5, 0.48), (0.5, 0.48)), fog=0.05, flicker=0.15),
        dict(id="S09_foule", t=T("et", 2), fn=crowd.frame, cam=(1.0, 1.22, (0.5, 0.55), (0.5, 0.5)), fog=0.25, flicker=0.1, loc="PARIS 11E · RUE OBERKAMPF"),
        dict(id="S10_superette", t=T("emma", 3), fn=front.frame, cam=(1.08, 1.0, (0.45, 0.6), (0.55, 0.6)), fog=0.25, shake=lambda t: 3, loc="SUPÉRETTE · PARIS 11E"),
        dict(id="S11_vitre_thomas", t=T("c'est"), fn=glass.frame, cam=(1.0, 1.25, (0.5, 0.45), (0.5, 0.38)), fog=0.1, shake=glass.shake, loc="SUPÉRETTE · PARIS 11E",
             tags=[("THOMAS · SON MARI", T("thomas", 1), (0.5, 0.24))]),
        dict(id="S12_enterrement", t=T("pourtant"), fn=fun.frame, cam=(1.0, 1.1, (0.5, 0.55), (0.5, 0.52)), fog=0.15, grade="flashback", glitch=(0.0, 0.25), loc="IL Y A 3 JOURS · CIMETIÈRE",
             tags=[("ENTERRÉ IL Y A 3 JOURS", T("enterré"), (0.5, 0.36))]),
        dict(id="S13_vitre_ouvre", t=T("thomas", 2), fn=glass.frame, cam=(1.3, 1.45, (0.5, 0.38), (0.5, 0.36)), fog=0.1, shake=glass.shake, glitch=(0.0, 0.2), loc="SUPÉRETTE · PARIS 11E"),
        dict(id="S14_telephone", t=T("soudain"), fn=phone.frame, cam=(1.0, 1.18, (0.5, 0.5), (0.5, 0.42)), fog=0.05, loc="SUPÉRETTE · PARIS 11E"),
        dict(id="S15_reserve", t=T("emma", 4), fn=aisle.frame, cam=(1.0, 1.6, (0.5, 0.46), (0.5, 0.46)), fog=0.12, loc="SUPÉRETTE · RÉSERVE"),
        dict(id="S16_poignee", t=T("la", 4), fn=handle.frame, cam=(1.0, 1.12, (0.45, 0.48), (0.45, 0.48)), fog=0.05, flicker=0.2, loc="SUPÉRETTE · RÉSERVE"),
        dict(id="S17_deux_thomas", t=T("deux"), fn=split.frame, cam=(1.0, 1.06, (0.5, 0.5), (0.5, 0.5)), fog=0.08, glitch=(0.0, 0.35), loc="06:17 · DEUX THOMAS"),
        dict(id="S18_question", t=T("et", 3), fn=quest.frame, cam=(1.0, 1.0, (0.5, 0.5), (0.5, 0.5)), fog=0.0, captions=False, loc="ÉPISODE 1 · VOTRE CHOIX"),
    ]
    for i, s in enumerate(S):
        s["end"] = S[i + 1]["t"] if i + 1 < len(S) else END
    return S, END


# Mots-clés mis en rouge dans les sous-titres
KEYWORDS = {"MORT", "PARIS", "IMMOBILISÉS", "FIGÉS", "EMMA", "ADAM", "NOIRS", "THOMAS", "ENTERRÉ", "RÉSERVE",
            "VÉRITÉ", "DEUX", "6H17", "TERRIFIANT", "SURTOUT", "PAS.", "TOURNER", "DIRECTION", "VIBRÉ", "OUVRIR"}

#!/usr/bin/env python3
"""THE WORLD IN A DAY -- front page for Saturday 21 November 2026.

Draws a 1024x1024 newspaper front page entirely from code: a tiny
software rasterizer, an embedded 5x7 bitmap font, and a built-in PNG
encoder (zlib). No image files, no network, standard library only.

Output: $MAKEFUN_OUTPUT_DIR/entry.png (default /output).
Deterministic: the same input always produces byte-identical output.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (250, 246, 236)   # newsprint cream
INK = (20, 20, 20)        # near-black ink
RED = (178, 34, 34)       # masthead / accent red
BLUE = (30, 70, 140)      # section blue
GOLD = (198, 158, 40)     # badge gold
GRAY = (112, 112, 112)    # mid gray
LGRAY = (214, 212, 202)   # light rule gray
SKY = (196, 212, 224)     # scene sky
SLATE = (72, 74, 80)      # damaged buildings
ORANGE = (220, 110, 30)   # fire
GREEN = (40, 120, 60)     # globe land
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def fill_rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = c

    def rect(self, x, y, w, h, c, t=1):
        self.fill_rect(x, y, w, t, c)
        self.fill_rect(x, y + h - t, w, t, c)
        self.fill_rect(x, y, t, h, c)
        self.fill_rect(x + w - t, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            if t == 1:
                self.set(x, y, c)
            else:
                self.fill_rect(x - t // 2, y - t // 2, t, t, c)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def fill_circle(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def circle(self, cx, cy, r, c, t=2):
        for k in range(t):
            rr = r - k
            for a in range(360):
                rad = math.radians(a)
                self.set(cx + int(rr * math.cos(rad)),
                         cy + int(rr * math.sin(rad)), c)

    def fill_polygon(self, pts, c):
        # scanline even-odd fill
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                self.fill_rect(int(xs[j]), y, int(xs[j + 1]) - int(xs[j]) + 1, 1, c)

    def fill_triangle(self, p0, p1, p2, c):
        self.fill_polygon([p0, p1, p2], c)

# ------------------------------------------------------------------ font
# 5x7 bitmap font. Each glyph is 7 rows of 5 cells ('#' = ink).
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", "#.##.", "#..##"),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "&": (".##..", "#..#.", "#..#.", ".#...", "#.#.#", "#..#.", ".##.#"),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    "\u2022": (".....", ".....", ".##..", ".##..", ".....", ".....", "....."),
    "*": (".....", ".#.#.", ".###.", "#####", ".###.", ".#.#.", "....."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
}

BLANK = (".....", ".....", ".....", ".....", ".....", ".....", ".....")


def text_width(s, scale):
    return len(s) * 6 * scale - scale if s else 0


def draw_text(c, x, y, s, scale, color):
    cx = x
    for ch in s:
        glyph = FONT.get(ch, BLANK)
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "#":
                    c.fill_rect(cx + col * scale, y + row * scale,
                                scale, scale, color)
        cx += 6 * scale


def draw_text_centered(c, cx, y, s, scale, color):
    draw_text(c, cx - text_width(s, scale) // 2, y, s, scale, color)


def wrap_text(s, max_chars):
    lines = []
    for chunk in s.split("\n"):
        words = chunk.split(" ")
        cur = ""
        for w in words:
            if not cur:
                cur = w
            elif len(cur) + 1 + len(w) <= max_chars:
                cur += " " + w
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines


def draw_wrapped(c, x, y, s, scale, color, max_chars, leading):
    lines = wrap_text(s, max_chars)
    for i, ln in enumerate(lines):
        draw_text(c, x, y + i * leading, ln, scale, color)
    return y + len(lines) * leading


# ------------------------------------------------------------------ scenes
def draw_star(c, cx, cy, r_outer, r_inner, color):
    pts = []
    for i in range(10):
        r = r_outer if i % 2 == 0 else r_inner
        a = math.radians(-90 + i * 36)
        pts.append((cx + int(r * math.cos(a)), cy + int(r * math.sin(a))))
    c.fill_polygon(pts, color)


def draw_lead_scene(c, x, y, w, h):
    """Damaged city skyline after the strikes, with smoke, fire,
    and a rescue ambulance."""
    c.fill_rect(x, y, w, h, SKY)
    # smoke puffs
    for (sx, sy, sr, col) in ((x + 200, y + 22, 26, GRAY),
                              (x + 228, y + 12, 20, (150, 150, 150)),
                              (x + 430, y + 18, 24, GRAY),
                              (x + 452, y + 8, 16, (150, 150, 150))):
        c.fill_circle(sx, sy, sr, col)
    # buildings with jagged, broken tops
    ground = y + h - 16
    b1 = [(x + 16, ground), (x + 16, y + 78), (x + 40, y + 62),
          (x + 58, y + 74), (x + 84, y + 60), (x + 106, y + 78),
          (x + 106, ground)]
    c.fill_polygon(b1, SLATE)
    b2 = [(x + 122, ground), (x + 122, y + 48), (x + 150, y + 30),
          (x + 168, y + 46), (x + 196, y + 34), (x + 232, y + 48),
          (x + 232, ground)]
    c.fill_polygon(b2, (88, 90, 96))
    b3 = [(x + 248, ground), (x + 248, y + 84), (x + 272, y + 70),
          (x + 292, y + 82), (x + 322, y + 72), (x + 322, ground)]
    c.fill_polygon(b3, SLATE)
    b4 = [(x + 338, ground), (x + 338, y + 58), (x + 366, y + 42),
          (x + 388, y + 56), (x + 420, y + 44), (x + 438, y + 58),
          (x + 438, ground)]
    c.fill_polygon(b4, (88, 90, 96))
    # windows
    for bx, by, bw, bh in ((x + 16, y + 78, 90, 76), (x + 122, y + 48, 110, 106),
                           (x + 248, y + 84, 74, 70), (x + 338, y + 58, 100, 96)):
        for wy in range(by + 10, by + bh - 8, 18):
            for wx in range(bx + 10, bx + bw - 8, 18):
                c.fill_rect(wx, wy, 8, 10, (250, 220, 130))
    # cracks on the broken buildings
    c.line(x + 150, y + 48, x + 162, y + 92, INK, 2)
    c.line(x + 162, y + 92, x + 152, y + 120, INK, 2)
    c.line(x + 388, y + 56, x + 398, y + 96, INK, 2)
    # fire at the base of two buildings
    c.fill_triangle((x + 30, ground), (x + 58, ground), (x + 44, ground - 34), ORANGE)
    c.fill_triangle((x + 52, ground), (x + 80, ground), (x + 66, ground - 26), RED)
    c.fill_triangle((x + 250, ground), (x + 276, ground), (x + 263, ground - 28), ORANGE)
    # ground
    c.fill_rect(x, ground, w, 16, (60, 58, 52))
    # ambulance, bottom right
    ax, ay = x + 452, ground - 30
    c.fill_rect(ax, ay, 84, 28, WHITE)
    c.rect(ax, ay, 84, 28, INK, 2)
    c.fill_rect(ax + 10, ay + 8, 8, 22, RED)
    c.fill_rect(ax + 2, ay + 15, 24, 8, RED)
    c.fill_circle(ax + 18, ay + 30, 7, INK)
    c.fill_circle(ax + 66, ay + 30, 7, INK)
    c.fill_circle(ax + 18, ay + 30, 3, LGRAY)
    c.fill_circle(ax + 66, ay + 30, 3, LGRAY)


def draw_icon_mexico(c, x, y, s):
    """A gold sheriff-style badge with a star."""
    c.fill_circle(x + s // 2, y + s // 2, s // 2, GOLD)
    c.circle(x + s // 2, y + s // 2, s // 2, INK, 2)
    draw_star(c, x + s // 2, y + s // 2, s // 3, s // 7, INK)


def draw_icon_cop(c, x, y, s):
    """A globe with a small sun."""
    cx, cy, r = x + s // 2, y + s // 2, s // 2 - 2
    c.fill_circle(cx, cy, r, BLUE)
    c.circle(cx, cy, r, INK, 2)
    c.line(cx - r, cy, cx + r, cy, WHITE, 2)
    c.line(cx, cy - r, cx, cy + r, WHITE, 2)
    c.fill_circle(cx - r // 2, cy - r // 3, r // 3, GREEN)
    c.fill_circle(cx + r // 3, cy + r // 3, r // 4, GREEN)
    for k in range(8):
        a = math.radians(k * 45)
        x0 = cx + int((r + 3) * math.cos(a))
        y0 = cy + int((r + 3) * math.sin(a))
        x1 = cx + int((r + 5) * math.cos(a))
        y1 = cy + int((r + 5) * math.sin(a))
        c.line(x0, y0, x1, y1, GOLD, 2)


def draw_icon_markets(c, x, y, s):
    """A falling chart line with a red arrowhead."""
    c.fill_rect(x, y, s, s, WHITE)
    c.rect(x, y, s, s, INK, 2)
    pts = [(x + 6, y + 8), (x + 16, y + 16), (x + 24, y + 14),
           (x + 32, y + 26), (x + 40, y + 34)]
    for i in range(len(pts) - 1):
        c.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED, 3)
    c.fill_triangle((x + 40, y + 34), (x + 30, y + 32), (x + 38, y + 24), RED)
    c.line(x + 6, y + s - 6, x + s - 6, y + s - 6, INK, 2)


def draw_icon_mercury(c, x, y, s):
    """Mercury with craters on an orbit ring."""
    cx, cy = x + s // 2, y + s // 2
    c.circle(cx, cy, s // 2 - 2, INK, 2)
    c.fill_circle(cx, cy, s // 2 - 4, (160, 140, 120))
    for (ox, oy, orr) in ((-8, -6, 5), (6, 4, 4), (-2, 8, 3), (9, -8, 3)):
        c.fill_circle(cx + ox, cy + oy, orr, (120, 100, 84))
    c.fill_circle(cx + s // 2 - 2, cy - s // 2 + 4, 3, RED)


# -------------------------------------------------------------------- page
def draw_panel(c, x, y, w, h, kicker, headline, body, icon_fn):
    c.fill_rect(x, y, w, h, WHITE)
    c.rect(x, y, w, h, INK, 2)
    c.fill_rect(x, y, w, 4, RED)
    pad = 12
    draw_text(c, x + pad, y + 12, kicker, 2, RED)
    icon_fn(c, x + w - pad - 30, y + 4, 30)
    hy = y + 36
    for i, ln in enumerate(headline):
        draw_text(c, x + pad, hy + i * 24, ln, 3, INK)
    by = hy + len(headline) * 24 + 8
    draw_wrapped(c, x + pad, by, body, 2, INK, 30, 18)


def draw_page():
    c = Canvas(W, H, PAPER)

    # ---- masthead
    c.fill_rect(0, 0, W, 10, RED)
    draw_text_centered(c, W // 2, 26, "THE WORLD IN A DAY", 8, INK)
    draw_text_centered(c, W // 2, 92, "SATURDAY 21 NOVEMBER 2026", 4, RED)
    c.fill_rect(20, 126, W - 40, 3, INK)
    c.fill_rect(20, 132, W - 40, 1, INK)

    # ---- lead story (left)
    lx, ly, lw, lh = 20, 144, 576, 684
    c.fill_rect(lx, ly, lw, lh, WHITE)
    c.rect(lx, ly, lw, lh, INK, 2)
    draw_text(c, lx + 14, ly + 12, "UKRAINE - WAR", 2, RED)
    draw_text(c, lx + 14, ly + 36, "MISSILES HIT", 5, INK)
    draw_text(c, lx + 14, ly + 76, "KRYVYI RIH", 5, INK)
    draw_text(c, lx + 14, ly + 122, "DOUBLE-TAP STRIKE KILLS 2, WOUNDS 60", 2, INK)
    draw_lead_scene(c, lx + 14, ly + 150, lw - 28, 170)
    draw_text(c, lx + 14, ly + 328,
              "THE CENTRE OF KRYVYI RIH AFTER THE STRIKES.", 2, GRAY)
    body = (
        "RUSSIAN BALLISTIC MISSILES STRUCK THE CENTRE OF KRYVYI RIH, "
        "PRESIDENT ZELENSKYY'S HOMETOWN, ON FRIDAY NIGHT. TWO PEOPLE WERE "
        "KILLED - A 7-YEAR-OLD BOY AND A 20-YEAR-OLD PARAMEDIC. 60 WERE "
        "WOUNDED, 28 STILL IN HOSPITAL ON SATURDAY. ABOUT 25 FLATS, A "
        "HOSPITAL AND SCHOOLS WERE DAMAGED. FOLLOW-UP DRONES HIT RESCUERS. "
        "RUSSIA FIRED 3 MISSILES AND 148 DRONES ACROSS UKRAINE IN THE NIGHT."
    )
    draw_wrapped(c, lx + 14, ly + 356, body, 2, INK, 46, 18)
    # numbers box
    nx, ny, nw, nh = lx + 14, ly + 556, lw - 28, 112
    c.fill_rect(nx, ny, nw, nh, PAPER)
    c.rect(nx, ny, nw, nh, INK, 2)
    draw_text_centered(c, nx + nw // 2, ny + 10, "THE NIGHT IN NUMBERS", 2, RED)
    draw_text_centered(c, nx + nw // 2, ny + 36, "3 MISSILES - 148 DRONES", 3, INK)
    draw_text_centered(c, nx + nw // 2, ny + 66, "117 SHOT DOWN - 19 IMPACTS", 3, INK)

    # ---- four panels (right column, stacked)
    px, pw = 612, 392
    ph = 168
    gap = 8
    panels = [
        (px, 144, "MEXICO - CRIME", ["CARTEL BOSS CAPTURED"],
         "FAUSTO ISIDRO MEZA FLORES, 'EL CHAPO ISIDRO', SEIZED IN SINALOA. "
         "FBI TOP 10 FUGITIVE. $5M REWARD. 11 KILLED IN CARTEL VIOLENCE.",
         draw_icon_mexico),
        (px, 144 + (ph + gap), "ANTALYA - CLIMATE", ["COP31 IN OVERTIME"],
         "TALKS PAST THE FRIDAY DEADLINE, NO DEAL YET. DRAFT DROPS FOSSIL "
         "FUELS AND A $120BN FINANCE TARGET. EU: 'GOOD DEAL OR NO DEAL.'",
         draw_icon_cop),
        (px, 144 + 2 * (ph + gap), "MARKETS - ECONOMY",
         ["AI SELL-OFF", "ROCKS MARKETS"],
         "S&P 500 -3.7%. NASDAQ -5.3%. NVIDIA -14%. VIX NEAR 40.",
         draw_icon_markets),
        (px, 144 + 3 * (ph + gap), "SPACE - SCIENCE",
         ["BEPICOLOMBO", "AT MERCURY"],
         "ENTERED ORBIT AFTER AN 8-YEAR TRIP. ONLY THE 2ND MISSION EVER "
         "TO ORBIT MERCURY.",
         draw_icon_mercury),
    ]
    for (x, y, kicker, headline, body, icon_fn) in panels:
        draw_panel(c, x, y, pw, ph, kicker, headline, body, icon_fn)

    # ---- bottom strip: Peru quake
    sy = 840
    c.fill_rect(20, sy, W - 40, 72, WHITE)
    c.rect(20, sy, W - 40, 72, INK, 2)
    draw_text(c, 34, sy + 24, "PERU", 3, RED)
    draw_text(c, 34, sy + 48, "QUAKE", 3, RED)
    strip = ("MAGNITUDE 6.7 EARTHQUAKE STRUCK CENTRAL PERU ON FRIDAY "
             "EVENING, FELT IN LIMA. NO DEATHS AND NO MAJOR DAMAGE REPORTED.")
    draw_wrapped(c, 210, sy + 14, strip, 2, INK, 62, 20)

    # ---- ticker
    ty = 924
    c.fill_rect(20, ty, W - 40, 84, BLACK)
    draw_text(c, 34, ty + 12,
              "ALSO SATURDAY: BRAZIL: DENGUE CUT 69% IN KIDS \u2022 TRUMP WEIGHS IRAN STRIKES",
              2, WHITE)
    draw_text(c, 34, ty + 34,
              "BRITAIN-EU RESET \u2022 EU APPROVES 1BN EUROS FOR UKRAINE \u2022 HOUTHIS STRIKE RIYADH",
              2, WHITE)
    draw_text(c, 34, ty + 56,
              "TRUMP: STOP FUNDING UKRAINE, HE TOLD EUROPEAN LEADERS (REPORTED)",
              2, WHITE)
    return c


# --------------------------------------------------------------------- png
def chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return out


def encode_png(w, h, rgb):
    raw = b"".join(
        b"\x00" + bytes(rgb[y * w * 3:(y + 1) * w * 3]) for y in range(h)
    )
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    c = draw_page()
    data = encode_png(W, H, c.px)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes)" % (path, len(data)))


if __name__ == "__main__":
    main()

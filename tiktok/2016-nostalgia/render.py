"""Рендер TikTok-ролика «2026 — это новый 2016».

Вход: timeline.json и audio/*.mp3 (см. tts.py). Выход: out/nostalgia_2016_tiktok.mp4 (1080x1920, 30 fps).
Графика — pycairo (персонаж-телефончик, ретро/VHS-стиль), музыка и эффекты синтезируются numpy.
"""
import json
import math
import random
import re
import subprocess
import sys
from pathlib import Path

import cairo
import numpy as np

HERE = Path(__file__).parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
W, H, FPS, SR = 1080, 1920, 30, 44100
TL = json.loads((HERE / "timeline.json").read_text())
SEGS = TL["segments"]
TOTAL = TL["total"]

FONT = "Inter Black"
PINK = (1.0, 0.42, 0.72)
CYAN = (0.30, 0.92, 1.0)
YELLOW = (1.0, 0.88, 0.30)
WHITE = (1, 1, 1)
INK = (0.12, 0.07, 0.20)
PURPLE = (0.45, 0.30, 0.95)
RAINBOW = [(1, 0.25, 0.3), (1, 0.6, 0.2), (1, 0.9, 0.3), (0.3, 0.85, 0.4), (0.3, 0.6, 1), (0.6, 0.35, 0.95)]


# ---------------------------------------------------------------- easing / helpers
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, t0, d):
    return clamp((t - t0) / d)


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_back(x, k=1.9):
    x -= 1
    return 1 + (k + 1) * x ** 3 + k * x ** 2


def pop(t, t0, d=0.35):
    p = prog(t, t0, d)
    return 0.0 if p <= 0 else ease_back(p)


def rrect(c, x, y, w, h, r):
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    c.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    c.close_path()


def fill_rrect(c, x, y, w, h, r, color, alpha=1.0, stroke=None, lw=8):
    rrect(c, x, y, w, h, r)
    c.set_source_rgba(*color, alpha)
    if stroke:
        c.fill_preserve()
        c.set_source_rgb(*stroke)
        c.set_line_width(lw)
        c.stroke()
    else:
        c.fill()


def text(c, s, x, y, size, color=WHITE, align="c", outline=0, outline_color=INK, alpha=1.0, font=FONT):
    c.select_font_face(font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    c.set_font_size(size)
    ext = c.text_extents(s)
    tx = x - ext.x_advance / 2 if align == "c" else (x - ext.x_advance if align == "r" else x)
    c.move_to(tx, y + size * 0.36)
    c.text_path(s)
    if outline:
        c.set_source_rgba(*outline_color, alpha)
        c.set_line_width(outline)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.stroke_preserve()
    c.set_source_rgba(*color, alpha)
    c.fill()


def text_w(c, s, size, font=FONT):
    c.select_font_face(font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    c.set_font_size(size)
    return c.text_extents(s).x_advance


def scaled(c, cx, cy, s, rot=0.0):
    c.save()
    c.translate(cx, cy)
    if rot:
        c.rotate(rot)
    c.scale(max(s, 1e-4), max(s, 1e-4))
    c.translate(-cx, -cy)


def pill(c, s, cx, cy, size, bg, fg, pad=28, alpha=1.0):
    w = text_w(c, s, size) + pad * 2
    h = size * 1.55
    fill_rrect(c, cx - w / 2, cy - h / 2, w, h, h / 2, bg, alpha, stroke=INK, lw=6)
    text(c, s, cx, cy, size, fg, alpha=alpha)


# ---------------------------------------------------------------- voice envelope (lip-sync)
def load_audio(path):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"])
    return np.frombuffer(raw, dtype=np.float32).copy()


VOICE = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for s in SEGS:
    a = load_audio(HERE / "audio" / f"{s['id']}.mp3")
    i = int(s["start"] * SR)
    VOICE[i:i + len(a)] += a[: len(VOICE) - i]
_hop = SR // FPS
ENV = np.array([np.sqrt(np.mean(VOICE[i * _hop:(i + 1) * _hop] ** 2) + 1e-12) for i in range(len(VOICE) // _hop)])
ENV = np.clip(ENV / (np.percentile(ENV[ENV > 1e-3], 95) + 1e-9), 0, 1)


def mouth(t):
    i = int(t * FPS)
    return float(ENV[i]) if 0 <= i < len(ENV) else 0.0


# ---------------------------------------------------------------- character: телефончик
def draw_phone(c, cx, cy, s, t, dog=0.0, rainbow=0.0, sad=0.0, wave=0.0, talk=True):
    c.save()
    c.translate(cx, cy)
    c.scale(s, s)
    c.translate(0, math.sin(t * 4) * 6)
    c.rotate(math.sin(t * 1.7) * 0.03)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    # legs
    c.set_source_rgb(*INK); c.set_line_width(16)
    for sx in (-1, 1):
        c.move_to(sx * 60, 250); c.line_to(sx * 70, 340); c.stroke()
        c.save(); c.translate(sx * 82, 345); c.scale(1.5, 1); c.arc(0, 0, 18, 0, 2 * math.pi); c.restore(); c.fill()
    # arms (one waves)
    for sx in (-1, 1):
        ang = -0.6 - 1.2 * wave * (0.5 + 0.5 * math.sin(t * 9)) if sx == 1 else 0.5
        ex, ey = sx * (150 + 110 * math.cos(ang)), 30 + 110 * math.sin(ang)
        c.move_to(sx * 150, 30); c.line_to(ex, ey); c.set_line_width(16); c.set_source_rgb(*INK); c.stroke()
        c.arc(ex, ey, 24, 0, 2 * math.pi); c.set_source_rgb(1, 1, 1); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(7); c.stroke()
    # dog ears (behind body)
    if dog > 0:
        for sx in (-1, 1):
            c.save(); c.translate(sx * 175, -215); c.rotate(sx * (0.35 + 0.1 * math.sin(t * 6))); c.scale(dog, dog)
            c.save(); c.scale(0.6, 1.1); c.arc(0, 60, 90, 0, 2 * math.pi); c.restore()
            c.set_source_rgb(0.62, 0.40, 0.25); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(7); c.stroke()
            c.save(); c.scale(0.35, 0.8); c.arc(0, 90, 80, 0, 2 * math.pi); c.restore()
            c.set_source_rgb(0.9, 0.62, 0.55); c.fill()
            c.restore()
    # body
    fill_rrect(c, -160, -280, 320, 540, 60, (0.97, 0.97, 1.0), stroke=INK, lw=10)
    g = cairo.LinearGradient(0, -240, 0, 200)
    g.add_color_stop_rgb(0, *CYAN); g.add_color_stop_rgb(1, *PINK)
    rrect(c, -130, -235, 260, 430, 34); c.set_source(g); c.fill()
    c.arc(0, -258, 8, 0, 2 * math.pi); c.set_source_rgb(*INK); c.fill()
    fill_rrect(c, -40, 215, 80, 22, 11, (0.8, 0.8, 0.88))
    # face
    blink = (t % 3.3) < 0.12
    for sx in (-1, 1):
        ex, ey = sx * 55, -90
        if blink:
            c.move_to(ex - 26, ey); c.line_to(ex + 26, ey); c.set_source_rgb(*INK); c.set_line_width(8); c.stroke()
        else:
            c.save(); c.translate(ex, ey); c.scale(0.85, 1); c.arc(0, 0, 34, 0, 2 * math.pi); c.restore()
            c.set_source_rgb(1, 1, 1); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(7); c.stroke()
            c.arc(ex + 4, ey + 6, 16, 0, 2 * math.pi); c.set_source_rgb(*INK); c.fill()
            c.arc(ex + 10, ey, 6, 0, 2 * math.pi); c.set_source_rgb(1, 1, 1); c.fill()
        # brows
        tilt = sx * 12 * sad
        c.move_to(ex - 26, ey - 52 - tilt); c.line_to(ex + 26, ey - 52 + tilt)
        c.set_source_rgb(*INK); c.set_line_width(8); c.stroke()
        c.arc(sx * 85, -20, 22, 0, 2 * math.pi); c.set_source_rgba(1, 0.3, 0.5, 0.45); c.fill()
    m = mouth(t) if talk else 0.0
    if dog > 0:
        c.save(); c.translate(0, -30); c.scale(dog, dog)
        c.save(); c.scale(1.4, 1); c.arc(0, 0, 18, 0, 2 * math.pi); c.restore(); c.set_source_rgb(*INK); c.fill()
        c.restore()
    my = 20
    if m > 0.08 or rainbow > 0:
        o = max(m, 0.6 if rainbow > 0 else 0)
        c.save(); c.translate(0, my); c.scale(1, 0.3 + o * 0.8); c.arc(0, 0, 38 - 10 * sad, 0, 2 * math.pi); c.restore()
        c.set_source_rgb(0.45, 0.08, 0.2); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(6); c.stroke()
        if dog > 0:
            c.save(); c.translate(0, my + 25 + o * 10); c.scale(0.8, 1.2); c.arc(0, 0, 18 * dog, 0, math.pi); c.restore()
            c.set_source_rgb(1, 0.45, 0.55); c.fill()
    else:
        c.set_source_rgb(*INK); c.set_line_width(7)
        if sad > 0.5:
            c.arc_negative(0, my + 30, 30, -0.4, -math.pi + 0.4)
        else:
            c.arc(0, my - 10, 30, 0.4, math.pi - 0.4)
        c.stroke()
    c.restore()
    # rainbow from the mouth (screen space so it flows straight down)
    if rainbow > 0:
        L = 620 * rainbow
        x0, y0 = cx, cy + my * s + 10
        bw = 30 * s
        for k, col in enumerate(RAINBOW):
            off = (k - 2.5) * bw
            c.move_to(x0 + off * 0.5, y0)
            for j in range(0, 21):
                yy = y0 + L * j / 20
                spread = 1 + 1.6 * j / 20
                xx = x0 + off * spread + math.sin(t * 6 + j * 0.5) * 12 * j / 20
                c.line_to(xx, yy)
            c.set_source_rgba(*col, 0.92)
            c.set_line_width(bw * 1.05)
            c.stroke()


# ---------------------------------------------------------------- background (retro / VHS)
random.seed(16)
SPARKS = [(random.uniform(0, W), random.uniform(0, H), random.uniform(4, 12), random.uniform(0, 6.28)) for _ in range(28)]


def background(c, t, top=(0.98, 0.55, 0.62), bottom=(0.35, 0.25, 0.75)):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *top)
    g.add_color_stop_rgb(1, *bottom)
    c.set_source(g)
    c.paint()
    # retro sun with stripes
    c.save()
    c.arc(540, 1250, 420, math.pi, 2 * math.pi)
    c.set_source_rgba(1, 0.85, 0.45, 0.22)
    c.fill()
    c.restore()
    # sparkles
    for x, y, r, ph in SPARKS:
        a = 0.3 + 0.5 * (0.5 + 0.5 * math.sin(t * 3 + ph))
        yy = (y - t * 20) % H
        c.save(); c.translate(x, yy); c.rotate(t + ph)
        c.move_to(0, -r * 2); c.line_to(r * 0.4, 0); c.line_to(0, r * 2); c.line_to(-r * 0.4, 0); c.close_path()
        c.move_to(-r * 2, 0); c.line_to(0, r * 0.4); c.line_to(r * 2, 0); c.line_to(0, -r * 0.4); c.close_path()
        c.set_source_rgba(1, 1, 1, a); c.fill(); c.restore()


def vhs_overlay(c, t):
    # scanlines
    c.set_source_rgba(0, 0, 0, 0.06)
    for y in range(0, H, 6):
        c.rectangle(0, y, W, 2)
    c.fill()
    # rolling bright band
    yb = (t * 260) % (H + 300) - 150
    g = cairo.LinearGradient(0, yb - 60, 0, yb + 60)
    g.add_color_stop_rgba(0, 1, 1, 1, 0); g.add_color_stop_rgba(0.5, 1, 1, 1, 0.07); g.add_color_stop_rgba(1, 1, 1, 1, 0)
    c.set_source(g); c.rectangle(0, yb - 60, W, 120); c.fill()
    # camcorder OSD
    text(c, "▶ PLAY", 60, 120, 40, WHITE, align="l", font="DejaVu Sans Mono", outline=6)
    text(c, "2016", W - 60, 120, 40, WHITE, align="r", font="DejaVu Sans Mono", outline=6)


def header(c, lt, label):
    a = ease_out(prog(lt, 0, 0.3))
    scaled(c, 540, 250, 0.6 + 0.4 * a, rot=-0.03)
    pill(c, label, 540, 250, 50, YELLOW, INK, pad=34, alpha=a)
    c.restore()


# ---------------------------------------------------------------- scenes
def scene_hook(c, t, lt, D):
    # big year with rolling digit 2 -> 1
    p = pop(lt, 0.05, 0.4)
    scaled(c, 540, 470, p, rot=-0.04)
    size = 260
    roll = ease_out(prog(lt, D * 0.32, 0.5))
    digits = ["2", "0", None, "6"]
    widths = [text_w(c, "2", size)] * 4
    x = 540 - sum(widths) / 2
    for i, d in enumerate(digits):
        cxd = x + widths[i] / 2
        if d is None:
            c.save(); c.rectangle(x - 10, 470 - size * 0.62, widths[i] + 20, size * 1.24); c.clip()
            off = roll * size * 1.1
            text(c, "2", cxd, 470 - off, size, PINK, outline=18)
            text(c, "1", cxd, 470 + size * 1.1 - off, size, CYAN, outline=18)
            c.restore()
        else:
            text(c, d, cxd, 470, size, WHITE, outline=18)
        x += widths[i]
    c.restore()
    q = pop(lt, D * 0.32 + 0.4, 0.35)
    if q > 0:
        scaled(c, 540, 680, q, rot=0.04)
        pill(c, "#2026isthenew2016", 540, 680, 46, CYAN, INK, pad=34)
        c.restore()
    rise = ease_back(prog(lt, 0.3, 0.6), 1.2)
    draw_phone(c, 540, 1480 - rise * 440, 1.0, t, wave=1.0)


def scene_filter(c, t, lt, D):
    header(c, lt, "СОБАЧИЙ ФИЛЬТР")
    dog = ease_back(prog(lt, 0.4, 0.4))
    rb = ease_out(prog(lt, D * 0.55, 0.5))
    # story frame
    fill_rrect(c, 160, 360, 760, 1000, 50, (1, 1, 1), alpha=0.18, stroke=WHITE, lw=6)
    for i in range(3):
        fill_rrect(c, 190 + i * 240, 385, 220, 10, 5, WHITE, alpha=0.9 if i == 0 else 0.4)
    draw_phone(c, 540, 830, 0.95, t, dog=dog, rainbow=rb)
    if dog > 0.5:
        text(c, "♥ 128", 840, 1300, 44, WHITE, align="r", outline=8, font="DejaVu Sans")


def person(c, x, y, s, pose, col):
    """Простая фигурка в «замершей» позе. pose: (arm1, arm2, leg1, leg2, lean) в радианах."""
    a1, a2, l1, l2, lean = pose
    c.save(); c.translate(x, y); c.scale(s, s); c.rotate(lean)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_source_rgb(*INK); c.set_line_width(26)
    for ang in (l1, l2):
        c.move_to(0, 120); c.line_to(math.sin(ang) * 150, 120 + math.cos(ang) * 150); c.stroke()
    fill_rrect(c, -55, -60, 110, 200, 40, col, stroke=INK, lw=7)
    c.set_source_rgb(*INK); c.set_line_width(22)
    for sx, ang in ((-1, a1), (1, a2)):
        c.move_to(sx * 45, -30); c.line_to(sx * 45 + sx * math.cos(ang) * 130, -30 - math.sin(ang) * 130); c.stroke()
    c.arc(0, -120, 55, 0, 2 * math.pi); c.set_source_rgb(1, 0.85, 0.72); c.fill_preserve()
    c.set_source_rgb(*INK); c.set_line_width(7); c.stroke()
    for sx in (-1, 1):
        c.arc(sx * 18, -125, 6, 0, 2 * math.pi); c.fill()
    c.move_to(-12, -95); c.line_to(12, -95); c.set_line_width(5); c.stroke()
    c.restore()


def scene_mannequin(c, t, lt, D):
    header(c, lt, "МАНЕКЕН-ЧЕЛЛЕНДЖ")
    pan = -260 * ease_out(prog(lt, 0.2, D))  # camera slowly moves
    c.save(); c.translate(pan, 0)
    # room: floor + couch
    c.rectangle(-400, 1150, 2200, 400); c.set_source_rgba(0.25, 0.15, 0.4, 0.5); c.fill()
    fill_rrect(c, 520, 950, 560, 220, 50, (0.9, 0.45, 0.5), stroke=INK)
    poses = [((1.2, -0.4, 0.3, -0.2, 0.05), PINK), ((0.2, 2.2, -0.4, 0.5, -0.12), CYAN),
             ((-0.6, 0.9, 0.1, -0.1, 0.0), YELLOW), ((2.4, 2.4, 0.6, -0.6, 0.08), (0.6, 0.9, 0.5))]
    for i, (pose, col) in enumerate(poses):
        person(c, 230 + i * 300, 950 + (i % 2) * 40, 1.0, pose, col)
    # flying "frozen" object
    c.save(); c.translate(1180, 760); c.rotate(0.6)
    fill_rrect(c, -50, -50, 100, 100, 18, YELLOW, stroke=INK, lw=6)
    c.restore()
    c.restore()
    # REC overlay
    if int(lt * 2) % 2 == 0:
        c.arc(110, 380, 18, 0, 2 * math.pi); c.set_source_rgb(1, 0.15, 0.2); c.fill()
    text(c, "REC", 145, 380, 40, WHITE, align="l", font="DejaVu Sans Mono", outline=6)
    c.set_source_rgba(1, 1, 1, 0.8); c.set_line_width(6)
    for x, y, dx, dy in ((80, 330, 1, 1), (1000, 330, -1, 1), (80, 1320, 1, -1), (1000, 1320, -1, -1)):
        c.move_to(x, y + dy * 60); c.line_to(x, y); c.line_to(x + dx * 60, y); c.stroke()


def blob_monster(c, x, y, s, t):
    c.save(); c.translate(x, y); c.scale(s, s * (1 + 0.05 * math.sin(t * 8)))
    c.move_to(-90, 60)
    c.curve_to(-110, -60, -40, -110, 0, -110); c.curve_to(40, -110, 110, -60, 90, 60)
    for i in range(4):
        x0 = 90 - i * 45
        c.curve_to(x0 - 10, 80, x0 - 35, 80, x0 - 45, 60)
    c.close_path()
    c.set_source_rgb(0.55, 0.9, 0.55); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(7); c.stroke()
    for sx in (-1, 1):
        c.arc(sx * 35, -30, 22, 0, 2 * math.pi); c.set_source_rgb(1, 1, 1); c.fill_preserve(); c.set_source_rgb(*INK); c.stroke()
        c.arc(sx * 35 + 4, -26, 10, 0, 2 * math.pi); c.fill()
    c.arc(0, 15, 20, 0.2, math.pi - 0.2); c.stroke()
    c.move_to(0, -110); c.curve_to(10, -150, 40, -150, 40, -140); c.stroke()
    c.arc(42, -142, 10, 0, 2 * math.pi); c.set_source_rgb(*YELLOW); c.fill()
    c.restore()


def scene_hunt(c, t, lt, D):
    header(c, lt, "ОХОТА НА МОНСТРИКОВ")
    # night map in a phone screen
    fill_rrect(c, 180, 360, 720, 1000, 60, (0.97, 0.97, 1), stroke=INK, lw=10)
    rrect(c, 210, 390, 660, 940, 40)
    c.save(); c.clip()
    c.set_source_rgb(0.18, 0.22, 0.38); c.paint()
    c.set_source_rgb(0.30, 0.36, 0.55); c.set_line_width(36)
    for i in range(5):
        c.move_to(210, 470 + i * 200); c.line_to(870, 430 + i * 200); c.stroke()
        c.move_to(260 + i * 160, 390); c.line_to(300 + i * 160, 1330); c.stroke()
    fill_rrect(c, 560, 880, 230, 170, 30, (0.2, 0.45, 0.3))
    # dashed path walked so far
    path = [(300, 1250), (330, 1050), (520, 1030), (560, 820), (720, 790), (750, 600)]
    f = ease_out(prog(lt, 0.2, D * 0.55))
    total = len(path) - 1
    pos = f * total
    c.set_dash([18, 14]); c.set_line_width(10); c.set_source_rgb(*CYAN)
    c.move_to(*path[0])
    for i in range(1, int(pos) + 1):
        c.line_to(*path[i])
    k = min(int(pos), total - 1)
    fx = path[k][0] + (path[k + 1][0] - path[k][0]) * (pos - k)
    fy = path[k][1] + (path[k + 1][1] - path[k][1]) * (pos - k)
    c.line_to(fx, fy); c.stroke(); c.set_dash([])
    c.arc(fx, fy, 22, 0, 2 * math.pi); c.set_source_rgb(*PINK); c.fill_preserve(); c.set_source_rgb(1, 1, 1); c.set_line_width(6); c.stroke()
    # monster appears
    q = pop(lt, D * 0.62, 0.4)
    if q > 0:
        blob_monster(c, 740, 560, 0.9 * q, t)
        ring = prog(lt, D * 0.62, 0.8)
        c.arc(740, 570, 60 + 140 * ring, 0, 2 * math.pi); c.set_source_rgba(*YELLOW, 1 - ring); c.set_line_width(8); c.stroke()
    c.restore()
    # clock
    hh = 21 + int(3 * f)
    text(c, f"{hh % 24:02d}:{int(lt * 37) % 60:02d}", 770, 1290, 50, WHITE, outline=10, font="DejaVu Sans Mono")
    q = pop(lt, D * 0.72, 0.35)
    if q > 0:
        scaled(c, 540, 450, q, rot=-0.06)
        pill(c, "РЕДКИЙ!", 540, 450, 54, PINK, WHITE, pad=36)
        c.restore()


def scene_battery(c, t, lt, D):
    header(c, lt, "ЗАРЯДКА")
    f = lt / D
    lvl = 1 - ease_out(prog(f, 0.05, 0.4)) * 0.99
    low = lvl < 0.2
    # battery icon
    x, y, w, h = 230, 430, 560, 280
    fill_rrect(c, x, y, w, h, 40, (1, 1, 1), stroke=INK, lw=12)
    fill_rrect(c, x + w, y + 90, 40, 100, 14, INK)
    blink = (not low) or int(lt * 4) % 2 == 0
    if blink:
        col = (0.3, 0.85, 0.4) if lvl > 0.5 else (YELLOW if lvl > 0.2 else (1, 0.2, 0.25))
        fill_rrect(c, x + 22, y + 22, max(30, (w - 44) * lvl), h - 44, 22, col)
    text(c, f"{max(1, int(lvl * 100))}%", 510, 570, 110, INK)
    text(c, "13:07", 510, 790, 64, WHITE, outline=10, font="DejaVu Sans Mono")
    # power bank brick
    q = ease_back(prog(f, 0.5, 0.15))
    if q > 0:
        by = 1500 - 420 * q
        c.save(); c.translate(540, by); c.rotate(-0.06 + math.sin(lt * 3) * 0.02)
        fill_rrect(c, -300, -150, 600, 300, 40, (0.35, 0.35, 0.42), stroke=INK, lw=12)
        fill_rrect(c, -260, -110, 520, 70, 20, (0.25, 0.25, 0.3))
        for i in range(4):
            c.arc(-200 + i * 50, 70, 14, 0, 2 * math.pi)
            c.set_source_rgb(0.3, 0.9, 1) if i < 3 else c.set_source_rgb(0.2, 0.2, 0.25)
            c.fill()
        text(c, "20 000 мАч", 120, 70, 44, WHITE)
        text(c, "POWER BANK", 0, -75, 40, (0.85, 0.85, 0.9))
        c.restore()
    q = pop(lt, D * 0.72, 0.35)
    if q > 0:
        scaled(c, 820, 1250, q, rot=0.12)
        pill(c, "≈ КИРПИЧ", 820, 1250, 52, PINK, WHITE, pad=34)
        c.restore()


def polaroid(c, x, y, rot, s, label, draw):
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(s, s)
    c.set_source_rgba(0, 0, 0, 0.25); rrect(c, -165, -185, 340, 400, 8); c.fill()
    fill_rrect(c, -170, -195, 340, 400, 8, (1, 0.99, 0.96), stroke=(0.85, 0.82, 0.8), lw=3)
    c.rectangle(-145, -170, 290, 280); c.set_source_rgb(0.95, 0.75, 0.6); c.fill()
    c.save(); c.rectangle(-145, -170, 290, 280); c.clip(); draw(c); c.restore()
    c.rectangle(-145, -170, 290, 280); c.set_source_rgba(1, 0.75, 0.4, 0.25); c.fill()  # warm film tint
    text(c, label, 0, 155, 40, INK, font="DejaVu Sans")
    c.restore()


def scene_today(c, t, lt, D):
    c.set_source_rgba(0.1, 0.05, 0.2, 0.35); c.paint()
    pics = [
        (300, 520, -0.18, "#собака", lambda cc: draw_phone(cc, 0, -10, 0.42, 0, dog=1, talk=False)),
        (760, 600, 0.14, "#монстрик", lambda cc: blob_monster(cc, 0, -20, 0.9, 0)),
        (520, 930, -0.05, "#2016", lambda cc: (text(cc, "2016", 0, -30, 110, PINK, outline=10))),
    ]
    for i, (x, y, r, lab, fn) in enumerate(pics):
        q = ease_out(prog(lt, 0.1 + i * 0.35, 0.45))
        if q <= 0:
            continue
        polaroid(c, x, y - (1 - q) * 900, r * (2 - q), 1.0, lab, fn)
    sad = ease_out(prog(lt, D * 0.5, 0.4))
    draw_phone(c, 540, 1740, 0.6, t, sad=sad)


def scene_cta(c, t, lt, D):
    p = pop(lt, 0.0, 0.4)
    scaled(c, 540, 520, p, rot=-0.02)
    fill_rrect(c, 110, 360, 860, 320, 50, WHITE, stroke=INK, lw=10)
    c.move_to(260, 670); c.line_to(220, 760); c.line_to(360, 670); c.close_path()
    c.set_source_rgb(1, 1, 1); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(10); c.stroke()
    c.rectangle(250, 660, 120, 14); c.set_source_rgb(1, 1, 1); c.fill()
    text(c, "А что помнишь", 540, 470, 64, INK)
    text(c, "ТЫ из 2016?", 540, 570, 76, PINK)
    c.restore()
    # typing dots
    q = pop(lt, D * 0.35, 0.3)
    if q > 0:
        scaled(c, 540, 880, q)
        fill_rrect(c, 380, 820, 320, 120, 60, (0.95, 0.95, 1), stroke=INK, lw=8)
        for i in range(3):
            yy = 880 - 14 * max(0, math.sin(lt * 8 - i * 0.8))
            c.arc(470 + i * 70, yy, 18, 0, 2 * math.pi); c.set_source_rgb(*PURPLE); c.fill()
        c.restore()
    q = pop(lt, D * 0.55, 0.35)
    if q > 0:
        b = abs(math.sin(lt * 5)) * 24
        scaled(c, 540, 1140 - b, q)
        pill(c, "ПИШИ В КОММЕНТЫ", 540, 1140 - b, 60, YELLOW, INK, pad=40)
        c.restore()
    draw_phone(c, 880, 1745, 0.5, t, wave=1.0)


SCENES = {"hook": scene_hook, "filter": scene_filter, "mannequin": scene_mannequin, "hunt": scene_hunt,
          "battery": scene_battery, "today": scene_today, "cta": scene_cta}
BG = {"hook": ((0.98, 0.55, 0.62), (0.35, 0.25, 0.75)), "filter": ((0.55, 0.85, 1.0), (0.85, 0.40, 0.85)),
      "mannequin": ((0.95, 0.70, 0.45), (0.55, 0.25, 0.55)), "hunt": ((0.20, 0.25, 0.55), (0.08, 0.06, 0.25)),
      "battery": ((1.0, 0.65, 0.45), (0.85, 0.25, 0.45)), "today": ((0.75, 0.55, 0.75), (0.25, 0.20, 0.45)),
      "cta": ((0.98, 0.55, 0.62), (0.35, 0.25, 0.75))}


# ---------------------------------------------------------------- captions
def build_captions():
    caps = []
    for s in SEGS:
        words = re.findall(r"\S+", s["text"])
        weights = [len(re.sub(r"[^\wё-]", "", w, flags=re.I)) + 2 + (4 if re.search(r"[.,:?!—]$", w) else 0) for w in words]
        tot = sum(weights)
        t = s["start"] + 0.08
        speech = s["dur"] - 0.15
        timed = []
        for w, wt in zip(words, weights):
            d = speech * wt / tot
            timed.append((t, t + d, w))
            t += d
        chunk = []
        for item in timed:
            chunk.append(item)
            if len(chunk) >= 3 or len(" ".join(x[2] for x in chunk)) > 16 or re.search(r"[.?!:]$", item[2]):
                caps.append(chunk); chunk = []
        if chunk:
            caps.append(chunk)
    return caps


CAPS = build_captions()


def draw_captions(c, t):
    for chunk in CAPS:
        if chunk[0][0] <= t < chunk[-1][1] + 0.05:
            break
    else:
        return
    p = pop(t, chunk[0][0], 0.18)
    size = 86
    words = [w.upper() for _, _, w in chunk]
    widths = [text_w(c, w, size) for w in words]
    space = 34
    total = sum(widths) + space * (len(words) - 1)
    if total > 960:
        k = 960 / total
        size *= k; space *= k; widths = [w * k for w in widths]; total = 960
    y = 1470
    scaled(c, 540, y, 0.6 + 0.4 * p)
    x = 540 - total / 2
    for (t0, t1, _), w, wd in zip(chunk, words, widths):
        active = t0 <= t < t1 + 0.02
        if active:
            scaled(c, x + wd / 2, y, 1.05)
        text(c, w, x, y, size, CYAN if active else WHITE, align="l", outline=18)
        if active:
            c.restore()
        x += wd + space
    c.restore()


# ---------------------------------------------------------------- frame
def render_frame(c, t):
    seg = SEGS[0]
    for s in SEGS:
        if t >= s["start"] - 0.12:
            seg = s
    i = SEGS.index(seg)
    end = SEGS[i + 1]["start"] - 0.12 if i + 1 < len(SEGS) else TOTAL
    lt = t - (seg["start"] - 0.12)
    D = end - (seg["start"] - 0.12)
    background(c, t, *BG[seg["id"]])
    tr = ease_out(prog(lt, 0, 0.25))
    c.save()
    c.translate(540, 900)
    c.rotate((1 - tr) * 0.06)
    c.scale(1.1 - 0.1 * tr, 1.1 - 0.1 * tr)
    c.translate(-540, -900 + (1 - tr) * 160)
    SCENES[seg["id"]](c, t, lt, D)
    c.restore()
    if lt < 0.15:  # VHS glitch between scenes
        k = 1 - lt / 0.15
        for j in range(6):
            yy = random.Random(int(t * 100) + j).uniform(0, H)
            c.rectangle(0, yy, W, 30 * k); c.set_source_rgba(*(CYAN if j % 2 else PINK), 0.4 * k); c.fill()
    draw_captions(c, t)
    vhs_overlay(c, t)


# ---------------------------------------------------------------- audio: tropical-house-ish beat + sfx
def synth_audio():
    n = len(VOICE)
    music = np.zeros(n, dtype=np.float32)
    rng = np.random.default_rng(2016)
    beat = 60 / 102

    def add(buf, sig, at, gain):
        i = int(at * SR)
        if i < n:
            j = min(n, i + len(sig))
            buf[i:j] += gain * sig[: j - i]

    def tone(freq, dur, decay):
        tt = np.arange(int(dur * SR)) / SR
        return (np.sin(2 * np.pi * freq * tt) + 0.3 * np.sin(4 * np.pi * freq * tt) + 0.15 * np.sin(6 * np.pi * freq * tt)) * np.exp(-tt * decay)

    kt = np.arange(int(0.3 * SR)) / SR
    kick = np.sin(2 * np.pi * (45 + 90 * np.exp(-kt * 30)) * kt) * np.exp(-kt * 10)
    cl = int(0.15 * SR)
    clap = rng.standard_normal(cl) * np.exp(-np.arange(cl) / SR * 30)
    clap = np.diff(clap, prepend=0) * 0.7
    # Am - F - C - G (vi-IV-I-V), marimba-like pluck melody
    chords = [[220.0, 261.6, 329.6], [174.6, 220.0, 261.6], [261.6, 329.6, 392.0], [196.0, 246.9, 293.7]]
    mel = [[659.3, 523.3, 440.0, 523.3], [698.5, 523.3, 440.0, 523.3], [784.0, 659.3, 523.3, 659.3], [740.0, 587.3, 493.9, 587.3]]
    nb = int(TOTAL / beat) + 4
    for b in range(nb):
        at = b * beat
        bar = (b // 4) % 4
        add(music, kick, at, 0.8)
        if b % 2 == 1:
            add(music, clap, at, 0.35)
        for fq in chords[bar]:  # off-beat chord stabs
            add(music, tone(fq, 0.25, 14), at + beat / 2, 0.12)
        add(music, tone(chords[bar][0] / 2, beat, 4), at, 0.35)  # bass
        for k2 in range(2):  # pluck melody on 8ths
            add(music, tone(mel[bar][(b % 4 + k2) % 4], 0.3, 12), at + k2 * beat / 2, 0.13)
    sfx = np.zeros(n, dtype=np.float32)
    wl = int(0.3 * SR)
    glitch = rng.standard_normal(wl) * np.exp(-np.arange(wl) / SR * 12) * (np.sign(np.sin(np.arange(wl) / SR * 2 * np.pi * 60)) * 0.5 + 0.5)
    pt = np.arange(int(0.12 * SR)) / SR
    popsnd = np.sin(2 * np.pi * (400 + 1200 * pt / 0.12) * pt) * np.exp(-pt * 30)
    it = np.arange(int(0.6 * SR)) / SR
    chime = (np.sin(2 * np.pi * 1046 * it) + np.sin(2 * np.pi * 1568 * it) * 0.5) * np.exp(-it * 5)
    st = np.arange(int(0.35 * SR)) / SR
    shutter = rng.standard_normal(len(st)) * (np.exp(-st * 60) + 0.6 * np.exp(-np.maximum(st - 0.09, 0) * 60) * (st > 0.09))
    seg = {s["id"]: s for s in SEGS}

    def win(sid):
        i = SEGS.index(seg[sid])
        s0 = seg[sid]["start"] - 0.12
        e = SEGS[i + 1]["start"] - 0.12 if i + 1 < len(SEGS) else TOTAL
        return s0, e - s0

    for s in SEGS:
        add(sfx, glitch, s["start"] - 0.15, 0.25)
    h0, hd = win("hook")
    add(sfx, popsnd, h0 + hd * 0.32, 0.6); add(sfx, chime, h0 + hd * 0.32 + 0.4, 0.4)
    f0, fd = win("filter")
    add(sfx, popsnd, f0 + 0.4, 0.6); add(sfx, chime, f0 + fd * 0.55, 0.5)
    m0, md = win("mannequin")
    add(sfx, shutter, m0 + 0.3, 0.5)
    u0, ud = win("hunt")
    add(sfx, chime, u0 + ud * 0.62, 0.5); add(sfx, popsnd, u0 + ud * 0.72, 0.5)
    b0, bd = win("battery")
    for k in range(3):
        add(sfx, tone(220, 0.15, 20), b0 + bd * 0.45 + k * 0.18, 0.4)
    add(sfx, kick, b0 + bd * 0.55, 1.0)
    t0, td = win("today")
    for i in range(3):
        add(sfx, shutter, t0 + 0.1 + i * 0.35, 0.4)
    c0, cd = win("cta")
    add(sfx, popsnd, c0 + cd * 0.55, 0.6)
    # lo-fi: in the "today" scene the music gets muffled (simple low-pass)
    env = np.convolve(np.abs(VOICE), np.ones(int(0.15 * SR)) / int(0.15 * SR), mode="same")
    duck = 1 - 0.55 * np.clip(env / (np.percentile(env, 90) + 1e-9), 0, 1)
    lo = np.convolve(music, np.ones(40) / 40, mode="same")
    mask = np.zeros(n, dtype=np.float32)
    mask[int(t0 * SR):int((t0 + td) * SR)] = 1
    mask = np.convolve(mask, np.ones(int(0.3 * SR)) / int(0.3 * SR), mode="same")
    music = music * (1 - mask) + lo * mask * 1.4
    mix = VOICE + music * 0.17 * duck + sfx * 0.45
    fade = np.ones(n); fl = int(0.6 * SR); fade[-fl:] = np.linspace(1, 0, fl)
    mix *= fade
    mix /= max(1e-6, np.max(np.abs(mix))) / 0.95
    return mix.astype(np.float32)


def main():
    if "--preview" in sys.argv:
        for s in SEGS:
            surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
            render_frame(cairo.Context(surf), s["start"] + s["dur"] * 0.85)
            surf.write_to_png(str(OUT / f"preview_{s['id']}.png"))
        print("previews written")
        return
    audio = synth_audio()
    wav = OUT / "mix.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-c:a", "pcm_s16le", str(wav)], input=audio.tobytes(), check=True)
    out = OUT / "nostalgia_2016_tiktok.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "medium",
                           "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                           "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    nframes = int(TOTAL * FPS)
    for i in range(nframes):
        render_frame(cairo.Context(surf), i / FPS)
        surf.flush()
        ff.stdin.write(bytes(surf.get_data()))
        if i % 150 == 0:
            print(f"frame {i}/{nframes}", flush=True)
    ff.stdin.close()
    ff.wait()
    wav.unlink()
    print("done:", out)


if __name__ == "__main__":
    main()

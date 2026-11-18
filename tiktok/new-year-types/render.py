"""Рендер TikTok-ролика «До Нового года 43 дня: 5 типов людей».

Вход: timeline.json и audio/*.mp3 (см. tts.py). Выход: out/new_year_types_tiktok.mp4 (1080x1920, 30 fps).
Графика — pycairo (персонаж Мандаринка), музыка и эффекты синтезируются numpy.
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




ORANGE = (1.0, 0.58, 0.12)
ORANGE_D = (0.85, 0.42, 0.05)
GREEN = (0.25, 0.75, 0.35)
RED = (0.92, 0.18, 0.25)
GOLD = (1.0, 0.80, 0.25)
NAVY = (0.06, 0.10, 0.28)
SNOW = (0.95, 0.97, 1.0)


# ---------------------------------------------------------------- character: Мандаринка
def draw_mandarin(c, cx, cy, s, t, outfit=None, sleep=False, run=0.0, smug=0.0, wave=0.0, talk=True):
    c.save()
    c.translate(cx, cy)
    c.scale(s, s)
    bob = abs(math.sin(t * (14 if run else 4))) * (22 if run else 8)
    c.translate(0, -bob)
    c.rotate(0.18 * run + math.sin(t * 1.8) * 0.03)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    # legs
    c.set_source_rgb(*INK); c.set_line_width(16)
    for sx in (-1, 1):
        sw = math.sin(t * 16 + (0 if sx < 0 else math.pi)) * 0.9 * run
        fx, fy = sx * 55 + math.sin(sw) * 110, 160 + math.cos(sw) * 110
        c.move_to(sx * 55, 150); c.line_to(fx, fy); c.stroke()
        c.save(); c.translate(fx + 10, fy + 4); c.scale(1.5, 1); c.arc(0, 0, 18, 0, 2 * math.pi); c.restore(); c.fill()
    # arms
    for sx in (-1, 1):
        if sx == 1 and wave:
            ang = -0.7 - 1.0 * (0.5 + 0.5 * math.sin(t * 9))
        elif run:
            ang = 0.3 + math.sin(t * 16 + (math.pi if sx > 0 else 0)) * 0.9
        else:
            ang = 0.5
        ex, ey = sx * (165 + 110 * math.cos(ang)), 20 + 110 * math.sin(ang)
        c.move_to(sx * 160, 20); c.line_to(ex, ey); c.set_source_rgb(*INK); c.set_line_width(16); c.stroke()
        c.arc(ex, ey, 24, 0, 2 * math.pi); c.set_source_rgb(1, 1, 1); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(7); c.stroke()
    # body
    c.save(); c.scale(1.05, 0.95); c.arc(0, 0, 175, 0, 2 * math.pi); c.restore()
    g = cairo.RadialGradient(-60, -70, 20, 0, 0, 200)
    g.add_color_stop_rgb(0, 1, 0.75, 0.35); g.add_color_stop_rgb(1, *ORANGE)
    c.set_source(g); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(9); c.stroke()
    random.seed(3)
    for _ in range(14):
        a, r = random.uniform(0, 6.28), random.uniform(60, 150)
        c.arc(math.cos(a) * r, math.sin(a) * r * 0.9, 4, 0, 2 * math.pi); c.set_source_rgba(*ORANGE_D, 0.5); c.fill()
    # leaf / hats
    if outfit == "santa" or sleep:
        col = RED if outfit == "santa" else (0.35, 0.45, 0.9)
        c.move_to(-150, -95); c.curve_to(-60, -230, 80, -260, 190, -170); c.line_to(150, -95); c.close_path()
        c.set_source_rgb(*col); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(8); c.stroke()
        fill_rrect(c, -170, -120, 340, 55, 27, SNOW, stroke=INK, lw=7)
        c.arc(200, -160, 32, 0, 2 * math.pi); c.set_source_rgb(*SNOW); c.fill_preserve(); c.set_source_rgb(*INK); c.stroke()
    else:
        c.move_to(0, -160); c.line_to(0, -200); c.set_source_rgb(0.4, 0.25, 0.1); c.set_line_width(12); c.stroke()
        c.save(); c.translate(15, -205); c.rotate(-0.5 + math.sin(t * 3) * 0.1)
        c.move_to(0, 0); c.curve_to(30, -60, 110, -60, 130, -10); c.curve_to(90, 20, 30, 20, 0, 0)
        c.set_source_rgb(*GREEN); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(7); c.stroke()
        c.restore()
    if outfit == "headband":
        c.save(); c.scale(1.05, 0.95)
        c.arc(0, 0, 177, math.pi * 1.12, math.pi * 1.88); c.set_source_rgb(*RED); c.set_line_width(46); c.stroke()
        c.arc(0, 0, 177, math.pi * 1.12, math.pi * 1.88); c.set_source_rgb(1, 1, 1); c.set_line_width(12); c.stroke()
        c.restore()
    # face
    blink = (t % 3.1) < 0.12
    for sx in (-1, 1):
        ex, ey = sx * 60, -20
        if sleep or blink:
            c.arc(ex, ey - 5, 26, 0.3, math.pi - 0.3); c.set_source_rgb(*INK); c.set_line_width(8); c.stroke()
        else:
            c.save(); c.translate(ex, ey); c.scale(0.85, 1); c.arc(0, 0, 34, 0, 2 * math.pi); c.restore()
            c.set_source_rgb(1, 1, 1); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(7); c.stroke()
            c.arc(ex + 4, ey + 4, 16, 0, 2 * math.pi); c.set_source_rgb(*INK); c.fill()
            c.arc(ex + 10, ey - 3, 6, 0, 2 * math.pi); c.set_source_rgb(1, 1, 1); c.fill()
            if smug:  # half-closed lids
                c.save(); c.translate(ex, ey); c.scale(0.85, 1); c.arc(0, 0, 34, 0, 2 * math.pi); c.restore(); c.clip()
                c.rectangle(ex - 40, ey - 40, 80, 36 * smug); c.set_source_rgb(*ORANGE); c.fill(); c.reset_clip()
                c.move_to(ex - 30, ey - 40 + 36 * smug); c.line_to(ex + 30, ey - 40 + 36 * smug)
                c.set_source_rgb(*INK); c.set_line_width(6); c.stroke()
        c.arc(sx * 100, 30, 24, 0, 2 * math.pi); c.set_source_rgba(1, 0.3, 0.35, 0.45); c.fill()
    if outfit == "glasses":
        c.set_source_rgb(*INK); c.set_line_width(7)
        for sx in (-1, 1):
            c.arc(sx * 60, -20, 46, 0, 2 * math.pi); c.stroke()
        c.move_to(-14, -24); c.line_to(14, -24); c.stroke()
    m = mouth(t) if talk else 0.0
    if m > 0.08:
        c.save(); c.translate(0, 55); c.scale(1, 0.3 + m * 0.8); c.arc(0, 0, 34, 0, 2 * math.pi); c.restore()
        c.set_source_rgb(0.5, 0.1, 0.12); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(6); c.stroke()
    elif sleep:
        c.save(); c.translate(0, 60); c.scale(1, 0.6 + 0.2 * math.sin(t * 2)); c.arc(0, 0, 12, 0, 2 * math.pi); c.restore()
        c.set_source_rgb(*INK); c.set_line_width(6); c.stroke()
    else:
        c.set_source_rgb(*INK); c.set_line_width(7)
        c.arc(0, 30, 32, 0.4, math.pi - 0.4); c.stroke()
    if outfit == "sweat":
        for k, (x, y) in enumerate(((170, -110), (-185, -60), (150, -170))):
            ph = (t * 2 + k * 0.33) % 1
            c.save(); c.translate(x, y + ph * 60)
            c.move_to(0, -22); c.curve_to(16, 0, 16, 14, 0, 16); c.curve_to(-16, 14, -16, 0, 0, -22)
            c.set_source_rgba(0.55, 0.85, 1, 1 - ph); c.fill(); c.restore()
    c.restore()


# ---------------------------------------------------------------- background (winter night)
random.seed(43)
FLAKES = [(random.uniform(0, W), random.uniform(0, H), random.uniform(3, 9), random.uniform(0, 6.28)) for _ in range(90)]
BULBS = [RED, GOLD, GREEN, (0.35, 0.7, 1), PINK]


def background(c, t, top=(0.10, 0.18, 0.45), bottom=NAVY):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *top)
    g.add_color_stop_rgb(1, *bottom)
    c.set_source(g)
    c.paint()
    # snowdrift
    c.move_to(0, 1780)
    for i in range(7):
        c.curve_to(i * 180 + 60, 1720, i * 180 + 120, 1720, (i + 1) * 180, 1780)
    c.line_to(W, H); c.line_to(0, H); c.close_path()
    c.set_source_rgba(*SNOW, 0.9); c.fill()
    for x, y, r, ph in FLAKES:
        yy = (y + t * 40 * r) % H
        xx = x + math.sin(t + ph) * 20
        c.arc(xx, yy, r, 0, 2 * math.pi)
        c.set_source_rgba(1, 1, 1, 0.35 + 0.05 * r)
        c.fill()


def garland(c, t):
    c.set_source_rgb(0.1, 0.25, 0.12); c.set_line_width(5)
    c.move_to(-20, 40)
    for i in range(6):
        c.curve_to(i * 200 + 50, 130, i * 200 + 150, 130, (i + 1) * 200 - 20, 40)
    c.stroke()
    for i in range(30):
        x = -20 + i * 40
        seg = (x + 20) % 200 / 200
        y = 40 + 90 * 4 * seg * (1 - seg) * 0.9
        col = BULBS[i % len(BULBS)]
        on = 0.5 + 0.5 * math.sin(t * 5 + i * 1.3)
        g = cairo.RadialGradient(x, y + 18, 2, x, y + 18, 40)
        g.add_color_stop_rgba(0, *col, 0.6 * on); g.add_color_stop_rgba(1, *col, 0)
        c.set_source(g); c.arc(x, y + 18, 40, 0, 2 * math.pi); c.fill()
        c.save(); c.translate(x, y + 18); c.scale(0.7, 1); c.arc(0, 0, 14, 0, 2 * math.pi); c.restore()
        c.set_source_rgb(*[v * (0.55 + 0.45 * on) for v in col]); c.fill()


def header(c, lt, num, label):
    a = ease_out(prog(lt, 0, 0.3))
    scaled(c, 540, 250, 0.6 + 0.4 * a, rot=-0.03)
    pill(c, f"ТИП #{num}", 540, 230, 44, GOLD, INK, pad=30, alpha=a)
    text(c, label, 540, 320, 58, WHITE, outline=12, alpha=a)
    c.restore()


def gift(c, x, y, s, col, rib=GOLD):
    c.save(); c.translate(x, y); c.scale(s, s)
    fill_rrect(c, -70, -60, 140, 120, 12, col, stroke=INK, lw=6)
    c.rectangle(-12, -60, 24, 120); c.set_source_rgb(*rib); c.fill()
    fill_rrect(c, -80, -80, 160, 34, 10, col, stroke=INK, lw=6)
    c.rectangle(-12, -80, 24, 34); c.set_source_rgb(*rib); c.fill()
    for sx in (-1, 1):
        c.save(); c.translate(sx * 22, -92); c.rotate(sx * 0.5); c.scale(1.4, 0.8)
        c.arc(0, 0, 18, 0, 2 * math.pi); c.restore()
        c.set_source_rgb(*rib); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(5); c.stroke()
    c.restore()


def calendar(c, x, y, s, top, big, rot=0.0, col=RED):
    if s <= 1e-3:
        return
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(s, s)
    fill_rrect(c, -140, -130, 280, 260, 28, WHITE, stroke=INK)
    fill_rrect(c, -140, -130, 280, 76, 28, col)
    c.rectangle(-140, -84, 280, 30); c.set_source_rgb(*col); c.fill()
    text(c, top, 0, -92, 36, WHITE)
    text(c, big, 0, 30, 120, INK)
    c.restore()


# ---------------------------------------------------------------- scenes
def scene_hook(c, t, lt, D):
    roll = ease_out(prog(lt, 0.1, 1.2))
    days = int(round(60 - 17 * roll))
    p = pop(lt, 0.05, 0.4)
    scaled(c, 540, 470, p, rot=-0.04)
    text(c, str(days), 540, 440, 300, GOLD, outline=24)
    text(c, "ДНЯ ДО НОВОГО ГОДА", 540, 640, 64, WHITE, outline=14)
    c.restore()
    q = pop(lt, D * 0.45, 0.4)
    if q > 0:
        scaled(c, 850, 800, q, rot=0.12)
        c.arc(850, 800, 120, 0, 2 * math.pi); c.set_source_rgb(*RED); c.fill_preserve()
        c.set_source_rgb(*WHITE); c.set_line_width(9); c.stroke()
        text(c, "5", 850, 770, 120, WHITE)
        text(c, "ТИПОВ", 850, 860, 40, WHITE)
        c.restore()
    rise = ease_back(prog(lt, 0.3, 0.6), 1.2)
    draw_mandarin(c, 470, 1500 - rise * 420, 1.0, t, wave=1.0)


def scene_planner(c, t, lt, D):
    header(c, lt, 1, "ПЛАНИРОВЩИК")
    p = pop(lt, 0.1, 0.4)
    scaled(c, 330, 720, p, rot=-0.05)
    fill_rrect(c, 110, 450, 440, 560, 30, (0.98, 0.95, 0.85), stroke=INK)
    fill_rrect(c, 260, 425, 140, 50, 14, (0.6, 0.6, 0.65), stroke=INK, lw=6)
    text(c, "ПОДАРКИ", 330, 530, 46, INK)
    for i, name in enumerate(["Маме", "Папе", "Сестре", "Другу"]):
        y = 630 + i * 95
        text(c, name, 170, y, 44, INK, align="l")
        q = ease_back(prog(lt, D * (0.25 + i * 0.12), 0.25))
        if q > 0:
            c.save(); c.translate(480, y); c.scale(q, q)
            c.move_to(-25, 0); c.line_to(-5, 22); c.line_to(30, -25)
            c.set_source_rgb(*GREEN); c.set_line_width(14); c.stroke(); c.restore()
    c.restore()
    for i, col in enumerate((RED, (0.3, 0.6, 1), GREEN, PINK)):
        q = ease_back(prog(lt, D * (0.3 + i * 0.12), 0.3))
        if q > 0:
            gift(c, 800 + (i % 2) * 60 - 30, 1000 - i * 125 - (1 - q) * 300, 0.95, col)
    draw_mandarin(c, 300, 1240, 0.65, t, outfit="glasses", smug=0.5)
    q = pop(lt, D * 0.75, 0.35)
    if q > 0:
        scaled(c, 760, 1200, q, rot=0.08)
        pill(c, "ВСЁ КУПЛЕНО", 760, 1200, 46, GREEN, WHITE, pad=30)
        c.restore()


def xmas_tree(c, x, y, s, t):
    if s <= 1e-3:
        return
    c.save(); c.translate(x, y); c.scale(s, s)
    fill_rrect(c, -35, 250, 70, 70, 8, (0.5, 0.3, 0.15), stroke=INK, lw=6)
    for i, (w, yy) in enumerate(((300, 260), (240, 130), (170, 10))):
        c.move_to(-w, yy); c.line_to(0, yy - 220); c.line_to(w, yy); c.close_path()
        c.set_source_rgb(0.15, 0.6, 0.3); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(7); c.stroke()
    random.seed(9)
    for k in range(22):
        yy = random.uniform(-150, 240)
        half = 300 * (yy + 210) / 470
        xx = random.uniform(-half * 0.8, half * 0.8)
        on = 0.5 + 0.5 * math.sin(t * 6 + k)
        c.arc(xx, yy, 14, 0, 2 * math.pi)
        col = BULBS[k % len(BULBS)]
        c.set_source_rgb(*[v * (0.5 + 0.5 * on) for v in col]); c.fill()
    # star
    c.save(); c.translate(0, -225); c.rotate(math.sin(t * 2) * 0.1)
    for k in range(10):
        r = 60 if k % 2 == 0 else 26
        a = -math.pi / 2 + k * math.pi / 5
        (c.move_to if k == 0 else c.line_to)(math.cos(a) * r, math.sin(a) * r)
    c.close_path(); c.set_source_rgb(*GOLD); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(6); c.stroke()
    c.restore()
    c.restore()


def scene_tree(c, t, lt, D):
    header(c, lt, 2, "ЁЛКА В НОЯБРЕ")
    p = ease_back(prog(lt, 0.2, 0.5))
    xmas_tree(c, 380, 800, 0.95 * p, t)
    calendar(c, 860, 560, 0.75 * pop(lt, 0.4, 0.4), "НОЯБРЬ", "15", rot=0.1)
    draw_mandarin(c, 780, 1140, 0.62, t + 0.3 * math.sin(t * 6), outfit="santa")
    # floating music notes
    for k in range(4):
        ph = (lt * 0.6 + k * 0.25) % 1
        x = 900 + math.sin(ph * 6 + k) * 60
        y = 1000 - ph * 500
        a = math.sin(ph * math.pi)
        c.set_source_rgba(*GOLD, a)
        c.save(); c.translate(x, y); c.scale(1.3, 1); c.arc(0, 0, 16, 0, 2 * math.pi); c.restore(); c.fill()
        c.rectangle(x + 16, y - 70, 7, 70); c.fill()
        c.move_to(x + 23, y - 70); c.curve_to(x + 50, y - 55, x + 45, y - 35, x + 40, y - 30)
        c.set_source_rgba(*GOLD, a); c.set_line_width(7); c.stroke()


def scene_rush(c, t, lt, D):
    header(c, lt, 3, "ПОСЛЕДНИЙ МОМЕНТ")
    f = lt / D
    # shop
    fill_rrect(c, 560, 470, 440, 520, 20, (0.9, 0.9, 0.95), stroke=INK)
    fill_rrect(c, 540, 430, 480, 100, 20, RED, stroke=INK)
    text(c, "МАГАЗИН", 780, 480, 48, WHITE)
    fill_rrect(c, 640, 700, 280, 290, 10, (0.5, 0.75, 0.95), stroke=INK, lw=7)
    closed = f > 0.72
    flip = prog(f, 0.72, 0.05)
    sc = abs(math.cos(flip * math.pi))
    c.save(); c.translate(780, 620); c.scale(1, max(0.05, sc))
    fill_rrect(c, -140, -40, 280, 80, 14, RED if (closed and flip > 0.5) else GREEN, stroke=INK, lw=6)
    text(c, "ЗАКРЫТО" if (closed and flip > 0.5) else "ОТКРЫТО", 0, 0, 42, WHITE)
    c.restore()
    # clock
    mins = int(f * 59)
    fill_rrect(c, 90, 460, 420, 170, 30, INK, stroke=GOLD, lw=8)
    text(c, "31.12", 300, 505, 40, GOLD, font="DejaVu Sans Mono")
    text(c, f"23:{mins:02d}", 300, 580, 80, RED, font="DejaVu Sans Mono")
    # running mandarin across the scene
    x = 100 + ((lt * 0.45) % 1) * 600
    for k in range(4):  # speed lines
        c.move_to(x - 200 - k * 20, 1050 + k * 50); c.line_to(x - 110, 1050 + k * 50)
        c.set_source_rgba(1, 1, 1, 0.6); c.set_line_width(8); c.stroke()
    draw_mandarin(c, x, 1120, 0.6, t, outfit="sweat", run=1.0)
    if closed:
        q = pop(lt, D * 0.78, 0.3)
        scaled(c, 540, 1260, q, rot=-0.05)
        pill(c, "НЕ УСПЕЛ", 540, 1260, 56, RED, WHITE, pad=36)
        c.restore()


def scene_newlife(c, t, lt, D):
    header(c, lt, 4, "НОВАЯ ЖИЗНЬ")
    calendar(c, 290, 640, 1.0 * pop(lt, 0.1, 0.4), "ЯНВАРЬ", "1", rot=-0.08, col=(0.3, 0.55, 1))
    goals = ["Спортзал", "Без сладкого", "Английский"]
    for i, g in enumerate(goals):
        q = pop(lt, D * (0.15 + i * 0.1), 0.3)
        if q > 0:
            scaled(c, 780, 520 + i * 120, q)
            fill_rrect(c, 580, 470 + i * 120, 400, 100, 22, WHITE, stroke=INK, lw=6)
            text(c, g, 780, 520 + i * 120, 40, INK)
            c.restore()
    draw_mandarin(c, 540, 1180, 0.65, t, outfit="headband", smug=0.0 if lt < D * 0.65 else 0.6)
    q = pop(lt, D * 0.62, 0.3)
    if q > 0:
        s = 1 + (1 - q) * 2 if q < 1 else 1
        scaled(c, 780, 900, s, rot=0.12)
        fill_rrect(c, 560, 830, 440, 140, 20, RED, alpha=0.95, stroke=WHITE, lw=8)
        text(c, "5-Й ГОД", 780, 875, 52, WHITE)
        text(c, "ПОДРЯД", 780, 935, 44, GOLD)
        c.restore()


def scene_sleeper(c, t, lt, D):
    c.set_source_rgba(0, 0, 0.08, 0.5); c.paint()
    header(c, lt, 5, "СПЯЩИЙ")
    c.arc(860, 480, 90, 0, 2 * math.pi); c.set_source_rgb(1, 0.95, 0.75); c.fill()
    c.arc(895, 455, 80, 0, 2 * math.pi); c.set_source_rgba(0.08, 0.12, 0.35, 1); c.fill()
    # bed
    fill_rrect(c, 140, 1000, 800, 160, 30, (0.55, 0.35, 0.25), stroke=INK)
    fill_rrect(c, 120, 820, 60, 340, 20, (0.55, 0.35, 0.25), stroke=INK)
    draw_mandarin(c, 360, 880, 0.6, t, sleep=True, talk=False)
    c.move_to(280, 960); c.curve_to(450, 900, 700, 900, 920, 960); c.line_to(920, 1040); c.line_to(250, 1040); c.close_path()
    c.set_source_rgb(0.4, 0.5, 0.95); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(8); c.stroke()
    for k in range(3):
        ph = (lt * 0.5 + k / 3) % 1
        text(c, "Z", 470 + ph * 150 + k * 10, 760 - ph * 260, 50 + ph * 40, WHITE, outline=8, alpha=math.sin(ph * math.pi))
    days = ["1", "2", "3"]
    idx = min(2, int(prog(lt, D * 0.3, D * 0.6) * 3))
    calendar(c, 780, 640, 0.6 * pop(lt, 0.2, 0.4), "ЯНВАРЬ", days[idx], rot=0.08, col=(0.3, 0.55, 1))


def scene_cta(c, t, lt, D):
    p = pop(lt, 0.0, 0.4)
    scaled(c, 540, 330, p, rot=-0.03)
    pill(c, "ОТМЕТЬ ДРУГА", 540, 330, 76, GOLD, INK, pad=46)
    c.restore()
    q = pop(lt, 0.3, 0.4)
    if q > 0:
        scaled(c, 540, 520, q)
        c.arc(540, 520, 90, 0, 2 * math.pi); c.set_source_rgb(*RED); c.fill_preserve()
        c.set_source_rgb(1, 1, 1); c.set_line_width(8); c.stroke()
        text(c, "@", 540, 510, 110, WHITE, font="DejaVu Sans")
        c.restore()
    text(c, "КТО ТЫ?", 540, 720, 80, WHITE, outline=14, alpha=clamp(prog(lt, D * 0.4, 0.3)))
    for i in range(5):
        q = pop(lt, D * 0.45 + i * 0.12, 0.3)
        if q > 0:
            x = 220 + i * 160
            scaled(c, x, 860, q * (1.15 if i == 2 else 1))
            c.arc(x, 860, 62, 0, 2 * math.pi)
            c.set_source_rgb(*(RED if i == 2 else WHITE)); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(7); c.stroke()
            text(c, str(i + 1), x, 855, 70, WHITE if i == 2 else INK)
            c.restore()
    draw_mandarin(c, 540, 1180, 0.65, t, wave=1.0)


SCENES = {"hook": scene_hook, "planner": scene_planner, "tree": scene_tree, "rush": scene_rush,
          "newlife": scene_newlife, "sleeper": scene_sleeper, "cta": scene_cta}
BG = {"hook": ((0.12, 0.20, 0.50), NAVY), "planner": ((0.10, 0.35, 0.40), (0.04, 0.12, 0.18)),
      "tree": ((0.35, 0.10, 0.20), (0.12, 0.03, 0.10)), "rush": ((0.40, 0.15, 0.10), (0.15, 0.04, 0.06)),
      "newlife": ((0.10, 0.30, 0.20), (0.03, 0.10, 0.08)), "sleeper": ((0.05, 0.08, 0.25), (0.02, 0.02, 0.08)),
      "cta": ((0.12, 0.20, 0.50), NAVY)}
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
        text(c, w, x, y, size, GOLD if active else WHITE, align="l", outline=18)
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
    c.scale(1.1 - 0.1 * tr, 1.1 - 0.1 * tr)
    c.translate(-540 + (1 - tr) * 200, -900)
    SCENES[seg["id"]](c, t, lt, D)
    c.restore()
    garland(c, t)
    if lt < 0.12:  # sparkle flash between scenes
        c.set_source_rgba(1, 0.95, 0.8, 0.45 * (1 - lt / 0.12)); c.paint()
    draw_captions(c, t)


# ---------------------------------------------------------------- audio: festive beat + sleigh bells + sfx
def synth_audio():
    n = len(VOICE)
    music = np.zeros(n, dtype=np.float32)
    rng = np.random.default_rng(2027)
    beat = 60 / 118

    def add(buf, sig, at, gain):
        i = int(at * SR)
        if 0 <= i < n:
            j = min(n, i + len(sig))
            buf[i:j] += gain * sig[: j - i]

    def bell(freq, dur, decay):
        tt = np.arange(int(dur * SR)) / SR
        return (np.sin(2 * np.pi * freq * tt) + 0.5 * np.sin(2 * np.pi * freq * 2.76 * tt)
                + 0.25 * np.sin(2 * np.pi * freq * 5.4 * tt)) * np.exp(-tt * decay)

    def pluck(freq, dur, decay):
        tt = np.arange(int(dur * SR)) / SR
        return np.tanh(1.5 * np.sin(2 * np.pi * freq * tt)) * np.exp(-tt * decay)

    kt = np.arange(int(0.3 * SR)) / SR
    kick = np.sin(2 * np.pi * (50 + 100 * np.exp(-kt * 30)) * kt) * np.exp(-kt * 10)
    jl = int(0.12 * SR)
    jingle = rng.standard_normal(jl) * np.exp(-np.arange(jl) / SR * 35)
    jingle = np.diff(np.diff(jingle, prepend=0), prepend=0) * 0.5  # bright, sleigh-bell-like
    sl = int(0.16 * SR)
    snap = np.diff(rng.standard_normal(sl) * np.exp(-np.arange(sl) / SR * 28), prepend=0) * 0.7
    # C - Am - F - G
    chords = [[261.6, 329.6, 392.0], [220.0, 261.6, 329.6], [174.6, 220.0, 261.6], [196.0, 246.9, 293.7]]
    arps = [[523.3, 659.3, 784.0, 659.3], [440.0, 523.3, 659.3, 523.3], [349.2, 440.0, 523.3, 440.0], [392.0, 493.9, 587.3, 493.9]]
    nb = int(TOTAL / beat) + 4
    for b in range(nb):
        at = b * beat
        bar = (b // 4) % 4
        add(music, kick, at, 0.75 if b % 2 == 0 else 0.4)
        if b % 2 == 1:
            add(music, snap, at, 0.35)
        add(music, jingle, at + beat / 2, 0.3)
        add(music, jingle, at, 0.15)
        add(music, pluck(chords[bar][0] / 2, beat * 0.9, 5), at, 0.3)
        for k in range(2):
            add(music, bell(arps[bar][(b % 4 * 2 + k) % 4], 0.5, 6), at + k * beat / 2, 0.08)
        if b % 4 == 0:
            for fq in chords[bar]:
                add(music, pluck(fq, beat * 4, 1.2), at, 0.05)
    sfx = np.zeros(n, dtype=np.float32)
    wl = int(0.4 * SR); wt = np.arange(wl) / SR
    sparkle = sum(bell(f, 0.4, 12) for f in (1568, 2093, 2637)) * 0.4
    pt = np.arange(int(0.12 * SR)) / SR
    popsnd = np.sin(2 * np.pi * (300 + 1000 * pt / 0.12) * pt) * np.exp(-pt * 30)
    whoosh = np.convolve(rng.standard_normal(wl), np.ones(30) / 30, mode="same") * np.sin(np.pi * wt / 0.4) ** 2
    bl = int(0.3 * SR); bt = np.arange(bl) / SR
    stamp = np.sin(2 * np.pi * (45 + 80 * np.exp(-bt * 15)) * bt) * np.exp(-bt * 7)
    seg = {s["id"]: s for s in SEGS}

    def win(sid):
        i = SEGS.index(seg[sid])
        s0 = seg[sid]["start"] - 0.12
        e = SEGS[i + 1]["start"] - 0.12 if i + 1 < len(SEGS) else TOTAL
        return s0, e - s0

    for s in SEGS:
        add(sfx, whoosh, s["start"] - 0.3, 0.3)
        add(sfx, sparkle, s["start"] - 0.1, 0.35)
    h0, hd = win("hook")
    add(sfx, popsnd, h0 + hd * 0.45, 0.6)
    p0, pd = win("planner")
    for i in range(4):
        add(sfx, popsnd, p0 + pd * (0.25 + i * 0.12), 0.45)
    t0, td = win("tree")
    add(sfx, sparkle, t0 + 0.3, 0.6)
    r0, rd = win("rush")
    add(sfx, stamp, r0 + rd * 0.72, 0.9); add(sfx, popsnd, r0 + rd * 0.78, 0.5)
    n0, nd = win("newlife")
    add(sfx, stamp, n0 + nd * 0.62, 1.0)
    s0, sd = win("sleeper")
    c0, cd = win("cta")
    for i in range(5):
        add(sfx, popsnd, c0 + cd * 0.45 + i * 0.12, 0.4)
    env = np.convolve(np.abs(VOICE), np.ones(int(0.15 * SR)) / int(0.15 * SR), mode="same")
    duck = 1 - 0.55 * np.clip(env / (np.percentile(env, 90) + 1e-9), 0, 1)
    # sleeper scene: music almost stops (only soft bells)
    quiet = np.zeros(n, dtype=np.float32)
    quiet[int(s0 * SR):int((s0 + sd) * SR)] = 1
    quiet = np.convolve(quiet, np.ones(int(0.3 * SR)) / int(0.3 * SR), mode="same")
    music *= 1 - 0.75 * quiet
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
    out = OUT / "new_year_types_tiktok.mp4"
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

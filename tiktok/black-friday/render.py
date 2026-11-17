"""Рендер анимации + сведение звука для TikTok-ролика «4 трюка Чёрной пятницы».

Вход: timeline.json и audio/*.mp3 (см. tts.py).
Выход: out/black_friday_tiktok.mp4 (1080x1920, 30 fps).
Вся графика рисуется кодом (pycairo), музыка и звуковые эффекты синтезируются (numpy).
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
SEG = {s["id"]: s for s in SEGS}

FONT = "Inter Black"
YELLOW = (1.0, 0.86, 0.18)
RED = (1.0, 0.23, 0.30)
GREEN = (0.20, 0.90, 0.55)
WHITE = (1, 1, 1)
INK = (0.08, 0.05, 0.12)
ORANGE = (0.97, 0.62, 0.22)

# ---------------------------------------------------------------- easing
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
    """0 → 1 with overshoot."""
    p = prog(t, t0, d)
    return 0.0 if p <= 0 else ease_back(p)


def fmt(n):
    return f"{int(round(n)):,}".replace(",", " ")


# ---------------------------------------------------------------- drawing helpers
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
    if align == "c":
        tx = x - (ext.x_advance) / 2
    elif align == "r":
        tx = x - ext.x_advance
    else:
        tx = x
    ty = y + size * 0.36
    c.move_to(tx, ty)
    c.text_path(s)
    if outline:
        c.set_source_rgba(*outline_color, alpha)
        c.set_line_width(outline)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.stroke_preserve()
    c.set_source_rgba(*color, alpha)
    c.fill()
    return ext.x_advance


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
    fill_rrect(c, cx - w / 2, cy - h / 2, w, h, h / 2, bg, alpha)
    text(c, s, cx, cy, size, fg, alpha=alpha)
    return w


# ---------------------------------------------------------------- voice envelope (lip-sync)
def load_audio(path):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR),
                                   "-f", "f32le", "-"])
    return np.frombuffer(raw, dtype=np.float32).copy()


VOICE = np.zeros(int(TOTAL * SR) + SR, dtype=np.float32)
for s in SEGS:
    a = load_audio(HERE / "audio" / f"{s['id']}.mp3")
    i = int(s["start"] * SR)
    VOICE[i:i + len(a)] += a[: len(VOICE) - i]

_hop = SR // FPS
ENV = np.array([np.sqrt(np.mean(VOICE[i * _hop:(i + 1) * _hop] ** 2) + 1e-12)
                for i in range(len(VOICE) // _hop)])
ENV = np.clip(ENV / (np.percentile(ENV[ENV > 1e-3], 95) + 1e-9), 0, 1)


def mouth(t):
    i = int(t * FPS)
    return float(ENV[i]) if 0 <= i < len(ENV) else 0.0


# ---------------------------------------------------------------- character: кот-продавец
def draw_cat(c, cx, cy, s, t, sly=0.0, look=(0, 0), talk=True):
    c.save()
    c.translate(cx, cy)
    c.scale(s, s)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    bob = math.sin(t * 5) * 4
    # body (suit)
    c.move_to(-230, 1000); c.line_to(-200, 470); c.curve_to(-200, 230, -140, 150, 0, 150)
    c.curve_to(140, 150, 200, 230, 200, 470); c.line_to(230, 1000); c.close_path()
    c.set_source_rgb(0.13, 0.12, 0.27); c.fill_preserve()
    c.set_source_rgb(*INK); c.set_line_width(8); c.stroke()
    c.move_to(-60, 152); c.line_to(0, 300); c.line_to(60, 152); c.close_path()
    c.set_source_rgb(0.96, 0.96, 1); c.fill()
    # bow tie
    for sx in (-1, 1):
        c.move_to(0, 175); c.line_to(sx * 62, 140); c.line_to(sx * 62, 210); c.close_path()
    c.set_source_rgb(*YELLOW); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(6); c.stroke()
    c.arc(0, 175, 16, 0, 2 * math.pi); c.set_source_rgb(*YELLOW); c.fill_preserve(); c.set_source_rgb(*INK); c.stroke()

    c.translate(0, bob)
    tilt = math.sin(t * 2.2) * 0.04 + sly * 0.08
    c.rotate(tilt)
    # ears
    for sx in (-1, 1):
        c.move_to(sx * 160, -40); c.line_to(sx * 135, -205); c.line_to(sx * 40, -135); c.close_path()
        c.set_source_rgb(*ORANGE); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(8); c.stroke()
        c.move_to(sx * 140, -70); c.line_to(sx * 128, -170); c.line_to(sx * 70, -128); c.close_path()
        c.set_source_rgb(1, 0.6, 0.68); c.fill()
    # head
    c.save(); c.scale(1, 0.86); c.arc(0, 0, 175, 0, 2 * math.pi); c.restore()
    c.set_source_rgb(*ORANGE); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(8); c.stroke()
    # stripes
    c.set_source_rgb(0.82, 0.42, 0.12); c.set_line_width(12)
    for dx, l in ((-34, 38), (0, 50), (34, 38)):
        c.move_to(dx, -146); c.line_to(dx * 0.8, -146 + l); c.stroke()
    # muzzle
    c.save(); c.translate(0, 62); c.scale(1.45, 1); c.arc(0, 0, 66, 0, 2 * math.pi); c.restore()
    c.set_source_rgb(1, 0.9, 0.78); c.fill()
    # eyes
    blink = 1.0 if (t % 3.7) < 0.12 else 0.0
    lid = max(blink, 0.15 + 0.4 * sly)
    for sx in (-1, 1):
        ex, ey = sx * 66, -18
        c.save(); c.translate(ex, ey); c.scale(1, 0.9); c.arc(0, 0, 38, 0, 2 * math.pi); c.restore()
        c.set_source_rgb(1, 1, 1); c.fill_preserve()
        c.save(); c.clip()
        c.arc(ex + look[0] * 14, ey + 4 + look[1] * 10, 19, 0, 2 * math.pi); c.set_source_rgb(*INK); c.fill()
        c.arc(ex + look[0] * 14 + 7, ey - 3 + look[1] * 10, 6, 0, 2 * math.pi); c.set_source_rgb(1, 1, 1); c.fill()
        # eyelid (slanted for the sly look)
        ly = ey - 40 + lid * 78
        slant = sx * 14 * sly
        c.move_to(ex - 50, ey - 60); c.line_to(ex + 50, ey - 60)
        c.line_to(ex + 50, ly - slant); c.line_to(ex - 50, ly + slant); c.close_path()
        c.set_source_rgb(*ORANGE); c.fill()
        c.move_to(ex - 50, ly + slant); c.line_to(ex + 50, ly - slant)
        c.set_source_rgb(*INK); c.set_line_width(7); c.stroke()
        c.restore()
        c.save(); c.translate(ex, ey); c.scale(1, 0.9); c.arc(0, 0, 38, 0, 2 * math.pi); c.restore()
        c.set_source_rgb(*INK); c.set_line_width(7); c.stroke()
        # brows
        raise_ = 10 + (20 * sly if sx == 1 else -4 * sly)
        c.move_to(ex - 30, ey - 52 - raise_ + sx * 6 * sly); c.line_to(ex + 30, ey - 52 - raise_ - sx * 6 * sly)
        c.set_line_width(10); c.stroke()
    # nose
    c.move_to(-16, 34); c.line_to(16, 34); c.line_to(0, 50); c.close_path()
    c.set_source_rgb(1, 0.45, 0.58); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(5); c.stroke()
    # mouth
    m = mouth(t) if talk else 0.0
    if m > 0.08:
        c.save(); c.translate(0, 78 + m * 6); c.scale(1, 0.25 + m * 0.9); c.arc(0, 0, 34, 0, 2 * math.pi); c.restore()
        c.set_source_rgb(0.45, 0.07, 0.14); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(6); c.stroke()
    else:
        c.set_source_rgb(*INK); c.set_line_width(6)
        c.move_to(0, 50); c.curve_to(0, 70, -30, 76, -40, 60 - 10 * sly); c.stroke()
        c.move_to(0, 50); c.curve_to(0, 70, 30, 76, 46, 54 - 14 * sly); c.stroke()
    # whiskers
    c.set_line_width(4)
    for sx in (-1, 1):
        for k, dy in enumerate((-8, 6, 20)):
            c.move_to(sx * 92, 58 + dy); c.line_to(sx * 175, 46 + dy + k * 12 - 8); c.stroke()
    c.restore()


# ---------------------------------------------------------------- background
random.seed(7)
STARS = [(random.uniform(0, W), random.uniform(0, H), random.uniform(2, 6), random.uniform(0, 6.28)) for _ in range(60)]


def background(c, t, hue=(0.16, 0.04, 0.28), hue2=(0.03, 0.01, 0.07)):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *hue)
    g.add_color_stop_rgb(1, *hue2)
    c.set_source(g)
    c.paint()
    # slow diagonal stripes
    c.save()
    c.set_source_rgba(1, 1, 1, 0.035)
    off = (t * 60) % 160
    for i in range(-20, 30):
        x = i * 160 + off
        c.move_to(x, 0); c.line_to(x + 80, 0); c.line_to(x + 80 - H * 0.6, H); c.line_to(x - H * 0.6, H); c.close_path()
    c.fill()
    c.restore()
    for x, y, r, ph in STARS:
        a = 0.15 + 0.25 * (0.5 + 0.5 * math.sin(t * 2 + ph))
        c.arc(x, (y - t * 25 * r) % H, r, 0, 2 * math.pi)
        c.set_source_rgba(1, 0.9, 0.5, a)
        c.fill()


def header(c, lt, label, sub):
    a = ease_out(prog(lt, 0, 0.3))
    y = 200 - (1 - a) * 80
    w = pill(c, label, 540, y, 46, YELLOW, INK, alpha=a)
    text(c, sub, 540, y + 82, 42, WHITE, outline=10, alpha=a)


# ---------------------------------------------------------------- scenes
def scene_hook(c, t, lt, D):
    # BLACK FRIDAY slam
    for i, (word, y, bg, fg) in enumerate((("BLACK", 330, INK, WHITE), ("FRIDAY", 500, YELLOW, INK))):
        p = pop(lt, 0.05 + i * 0.18, 0.4)
        if p <= 0:
            continue
        s = 1 + (1 - p) * 1.6
        scaled(c, 540, y, s, rot=-0.06)
        w = text_w(c, word, 170) + 70
        fill_rrect(c, 540 - w / 2, y - 100, w, 200, 30, bg, stroke=YELLOW if bg == INK else None, lw=10)
        text(c, word, 540, y, 170, fg)
        c.restore()
    # calendar card
    p = pop(lt, 0.9, 0.4)
    if p > 0:
        scaled(c, 250, 760, p, rot=-0.1)
        fill_rrect(c, 110, 640, 280, 270, 30, WHITE, stroke=INK)
        fill_rrect(c, 110, 640, 280, 80, 30, RED)
        c.rectangle(110, 690, 280, 30); c.set_source_rgb(*RED); c.fill()
        text(c, "НОЯБРЬ", 250, 680, 40, WHITE)
        text(c, "27", 250, 810, 130, INK)
        c.restore()
        b = pop(lt, 1.4, 0.35)
        scaled(c, 300, 905, b, rot=0.12)
        pill(c, "−10 ДНЕЙ", 300, 905, 40, YELLOW, INK)
        c.restore()
    # 4 tricks badge
    p = pop(lt, D * 0.5, 0.45)
    if p > 0:
        scaled(c, 830, 820, p, rot=0.08 + math.sin(lt * 4) * 0.03)
        c.arc(830, 820, 150, 0, 2 * math.pi)
        c.set_source_rgb(*RED); c.fill_preserve(); c.set_source_rgb(*WHITE); c.set_line_width(10); c.stroke()
        text(c, "4", 830, 780, 150, WHITE)
        text(c, "ТРЮКА", 830, 890, 46, WHITE)
        c.restore()
    # cat peeking up
    rise = ease_back(prog(lt, 0.4, 0.6), 1.2)
    draw_cat(c, 540, 1600 - rise * 400, 1.0, t, sly=0.4, look=(0.3, -0.2))


def scene_price(c, t, lt, D):
    header(c, lt, "ТРЮК #1", "ФЕЙКОВАЯ СКИДКА")
    f = lt / D
    swing = math.sin(lt * 2.4) * 0.05
    p = pop(lt, 0.1, 0.45)
    scaled(c, 540, 470, p, rot=swing)
    c.move_to(540, 390); c.line_to(540, 470)
    c.set_source_rgb(*WHITE); c.set_line_width(6); c.stroke()
    # tag body
    c.move_to(240, 560); c.line_to(540, 470); c.line_to(840, 560); c.line_to(840, 1060); c.line_to(240, 1060); c.close_path()
    c.set_source_rgb(1, 0.98, 0.93); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(10); c.stroke()
    c.arc(540, 545, 22, 0, 2 * math.pi); c.set_source_rgb(*INK); c.fill()
    # price that rolls up
    up = ease_out(prog(f, 0.28, 0.14))
    price = 2990 + (9990 - 2990) * up
    col = (INK if up < 0.01 else RED)
    text(c, fmt(price) + " ₽", 540, 690, 120, col)
    if 0.28 < f:
        a = prog(f, 0.28, 0.05)
        text(c, "за неделю до", 540, 790, 44, (0.4, 0.35, 0.5), alpha=a)
        # arrow up
        if f < 0.6:
            ay = 640 - 30 * math.sin(lt * 8)
            c.move_to(800, ay - 60); c.line_to(840, ay); c.line_to(820, ay); c.line_to(820, ay + 50)
            c.line_to(780, ay + 50); c.line_to(780, ay); c.line_to(760, ay); c.close_path()
            c.set_source_rgba(*RED, a); c.fill()
    # strike + new price
    st = ease_out(prog(f, 0.6, 0.06))
    if st > 0:
        c.move_to(290, 700); c.line_to(290 + 500 * st, 680)
        c.set_source_rgb(*RED); c.set_line_width(14); c.stroke()
        q = pop(lt, D * 0.66, 0.35)
        scaled(c, 540, 930, q)
        text(c, "2 997 ₽", 540, 930, 150, (0.05, 0.6, 0.3))
        c.restore()
    c.restore()
    # stamp −70%
    q = pop(lt, D * 0.62, 0.3)
    if q > 0:
        s = 1 + (1 - q) * 2.2 if q < 1 else 1
        scaled(c, 830, 470, s, rot=0.25)
        c.arc(830, 470, 125, 0, 2 * math.pi)
        c.set_source_rgb(*RED); c.fill_preserve(); c.set_source_rgb(*YELLOW); c.set_line_width(10); c.stroke()
        text(c, "−70%", 830, 470, 72, WHITE)
        c.restore()
    q = pop(lt, D * 0.86, 0.35)
    if q > 0:
        scaled(c, 540, 1180, q, rot=-0.04)
        pill(c, "= ТА ЖЕ ЦЕНА", 540, 1180, 64, RED, WHITE, pad=40)
        c.restore()


def scene_timer(c, t, lt, D):
    header(c, lt, "ТРЮК #2", "ФЕЙКОВЫЙ ТАЙМЕР")
    f = lt / D
    p = pop(lt, 0.1, 0.4)
    scaled(c, 540, 760, p)
    # browser window
    fill_rrect(c, 110, 430, 860, 660, 40, (0.95, 0.95, 1), stroke=INK, lw=10)
    rrect(c, 110, 430, 860, 100, 40); c.set_source_rgb(0.85, 0.85, 0.95); c.fill()
    for i, col in enumerate((RED, YELLOW, GREEN)):
        c.arc(170 + i * 50, 480, 15, 0, 2 * math.pi); c.set_source_rgb(*col); c.fill()
    fill_rrect(c, 330, 455, 560, 50, 25, WHITE)
    text(c, "shop.example/sale", 610, 480, 30, (0.4, 0.4, 0.5))
    # reset logic
    resets = [0.52, 0.8]
    last = max([r for r in resets if f >= r], default=0.0)
    since = (f - last) * D
    secs = max(0, 300 - 1 - int(since * 9))
    flash = clamp(1 - (f - last) * D / 0.4) if last else 0
    text(c, "ОСТАЛОСЬ:", 540, 610, 54, (0.35, 0.3, 0.45))
    pulse = 1 + 0.04 * math.sin(lt * 12)
    fill_rrect(c, 180, 680, 720, 260, 30, INK)
    scaled(c, 540, 810, pulse)
    text(c, f"{secs // 60:02d}:{secs % 60:02d}", 540, 810, 190, RED if not flash else YELLOW, font="DejaVu Sans Mono")
    c.restore()
    if flash:
        fill_rrect(c, 180, 680, 720, 260, 30, YELLOW, alpha=0.5 * flash)
    text(c, "успей купить!", 540, 1020, 48, RED)
    c.restore()
    # refresh button + cursor
    for r in resets:
        q = prog(f, r - 0.08, 0.08)
        if 0 < q < 1 or (0 < f - r < 0.1):
            ang = ease_out(prog(f, r, 0.1)) * 2 * math.pi
            c.save(); c.translate(225, 480)
            c.arc(0, 0, 70, 0, 2 * math.pi); c.set_source_rgb(*YELLOW); c.fill()
            c.rotate(ang)
            c.arc(0, 0, 36, 0.4, 2 * math.pi - 0.2); c.set_source_rgb(*INK); c.set_line_width(12); c.stroke()
            c.move_to(36, -30); c.line_to(52, 4); c.line_to(18, 4); c.close_path(); c.fill()
            c.restore()
            # cursor
            cx, cy = 225 + 200 * (1 - ease_out(q)) + 20, 480 + 300 * (1 - ease_out(q)) + 20
            c.move_to(cx, cy); c.line_to(cx, cy + 70); c.line_to(cx + 18, cy + 54); c.line_to(cx + 34, cy + 86)
            c.line_to(cx + 46, cy + 80); c.line_to(cx + 30, cy + 48); c.line_to(cx + 54, cy + 48); c.close_path()
            c.set_source_rgb(*WHITE); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(5); c.stroke()
    q = pop(lt, D * 0.58, 0.35)
    if q > 0:
        scaled(c, 540, 1200, q, rot=0.04)
        pill(c, "СНОВА 05:00", 540, 1200, 64, YELLOW, INK, pad=40)
        c.restore()


def draw_headphones(c, cx, cy, s, t):
    c.save(); c.translate(cx, cy); c.scale(s, s); c.rotate(math.sin(t * 2) * 0.06)
    c.arc(0, 0, 130, math.pi, 2 * math.pi)
    c.set_source_rgb(*INK); c.set_line_width(40); c.stroke()
    c.arc(0, 0, 130, math.pi, 2 * math.pi)
    c.set_source_rgb(0.35, 0.3, 0.95); c.set_line_width(24); c.stroke()
    for sx in (-1, 1):
        fill_rrect(c, sx * 130 - 45, -20, 90, 150, 40, (0.35, 0.3, 0.95), stroke=INK, lw=8)
        fill_rrect(c, sx * 130 - 25 + sx * 10, 10, 30, 90, 15, (0.6, 0.6, 1))
    c.restore()


def scene_stock(c, t, lt, D):
    header(c, lt, "ТРЮК #3", "ПОСЛЕДНИЙ ТОВАР")
    f = lt / D
    p = pop(lt, 0.1, 0.4)
    scaled(c, 400, 720, p)
    fill_rrect(c, 130, 430, 540, 600, 40, WHITE, stroke=INK)
    draw_headphones(c, 400, 640, 1.1, t)
    text(c, "Наушники Pro", 400, 860, 50, INK)
    text(c, "2 997 ₽", 400, 940, 60, (0.05, 0.6, 0.3))
    c.restore()
    q = pop(lt, D * 0.28, 0.35)
    if q > 0:
        s = q * (1 + 0.06 * math.sin(lt * 10))
        scaled(c, 400, 450, s, rot=-0.08)
        pill(c, "ОСТАЛСЯ 1 ШТ!", 400, 450, 54, RED, WHITE, pad=36)
        c.restore()
    # flipping calendar
    months = ["СЕНТЯБРЬ", "ОКТЯБРЬ", "НОЯБРЬ"]
    times = [0.5, 0.64, 0.78]
    q = pop(lt, D * 0.48, 0.35)
    if q > 0:
        idx = sum(1 for x in times if f >= x) - 1
        idx = max(0, idx)
        flip = prog(f, times[idx], 0.04) if idx > 0 else 1
        scaled(c, 820, 950, q, rot=0.08)
        fill_rrect(c, 650, 820, 340, 270, 30, WHITE, stroke=INK)
        fill_rrect(c, 650, 820, 340, 80, 30, (0.35, 0.3, 0.95))
        c.rectangle(650, 870, 340, 30); c.set_source_rgb(0.35, 0.3, 0.95); c.fill()
        text(c, months[idx], 820, 860, 38, WHITE)
        c.save(); c.translate(820, 1000); c.scale(1, max(0.05, flip)); c.translate(-820, -1000)
        text(c, "1 шт", 820, 1000, 84, RED)
        c.restore()
        c.restore()
    q = pop(lt, D * 0.86, 0.35)
    if q > 0:
        scaled(c, 540, 1210, q, rot=-0.04)
        pill(c, "3 МЕСЯЦА ПОДРЯД", 540, 1210, 60, YELLOW, INK, pad=40)
        c.restore()


def scene_cart(c, t, lt, D):
    header(c, lt, "ТРЮК #4", "СЮРПРИЗ В КОРЗИНЕ")
    f = lt / D
    q = pop(lt, 0.1, 0.35)
    scaled(c, 540, 420, q)
    pill(c, "В каталоге: 2 997 ₽", 540, 420, 52, GREEN, INK, pad=36)
    c.restore()
    items = [(0.36, "Доставка", 499), (0.48, "Сервисный сбор", 199), (0.62, "Подписка /мес", 399)]
    shown = [it for it in items if f >= it[0]]
    n = len(shown)
    # receipt grows
    hgt = 260 + 110 * n
    p = pop(lt, 0.25, 0.4)
    scaled(c, 540, 520, p)
    top = 510
    c.move_to(160, top); c.line_to(920, top); c.line_to(920, top + hgt)
    for i in range(19):
        c.line_to(920 - (i + 0.5) * 40, top + hgt + (18 if i % 2 == 0 else 0))
    c.line_to(160, top + hgt); c.close_path()
    c.set_source_rgb(1, 0.99, 0.95); c.fill_preserve(); c.set_source_rgb(*INK); c.set_line_width(8); c.stroke()
    text(c, "КОРЗИНА", 540, top + 60, 48, INK)
    text(c, "Наушники Pro", 200, top + 150, 44, INK, align="l")
    text(c, "2 997 ₽", 880, top + 150, 44, INK, align="r")
    total = 2997
    for i, (t0, name, val) in enumerate(shown):
        a = pop(lt, t0 * D, 0.3)
        y = top + 260 + i * 110
        dx = (1 - min(a, 1)) * 300
        text(c, "+ " + name, 200 + dx, y, 42, RED, align="l", alpha=clamp(a))
        text(c, fmt(val) + " ₽", 880 + dx, y, 42, RED, align="r", alpha=clamp(a))
        total += val * clamp(prog(lt, t0 * D, 0.3))
    c.restore()
    # total
    q = pop(lt, 0.4, 0.4)
    if q > 0:
        shake = (math.sin(lt * 50) * 6) if f > 0.7 else 0
        scaled(c, 540 + shake, 1260, q)
        fill_rrect(c, 160, 1180, 760, 160, 30, INK, stroke=RED if f > 0.62 else YELLOW, lw=10)
        text(c, "ИТОГО:", 330, 1260, 54, WHITE)
        text(c, fmt(total) + " ₽", 680, 1260, 80, RED if total > 2997 else YELLOW)
        c.restore()


def scene_meme(c, t, lt, D):
    # dramatic dark bg + spotlight
    c.set_source_rgba(0, 0, 0, 0.55); c.paint()
    g = cairo.RadialGradient(540, 800, 50, 540, 800, 800)
    g.add_color_stop_rgba(0, 1, 0.85, 0.4, 0.35)
    g.add_color_stop_rgba(1, 0, 0, 0, 0)
    c.set_source(g); c.paint()
    zoom = 1.0 + 0.45 * ease_out(prog(lt, D * 0.35, 0.25))
    draw_cat(c, 540, 830, 1.35 * zoom, t, sly=1.0, look=(0.6, 0.2))
    p = pop(lt, 0.0, 0.3)
    scaled(c, 540, 300, p, rot=-0.03)
    pill(c, "ПРОДАВЕЦ:", 540, 300, 56, WHITE, INK, pad=36)
    c.restore()


def scene_cta(c, t, lt, D):
    p = pop(lt, 0.0, 0.35)
    scaled(c, 540, 260, p)
    text(c, "ЗАПОМНИ:", 540, 260, 96, YELLOW, outline=14)
    c.restore()
    items = ["Смотри историю цен", "Не верь таймерам", "Считай итог в корзине"]
    for i, s in enumerate(items):
        q = pop(lt, 0.25 + i * 0.35, 0.35)
        if q <= 0:
            continue
        y = 470 + i * 200
        scaled(c, 540, y, q)
        fill_rrect(c, 110, y - 80, 860, 160, 34, WHITE, stroke=INK)
        c.arc(200, y, 50, 0, 2 * math.pi); c.set_source_rgb(*GREEN); c.fill()
        c.move_to(175, y); c.line_to(195, y + 22); c.line_to(228, y - 22)
        c.set_source_rgb(*WHITE); c.set_line_width(14); c.set_line_cap(cairo.LINE_CAP_ROUND); c.stroke()
        text(c, s, 280, y, 50, INK, align="l")
        c.restore()
    q = pop(lt, D * 0.6, 0.4)
    if q > 0:
        bounce = abs(math.sin(lt * 5)) * 30
        scaled(c, 540, 1180 - bounce, q)
        fill_rrect(c, 250, 1100 - bounce, 580, 160, 80, YELLOW, stroke=INK)
        # bookmark icon
        bx, by = 340, 1180 - bounce
        c.move_to(bx - 30, by - 50); c.line_to(bx + 30, by - 50); c.line_to(bx + 30, by + 50)
        c.line_to(bx, by + 25); c.line_to(bx - 30, by + 50); c.close_path()
        c.set_source_rgb(*INK); c.fill()
        text(c, "СОХРАНИ", 590, by, 76, INK)
        c.restore()


SCENES = {"hook": scene_hook, "price": scene_price, "timer": scene_timer, "stock": scene_stock,
          "cart": scene_cart, "meme": scene_meme, "cta": scene_cta}


# ---------------------------------------------------------------- captions (word-by-word)
def build_captions():
    caps = []
    for s in SEGS:
        words = re.findall(r"\S+", s["text"])
        weights = [len(re.sub(r"[^\wё-]", "", w, flags=re.I)) + 2 + (4 if re.search(r"[.,:?!»]$", w) else 0)
                   for w in words]
        tot = sum(weights)
        speech = s["dur"] - 0.15
        t = s["start"] + 0.08
        timed = []
        for w, wt in zip(words, weights):
            d = speech * wt / tot
            timed.append((t, t + d, w))
            t += d
        # chunk into lines of up to 3 words / 20 chars
        chunk = []
        for item in timed:
            chunk.append(item)
            txt = " ".join(x[2] for x in chunk)
            if len(chunk) >= 3 or len(txt) > 16 or re.search(r"[.?!:]$", item[2]):
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
    size = 88
    words = [w.upper() for _, _, w in chunk]
    widths = [text_w(c, w, size) for w in words]
    space = 36
    total = sum(widths) + space * (len(words) - 1)
    if total > 960:
        size = size * 960 / total
        widths = [text_w(c, w, size) for w in words]
        space *= 960 / total
        total = 960
    y = 1480
    scaled(c, 540, y, 0.6 + 0.4 * p)
    x = 540 - total / 2
    for (t0, t1, _), w, wd in zip(chunk, words, widths):
        active = t0 <= t < t1 + 0.02
        col = YELLOW if active else WHITE
        if active:
            scaled(c, x + wd / 2, y, 1.05)
        text(c, w, x, y, size, col, align="l", outline=18)
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
    nxt = SEGS[SEGS.index(seg) + 1] if seg is not SEGS[-1] else None
    end = (nxt["start"] - 0.12) if nxt else TOTAL
    lt = t - (seg["start"] - 0.12)
    D = end - (seg["start"] - 0.12)
    hues = {"hook": (0.20, 0.03, 0.30), "price": (0.30, 0.05, 0.18), "timer": (0.05, 0.07, 0.30),
            "stock": (0.06, 0.18, 0.26), "cart": (0.25, 0.10, 0.05), "meme": (0.12, 0.03, 0.16),
            "cta": (0.04, 0.20, 0.14)}
    background(c, t, hues[seg["id"]])
    # scene-in transition: quick zoom + slide
    tr = ease_out(prog(lt, 0, 0.22))
    c.save()
    c.translate(540, 900)
    c.scale(1.12 - 0.12 * tr, 1.12 - 0.12 * tr)
    c.translate(-540 + (1 - tr) * 220, -900)
    if seg["id"] == "hook" and lt < 0.6:  # impact shake
        k = (0.6 - lt) * 25
        c.translate(math.sin(lt * 90) * k, math.cos(lt * 70) * k)
    SCENES[seg["id"]](c, t, lt, D)
    c.restore()
    if lt < 0.12:  # white flash between scenes
        c.set_source_rgba(1, 1, 1, 0.5 * (1 - lt / 0.12)); c.paint()
    draw_captions(c, t)
    # progress bar (top)
    c.rectangle(0, 0, W * t / TOTAL, 10); c.set_source_rgb(*YELLOW); c.fill()


# ---------------------------------------------------------------- audio: music + sfx
def synth_audio():
    n = len(VOICE)
    tt = np.arange(n) / SR
    music = np.zeros(n, dtype=np.float32)
    bpm = 128
    beat = 60 / bpm
    rng = np.random.default_rng(1)

    def add(sig, at, gain=1.0):
        i = int(at * SR)
        if i >= n:
            return
        j = min(n, i + len(sig))
        music[i:j] += gain * sig[: j - i]

    kl = int(0.35 * SR); kt = np.arange(kl) / SR
    kick = np.sin(2 * np.pi * (50 + 120 * np.exp(-kt * 25)) * kt) * np.exp(-kt * 9)
    hl = int(0.05 * SR)
    hat = rng.standard_normal(hl) * np.exp(-np.arange(hl) / SR * 80)
    hat = np.diff(hat, prepend=0)
    sl = int(0.18 * SR)
    snare = rng.standard_normal(sl) * np.exp(-np.arange(sl) / SR * 22) * 0.6
    bass_notes = [41.2, 41.2, 49.0, 36.7]  # E1 E1 G1 D1
    chords = [[164.8, 196.0, 246.9], [164.8, 196.0, 246.9], [196.0, 246.9, 293.7], [146.8, 185.0, 220.0]]
    nb = int(TOTAL / beat) + 1
    for b in range(nb):
        at = b * beat
        bar = (b // 4) % 4
        add(kick, at, 0.9 if b % 4 in (0, 2) else 0.0)
        if b % 4 in (1, 3):
            add(snare, at, 0.5)
        add(hat, at + beat / 2, 0.25)
        add(hat, at, 0.12)
        bl = int(beat * SR); btt = np.arange(bl) / SR
        f0 = bass_notes[bar]
        bass = np.tanh(2 * np.sin(2 * np.pi * f0 * 2 * btt)) * np.exp(-btt * 3)
        add(bass, at, 0.35)
        if b % 4 == 0:
            cl = int(beat * 4 * SR); ctt = np.arange(cl) / SR
            pad = sum(np.sign(np.sin(2 * np.pi * fq * ctt)) * 0.3 + np.sin(2 * np.pi * fq * ctt) for fq in chords[bar])
            env = np.minimum(1, ctt * 6) * np.exp(-ctt * 0.6)
            add(pad * env, at, 0.05)
    # sfx
    sfx = np.zeros(n, dtype=np.float32)

    def put(sig, at, gain):
        i = int(at * SR)
        j = min(n, i + len(sig))
        if i < n:
            sfx[i:j] += gain * sig[: j - i]

    wl = int(0.35 * SR); wt = np.arange(wl) / SR
    noise = rng.standard_normal(wl)
    whoosh = np.convolve(noise, np.ones(30) / 30, mode="same") * np.sin(np.pi * wt / 0.35) ** 2
    pl = int(0.12 * SR); pt = np.arange(pl) / SR
    popsnd = np.sin(2 * np.pi * (300 + 900 * pt / 0.12) * pt) * np.exp(-pt * 30)
    il = int(0.45 * SR); it = np.arange(il) / SR
    ding = (np.sin(2 * np.pi * 1318 * it) + 0.5 * np.sin(2 * np.pi * 1975 * it)) * np.exp(-it * 7)
    bl2 = int(0.3 * SR); bt = np.arange(bl2) / SR
    boom = np.sin(2 * np.pi * (40 + 80 * np.exp(-bt * 15)) * bt) * np.exp(-bt * 6) + rng.standard_normal(bl2) * np.exp(-bt * 30) * 0.4
    for s in SEGS:
        put(whoosh, s["start"] - 0.25, 0.35)
    st = {s["id"]: (s["start"] - 0.12, None) for s in SEGS}

    def Dof(i):
        s = SEGS[i]
        end = SEGS[i + 1]["start"] - 0.12 if i + 1 < len(SEGS) else TOTAL
        return end - (s["start"] - 0.12)

    idx = {s["id"]: i for i, s in enumerate(SEGS)}
    h0 = st["hook"][0]
    put(boom, h0 + 0.05, 0.9); put(boom, h0 + 0.23, 0.9)
    put(popsnd, h0 + 0.9, 0.5); put(popsnd, h0 + 1.4, 0.5); put(popsnd, h0 + Dof(idx["hook"]) * 0.5, 0.6)
    p0, pd = st["price"][0], Dof(idx["price"])
    put(boom, p0 + pd * 0.62, 0.8); put(ding, p0 + pd * 0.66, 0.4); put(popsnd, p0 + pd * 0.86, 0.5)
    t0, td = st["timer"][0], Dof(idx["timer"])
    for r in (0.52, 0.8):
        put(popsnd, t0 + td * r, 0.6); put(ding, t0 + td * r + 0.02, 0.3)
    s0, sd = st["stock"][0], Dof(idx["stock"])
    put(popsnd, s0 + sd * 0.28, 0.5)
    for r in (0.64, 0.78):
        put(popsnd, s0 + sd * r, 0.35)
    put(popsnd, s0 + sd * 0.86, 0.5)
    c0, cd = st["cart"][0], Dof(idx["cart"])
    for r in (0.36, 0.48, 0.62):
        put(ding, c0 + cd * r, 0.35)
    m0, md = st["meme"][0], Dof(idx["meme"])
    put(boom, m0 + md * 0.35, 1.0)
    a0, ad = st["cta"][0], Dof(idx["cta"])
    for i in range(3):
        put(popsnd, a0 + 0.25 + i * 0.35, 0.5)
    put(ding, a0 + ad * 0.6, 0.4)

    # sidechain-ish ducking of music under voice
    env = np.convolve(np.abs(VOICE), np.ones(int(0.15 * SR)) / int(0.15 * SR), mode="same")
    duck = 1 - 0.55 * np.clip(env / (np.percentile(env, 90) + 1e-9), 0, 1)
    # in the meme scene the music drops out for drama
    drop = np.ones(n, dtype=np.float32)
    drop[int(m0 * SR):int((m0 + md) * SR)] = 0.15
    mix = VOICE * 1.0 + music * 0.18 * duck * drop + sfx * 0.5
    fade = np.ones(n); fl = int(0.5 * SR); fade[-fl:] = np.linspace(1, 0, fl)
    mix *= fade
    mix /= max(1e-6, np.max(np.abs(mix))) / 0.95
    return mix.astype(np.float32)


def main():
    preview = "--preview" in sys.argv
    if preview:  # stills for checking layout
        for s in SEGS:
            for k, fr in enumerate((0.3, 0.9)):
                t = s["start"] + s["dur"] * fr
                surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
                render_frame(cairo.Context(surf), t)
                surf.write_to_png(str(OUT / f"preview_{s['id']}_{k}.png"))
        print("previews written")
        return
    audio = synth_audio()
    wav = OUT / "mix.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-c:a", "pcm_s16le", str(wav)], input=audio.tobytes(), check=True)
    out = OUT / "black_friday_tiktok.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "medium",
                           "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                           "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    nframes = int(TOTAL * FPS)
    for i in range(nframes):
        c = cairo.Context(surf)
        render_frame(c, i / FPS)
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

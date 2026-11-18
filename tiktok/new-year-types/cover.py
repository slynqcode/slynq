"""Обложка для TikTok (1080x1920). Важное — в центре, чтобы не обрезалось в сетке профиля (3:4)."""
import cairo

from render import (GOLD, H, INK, OUT, RED, W, WHITE, background, draw_mandarin, garland, pill, scaled, text)


def main():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    background(c, 2.0)
    garland(c, 0.7)
    scaled(c, 540, 470, 1.0, rot=-0.04)
    text(c, "43 ДНЯ", 540, 400, 190, GOLD, outline=24)
    text(c, "ДО НОВОГО ГОДА", 540, 560, 78, WHITE, outline=16)
    c.restore()
    # 5 types: two rows of mandarins with numbers
    spots = [(230, 870, "glasses", {}), (540, 840, "santa", {}), (850, 870, "sweat", {"run": 0.0}),
             (360, 1210, "headband", {}), (720, 1210, None, {"sleep": True})]
    for i, (x, y, outfit, kw) in enumerate(spots):
        draw_mandarin(c, x, y, 0.5, 1.0 + i * 0.37, outfit=outfit, talk=False, **kw)
        c.arc(x - 95, y - 95, 38, 0, 6.2832)
        c.set_source_rgb(*RED); c.fill_preserve(); c.set_source_rgb(1, 1, 1); c.set_line_width(5); c.stroke()
        text(c, str(i + 1), x - 95, y - 98, 46, WHITE)
    scaled(c, 540, 1540, 1.0, rot=-0.03)
    pill(c, "ТЫ КАКОЙ ТИП?", 540, 1540, 80, GOLD, INK, pad=50)
    c.restore()
    out = OUT / "cover.png"
    surf.write_to_png(str(out))
    print(out)


if __name__ == "__main__":
    main()

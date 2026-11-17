"""Обложка для TikTok (1080x1920). Важное — в центре, чтобы не обрезалось в сетке профиля (3:4)."""
import cairo

from render import (CYAN, H, INK, OUT, PINK, W, YELLOW, background, blob_monster, draw_phone, pill, polaroid,
                    scaled, text, vhs_overlay)


def main():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    background(c, 1.3, (0.98, 0.55, 0.62), (0.35, 0.25, 0.75))
    # polaroids behind
    polaroid(c, 230, 1180, -0.22, 0.8, "#монстрик", lambda cc: blob_monster(cc, 0, -20, 0.9, 0))
    polaroid(c, 860, 1200, 0.2, 0.8, "#2016", lambda cc: text(cc, "2016", 0, -30, 110, PINK, outline=10))
    # hero: phone with dog filter + rainbow
    draw_phone(c, 540, 1080, 0.95, 1.0, dog=1.0, rainbow=0.6, talk=False)
    # title
    scaled(c, 540, 470, 1.0, rot=-0.05)
    text(c, "ВЕРНИТЕ", 540, 400, 130, YELLOW, outline=22)
    text(c, "2016", 540, 590, 260, CYAN, outline=26)
    c.restore()
    scaled(c, 540, 780, 1.0, rot=0.04)
    pill(c, "#2026isthenew2016", 540, 780, 50, PINK, (1, 1, 1), pad=36)
    c.restore()
    scaled(c, 540, 1610, 1.0, rot=-0.03)
    pill(c, "А ТЫ ПОМНИШЬ?", 540, 1610, 72, YELLOW, INK, pad=48)
    c.restore()
    vhs_overlay(c, 1.3)
    out = OUT / "cover.png"
    surf.write_to_png(str(out))
    print(out)


if __name__ == "__main__":
    main()

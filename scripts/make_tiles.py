#!/usr/bin/env python3
"""Turn the interest GIFs into web-ready tiles.

Originals live in assets/interests/raw/. Each is centre-cropped to fill the
tile box (no letterboxing, no squashing), desaturated to match the terminal,
framed with a hairline border, and written to assets/interests/<name>.gif —
same name as the source, so the README paths stay obvious.

Anything that would still land over ~2 MB is thinned out by dropping every
second frame and doubling its duration, until it's small enough to load fast.

    python3 scripts/make_tiles.py [--width 372] [--height 256] [--keep-colour]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageSequence

BG = (13, 13, 13)
# caption burned into each tile, keyed by source filename stem
CAPTIONS = {"1": "CODE GEASS", "2": "HELLSING", "3": "NANA", "4": "A SILENT VOICE"}
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/opt/freestyle/python/lib/python3.12/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSansMono.ttf",
]
EDGE = (38, 38, 38)
RAW = Path("assets/interests/raw")
OUT = Path("assets/interests")
LIMIT = 2_200_000
EXTS = (".gif", ".webp", ".png", ".apng")


def cover(im: Image.Image, w: int, h: int) -> Image.Image:
    sw, sh = im.size
    scale = max(w / sw, h / sh)
    nw, nh = max(w, round(sw * scale)), max(h, round(sh * scale))
    im = im.resize((nw, nh), Image.LANCZOS)
    x, y = (nw - w) // 2, (nh - h) // 2
    return im.crop((x, y, x + w, y + h))


def mono(size: int) -> ImageFont.FreeTypeFont | None:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return None


def caption(im: Image.Image, text: str) -> None:
    """Small letterspaced mono label, bottom-left, legible on light and dark."""
    font = mono(11)
    if not font:
        return
    d = ImageDraw.Draw(im)
    tracking, pad, baseline = 1.6, 12, im.height - 12
    x = pad
    for ch in text:
        d.text((x, baseline), ch, font=font, anchor="ls", fill=(240, 240, 240),
               stroke_width=2, stroke_fill=(0, 0, 0))
        x += d.textlength(ch, font=font) + tracking


def build(src: Path, dst: Path, w: int, h: int, colour: bool, step: int) -> tuple[int, float]:
    im = Image.open(src)
    frames, durations = [], []
    for i, frame in enumerate(ImageSequence.Iterator(im)):
        if i % step:
            continue
        rgba = frame.convert("RGBA")
        flat = Image.new("RGB", rgba.size, BG)
        flat.paste(rgba, mask=rgba.split()[-1])
        flat = cover(flat, w, h)
        if not colour:
            flat = flat.convert("L").convert("RGB")
        ImageDraw.Draw(flat).rectangle([0, 0, w - 1, h - 1], outline=EDGE)
        if src.stem in CAPTIONS:
            caption(flat, CAPTIONS[src.stem])
        frames.append(flat.quantize(colors=128, method=Image.MEDIANCUT))
        durations.append((frame.info.get("duration") or im.info.get("duration") or 80) * step)

    if all(d == 0 for d in durations):
        durations = [80] * len(frames)

    frames[0].save(dst, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, optimize=True, disposal=2)
    return len(frames), sum(durations) / 1000.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=372)
    ap.add_argument("--height", type=int, default=256)
    ap.add_argument("--keep-colour", action="store_true")
    args = ap.parse_args()

    sources = sorted(p for p in RAW.iterdir() if p.suffix.lower() in EXTS) if RAW.is_dir() else []
    if not sources:
        print(f"no source files in {RAW}/")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    for src in sources:
        dst = OUT / f"{src.stem}.gif"
        step = 1
        while True:
            n, secs = build(src, dst, args.width, args.height, args.keep_colour, step)
            size = dst.stat().st_size
            if size <= LIMIT or step >= 4:
                break
            step *= 2
        note = f"  (every {step}{'st' if step == 1 else 'nd' if step == 2 else 'th'} frame)" if step > 1 else ""
        print(f"{src.name:<10} -> {dst.name:<8} {n:>3} frames {secs:5.1f}s "
              f"{size/1024:6.0f} KB{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

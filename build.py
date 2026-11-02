"""Decode the braille portrait, shrink it to terminal width, rebuild the panel.

Braille glyphs are 2x4 dot cells, so shrinking means going back to the dot
matrix and resampling, not truncating characters. Everything here is exact
geometry, so the two columns can never drift.
"""
import math
from pathlib import Path

DOTS = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (0, 3), (1, 3)]
CELLS = 2  # cell width in dots
ROWS = 4   # cell height in dots
CHARSET = 36  # target width in characters (~72 dots)
GUTTER = 3

INFO = [
    "angelica@github",
    "---------------",
    "OS:       Linux Mint · full-stack dev",
    "Host:     Aiken, SC ⇄ Kuwait",
    "Kernel:   ICSA Kuwait · program 3 of 4",
    "Uptime:   building since middle school",
    "Packages: HTML CSS JS PHP MySQL Laravel",
    "Shell:    bash · zsh · powershell",
    "DE:       Figma · Adobe CC",
    "CPU:      human (1) @ 1.0 caffeine",
    "Memory:   NANA · Code Geass · Junji Ito",
    "Locale:   en_US · nu-metal + post-punk",
    "Status:   open to internships + freelance",
    "Contact:  aj-dornton@proton.me",
]


def decode(lines):
    """braille text -> dot matrix, m[x][y] in {0,1}"""
    cols = max(len(l) for l in lines)
    w, h = cols * CELLS, len(lines) * ROWS
    m = [[0] * h for _ in range(w)]
    for r, line in enumerate(lines):
        for c, ch in enumerate(line):
            off = ord(ch) - 0x2800
            if not 0 <= off <= 0xFF:
                continue
            for bit, (dx, dy) in enumerate(DOTS):
                if off >> bit & 1:
                    m[c * CELLS + dx][r * ROWS + dy] = 1
    return m


def encode(m, pad_to=None):
    """dot matrix -> braille text lines"""
    w, h = len(m), len(m[0])
    out = []
    for r in range(h // ROWS):
        row = []
        for c in range(w // CELLS):
            off = 0
            for bit, (dx, dy) in enumerate(DOTS):
                if m[c * CELLS + dx][r * ROWS + dy]:
                    off |= 1 << bit
            row.append(chr(0x2800 + off))
        line = "".join(row)
        if pad_to:
            line = line.ljust(pad_to, "\u2800")
        out.append(line)
    return out


def crop(m, margin=1):
    """trim empty dots around the art so the shrink spends pixels on the face"""
    w, h = len(m), len(m[0])
    xs = [x for x in range(w) if any(m[x])]
    ys = [y for y in range(h) if any(m[x][y] for x in range(w))]
    x0, x1 = max(0, xs[0] - margin), min(w - 1, xs[-1] + margin)
    y0, y1 = max(0, ys[0] - margin), min(h - 1, ys[-1] + margin)
    return [[m[x][y] for y in range(y0, y1 + 1)] for x in range(x0, x1 + 1)]


def resample(m, tw, th, thresh=0.34):
    """area-average downsample, then threshold back to 1-bit"""
    w, h = len(m), len(m[0])
    acc = [[0.0] * th for _ in range(tw)]
    for x in range(w):
        x0, x1 = x * tw / w, (x + 1) * tw / w
        for y in range(h):
            if not m[x][y]:
                continue
            y0, y1 = y * th / h, (y + 1) * th / h
            for tx in range(int(x0), min(tw, math.ceil(x1))):
                ox = min(x1, tx + 1) - max(x0, tx)
                if ox <= 0:
                    continue
                for ty in range(int(y0), min(th, math.ceil(y1))):
                    oy = min(y1, ty + 1) - max(y0, ty)
                    if oy > 0:
                        acc[tx][ty] += ox * oy
    area = (w / tw) * (h / th)
    return [[1 if acc[tx][ty] / area >= thresh else 0 for ty in range(th)] for tx in range(tw)]


def to_png(m, path, scale=3, ink=(20, 20, 20), paper=(250, 249, 246)):
    """render the dot matrix so it can actually be looked at"""
    from PIL import Image, ImageDraw
    w, h = len(m), len(m[0])
    img = Image.new("RGB", (w * scale + 2, h * scale + 2), paper)
    d = ImageDraw.Draw(img)
    for x in range(w):
        for y in range(h):
            if m[x][y]:
                d.rectangle([x * scale + 1, y * scale + 1,
                             x * scale + scale - 1, y * scale + scale - 1], fill=ink)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return img.size


def main():
    raw = [l for l in Path("art.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    m = decode(raw)
    cropped = crop(m)

    tw = CHARSET * CELLS
    th = max(ROWS, int(round(tw * len(cropped[0]) / len(cropped) / ROWS)) * ROWS)
    small = resample(cropped, tw, th, thresh=float(__import__("os").environ.get("THRESH", 0.34)))
    art = encode(small)
    Path("art_small.txt").write_text("\n".join(art) + "\n", encoding="utf-8")

    art_w = CHARSET
    top = (len(art) - len(INFO)) // 2
    rows = []
    for i, line in enumerate(art):
        j = i - top
        right = INFO[j] if 0 <= j < len(INFO) else ""
        rows.append((line + " " * GUTTER + right).rstrip())
    panel = "\n".join(rows)
    Path("panel.txt").write_text(panel + "\n", encoding="utf-8")

    print(panel)
    src_dots = (len(m), len(m[0]))
    print("\n--- geometry ---")
    print(f"source:      {src_dots[0]}x{src_dots[1]} dots  ({src_dots[0]//2}x{src_dots[1]//4} chars)")
    print(f"cropped:     {len(cropped)}x{len(cropped[0])} dots")
    print(f"shrunk:      {len(small)}x{len(small[0])} dots  ({CHARSET}x{len(art)} chars)")
    print(f"info rows:   {top + 1}..{top + len(INFO)} of {len(art)}")
    print(f"panel width: {max(len(r) for r in rows)} chars (target <=80)")

    try:
        print("\npng:", to_png(m, "artifacts/art_original.png"),
              to_png(small, "artifacts/art_small.png"))
    except ImportError:
        print("\n(pillow missing, skipped png preview)")


if __name__ == "__main__":
    main()

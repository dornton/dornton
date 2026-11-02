"""Build assets/stack.svg: a monochrome marquee of brand glyphs.

Icons are vendored under scripts/icons/ (Simple Icons, CC0) so nothing is
fetched at render time — the Action does not need network for this file.
The scroll is SMIL, because GitHub renders repo SVGs inside <img>, where
JavaScript never runs.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "scripts" / "icons"
OUT = ROOT / "assets" / "stack.svg"

ORDER = ["html5", "css", "javascript", "php", "mysql",
         "laravel", "figma", "linux", "git", "githubactions"]

W, H = 760, 92
BG, EDGE, INK = "#0d0d0d", "#262626", "#f0f0f0"
GLYPH, PITCH, SPEED = 46, 100, 45.0


def read(slug):
    raw = (ICONS / f"{slug}.svg").read_text(encoding="utf-8")
    paths = re.findall(r'<path[^>]*\sd="([^"]+)"', raw)
    box = re.search(r'viewBox="([\d.\s-]+)"', raw)
    vb = [float(v) for v in box.group(1).split()] if box else [0, 0, 24, 24]
    return paths, vb


def glyphs():
    items = []
    for slug in ORDER:
        paths, vb = read(slug)
        scale = GLYPH / vb[2]
        items.append((paths, scale))
    return items


copy_w = PITCH * len(ORDER)
parts = []
for copy in range(2):  # two copies: the loop point lands on an identical frame
    for i, (paths, scale) in enumerate(glyphs()):
        cx = copy * copy_w + i * PITCH + PITCH / 2
        px, py = cx - GLYPH / 2, H / 2 - GLYPH / 2
        body = "".join(f'<path d="{d}"/>' for d in paths)
        parts.append(f'      <g transform="translate({px:.1f},{py:.1f}) scale({scale:.4f})">{body}</g>')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
  <title id="t">tech stack</title>
  <desc id="d">Monochrome brand glyphs scrolling right to left: {", ".join(ORDER)}.</desc>
  <defs>
    <clipPath id="clip"><rect width="{W}" height="{H}" rx="10"/></clipPath>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#000000"/>
      <stop offset="0.07" stop-color="#ffffff"/>
      <stop offset="0.93" stop-color="#ffffff"/>
      <stop offset="1" stop-color="#000000"/>
    </linearGradient>
    <mask id="fade"><rect width="{W}" height="{H}" fill="url(#edge)"/></mask>
  </defs>

  <rect width="{W}" height="{H}" rx="10" fill="{BG}"/>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{EDGE}"/>

  <g clip-path="url(#clip)" mask="url(#fade)">
    <g fill="{INK}" opacity="0.9">
      <g>
        <animateTransform attributeName="transform" type="translate"
          from="0 0" to="{-copy_w} 0" dur="{SPEED:g}s" repeatCount="indefinite"/>
{chr(10).join(parts)}
      </g>
    </g>
  </g>
</svg>
'''

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(svg, encoding="utf-8")
print(f"wrote {OUT.relative_to(ROOT)}  {OUT.stat().st_size:,} bytes  "
      f"{W}x{H}  {len(ORDER)} glyphs x2  loop {copy_w}px / {SPEED:g}s")

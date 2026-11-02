"""Render assets/profile.svg: a monochrome terminal window with a typing prompt.

Self-contained by design — no external refs, no JS, no fonts to download.
GitHub renders a repo SVG inside <img>, where JavaScript never runs, so every
animation here is SMIL (plus one <style> block for static typography).

Live numbers come from scripts/stats.json, which the scheduled Action rewrites.
A committed SVG is never truly live: camo caches it until the file changes.
"""
import json
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
ART = [l for l in (ROOT / "art_small.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
STATS = json.loads((ROOT / "scripts/stats.json").read_text(encoding="utf-8"))
OUT = ROOT / "assets" / "profile.svg"

# grayscale only
BG, EDGE, BAR = "#0d0d0d", "#262626", "#151515"
TEXT, DIM, FAINT = "#f0f0f0", "#9a9a9a", "#4f4f4f"

W, H = 760, 510
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

# --- braille portrait -------------------------------------------------------
FACE_FS, FACE_PITCH, FACE_LH = 9, 5.2, 10
FACE_X, FACE_Y = 26, 62
FACE_ROWS = len(ART)
FACE_W = 36 * FACE_PITCH

# --- info column ------------------------------------------------------------
INFO_FS, INFO_PITCH, INFO_LH = 11, 6.6, 16
INFO_X, INFO_Y = 250, 68
INFO = [
    ("angelica@github", TEXT),
    ("---------------", FAINT),
    ("OS:       Linux Mint · full-stack dev", DIM),
    ("Host:     Aiken, SC ⇄ Kuwait", DIM),
    ("Kernel:   ICSA Kuwait · program 3 of 4", DIM),
    ("Uptime:   building since middle school", DIM),
    ("Packages: HTML CSS JS PHP MySQL Laravel", DIM),
    ("Shell:    bash · zsh · powershell", DIM),
    ("DE:       Figma · Adobe CC", DIM),
    ("CPU:      human (1) @ 1.0 caffeine", DIM),
    ("Memory:   NANA · Code Geass · Junji Ito", DIM),
    ("Locale:   en_US · nu-metal + post-punk", DIM),
    ("Status:   open to internships + freelance", TEXT),
    ("Contact:  aj-dornton@proton.me", TEXT),
]
INFO_W = max(len(t) for t, _ in INFO) * INFO_PITCH

# --- palette: neofetch's colour strip, answered in grayscale ------------------
PAL = ["#f0f0f0", "#c4c4c4", "#9a9a9a", "#7a7a7a", "#595959", "#3d3d3d", "#262626", "#0d0d0d"]
PAL_X, PAL_Y, PAL_W, PAL_H, PAL_GAP = 600, 82, 108, 12, 10

# --- contribution heatmap ---------------------------------------------------
HEAT_X, HEAT_Y = 26, 356
CELL, COL_PITCH, ROW_PITCH = 10, 13.4, 11.6
LEVELS = ["#1c1c1c", "#333333", "#525252", "#7d7d7d", "#b4b4b4", "#f0f0f0"]
GRID = STATS.get("contributions") or []
TOP = max((c for week in GRID for c in week), default=0)


def level(count):
    """grayscale ramp, scaled to the busiest day of the year"""
    if count <= 0 or TOP <= 0:
        return LEVELS[0]
    for i, cut in enumerate((0.25, 0.5, 0.75)):
        if count < TOP * cut:
            return LEVELS[i + 1]
    return LEVELS[4]

# --- typing prompt ----------------------------------------------------------
PROMPT = "angelica@github:~$ "
PROMPT_W = len(PROMPT) * INFO_PITCH
TYPE_X = 26 + PROMPT_W
TYPE_Y = 486
TYPE_FS, TYPE_PITCH = 11.5, 6.9
LOOP = 15.0
TYPED = [
    "whoami  # full-stack dev · php · mysql · laravel",
    "ls ~/work  # portfolio · spotify-redesign",
    "cat contact.txt  # aj-dornton@proton.me",
]
# each line owns a third of the loop: type for 15%, hold, then vanish
STARTS = [0.0, 1 / 3, 2 / 3]
TYPE_SPAN, HOLD_SPAN, CLEAR_SPAN = 0.15, 0.105, 0.012


def typewriter(text, start, pitch, same_time=True):
    """discrete keyframes: one step per character, then hold, then reset"""
    n = len(text)
    kt, kv = [0.0], ["0"]
    for k in range(1, n + 1):
        kt.append(round(start + (k / n) * TYPE_SPAN, 5))
        kv.append(f"{k * pitch:.2f}")
    kt.append(round(start + TYPE_SPAN + HOLD_SPAN, 5))
    kv.append(f"{n * pitch:.2f}")
    kt.append(round(start + TYPE_SPAN + HOLD_SPAN + CLEAR_SPAN, 5))
    kv.append("0")
    kt.append(1.0)
    kv.append("0")
    return ";".join(f"{t:g}" for t in kt), ";".join(kv)


def visibility(start):
    """group opacity: hidden, visible for its slot, then gone"""
    on = round(start, 5)
    off = round(min(0.999, start + TYPE_SPAN + HOLD_SPAN + CLEAR_SPAN), 5)
    return f"0;{on:g};{off:g};1", "0;1;0;0"


def animate(attr, kt, kv, calc="discrete"):
    return (f'<animate attributeName="{attr}" values="{kv}" keyTimes="{kt}" '
            f'dur="{LOOP:g}s" repeatCount="indefinite" calcMode="{calc}"/>')


# --- build ------------------------------------------------------------------
face = []
for i, line in enumerate(ART):
    y = FACE_Y + i * FACE_LH
    face.append(
        f'    <text x="{FACE_X}" y="{y}" textLength="{len(line) * FACE_PITCH:.2f}" '
        f'lengthAdjust="spacingAndGlyphs" xml:space="preserve">{escape(line)}</text>')

info = []
for i, (t, colour) in enumerate(INFO):
    info.append(
        f'    <text x="{INFO_X}" y="{INFO_Y + i * INFO_LH}" fill="{colour}" '
        f'textLength="{len(t) * INFO_PITCH:.2f}" lengthAdjust="spacingAndGlyphs" '
        f'xml:space="preserve">{escape(t)}</text>')

typed = []
for i, line in enumerate(TYPED):
    start = STARTS[i]
    kt, kv = typewriter(line, start, TYPE_PITCH)
    vis_kt, vis_val = visibility(start)
    width = len(line) * TYPE_PITCH
    typed.append(f'''  <g opacity="0">
{animate("opacity", vis_kt, vis_val).replace("<animate", "<animate", 1)}
  <text x="26" y="{TYPE_Y}" fill="{DIM}" textLength="{PROMPT_W:.2f}" lengthAdjust="spacingAndGlyphs" xml:space="preserve">{escape(PROMPT)}</text>
  <g clip-path="url(#t{i})">
    <text x="{TYPE_X:.2f}" y="{TYPE_Y}" fill="{TEXT}" textLength="{width:.2f}" lengthAdjust="spacingAndGlyphs" xml:space="preserve">{escape(line)}</text>
    <rect x="{TYPE_X:.2f}" y="{TYPE_Y - 11}" width="7" height="14" fill="{TEXT}" opacity="0.9">
      <animate attributeName="opacity" values="0.9;0.9;0;0" keyTimes="0;0.5;0.5;1" dur="1s" repeatCount="indefinite" calcMode="discrete"/>
    </rect>
    <animateTransform attributeName="transform" type="translate" values="{kv}" keyTimes="{kt}" dur="{LOOP:g}s" repeatCount="indefinite" calcMode="discrete"/>
  </g>
</g>''')

clips = []
for i, line in enumerate(TYPED):
    kt, kv = typewriter(line, STARTS[i], TYPE_PITCH)
    clips.append(f'''    <clipPath id="t{i}">
      <rect x="{TYPE_X:.2f}" y="{TYPE_Y - 14}" width="0" height="20">
        {animate("width", kt, kv)}
      </rect>
    </clipPath>''')

stats = STATS
pairs = [
    ("repos", stats.get("repos", 0)),
    ("stars", stats.get("stars", 0)),
    ("followers", stats.get("followers", 0)),
    ("following", stats.get("following", 0)),
    ("last push", stats.get("last_push", "—")),
]
stat_runs, cx = [], 26.0
for label, value in pairs:
    stat_runs.append(f'<text x="{cx:.1f}" y="316" fill="{FAINT}" xml:space="preserve">{escape(label)}</text>')
    cx += len(label) * 6.0 + 6
    stat_runs.append(f'<text x="{cx:.1f}" y="316" fill="{TEXT}" xml:space="preserve">{escape(str(value))}</text>')
    cx += len(str(value)) * 6.0 + 22

palette = [
    f'    <rect x="{PAL_X}" y="{PAL_Y + i * (PAL_H + PAL_GAP)}" '
    f'width="{PAL_W}" height="{PAL_H}" fill="{c}"/>'
    for i, c in enumerate(PAL)]

cells = [
    f'    <rect x="{HEAT_X + col * COL_PITCH:.1f}" y="{HEAT_Y + row * ROW_PITCH:.1f}" '
    f'width="{CELL}" height="{CELL}" rx="2" fill="{level(count)}"/>'
    for col, week in enumerate(GRID)
    for row, count in enumerate(week[:7])]
HEAT_W = (len(GRID) - 1) * COL_PITCH + CELL if GRID else 0

summary = f'{stats.get("contrib_total", 0):,} contributions · {stats.get("streak", 0)} day streak'
langs = " · ".join(f"{n.lower()} {c}" for n, c in (stats.get("langs") or [])[:4]) or "waiting for first refresh"
recent = " · ".join(stats.get("recent") or []) or "—"

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
  <title id="t">angelica@github</title>
  <desc id="d">Monochrome terminal window: a braille dot portrait, a neofetch style
  system readout, live GitHub counts, a year of contribution activity and a typing
  prompt.</desc>
  <style>
    text {{ font-family: {MONO}; font-size: {INFO_FS}px; white-space: pre; }}
    .chrome {{ font-size: 10px; letter-spacing: 0.08em; }}
  </style>
  <defs>
{chr(10).join(clips)}
  </defs>

  <rect width="{W}" height="{H}" rx="10" fill="{BG}"/>
  <path d="M0 34 H{W}" stroke="{EDGE}" stroke-width="1"/>
  <rect width="{W}" height="34" rx="10" fill="{BAR}"/>
  <rect y="24" width="{W}" height="10" fill="{BAR}"/>
  <g fill="none" stroke="{FAINT}" stroke-width="1">
    <circle cx="20" cy="17" r="4.5"/> <circle cx="38" cy="17" r="4.5"/> <circle cx="56" cy="17" r="4.5"/>
  </g>
  <text class="chrome" x="{W - 20}" y="21" fill="{FAINT}" text-anchor="end">zsh · 80×24</text>
  <text class="chrome" x="80" y="21" fill="{DIM}">angelica@github</text>

  <g fill="{TEXT}" font-size="{FACE_FS}" opacity="0.92">
{chr(10).join(face)}
  </g>

  <g font-size="{INFO_FS}">
{chr(10).join(info)}
  </g>

  <text x="{PAL_X}" y="68" fill="{FAINT}" font-size="9" letter-spacing="0.14em">palette</text>
  <g stroke="{EDGE}" stroke-width="0.5">
{chr(10).join(palette)}
  </g>

  <path d="M26 292 H{W - 26}" stroke="{EDGE}" stroke-width="1"/>
  <g font-size="10" letter-spacing="0.02em">
    {chr(10).join(stat_runs)}
  </g>
  <text x="{W - 26}" y="316" fill="{FAINT}" font-size="10" text-anchor="end" xml:space="preserve">updated {escape(str(stats.get("updated", "—")))}</text>

  <text x="{HEAT_X}" y="342" fill="{FAINT}" font-size="9" letter-spacing="0.14em">contributions · last 12 months</text>
  <text x="{HEAT_X + HEAT_W:.1f}" y="342" fill="{DIM}" font-size="9.5" text-anchor="end">{escape(summary)}</text>
  <g>
{chr(10).join(cells)}
  </g>

  <g font-size="9.5" letter-spacing="0.02em">
    <text x="26" y="452" fill="{DIM}" xml:space="preserve">langs   {escape(langs)}</text>
    <text x="{W - 26}" y="452" fill="{DIM}" text-anchor="end" xml:space="preserve">recent  {escape(recent)}</text>
  </g>
  <path d="M26 466 H{W - 26}" stroke="{EDGE}" stroke-width="1"/>

  <g font-size="{TYPE_FS}">
{chr(10).join(typed)}
  </g>
</svg>
'''

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(svg, encoding="utf-8")
print(f"wrote {OUT.relative_to(ROOT)}  {OUT.stat().st_size:,} bytes  "
      f"{W}x{H}  face {FACE_W:.0f}px  info {INFO_W:.0f}px")

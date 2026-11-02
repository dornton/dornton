# putting this on your profile

## the minimum: 2 files

- `README.md`
- `assets/profile.svg`

That's enough to make https://github.com/eliutot look right. The folder path
`assets/profile.svg` has to match exactly — the README's `<img src>` points at it.

## optional: the live numbers

The other files keep the SVG's stats row current:

- `.github/workflows/profile.yml`  — runs daily, commits the regenerated SVG
- `scripts/fetch_stats.py`         — asks the GitHub API for your real numbers
- `scripts/make_svg.py`            — rebuilds the SVG from stats + art
- `scripts/stats.json`             — the numbers (starts as placeholders)
- `art.txt`, `build.py`, `panel.txt`, `art_small.txt` — the braille panel source

Without these, the banner still renders — it just keeps showing whatever
numbers were baked in when it was generated.

## uploading

1. repo `eliutot` -> Add file -> Upload files
2. drag the whole folder in (GitHub keeps the subfolders)
3. Commit changes

Then: Actions tab -> "refresh profile stats" -> Run workflow.
First run replaces the placeholders with your real counts.

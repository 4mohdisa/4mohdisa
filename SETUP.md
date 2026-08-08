# Setup

Everything lives in your profile repo: `github.com/4mohdisa/4mohdisa`.

```
4mohdisa/
├── README.md
├── today.py                    # fetches live stats, renders the SVGs
├── prep_photo.py               # cleans a selfie (bg removal, patch out earbuds/phone)
├── make_ascii.py               # prepped photo -> ASCII portrait
├── ascii_art.txt               # the portrait (46 x 34 chars)
├── requirements.txt            # CI needs only this
├── requirements-portrait.txt   # local only, for regenerating the portrait
├── dark_mode.svg               # generated
├── light_mode.svg              # generated
├── cache/loc_cache.json        # generated — keep it committed
└── .github/workflows/main.yml
```

## 1. Token

The default `GITHUB_TOKEN` can't read private contributions or cross-repo commit
history, so make a classic PAT:

1. github.com/settings/tokens → **Generate new token (classic)**
2. Scopes: `repo`, `read:user`
3. Repo → Settings → Secrets and variables → Actions → **New repository secret**
   - Name: `ACCESS_TOKEN`

## 2. Push

```bash
python today.py                          # preview with placeholder numbers
GITHUB_TOKEN=ghp_xxx python today.py     # real numbers
git add -A && git commit -m "profile card" && git push
```

The Action then reruns daily at 15:00 UTC (~00:30 Adelaide) and commits the SVGs
whenever a number changes. `workflow_dispatch` lets you trigger it by hand.

**First run is slow** — it walks every repo's commit history to count lines.
After that `cache/loc_cache.json` keys off each repo's HEAD, so only repos that
moved get recounted. Keep the cache committed.

## 3. Editing your info

Open `today.py`. The `STATIC_ROWS` list near the top *is* the right-hand column —
add, remove or reorder freely. `{UPTIME}` is substituted at render time.

`LOC_EXCLUDE` skips repos when counting lines. `SignFlow` is in there already —
it has 8.3M additions and 8.3M deletions from a vendored folder that was
committed and later removed, which swamped everything else. Add any repo where a
`node_modules`, dataset or `dist/` folder ever got committed.

`UPTIME_FROM = None` counts from your GitHub account creation date.
Set it to `"YYYY-MM-DD"` to count from your birthday instead.

Colours live in `THEMES`. The card auto-sizes to whatever the art and rows need.

## 4. Regenerating the portrait

```bash
pip install -r requirements-portrait.txt

# 1) clean the photo — inpaint removes things, erase blanks them out
python prep_photo.py selfie.png \
  --inpaint 390 1540 505 1720 \      # the AirPod
  --erase   1000 1780 1320 2868 \    # the phone + hand
  --crop    130 950 1218 2560 \      # head + shoulders
  -o prepped.png

# 2) convert
python make_ascii.py prepped.png
```

All coordinates are pixels in the original photo. Open it in any viewer, read
off the corners of whatever you want gone, and pass them as `x1 y1 x2 y2`.
`prep_photo.py` flood-fills the wall behind you to pure white, so a plain
background helps a lot.

`make_ascii.py` builds the portrait from four layers rather than raw brightness —
silhouette, feature edges, skin, and dark mass (hair/clothing). Dials:

| Result | Try |
|---|---|
| Face too dark / closed up | `--skin-hi 0.32` |
| Hair not solid enough | `--dark 0.9` |
| Features not drawn | `--canny-lo 10 --canny-hi 40` |
| Too noisy | `--clahe 1.5 --canny-lo 30` |
| Shoulders end too abruptly | `--fade 8` |
| Bigger portrait | `--cols 52 --rows 39` (card resizes itself) |

---

Layout concept inspired by [Andrew6rant/Andrew6rant](https://github.com/Andrew6rant/Andrew6rant).

# FOMO World

A 3D little world of FOMO agents that hunt trending tokens, metas, and derivative / beta coin ideas. Research and concept generation only. The site does not create tokens, connect wallets, or sign transactions.

Live site (after Pages is pointed at `gh-pages`): <https://joeypbrrr.github.io/fomo-world/>

The product spec, including the owner's wording and the correction from 30 seconds to **30 minutes**, is in [SPEC.md](SPEC.md).

## Run a scan

Python 3.11+ and the stdlib. No packages.

```bash
python3 -m unittest discover -s tests -t .
python3 runner.py --once                 # write data/ideas.json
python3 runner.py --once --publish       # also push gh-pages
python3 runner.py --loop --publish       # every 30 minutes
```

Cron equivalent: `*/30 * * * * cd /path/to/fomo-world && python3 runner.py --once --publish`.

`publish_data.py` follows the Trenchfloor publisher: it copies the static site plus `data/ideas.json` onto `gh-pages`, commits as `joeypbrrr`, and rebases if the remote moved. It does not take a token on the command line. `python3 publish_data.py --dry-run` lists files and does not push.

The pages show **last scanned** in Eastern time and a countdown to the next 30-minute mark from that file. They re-read the JSON about once a minute.

## Coin images

The scan appends new concept ids to `data/image_queue.json` with a prompt for a 1000×1000 glossy mascot. Drop finished PNGs named `<concept_id>.png` in `/workspace/fomo-world/generated` (or `generated/` in this repo) and run:

```bash
python3 import_images.py --publish
```

Wrong sizes are rejected. Until a PNG exists, the site draws a labeled procedural placeholder.

## Pages

If this token cannot enable GitHub Pages, do this once:

**Settings → Pages → Build and deployment → Deploy from a branch → `gh-pages` / root → Save.**

## Sources

Keyless and documented only: DexScreener (profiles, boosts, token pairs, search), GeckoTerminal trending pools, Google News RSS, Google Trends daily RSS, and the Wikipedia most-read feed. Reddit public `search.json` is attempted; a 403 is recorded and not worked around. X trends and pump.fun are skipped (auth, or no documented keyless API).

If a theme has no matching description or headline, the card says **trend unclear** and ranks lower. Numbers that the APIs omit stay `n/a`.

## Layout

- `index.html` — rotatable 3D world, agent feed, idea board
- `top10.html` — Top 10 Launchable, Launch button on each card
- `launch.html` — prefilled kit, copy buttons, 1000×1000 download, link to <https://pump.fun/create>

# FOMO World spec

FOMO World is a research desk. FOMO agents watch trending tokens, decide whether a cluster is a meta or a launchpad opportunity, and draft a beta coin or derivative concept. The site never creates, deploys, or launches a token, never connects a wallet, and never signs or sends a transaction.

## Owner, in their words

> a 3D little world with a whole bunch of agents (FOMO agents) that search up trends: they go on FOMO, look for trending tokens, and look for derivatives. They try to see what's trending and how to create a token revolving around those trending tokens. It might be a launchpad, or it might be a meta; if it's a meta, make a beta coin, like a derivative. Example: if Elon Musk is trending, make a Tesla-like derivative coin.

> every 30 seconds it's scanning for trending tokens

> every 30 seconds there's a page of the top 10 tokens that I can launch

> there should be a launch button

> it says the name, the token name

> it will have the token, like make it as easy as possible to launch. Like it has the image, the token name, the ticker, et cetera, et cetera, to make this as fast as possible.

> while you're doing research on these coins, and like names and like images, make sure you know what the, like what trends are

> when you make me a derivative, make sure the images come out really nice.

Use these names in the product: FOMO agents, trending tokens, derivatives, launchpad, meta, beta coin.

## Cadence correction

The owner first said the scan and the Top 10 page refresh every 30 seconds, then corrected that to **30 minutes** ("30 minute").

GitHub Pages is static, so the 30-minute scan runs on the owner's box:

```bash
python3 runner.py --loop --publish
```

or cron `*/30 * * * *`. `publish_data.py` pushes `data/ideas.json`, `data/image_queue.json`, and the static site to the `gh-pages` branch, the same publish shape as [Trenchfloor](https://github.com/joeypbrrr/trenchfloor): existing git credentials, no token on the command line, rebase-and-retry if the remote moved.

The page re-reads `data/ideas.json` about once a minute. It shows **last scanned** in US Eastern time and a countdown to `generated_at + 30 minutes`. If that time has passed, the countdown says the publish is overdue. It does not pretend a new scan happened.

Optional buttons:

- **Re-read published data** fetches the JSON again.
- **Scan public APIs now** runs in the browser against DexScreener and GeckoTerminal (both send `Access-Control-Allow-Origin: *`). That pass is labeled as a manual browser scan. It is not published, and it does not reset the 30-minute countdown. News, Google Trends, Wikipedia, and Reddit stay on the Python publisher. The button waits 20 seconds before it can run again.

## What a concept is

Each scan writes at most 10 concepts to `data/ideas.json`.

- **META** — two or more trending tokens share a word in their names. The concept is a **beta coin** / **derivative**. If the shared word is Elon, Musk, or Tesla, the copy says it is a Tesla-style derivative and the concept is not named Elon, Tesla, or Musk.
- **LAUNCHPAD** — a trending token that does not share a theme word. The concept is an original idea revolving around that token, not a copy of its name.

Rank uses 24h volume, positive 24h price change, how many tokens share the meta, and freshness (rising / peaking / fading from pool age and price change). Missing numbers stay `n/a`. They are not filled in.

## Trend context

Every concept carries a **Why this is trending** block:

- why it is trending
- the meme or story
- who is driving it (a linked X account, Telegram, a subreddit, or a publication — only when that URL or name was actually returned)
- freshness: when the earliest sourced pool or headline time started, and whether the move looks rising, peaking, fading, or unclear

Sources, public and keyless:

| Source | Endpoint | Use |
| --- | --- | --- |
| DexScreener profiles | `GET /token-profiles/latest/v1` | Description and links |
| DexScreener boosts | `GET /token-boosts/latest/v1` and `/top/v1` | What is being promoted |
| DexScreener pairs | `GET /latest/dex/tokens/{addresses}` | Volume, market cap, price change, pair age, link |
| DexScreener search | `GET /latest/dex/search?q=` | Extra pairs whose name contains a meta word |
| GeckoTerminal | `GET /api/v2/networks/trending_pools` | Trending pools |
| Google News | RSS search | Headlines that contain the theme word |
| Google Trends | `https://trends.google.com/trending/rss?geo=US` | Daily trends, matched by whole word |
| Wikipedia | featured-feed most-read | Article titles matched by whole word |
| Reddit | `https://www.reddit.com/search.json` | Posts whose title contains the theme word |

A headline is kept only when it contains a distinctive anchor: the meta word when that word is not a common name or noun, a ticker with a digit such as GTA6, or a rare word from the token's own profile. A headline that merely contains "Alice" or "diamond" is not treated as the story. A Google Trends picture is never used as a coin image. At most two headlines are cited.

If none of those texts match, `why` and `meme_or_story` are exactly **trend unclear**, the concept is down-ranked (`score * 0.45`), and the image prompt says not to invent a scene. The pipeline does not write a story to fill the gap.

Skipped on purpose:

- X trends: the official API needs a bearer token.
- pump.fun: no documented keyless API. The front page is not scraped.
- Reddit, when `search.json` returns 403 or another block. The failure is recorded. It is not retried with a spoofed browser.

## Images

Coin logos should look like finished marks, not diagrams.

1. Each new Top 10 concept appends one row to `data/image_queue.json`: concept id, a detailed original prompt (glossy mascot, centered, clean background, ticker badge, riffing only on sourced text, no real logos, no likeness, no brand marks), 1000×1000 PNG, status `pending`. Ids already in the queue are not added again. A `pending` prompt can refresh. A `done` prompt stays.
2. The site shows `images/<concept_id>.png` when that file exists. Otherwise it draws a procedural coin (gradient, rim light, mascot, ticker badge) and labels it as a placeholder.
3. `import_images.py` reads PNGs from `/workspace/fomo-world/generated` when that folder exists, else `generated/` in the repo. The file name is `<concept_id>.png`. The PNG header must be 1000×1000. Valid files are copied to `images/` and the queue row is marked `done`. `--publish` then runs `publish_data.py`.

```bash
python3 import_images.py --from /workspace/fomo-world/generated --publish
```

FOMO World does not call an image API itself.

## Launch kit

Each card has a **Launch** button. The kit prefills token name, ticker, description, and suggested socials text, with a copy button on each. The image downloads as a 1000×1000 PNG. **Open pump.fun create** links to `https://pump.fun/create` in a new tab. Small print on the kit says the site does not launch anything and does not touch a wallet.

## The little world

Eighteen FOMO agents walk between four stations: trend board, token radar, idea lab, launchpad desk.

| Role | Agents |
| --- | --- |
| Trend Scout | Nib, Pico, Kip |
| Token Tracker | Mara, Jun, Ada |
| Meta Spotter | Solene, Bex, Fizz |
| Derivative Designer | Otis, Luma, Vee |
| Launchpad Analyst | Hank, Rae, Dot |
| Skeptic | Quill, Moss, Rue |

Speech bubbles and the agent feed quote the published scan: rank, freshness, volume, market cap, and either the sourced why-line or "trend unclear". Empty scans say the board was left empty on purpose.

The camera orbits. Touch and mouse both rotate it. `prefers-reduced-motion` stops the walking.

## Safety

- Concepts are labeled concepts.
- Every idea has a trademark and impersonation risk note.
- Generated names do not use a blocked person or brand (Tesla, Elon, Musk, and the rest of the list in `research/textutil.py`) and do not copy a source token's full name.
- No wallets, keys, transactions, or token deployment anywhere in this repo.
- No fabricated volume, market cap, or headline. Empty and "trend unclear" are the honest states.

## Pages setting

The publisher writes the `gh-pages` branch. One setting, if the token cannot enable it:

GitHub → **Settings → Pages → Build and deployment → Deploy from a branch → Branch: `gh-pages` / root → Save.**

The site is then `https://joeypbrrr.github.io/fomo-world/`.

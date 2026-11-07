"""Build trend context from fetched text only.

If nothing quotable matches the theme, the story fields are the exact phrase
"trend unclear". Market freshness can still be computed from timestamps and
24h price change, because those are measurements, not a story.
"""

from __future__ import annotations

from datetime import datetime, timezone

from research.textutil import COMMON_WORDS, hours_between, parse_time, theme_words, whole_word

UNCLEAR = "trend unclear"
DRIVER_UNCLEAR = "driver unclear"


def story_anchors(classification: str, theme_key: str, tokens: list[dict]) -> list[str]:
    """Terms specific enough that a headline containing one is about this trend.

    Common words and bare personal names are not anchors. A symbol with a
    digit (GTA6) or a rare word from the token name or its own profile is.
    """
    found: list[str] = []

    def add(word: str) -> None:
        cleaned = "".join(ch for ch in (word or "").lower() if ch.isalnum())
        if len(cleaned) < 4 or cleaned in COMMON_WORDS or cleaned in found:
            return
        found.append(cleaned)

    if classification == "META":
        add(theme_key)
    for token in tokens:
        symbol = "".join(ch for ch in (token.get("symbol") or "").lower() if ch.isalnum())
        if any(ch.isdigit() for ch in symbol) or (len(symbol) >= 5 and symbol not in COMMON_WORDS):
            add(symbol)
        for word in theme_words(token.get("name"), token.get("description")):
            if len(word) >= 5:
                add(word)
    return found[:12]


def _text_has_anchor(anchors: list[str], *parts: str) -> bool:
    blob = " ".join(part or "" for part in parts)
    return any(whole_word(anchor, blob) for anchor in anchors)


def match_words_for_group(classification: str, theme_key: str, tokens: list[dict]) -> list[str]:
    if classification == "META":
        return [theme_key] if theme_key else []
    words = []
    for token in tokens:
        for part in (token.get("symbol") or "", token.get("name") or ""):
            for raw in part.replace("/", " ").split():
                word = "".join(ch for ch in raw.lower() if ch.isalnum())
                if len(word) >= 4 and word not in words:
                    words.append(word)
    return words[:6]


def _matches(words: list[str], *parts: str) -> bool:
    blob = " ".join(part or "" for part in parts)
    return any(whole_word(word, blob) for word in words)


def _link_driver(tokens: list[dict]) -> list[str]:
    handles = []
    telegrams = []
    sites = []
    for token in tokens:
        for link in token.get("links") or []:
            url = link.get("url") or ""
            kind = (link.get("type") or "link").lower()
            handle = ""
            for host in ("x.com/", "twitter.com/"):
                if host in url:
                    tail = url.split(host, 1)[1].split("?", 1)[0].strip("/")
                    piece = tail.split("/")[0]
                    if piece and piece.lower() not in {"i", "intent", "share", "home"}:
                        handle = "@" + piece
            if handle and handle not in handles:
                handles.append(handle)
            elif "t.me/" in url or "telegram" in kind:
                if url not in telegrams:
                    telegrams.append(url)
            elif url.startswith("http") and url not in sites:
                sites.append(url)
    notes = []
    if handles:
        shown = ", ".join(handles[:4])
        extra = f" (+{len(handles) - 4} more)" if len(handles) > 4 else ""
        notes.append(f"X accounts linked on the DexScreener profiles: {shown}{extra}.")
    if telegrams:
        notes.append(f"Telegram links on the profiles: {len(telegrams)}.")
    if sites:
        notes.append("Websites linked on the profiles: " + ", ".join(sites[:2]) + ".")
    return notes


def freshness(tokens: list[dict], now: datetime) -> dict:
    ages = []
    changes = []
    started = None
    started_url = None
    for token in tokens:
        created = token.get("pair_created_at")
        age = hours_between(created, now)
        if age is not None:
            ages.append(age)
            if started is None or created < started:
                started = created
                started_url = token.get("dexscreener_url") or None
        if token.get("price_change_h24") is not None:
            changes.append(token["price_change_h24"])
    change = max(changes) if changes else None
    age = min(ages) if ages else None
    if change is None and age is None:
        phase, basis = "unclear", "No pool age or 24h price change was returned."
    elif change is not None and change <= -15:
        phase, basis = "fading", f"24h price change {change:.1f}%."
    elif change is not None and change >= 25:
        phase, basis = "rising", f"24h price change {change:.1f}%."
    elif age is not None and age <= 12 and (change is None or change >= 0):
        phase, basis = "rising", f"Newest pool is {age:.1f} hours old."
    elif change is not None:
        phase, basis = "peaking", f"24h price change {change:.1f}%."
    elif age is not None and age <= 48:
        phase, basis = "rising", f"Newest pool is {age:.1f} hours old."
    elif age is not None:
        phase, basis = "peaking", f"Newest pool is {age:.1f} hours old."
    else:
        phase, basis = "unclear", "No pool age or 24h price change was returned."
    return {
        "started_at": started,
        "started_at_source": started_url,
        "phase": phase,
        "basis": basis,
    }


def build_trend_context(
    classification: str,
    theme_key: str,
    tokens: list[dict],
    *,
    news: list[dict] | None = None,
    trends: list[dict] | None = None,
    wiki: list[dict] | None = None,
    reddit: list[dict] | None = None,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now(timezone.utc)
    anchors = story_anchors(classification, theme_key, tokens)
    sources: list[dict] = []
    quotes: list[str] = []
    drivers: list[str] = []
    profile_quotes = 0

    for token in tokens:
        description = (token.get("description") or "").strip()
        if description and profile_quotes < 2:
            snippet = description[:320]
            sources.append({
                "kind": "dexscreener_profile",
                "title": f"{token.get('name') or token.get('symbol') or 'token'} profile",
                "url": token.get("dexscreener_url") or "",
                "snippet": snippet,
            })
            quotes.append(f'DexScreener profile: "{snippet}"')
            profile_quotes += 1
    drivers.extend(_link_driver(tokens))

    news_kept = 0
    for item in news or []:
        if news_kept >= 2:
            break
        title = item.get("title") or ""
        if not _text_has_anchor(anchors, title, item.get("description") or ""):
            continue
        url = item.get("url") or item.get("source_url") or ""
        publication = item.get("source_name") or "Google News"
        sources.append({
            "kind": "google_news",
            "title": title,
            "url": url,
            "snippet": title,
        })
        quotes.append(f'Google News: "{title}" ({publication}).')
        if publication:
            drivers.append(f"Coverage: {publication}")
        news_kept += 1

    for item in trends or []:
        title = item.get("title") or ""
        if not _text_has_anchor(anchors, title):
            continue
        headline = ""
        headline_url = item.get("url") or "https://trends.google.com/trending/rss?geo=US"
        for news_item in item.get("news") or []:
            if news_item.get("title"):
                headline = news_item["title"]
                headline_url = news_item.get("url") or headline_url
                break
        snippet = headline or title
        sources.append({
            "kind": "google_trends",
            "title": title,
            "url": headline_url,
            "snippet": snippet,
        })
        if headline:
            quotes.append(f'Google Trends daily list includes "{title}". Headline: "{headline}".')
        else:
            quotes.append(f'Google Trends daily list includes "{title}".')
        break

    for article in wiki or []:
        title = article.get("title") or ""
        if not _text_has_anchor(anchors, title):
            continue
        sources.append({
            "kind": "wikipedia",
            "title": title,
            "url": article.get("url") or "",
            "snippet": title,
        })
        quotes.append(f'Wikipedia most-read includes "{title}".')
        break

    for post in reddit or []:
        title = post.get("title") or ""
        if not _text_has_anchor(anchors, title, post.get("snippet") or ""):
            continue
        sources.append({
            "kind": "reddit",
            "title": title,
            "url": post.get("url") or "",
            "snippet": title,
        })
        sub = post.get("subreddit") or "a subreddit"
        quotes.append(f'Reddit {sub}: "{title}".')
        drivers.append(f"Reddit community in search results: {sub}")
        break
    fresh = freshness(tokens, now)
    # A profile link is not a story. Quotes are.
    sourced = bool(quotes)
    if classification == "META" and theme_key:
        trend_name = f"{theme_key} meta"
    elif tokens:
        label = tokens[0].get("name") or tokens[0].get("symbol") or "token"
        trend_name = f"{label} launchpad"
    else:
        trend_name = UNCLEAR
    if not sourced:
        why = UNCLEAR
        meme = UNCLEAR
    else:
        why = " ".join(quotes[:3])
        meme = why
    if drivers:
        # Keep driver notes even when the story is unclear: they are URLs we fetched.
        driver = " ".join(dict.fromkeys(drivers))
    else:
        driver = DRIVER_UNCLEAR
    return {
        "status": "sourced" if sourced else UNCLEAR,
        "trend_name": trend_name,
        "why": why,
        "meme_or_story": meme,
        "driver": driver,
        "freshness": fresh,
        "sources": sources,
        "match_words": anchors,
    }


def parse_iso(value: str | None) -> datetime | None:
    parsed = parse_time(value) if value and not str(value).endswith("+00:00") and "T" not in str(value) else value
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp

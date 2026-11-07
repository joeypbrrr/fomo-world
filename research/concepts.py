"""Cluster trending tokens and write beta-coin / launchpad concepts.

Names riff on words that actually appear in the token name or in sourced
text. Person and brand names are not used as the concept name. Every idea
carries a trademark / impersonation risk note.
"""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timedelta, timezone
from random import Random

from research.config import CONTEXT_SCORE_FACTOR, PUBLIC_URL, SCAN_INTERVAL_SECONDS
from research.context import UNCLEAR, build_trend_context
from research.roster import ANALYSTS, DESIGNERS, SCOUTS, SKEPTICS, SPOTTERS, TRACKERS
from research.textutil import (
    ADJECTIVES,
    BRAND_TICKERS,
    BRANDS,
    CONCRETE,
    NOUNS,
    STYLE_HINTS,
    theme_words,
    usd,
)

UNCLEAR_PHRASE = "trend unclear"


def cluster_tokens(tokens: list[dict]) -> list[dict]:
    buckets: dict[str, list[dict]] = {}
    for token in tokens:
        for word in theme_words(token.get("name"), token.get("symbol")):
            buckets.setdefault(word, []).append(token)
    groups: dict[str, list[dict]] = {}
    singles: list[dict] = []
    for token in tokens:
        options = [word for word in theme_words(token.get("name"), token.get("symbol")) if len(buckets.get(word, [])) >= 2]
        if not options:
            singles.append(token)
            continue
        best = max(options, key=lambda word: (len(buckets[word]), word))
        groups.setdefault(best, [])
        key = (token.get("chain"), token.get("address"))
        if key not in {(item.get("chain"), item.get("address")) for item in groups[best]}:
            groups[best].append(token)
    clustered = []
    for word, members in groups.items():
        clustered.append({
            "classification": "META",
            "theme_key": word,
            "tokens": members,
        })
    for token in singles:
        clustered.append({
            "classification": "LAUNCHPAD",
            "theme_key": f"token:{token.get('chain')}:{token.get('address')}",
            "tokens": [token],
        })
    return clustered


def _sum_volume(tokens: list[dict]) -> float | None:
    values = [token["volume_usd"] for token in tokens if token.get("volume_usd") is not None]
    if not values:
        return None
    return float(sum(values))


def _max_change(tokens: list[dict]) -> float | None:
    values = [token["price_change_h24"] for token in tokens if token.get("price_change_h24") is not None]
    if not values:
        return None
    return float(max(values))


def score_group(tokens: list[dict], now: datetime, status: str) -> dict:
    volume = _sum_volume(tokens)
    change = _max_change(tokens)
    breadth = len(tokens)
    fresh = build_trend_context("META", "", tokens, now=now)["freshness"]
    age_basis = fresh["basis"]
    volume_pts = 0.0 if volume is None else min(40.0, math.log10(volume + 1) * 8.0)
    momentum_pts = 0.0 if change is None else min(25.0, max(0.0, change) / 4.0)
    breadth_pts = min(25.0, max(0, breadth - 1) * 8.0)
    phase = fresh["phase"]
    if phase == "rising":
        fresh_pts = 15.0
    elif phase == "peaking":
        fresh_pts = 8.0
    else:
        fresh_pts = 0.0
    raw = min(100.0, volume_pts + momentum_pts + breadth_pts + fresh_pts)
    factor = 1.0 if status == "sourced" else CONTEXT_SCORE_FACTOR
    return {
        "volume": round(volume_pts, 1),
        "momentum": round(momentum_pts, 1),
        "breadth": round(breadth_pts, 1),
        "freshness": round(fresh_pts, 1),
        "raw": round(raw, 1),
        "context_factor": factor,
        "age_basis": age_basis,
        "volume_usd": volume,
        "price_change_h24": change,
        "score": round(raw * factor, 1),
    }


def _style(tokens: list[dict], theme_key: str) -> str | None:
    blob = " ".join(
        [theme_key]
        + [f"{token.get('name') or ''} {token.get('symbol') or ''} {token.get('description') or ''}" for token in tokens]
    ).lower()
    for key, label in STYLE_HINTS.items():
        if key in blob.split() or f" {key} " in f" {blob} ":
            return label
    # Whole-word check against the joined blob.
    padded = f" {blob} "
    for key, label in STYLE_HINTS.items():
        if f" {key} " in padded:
            return label
    return None


def _concept_name(theme_key: str, tokens: list[dict], quotes: list[str], salt: str) -> str:
    rng = Random(salt)
    full_names = {(token.get("name") or "").lower() for token in tokens}
    candidates: list[str] = []
    theme = "" if theme_key.startswith("token:") else theme_key.lower()
    if theme and theme not in BRANDS and len(theme) >= 4:
        candidates.append(theme)
    def tainted(word: str) -> bool:
        if word in BRANDS:
            return True
        return any(len(brand) >= 3 and word.startswith(brand) for brand in BRANDS)

    if not candidates:
        for token in tokens:
            for word in theme_words(token.get("name")):
                if not tainted(word) and word not in candidates:
                    candidates.append(word)
    blob = " ".join(quotes).lower()
    for word in theme_words(blob, *[token.get("description") or "" for token in tokens]):
        if word in CONCRETE and not tainted(word) and word not in candidates:
            candidates.append(word)

    def acceptable(name: str) -> bool:
        parts = name.lower().split()
        if len(parts) < 2 or name.lower() in full_names:
            return False
        return not any(
            part in BRANDS or any(len(brand) >= 3 and part.startswith(brand) for brand in BRANDS)
            for part in parts
        )

    if candidates:
        head = candidates[0].title()
        tails = [word.title() for word in candidates[1:]] + list(NOUNS)
        name = next((f"{head} {tail}" for tail in tails if acceptable(f"{head} {tail}")), "")
    else:
        name = ""
    if not name:
        for _ in range(8):
            guess = f"{rng.choice(ADJECTIVES)} {rng.choice(NOUNS)}"
            if acceptable(guess):
                return guess
        return "Pebble Lantern"
    return name


def _ticker(name: str, tokens: list[dict], salt: str) -> str:
    avoid = {(token.get("symbol") or "").upper() for token in tokens} | set(BRAND_TICKERS)
    stems = ("ELON", "TESLA", "TSLA", "MUSK", "TRUMP", "NVDA", "AAPL", "DOGE", "PEPE")
    parts = [part for part in name.upper().split() if part.isalpha()]
    base = "".join(part[0] for part in parts)
    rest = "".join(ch for part in parts for ch in part[1:] if ch not in "AEIOU")
    ticker = (base + rest + "X")[:5]
    rng = Random(salt + ":ticker")
    alphabet = "BCDFGHJKLMNPQRSTVWXYZ"

    def blocked(value: str) -> bool:
        return value in avoid or any(stem in value for stem in stems) or len(value) < 4

    spins = 0
    while blocked(ticker) and spins < 12:
        ticker = "".join(rng.choice(alphabet) for _ in range(5))
        spins += 1
    return ticker


def _art(seed: str) -> dict:
    rng = Random(seed)
    return {
        "seed": seed,
        "palette": rng.randrange(6),
        "body": rng.randrange(4),
        "ears": rng.randrange(4),
        "accent": rng.randrange(4),
    }


def _risk_note(style: str | None) -> str:
    extra = ""
    if style == "Tesla-style":
        extra = " Not affiliated with Tesla, Elon Musk, or their companies."
    elif style == "political-figure-style":
        extra = " Not affiliated with any political figure or campaign."
    elif style == "GTA-style":
        extra = " Not affiliated with Rockstar Games or Grand Theft Auto."
    elif style:
        extra = f" The {style} label is a derivative framing, not an official product."
    return (
        "Trademark and impersonation risk: this is an unofficial concept, not issued by "
        "and not affiliated with any real person, company, or the source trending tokens. "
        "Do not use their logos, brand marks, or likeness, and do not present it as official."
        + extra
        + " Research only — nothing here is deployed."
    )


def _description(classification: str, trend_name: str, style: str | None, context: dict, token: dict | None) -> str:
    if classification == "META":
        line = f"Beta coin concept for the {trend_name}."
        if style:
            line += f" {style} derivative, not an official product."
        else:
            line += " A derivative riff, not a copy of the source tickers."
    else:
        label = ""
        if token:
            label = f" {token.get('name') or token.get('symbol') or 'the trending token'} ({token.get('symbol') or 'n/a'})"
        line = f"Launchpad concept revolving around{label}."
    if context["status"] == "sourced":
        quote = context["why"]
        if len(quote) > 140:
            quote = quote[:139].rstrip() + "…"
        line += f" Riffs on sourced context: {quote}"
    else:
        line += " Trend context: trend unclear."
    return line


def _image_prompt(name: str, ticker: str, context: dict) -> str:
    rules = (
        "Premium glossy mascot coin-logo art, square 1:1, centered original character, "
        "clean soft gradient background, studio lighting, thick rounded shapes, enamel "
        f"rim, small readable ticker badge '{ticker}' only. No real logos, no brand marks, "
        "no real person's likeness, no celebrity face, no copied mascot."
    )
    if context["status"] == "sourced":
        snippet = context["why"][:280]
        story = f'Riff only on this sourced trend text, and do not add events that are not in it: "{snippet}"'
    else:
        story = (
            "The trend story is unknown (trend unclear). Do not invent a news event, "
            "celebrity, or brand scene. Design an original creature with no topical costume."
        )
    return f"{rules} Concept name: {name}. {story}"


def _public_token(token: dict) -> dict:
    return {
        "name": token.get("name") or "",
        "symbol": token.get("symbol") or "",
        "chain": token.get("chain") or "",
        "address": token.get("address") or "",
        "dexscreener_url": token.get("dexscreener_url") or "",
        "volume_usd": token.get("volume_usd"),
        "market_cap_usd": token.get("market_cap_usd"),
        "price_change_h24": token.get("price_change_h24"),
        "pair_created_at": token.get("pair_created_at"),
    }


def _socials(name: str, ticker: str, description: str, context: dict) -> str:
    return (
        f"{name} (${ticker}) — unofficial concept from FOMO World.\n\n"
        f"{description}\n\n"
        f"Why it's trending: {context['why']}\n"
        f"Driver: {context['driver']}\n\n"
        "Research concept only. Not a launched token. Not affiliated with any trending "
        "token, person, or brand. Not financial advice."
    )


def build_ideas(groups: list[dict], evidence: dict | None = None, now: datetime | None = None, limit: int = 10) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    evidence = evidence or {}
    ideas = []
    for group in groups:
        context = build_trend_context(
            group["classification"],
            group["theme_key"] if group["classification"] == "META" else "",
            group["tokens"],
            news=evidence.get(group["theme_key"], {}).get("news"),
            trends=evidence.get("trends"),
            wiki=evidence.get("wiki"),
            reddit=evidence.get(group["theme_key"], {}).get("reddit"),
            now=now,
        )
        parts = score_group(group["tokens"], now, context["status"])
        concept_id = "c_" + hashlib.sha256(f"{group['classification']}|{group['theme_key']}".encode()).hexdigest()[:12]
        quotes = [source["snippet"] for source in context["sources"] if source["kind"] != "dexscreener_link"]
        name = _concept_name(group["theme_key"], group["tokens"], quotes, concept_id)
        ticker = _ticker(name, group["tokens"], concept_id)
        style = _style(group["tokens"], group["theme_key"] if group["classification"] == "META" else "")
        description = _description(group["classification"], context["trend_name"], style, context, group["tokens"][0])
        cluster_note = ""
        if group["classification"] == "META":
            cluster_note = f"{len(group['tokens'])} trending tokens share the word '{group['theme_key']}'."
        else:
            token = group["tokens"][0]
            cluster_note = f"Single trending token {token.get('symbol') or token.get('name') or 'unknown'} — treated as a launchpad opportunity."
        ideas.append({
            "id": concept_id,
            "classification": group["classification"],
            "concept_kind": "beta coin" if group["classification"] == "META" else "launchpad",
            "trend_name": context["trend_name"],
            "name": name,
            "token_name": name,
            "ticker": ticker,
            "description": description,
            "reasoning": description + " " + cluster_note,
            "cluster_note": cluster_note,
            "style_note": style,
            "score": parts["score"],
            "score_parts": parts,
            "trend_context": context,
            "source_tokens": [_public_token(token) for token in group["tokens"]],
            "risk_note": _risk_note(style),
            "socials_text": _socials(name, ticker, description, context),
            "art": _art(concept_id),
            "image_prompt": _image_prompt(name, ticker, context),
            "image_file": f"images/{concept_id}.png",
        })
    ideas.sort(key=lambda idea: (
        -idea["score"],
        -(idea["score_parts"]["volume_usd"] or -1),
        idea["token_name"],
    ))
    for rank, idea in enumerate(ideas[:limit], start=1):
        idea["rank"] = rank
    return ideas[:limit]


def build_feed(ideas: list[dict]) -> list[dict]:
    if not ideas:
        return [{
            "agent_id": "rue",
            "role": "Skeptic",
            "text": "No concepts this scan. I won't invent tokens to fill the board.",
        }]
    feed = []
    for index, idea in enumerate(ideas):
        phase = idea["trend_context"]["freshness"]["phase"]
        feed.append({
            "agent_id": SCOUTS[index % len(SCOUTS)],
            "role": "Trend Scout",
            "text": f"Top {idea['rank']}: {idea['trend_name']}. Freshness {phase}.",
        })
        token = idea["source_tokens"][0] if idea["source_tokens"] else None
        if token:
            feed.append({
                "agent_id": TRACKERS[index % len(TRACKERS)],
                "role": "Token Tracker",
                "text": (
                    f"{token['symbol'] or token['name'] or 'token'}: volume {usd(token['volume_usd'])}, "
                    f"mcap {usd(token['market_cap_usd'])}."
                ),
            })
        if idea["classification"] == "META":
            why = idea["trend_context"]["why"]
            feed.append({
                "agent_id": SPOTTERS[index % len(SPOTTERS)],
                "role": "Meta Spotter",
                "text": f"Meta {idea['trend_name']}. {why[:120]}",
            })
        else:
            feed.append({
                "agent_id": ANALYSTS[index % len(ANALYSTS)],
                "role": "Launchpad Analyst",
                "text": f"Launchpad kit for {idea['token_name']} (${idea['ticker']}), rank {idea['rank']}.",
            })
        kind = "Beta coin" if idea["classification"] == "META" else "Derivative"
        feed.append({
            "agent_id": DESIGNERS[index % len(DESIGNERS)],
            "role": "Derivative Designer",
            "text": f"{kind} {idea['token_name']} (${idea['ticker']}). Coin logo is queued.",
        })
        if idea["trend_context"]["status"] != "sourced":
            skeptic = "trend unclear — I will not invent a story."
        else:
            skeptic = "Trademark risk: unofficial concept, not an official brand."
        feed.append({
            "agent_id": SKEPTICS[index % len(SKEPTICS)],
            "role": "Skeptic",
            "text": skeptic,
        })
    return feed


def build_document(
    ideas: list[dict],
    *,
    now: datetime | None = None,
    data_origin: str = "live",
    source_reports: list[dict] | None = None,
    sources_skipped: list[dict] | None = None,
    errors: list[str] | None = None,
) -> dict:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    generated = now.astimezone(timezone.utc).isoformat()
    nxt = (now + timedelta(seconds=SCAN_INTERVAL_SECONDS)).astimezone(timezone.utc).isoformat()
    return {
        "schema": "fomo-world.ideas.v1",
        "data_origin": data_origin,
        "label": "Research concepts only. These are not launched tokens.",
        "generated_at": generated,
        "scan_interval_seconds": SCAN_INTERVAL_SECONDS,
        "next_scan_at": nxt,
        "public_url": PUBLIC_URL,
        "source_reports": source_reports or [],
        "sources_skipped": sources_skipped or [],
        "errors": errors or [],
        "ideas": ideas,
        "feed": build_feed(ideas),
        "candidate_count": len(ideas),
    }


def example_document(now: datetime | None = None) -> dict:
    """Clearly fake layout data. Not written over a live scan."""
    now = now or datetime(2026, 11, 7, 15, 0, tzinfo=timezone.utc)
    tokens = [
        {
            "name": "Example Trout",
            "symbol": "EXTROUT",
            "chain": "solana",
            "address": "ExampleTrout111111111111111111111111111111",
            "dexscreener_url": "https://dexscreener.com/solana/example",
            "volume_usd": None,
            "market_cap_usd": None,
            "price_change_h24": None,
            "pair_created_at": None,
            "description": "EXAMPLE ONLY. This sentence is not a market quote.",
            "links": [],
            "source": "example",
        },
        {
            "name": "Example Trout Jr",
            "symbol": "EXTJ",
            "chain": "solana",
            "address": "ExampleTroutJr1111111111111111111111111111",
            "dexscreener_url": "https://dexscreener.com/solana/example-jr",
            "volume_usd": None,
            "market_cap_usd": None,
            "price_change_h24": None,
            "pair_created_at": None,
            "description": "",
            "links": [],
            "source": "example",
        },
    ]
    groups = cluster_tokens(tokens)
    ideas = build_ideas(groups, now=now)
    document = build_document(
        ideas,
        now=now,
        data_origin="example",
        source_reports=[],
        sources_skipped=[{"id": "example", "reason": "Labeled example layout. Not a live scan."}],
    )
    document["label"] = "EXAMPLE DATA — not a live scan and not real market figures."
    return document

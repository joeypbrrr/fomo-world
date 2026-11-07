"""One research scan: markets, trend context, top concepts, image queue."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from research.concepts import build_document, build_ideas, cluster_tokens
from research.http_client import make_fetcher
from research.queue import load_queue, merge_queue, write_queue
from research.sources import collect_markets, collect_reference, search_dex, search_news, search_reddit
from research.textutil import theme_words

ROOT = Path(__file__).resolve().parents[1]


def _news_query(group: dict) -> str | None:
    if group["classification"] == "META":
        word = group["theme_key"]
        if len(word) >= 4:
            return word
        return None
    token = group["tokens"][0]
    words = theme_words(token.get("name"), token.get("symbol"))
    if words:
        return words[0]
    symbol = (token.get("symbol") or "").strip()
    if len(symbol) >= 4:
        return symbol
    return None


def gather(fetch, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    tokens, reports, skipped = collect_markets(fetch)
    reference = collect_reference(fetch, now=now)
    reports.extend(reference["reports"])
    skipped.extend(reference["skipped"])
    groups = cluster_tokens(tokens)
    themes = [group["theme_key"] for group in groups if group["classification"] == "META"][:3]
    if themes:
        extra, extra_reports = search_dex(fetch, themes)
        reports.extend(extra_reports)
        if extra:
            tokens = tokens + extra
            # merge_tokens lives in sources; search hits are already shaped.
            from research.sources import merge_tokens
            tokens = merge_tokens(tokens)
            groups = cluster_tokens(tokens)
    # Ask news only for the louder groups so a scan stays well under rate limits.
    groups.sort(key=lambda group: (
        -(sum(token["volume_usd"] or 0 for token in group["tokens"])),
        -len(group["tokens"]),
    ))
    evidence: dict = {"trends": reference["trends"], "wiki": reference["wiki"]}
    reddit_open = reference["reddit_open"]
    reddit_calls = 0
    for group in groups[:8]:
        query = _news_query(group)
        if not query:
            continue
        news, report = search_news(fetch, query)
        reports.append(report)
        evidence.setdefault(group["theme_key"], {})["news"] = news
        if reddit_open and reddit_calls < 4:
            posts, reddit_report = search_reddit(fetch, query)
            reports.append(reddit_report)
            reddit_calls += 1
            if not reddit_report["ok"]:
                reddit_open = False
                skipped.append({
                    "id": "reddit-search",
                    "reason": "Reddit search failed after the probe. Not retried with another client.",
                })
            else:
                evidence.setdefault(group["theme_key"], {})["reddit"] = posts
    ideas = build_ideas(groups, evidence, now=now, limit=10)
    document = build_document(
        ideas,
        now=now,
        data_origin="live",
        source_reports=reports,
        sources_skipped=skipped,
    )
    document["token_count"] = len(tokens)
    document["group_count"] = len(groups)
    return document


def write_outputs(root: Path, document: dict, now: datetime | None = None) -> dict:
    data = root / "data"
    data.mkdir(parents=True, exist_ok=True)
    ideas_path = data / "ideas.json"
    ideas_path.write_text(json.dumps(document, indent=2) + "\n")
    queue_path = data / "image_queue.json"
    queue = merge_queue(load_queue(queue_path), document["ideas"], now=now)
    write_queue(queue_path, queue)
    return {"ideas": str(ideas_path), "queue": str(queue_path), "queued": len(queue["items"])}


def run(root: Path | None = None, fetch=None, now: datetime | None = None) -> dict:
    root = Path(root or ROOT)
    fetch = fetch or make_fetcher()
    now = now or datetime.now(timezone.utc)
    document = gather(fetch, now=now)
    paths = write_outputs(root, document, now=now)
    document["output"] = paths
    return document

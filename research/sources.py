"""Public, keyless market and trend sources.

Documented endpoints used:
- DexScreener token profiles, boosts, token pairs, and search
  https://docs.dexscreener.com/api/reference
- GeckoTerminal trending pools
  https://api.geckoterminal.com/docs/index.html
- Google News RSS search
- Google Trends daily RSS (https://trends.google.com/trending/rss?geo=US)
- Wikipedia featured feed, most-read section
  https://en.wikipedia.org/api/rest_v1/
- Reddit public search JSON (https://www.reddit.com/search.json). A 403 is
  recorded and not worked around.

X trends need an authenticated bearer token, so they are skipped.
pump.fun has no keyless documented API we can call without scraping, so it
is skipped.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

from research.textutil import clean_text, parse_number, parse_time

DEX_PROFILES = "https://api.dexscreener.com/token-profiles/latest/v1"
DEX_BOOSTS_LATEST = "https://api.dexscreener.com/token-boosts/latest/v1"
DEX_BOOSTS_TOP = "https://api.dexscreener.com/token-boosts/top/v1"
DEX_TOKENS = "https://api.dexscreener.com/latest/dex/tokens/"
DEX_SEARCH = "https://api.dexscreener.com/latest/dex/search?q="
GECKO_TRENDING = "https://api.geckoterminal.com/api/v2/networks/trending_pools?page=1"
GECKO_HEADERS = {"Accept": "application/json;version=20230203"}
NEWS_RSS = "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q="
TRENDS_RSS = "https://trends.google.com/trending/rss?geo=US"
WIKI_FEED = "https://en.wikipedia.org/api/rest_v1/feed/featured/"
REDDIT_SEARCH = "https://www.reddit.com/search.json?limit=8&sort=new&q="

EVM_CHAINS = {
    "ethereum", "base", "bsc", "arbitrum", "polygon", "optimism",
    "avalanche", "robinhood", "linea", "scroll", "mantle", "blast",
}


def address_key(chain: str, address: str) -> tuple[str, str]:
    chain = (chain or "").lower()
    address = address or ""
    if chain in EVM_CHAINS or address.startswith("0x") or address.startswith("0X"):
        return chain, address.lower()
    return chain, address


def empty_token(**kwargs) -> dict:
    token = {
        "name": "",
        "symbol": "",
        "chain": "",
        "address": "",
        "dexscreener_url": "",
        "volume_usd": None,
        "market_cap_usd": None,
        "price_change_h24": None,
        "pair_created_at": None,
        "description": "",
        "links": [],
        "source": "",
    }
    token.update(kwargs)
    return token


def _dex_url(chain: str, address: str, pair_url: str = "") -> str:
    if pair_url and pair_url.startswith("https://dexscreener.com/"):
        return pair_url
    if chain and address:
        return f"https://dexscreener.com/{chain}/{address}"
    return ""


def parse_dex_list(payload: str, source: str) -> list[dict]:
    try:
        data = json.loads(payload or "null")
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = data.get("data") or data.get("tokens") or []
    if not isinstance(data, list):
        return []
    tokens = []
    for row in data:
        if not isinstance(row, dict):
            continue
        chain = str(row.get("chainId") or "")
        address = str(row.get("tokenAddress") or "")
        if not chain or not address:
            continue
        links = []
        for link in row.get("links") or []:
            if not isinstance(link, dict):
                continue
            url = str(link.get("url") or "")
            if not url.startswith("http"):
                continue
            links.append({
                "type": str(link.get("type") or link.get("label") or "link"),
                "url": url,
            })
        tokens.append(empty_token(
            chain=chain,
            address=address,
            dexscreener_url=_dex_url(chain, address, str(row.get("url") or "")),
            description=clean_text(row.get("description") or ""),
            links=links,
            source=source,
        ))
    return tokens


def parse_dex_pairs(payload: str, source: str = "dexscreener-tokens") -> list[dict]:
    try:
        data = json.loads(payload or "null")
    except json.JSONDecodeError:
        return []
    pairs = data.get("pairs") if isinstance(data, dict) else data
    if not isinstance(pairs, list):
        return []
    best: dict[tuple[str, str], dict] = {}
    for pair in pairs:
        if not isinstance(pair, dict):
            continue
        base = pair.get("baseToken") or {}
        chain = str(pair.get("chainId") or "")
        address = str(base.get("address") or "")
        if not chain or not address:
            continue
        volume = parse_number((pair.get("volume") or {}).get("h24"))
        token = empty_token(
            name=clean_text(base.get("name") or "", 80),
            symbol=clean_text(base.get("symbol") or "", 24),
            chain=chain,
            address=address,
            dexscreener_url=_dex_url(chain, address, str(pair.get("url") or "")),
            volume_usd=volume,
            market_cap_usd=parse_number(pair.get("marketCap") if pair.get("marketCap") is not None else pair.get("fdv")),
            price_change_h24=parse_number((pair.get("priceChange") or {}).get("h24")),
            pair_created_at=parse_time(pair.get("pairCreatedAt")),
            source=source,
        )
        key = address_key(chain, address)
        current = best.get(key)
        current_volume = -1 if current is None or current["volume_usd"] is None else current["volume_usd"]
        new_volume = -1 if volume is None else volume
        if current is None or new_volume > current_volume:
            best[key] = token
    return list(best.values())


def parse_gecko_pools(payload: str) -> list[dict]:
    try:
        data = json.loads(payload or "null")
    except json.JSONDecodeError:
        return []
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []
    tokens = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        rel = ((row.get("relationships") or {}).get("base_token") or {}).get("data") or {}
        raw_id = str(rel.get("id") or "")
        if "_" not in raw_id:
            continue
        chain, address = raw_id.split("_", 1)
        attrs = row.get("attributes") or {}
        pool_name = str(attrs.get("name") or "")
        base_name = pool_name.split("/")[0].strip() if pool_name else ""
        volume = parse_number((attrs.get("volume_usd") or {}).get("h24") if isinstance(attrs.get("volume_usd"), dict) else attrs.get("volume_usd"))
        change = attrs.get("price_change_percentage") or {}
        tokens.append(empty_token(
            name=clean_text(base_name, 80),
            symbol=clean_text(base_name, 24),
            chain=chain,
            address=address,
            dexscreener_url=_dex_url(chain, address),
            volume_usd=volume,
            market_cap_usd=parse_number(attrs.get("market_cap_usd") if attrs.get("market_cap_usd") not in (None, "") else attrs.get("fdv_usd")),
            price_change_h24=parse_number(change.get("h24") if isinstance(change, dict) else None),
            pair_created_at=parse_time(attrs.get("pool_created_at")),
            source="geckoterminal-trending",
        ))
    return tokens


def _children(element: ET.Element):
    return list(element)


def _child_text(element: ET.Element, name: str) -> str:
    for child in element:
        if child.tag.rsplit("}", 1)[-1] == name:
            return "".join(child.itertext()).strip()
    return ""


def parse_rss_items(payload: str) -> list[dict]:
    try:
        root = ET.fromstring(payload or "")
    except ET.ParseError:
        return []
    items = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] != "item":
            continue
        title = clean_text(_child_text(node, "title"), 240)
        link = _child_text(node, "link")
        description = clean_text(_child_text(node, "description"), 400)
        pub = parse_time(_child_text(node, "pubDate")) or _child_text(node, "pubDate")
        source_name = ""
        source_url = ""
        news = []
        for child in _children(node):
            local = child.tag.rsplit("}", 1)[-1]
            if local == "source":
                source_name = clean_text("".join(child.itertext()), 120)
                source_url = child.attrib.get("url") or ""
            elif local == "news_item":
                news.append({
                    "title": clean_text(_child_text(child, "news_item_title"), 240),
                    "url": _child_text(child, "news_item_url"),
                    "source": clean_text(_child_text(child, "news_item_source"), 120),
                    "snippet": clean_text(_child_text(child, "news_item_snippet"), 300),
                })
        items.append({
            "title": title,
            "url": link,
            "description": description,
            "published": pub if isinstance(pub, str) else None,
            "source_name": source_name,
            "source_url": source_url,
            "news": [item for item in news if item["title"]],
        })
    return items


def parse_wiki_mostread(payload: str) -> list[dict]:
    try:
        data = json.loads(payload or "null")
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    articles = ((data.get("mostread") or {}).get("articles")) or []
    parsed = []
    for article in articles:
        if not isinstance(article, dict):
            continue
        title = clean_text(str(article.get("title") or "").replace("_", " "), 160)
        urls = ((article.get("content_urls") or {}).get("desktop") or {})
        url = urls.get("page") or ""
        extract = clean_text(article.get("extract") or article.get("description") or "", 300)
        if title and url:
            parsed.append({"title": title, "url": url, "snippet": extract})
    return parsed


def parse_reddit_search(payload: str) -> list[dict]:
    try:
        data = json.loads(payload or "null")
    except json.JSONDecodeError:
        return []
    children = ((data.get("data") or {}).get("children")) if isinstance(data, dict) else None
    if not isinstance(children, list):
        return []
    posts = []
    for child in children:
        row = (child or {}).get("data") if isinstance(child, dict) else None
        if not isinstance(row, dict):
            continue
        title = clean_text(row.get("title") or "", 240)
        permalink = str(row.get("permalink") or "")
        if not title or not permalink.startswith("/"):
            continue
        posts.append({
            "title": title,
            "url": "https://www.reddit.com" + permalink,
            "subreddit": clean_text(row.get("subreddit_name_prefixed") or row.get("subreddit") or "", 80),
            "snippet": clean_text(row.get("selftext") or "", 300),
        })
    return posts


def merge_tokens(*groups: list[dict]) -> list[dict]:
    merged: dict[tuple[str, str], dict] = {}
    for group in groups:
        for token in group:
            if not token.get("chain") or not token.get("address"):
                continue
            key = address_key(token["chain"], token["address"])
            current = merged.get(key)
            if current is None:
                merged[key] = {
                    **token,
                    "chain": key[0],
                    "address": key[1],
                    "links": list(token.get("links") or []),
                }
                continue
            if token.get("description") and not current.get("description"):
                current["description"] = token["description"]
            if token.get("name") and (not current.get("name") or current["name"] == current.get("symbol")):
                current["name"] = token["name"]
            if token.get("symbol") and not current.get("symbol"):
                current["symbol"] = token["symbol"]
            elif token.get("symbol") and current.get("symbol") == current.get("name") and token["symbol"] != token.get("name"):
                current["symbol"] = token["symbol"]
            for field in ("volume_usd", "market_cap_usd", "price_change_h24", "pair_created_at"):
                if current.get(field) is None and token.get(field) is not None:
                    current[field] = token[field]
            if token.get("volume_usd") is not None and (
                current.get("volume_usd") is None or token["volume_usd"] > current["volume_usd"]
            ):
                current["volume_usd"] = token["volume_usd"]
                if token.get("market_cap_usd") is not None:
                    current["market_cap_usd"] = token["market_cap_usd"]
                if token.get("price_change_h24") is not None:
                    current["price_change_h24"] = token["price_change_h24"]
                if token.get("pair_created_at"):
                    current["pair_created_at"] = token["pair_created_at"]
                if token.get("dexscreener_url"):
                    current["dexscreener_url"] = token["dexscreener_url"]
            if token.get("links"):
                seen = {link["url"] for link in current["links"]}
                for link in token["links"]:
                    if link["url"] not in seen:
                        current["links"].append(link)
                        seen.add(link["url"])
            if token.get("dexscreener_url") and not current.get("dexscreener_url"):
                current["dexscreener_url"] = token["dexscreener_url"]
    return list(merged.values())


def _json_body(result) -> str:
    if result is None or not result.ok:
        return ""
    return result.body


def collect_markets(fetch, search_terms: list[str] | None = None) -> tuple[list[dict], list[dict], list[dict]]:
    """Fetch market lists. search_terms adds a few DexScreener searches."""
    reports = []
    skipped = [
        {
            "id": "x-trends",
            "reason": "The official X trends API requires a bearer token. Skipped. No login, no scraping.",
        },
        {
            "id": "pump.fun",
            "reason": "No documented keyless public API. The front page is not scraped.",
        },
    ]

    def grab(source_id: str, url: str, headers: dict | None = None):
        result = fetch(url, headers) if headers else fetch(url)
        reports.append({
            "id": source_id,
            "url": url,
            "ok": bool(result.ok),
            "status": result.status,
            "error": result.error,
        })
        return result

    profiles = parse_dex_list(_json_body(grab("dexscreener-profiles", DEX_PROFILES)), "dexscreener-profiles")
    boosts_latest = parse_dex_list(_json_body(grab("dexscreener-boosts-latest", DEX_BOOSTS_LATEST)), "dexscreener-boosts-latest")
    boosts_top = parse_dex_list(_json_body(grab("dexscreener-boosts-top", DEX_BOOSTS_TOP)), "dexscreener-boosts-top")
    gecko = parse_gecko_pools(_json_body(grab("geckoterminal-trending", GECKO_TRENDING, GECKO_HEADERS)))
    tokens = merge_tokens(profiles, boosts_latest, boosts_top, gecko)

    addresses = []
    seen = set()
    for token in tokens:
        key = address_key(token["chain"], token["address"])
        if key in seen:
            continue
        seen.add(key)
        addresses.append(token["address"])
    pair_tokens: list[dict] = []
    for start in range(0, min(len(addresses), 60), 30):
        batch = ",".join(addresses[start:start + 30])
        url = DEX_TOKENS + batch
        pair_tokens.extend(parse_dex_pairs(_json_body(grab("dexscreener-tokens", url)), "dexscreener-tokens"))
    tokens = merge_tokens(tokens, pair_tokens)

    for term in (search_terms or [])[:3]:
        url = DEX_SEARCH + quote_plus(term)
        found = parse_dex_pairs(_json_body(grab("dexscreener-search", url)), "dexscreener-search")
        tokens = merge_tokens(tokens, found[:8])
    return tokens, reports, skipped


def collect_reference(fetch, now: datetime | None = None) -> dict:
    """Trends RSS, Wikipedia most-read, and one Reddit probe."""
    now = now or datetime.now(timezone.utc)
    reports = []
    skipped = []

    trends_result = fetch(TRENDS_RSS)
    reports.append({
        "id": "google-trends-rss",
        "url": TRENDS_RSS,
        "ok": bool(trends_result.ok),
        "status": trends_result.status,
        "error": trends_result.error,
    })
    trends = parse_rss_items(trends_result.body) if trends_result.ok else []

    wiki_articles: list[dict] = []
    wiki_url = ""
    day = now.astimezone(timezone.utc).date()
    for candidate in (day - timedelta(days=1), day - timedelta(days=2)):
        wiki_url = WIKI_FEED + candidate.strftime("%Y/%m/%d")
        result = fetch(wiki_url)
        reports.append({
            "id": "wikipedia-mostread",
            "url": wiki_url,
            "ok": bool(result.ok),
            "status": result.status,
            "error": result.error,
        })
        if result.ok:
            wiki_articles = parse_wiki_mostread(result.body)
            if wiki_articles:
                break

    reddit_url = REDDIT_SEARCH + quote_plus("trending")
    reddit_result = fetch(reddit_url)
    reddit_ok = bool(reddit_result.ok)
    reports.append({
        "id": "reddit-search",
        "url": "https://www.reddit.com/search.json",
        "ok": reddit_ok,
        "status": reddit_result.status,
        "error": reddit_result.error,
    })
    if not reddit_ok:
        skipped.append({
            "id": "reddit-search",
            "reason": (
                "Reddit public search.json returned "
                f"{reddit_result.status or reddit_result.error}. "
                "Skipped. No login and no scrape around the block."
            ),
        })

    return {
        "trends": trends,
        "wiki": wiki_articles,
        "reddit_open": reddit_ok,
        "reports": reports,
        "skipped": skipped,
    }


def search_dex(fetch, terms: list[str]) -> tuple[list[dict], list[dict]]:
    """DexScreener search for a few theme words. Pairs that do not contain the word are dropped."""
    from research.textutil import whole_word

    found = []
    reports = []
    for term in terms[:3]:
        url = DEX_SEARCH + quote_plus(term)
        result = fetch(url)
        reports.append({
            "id": "dexscreener-search",
            "url": url,
            "ok": bool(result.ok),
            "status": result.status,
            "error": result.error,
            "query": term,
        })
        if not result.ok:
            continue
        for token in parse_dex_pairs(result.body, "dexscreener-search"):
            blob = f"{token.get('name') or ''} {token.get('symbol') or ''}"
            if whole_word(term, blob):
                found.append(token)
    return found[:12], reports


def search_news(fetch, query: str) -> tuple[list[dict], dict]:
    url = NEWS_RSS + quote_plus(query)
    result = fetch(url)
    report = {
        "id": "google-news-rss",
        "url": url,
        "ok": bool(result.ok),
        "status": result.status,
        "error": result.error,
        "query": query,
    }
    items = parse_rss_items(result.body) if result.ok else []
    return items, report


def search_reddit(fetch, query: str) -> tuple[list[dict], dict]:
    url = REDDIT_SEARCH + quote_plus(query)
    result = fetch(url)
    report = {
        "id": "reddit-search",
        "url": url,
        "ok": bool(result.ok),
        "status": result.status,
        "error": result.error,
        "query": query,
    }
    posts = parse_reddit_search(result.body) if result.ok else []
    return posts, report

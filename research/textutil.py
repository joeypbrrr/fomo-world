"""Small text helpers. No story is invented here."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone

STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "your", "you", "are",
    "was", "has", "have", "will", "not", "but", "its", "it's", "just", "into",
    "onto", "over", "under", "coin", "token", "tokens", "inu", "sol", "solana",
    "eth", "ethereum", "base", "bnb", "usd", "usdc", "usdt", "swap", "pool",
    "official", "meme", "fun", "pump", "dex", "www", "com", "net", "org",
    "http", "https", "crypto", "chain", "finance", "defi", "nft", "new", "old",
    "best", "real", "true", "fake", "version",     "baby", "mini", "max", "pro",
    "plus", "holder", "world", "record", "developed", "cooperation",
    "state", "money", "order", "home", "game", "real", "best", "based",
    "hands", "little", "mega", "super", "safe", "gold", "moon", "king",
    "love", "time", "life", "play", "star", "rock", "fire", "power",
    "trading", "virtual", "infinite", "cartoon", "hold", "hodl",
    "sparkle", "community", "someone", "would", "entire", "space",
    "build", "asked", "launch", "launchpad",
}

# Words that show up in unrelated headlines. They can still be a cluster key
# when tokens share them, but they are not enough to claim a news story.
COMMON_WORDS = STOPWORDS | {
    "alice", "diamond", "world", "money", "state", "queen", "prince",
    "angel", "devil", "happy", "lucky", "magic", "ninja", "pirate",
    "ghost", "kitty", "puppy", "doge", "pepe", "trump", "elon", "musk",
    "tesla", "apple", "google",
}

# Never use these as a generated concept name or ticker. Descriptions may
# still say "Tesla-style" when the source text actually contains the theme.
BRANDS = {
    "tesla", "elon", "musk", "trump", "nike", "apple", "google", "nvidia",
    "disney", "openai", "microsoft", "amazon", "facebook", "instagram",
    "tiktok", "meta", "solana", "ethereum", "bitcoin", "pepe", "doge",
    "binance", "coinbase", "robinhood", "gta", "gta6", "rockstar",
}
BRAND_TICKERS = {
    "TSLA", "DOGE", "TRUMP", "NVDA", "AAPL", "GOOG", "GOOGL", "META", "AMZN",
    "MSFT", "SOL", "ETH", "BTC", "NKE", "PEPE",
}

STYLE_HINTS = {
    "elon": "Tesla-style",
    "musk": "Tesla-style",
    "tesla": "Tesla-style",
    "doge": "dog-meme-style",
    "trump": "political-figure-style",
    "pepe": "frog-meme-style",
    "gta": "GTA-style",
    "gta6": "GTA-style",
    "rockstar": "GTA-style",
    "leonida": "GTA-style",
}

# Concrete words we may reuse in a concept name only when they appear in
# sourced text or in the token's own name.
CONCRETE = {
    "rocket", "hat", "cat", "dog", "frog", "pizza", "moon", "crown", "banana",
    "wind", "storm", "wave", "fish", "bird", "star", "cake", "bean", "cloud",
    "flame", "robot", "wizard", "knight", "ghost", "apple", "coffee", "tea",
    "boat", "train", "kite", "balloon", "candy", "honey", "maple", "tiger",
    "panda", "otter", "duck", "goose", "lion", "bear", "fox", "wolf", "peach",
    "cherry", "lemon", "mint", "cocoa", "drum", "bell", "lamp", "key", "castle",
    "garden", "island", "comet", "snow", "rain", "sun", "leaf", "seed", "nest",
    "egg", "milk", "bread", "cheese", "pickle", "taco", "noodle", "sushi",
    "alien", "pirate", "ninja", "crystal", "diamond", "gold", "silver",
    "copper", "volt", "garage", "battery", "engine", "wheel", "motor", "cable",
    "signal", "pixel", "byte", "orbit", "sprout", "lantern", "puddle", "kettle",
}

ADJECTIVES = (
    "Pebble", "Nimbus", "Cinder", "Mellow", "Pocket", "Linen", "Harbor",
    "Velvet", "Clover", "Marigold", "Paper", "Willow", "Amber", "Little",
    "Quiet", "Brass", "Sunny", "Mossy", "Ripple", "Fable",
)
NOUNS = (
    "Sprout", "Lantern", "Minnow", "Kettle", "Orbit", "Thimble", "Acorn",
    "Ferry", "Biscuit", "Comet", "Puddle", "Locket", "Sparrow", "Button",
    "Canyon", "Picnic", "Marble", "Whistle", "Drum", "Nest",
)

_TAG = re.compile(r"<[^>]+>")
_WORD = re.compile(r"[a-z][a-z0-9]{2,}")
_SPACE = re.compile(r"\s+")


def clean_text(value: str | None, limit: int = 400) -> str:
    text = _SPACE.sub(" ", _TAG.sub(" ", html.unescape(value or ""))).strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def words(value: str | None) -> list[str]:
    return _WORD.findall((value or "").lower())


def theme_words(*parts: str | None) -> list[str]:
    seen: list[str] = []
    for part in parts:
        for word in words(part):
            if len(word) < 4 or word in STOPWORDS or word in seen:
                continue
            if word.isdigit():
                continue
            seen.append(word)
    return seen


def whole_word(needle: str, haystack: str) -> bool:
    if not needle:
        return False
    return re.search(rf"\b{re.escape(needle.lower())}\b", (haystack or "").lower()) is not None


def usd(value: float | None) -> str:
    if value is None:
        return "n/a"
    number = float(value)
    sign = "-" if number < 0 else ""
    number = abs(number)
    if number >= 1_000_000_000:
        return f"{sign}${number / 1_000_000_000:.1f}B"
    if number >= 1_000_000:
        return f"{sign}${number / 1_000_000:.1f}M"
    if number >= 1_000:
        return f"{sign}${number / 1_000:.1f}K"
    return f"{sign}${number:.0f}"


def parse_number(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def parse_time(value) -> str | None:
    """Return an ISO-8601 UTC timestamp, or None. Never guess a time."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        raw = float(value)
        if raw > 10_000_000_000:
            raw /= 1000.0
        try:
            return datetime.fromtimestamp(raw, timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def hours_between(earlier_iso: str | None, now: datetime) -> float | None:
    if not earlier_iso:
        return None
    try:
        earlier = datetime.fromisoformat(earlier_iso)
    except ValueError:
        return None
    if earlier.tzinfo is None:
        earlier = earlier.replace(tzinfo=timezone.utc)
    delta = (now - earlier).total_seconds() / 3600.0
    if delta < 0:
        return 0.0
    return delta

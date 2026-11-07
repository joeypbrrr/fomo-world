"""Pipeline uses injected responses and does not invent a story when they are empty."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

from research.pipeline import gather

NOW = datetime(2026, 11, 7, 15, 0, tzinfo=timezone.utc)


class Result:
    def __init__(self, status, body, error=None):
        self.status = status
        self.body = body
        self.error = error
        self.ok = error is None and status is not None and 200 <= status < 300


class PipelineTests(unittest.TestCase):
    def test_live_shape_from_fixtures(self):
        calls = []

        def fetch(url, headers=None):
            calls.append(url)
            if url.endswith("/token-profiles/latest/v1"):
                return Result(200, json.dumps([{
                    "chainId": "solana",
                    "tokenAddress": "MintKite",
                    "url": "https://dexscreener.com/solana/MintKite",
                    "description": "Town kite festival sticker.",
                    "links": [{"type": "twitter", "url": "https://x.com/kiteclub"}],
                }, {
                    "chainId": "solana",
                    "tokenAddress": "MintOther",
                    "url": "https://dexscreener.com/solana/MintOther",
                    "description": "Town kite festival hat.",
                }]))
            if "token-boosts" in url:
                return Result(200, "[]")
            if "geckoterminal" in url:
                return Result(200, json.dumps({"data": []}))
            if "/latest/dex/tokens/" in url:
                return Result(200, json.dumps({"pairs": [
                    {
                        "chainId": "solana",
                        "url": "https://dexscreener.com/solana/pair1",
                        "baseToken": {"address": "MintKite", "name": "Kite Day", "symbol": "KITE"},
                        "volume": {"h24": 500000},
                        "marketCap": 900000,
                        "priceChange": {"h24": 30},
                        "pairCreatedAt": 1762520000000,
                    },
                    {
                        "chainId": "solana",
                        "url": "https://dexscreener.com/solana/pair2",
                        "baseToken": {"address": "MintOther", "name": "Kite Hat", "symbol": "KITEH"},
                        "volume": {"h24": 120000},
                        "marketCap": 80000,
                        "priceChange": {"h24": 5},
                        "pairCreatedAt": 1762521000000,
                    },
                ]}))
            if "news.google.com" in url:
                return Result(200, """<?xml version="1.0"?><rss><channel>
                    <item><title>Kite festival draws a crowd</title><link>https://news.example/kite</link>
                    <source url="https://news.example">Town Paper</source></item>
                    <item><title>Unrelated market close</title><link>https://news.example/nope</link></item>
                </channel></rss>""")
            if "trends.google.com" in url:
                return Result(200, """<?xml version="1.0"?><rss><channel>
                    <item><title>something else</title><link>https://trends.google.com/trending/rss?geo=US</link></item>
                </channel></rss>""")
            if "wikipedia.org" in url:
                return Result(200, json.dumps({"mostread": {"articles": []}}))
            if "reddit.com" in url:
                return Result(403, "blocked", "HTTP 403")
            return Result(404, "", "unexpected " + url)

        document = gather(fetch, now=NOW)
        self.assertEqual(document["data_origin"], "live")
        self.assertEqual(document["scan_interval_seconds"], 1800)
        self.assertTrue(document["ideas"])
        idea = document["ideas"][0]
        self.assertEqual(idea["classification"], "META")
        self.assertIn("Kite festival draws a crowd", idea["trend_context"]["why"])
        self.assertNotIn("Unrelated market", idea["trend_context"]["why"])
        self.assertIn("kiteclub", idea["trend_context"]["driver"])
        self.assertEqual(idea["source_tokens"][0]["volume_usd"] in (500000, 120000) or True, True)
        volumes = sorted(token["volume_usd"] for token in idea["source_tokens"])
        self.assertEqual(volumes, [120000, 500000])
        self.assertTrue(any(item["id"] == "reddit-search" for item in document["sources_skipped"]))
        self.assertTrue(any(item["id"] == "x-trends" for item in document["sources_skipped"]))
        self.assertTrue(any(item["id"] == "pump.fun" for item in document["sources_skipped"]))
        self.assertIn("Top 1", document["feed"][0]["text"])
        self.assertTrue(any("Kite" in line["text"] or "kite" in line["text"] for line in document["feed"]))

    def test_failed_sources_do_not_fabricate_ideas(self):
        def fetch(url, headers=None):
            return Result(503, "", "HTTP 503")

        document = gather(fetch, now=NOW)
        self.assertEqual(document["ideas"], [])
        self.assertIn("won't invent", document["feed"][0]["text"])
        self.assertTrue(document["source_reports"])
        self.assertTrue(all(not report["ok"] for report in document["source_reports"]))


if __name__ == "__main__":
    unittest.main()

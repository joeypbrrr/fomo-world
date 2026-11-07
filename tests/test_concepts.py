"""Classification, trend context, naming, and the image queue."""

from __future__ import annotations

import json
import struct
import tempfile
import unittest
import zlib
from datetime import datetime, timezone
from pathlib import Path

from research.concepts import build_document, build_ideas, cluster_tokens, example_document
from research.config import CONTEXT_SCORE_FACTOR, SCAN_INTERVAL_SECONDS
from research.context import build_trend_context
from research.queue import load_queue, merge_queue
from research.sources import (
    parse_dex_list,
    parse_dex_pairs,
    parse_gecko_pools,
    parse_reddit_search,
    parse_rss_items,
    parse_wiki_mostread,
)
from research.textutil import BRANDS

NOW = datetime(2026, 11, 7, 15, 0, tzinfo=timezone.utc)


def token(**kwargs):
    base = {
        "name": "Sample",
        "symbol": "SAMP",
        "chain": "solana",
        "address": "Addr11111111111111111111111111111111111111",
        "dexscreener_url": "https://dexscreener.com/solana/addr",
        "volume_usd": 1000.0,
        "market_cap_usd": 5000.0,
        "price_change_h24": 10.0,
        "pair_created_at": "2026-11-07T12:00:00+00:00",
        "description": "",
        "links": [],
        "source": "test",
    }
    base.update(kwargs)
    return base


def write_png(path: Path, width: int, height: int) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)
    raw = b"".join(b"\x00" + bytes((255, 180, 90)) * width for _ in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(PNG_SIG + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


PNG_SIG = b"\x89PNG\r\n\x1a\n"


class ClusterTests(unittest.TestCase):
    def test_shared_word_is_a_meta(self):
        groups = cluster_tokens([
            token(name="Elon Rocket", symbol="ELONR", address="a"),
            token(name="Elon Hat", symbol="ELONH", address="b"),
            token(name="Moonberry", symbol="MOONB", address="c", volume_usd=9_000_000),
        ])
        kinds = {(group["classification"], group["theme_key"]) for group in groups}
        self.assertIn(("META", "elon"), kinds)
        self.assertIn(("LAUNCHPAD", "token:solana:c"), kinds)

    def test_empty_sources_make_no_ideas(self):
        ideas = build_ideas(cluster_tokens([]), now=NOW)
        self.assertEqual(ideas, [])
        document = build_document(ideas, now=NOW)
        self.assertEqual(document["ideas"], [])
        self.assertEqual(document["feed"][0]["agent_id"], "rue")
        self.assertIn("won't invent", document["feed"][0]["text"])

    def test_missing_volume_stays_null(self):
        groups = cluster_tokens([
            token(name="Quiet Lamp", symbol="QLMP", address="q", volume_usd=None, market_cap_usd=None),
        ])
        idea = build_ideas(groups, now=NOW)[0]
        self.assertIsNone(idea["source_tokens"][0]["volume_usd"])
        self.assertIsNone(idea["source_tokens"][0]["market_cap_usd"])
        self.assertIn("n/a", idea and build_document([idea], now=NOW)["feed"][1]["text"])

    def test_elon_theme_is_tesla_style_but_not_named_tesla(self):
        groups = cluster_tokens([
            token(
                name="Elon Rocket",
                symbol="ELONR",
                address="a",
                description="Fans posting rocket jokes under the elon theme.",
                volume_usd=2_000_000,
            ),
            token(name="Elon Hat", symbol="ELONH", address="b", volume_usd=800_000),
        ])
        idea = build_ideas(groups, now=NOW)[0]
        self.assertEqual(idea["classification"], "META")
        self.assertEqual(idea["concept_kind"], "beta coin")
        self.assertEqual(idea["style_note"], "Tesla-style")
        blob = f"{idea['name']} {idea['token_name']} {idea['ticker']}".lower()
        for banned in ("elon", "tesla", "musk", "elonr", "elonh"):
            self.assertNotIn(banned, blob.split() if " " in banned else blob)
        self.assertNotIn("elon", idea["name"].lower().split())
        self.assertNotIn("tesla", idea["name"].lower().split())
        self.assertNotIn(idea["ticker"], {"TSLA", "ELON"})
        self.assertIn("trademark", idea["risk_note"].lower())
        self.assertIn("impersonat", idea["risk_note"].lower())
        self.assertIn("DexScreener profile:", idea["trend_context"]["why"])
        self.assertIn("Fans posting rocket jokes", idea["trend_context"]["why"])
        self.assertIn("rocket", idea["image_prompt"].lower())
        self.assertIn("likeness", idea["image_prompt"].lower())

    def test_unclear_trend_is_labeled_and_downranked(self):
        groups = cluster_tokens([
            token(name="Zibble Rocket", symbol="ZIBB", address="z1", description="", volume_usd=2_000_000, price_change_h24=40),
            token(name="Zibble Hat", symbol="ZIBH", address="z2", description="", volume_usd=2_000_000, price_change_h24=40),
        ])
        unclear = build_ideas(groups, now=NOW)[0]
        self.assertEqual(unclear["trend_context"]["status"], "trend unclear")
        self.assertEqual(unclear["trend_context"]["why"], "trend unclear")
        self.assertEqual(unclear["trend_context"]["meme_or_story"], "trend unclear")
        sourced_groups = cluster_tokens([
            token(
                name="Zibble Rocket",
                symbol="ZIBB",
                address="z1",
                description="A community joke about a paper zibble rocket.",
                volume_usd=2_000_000,
                price_change_h24=40,
            ),
            token(name="Zibble Hat", symbol="ZIBH", address="z2", description="", volume_usd=2_000_000, price_change_h24=40),
        ])
        sourced = build_ideas(sourced_groups, now=NOW)[0]
        self.assertEqual(sourced["trend_context"]["status"], "sourced")
        self.assertAlmostEqual(unclear["score"], round(sourced["score_parts"]["raw"] * CONTEXT_SCORE_FACTOR, 1))
        self.assertLess(unclear["score"], sourced["score"])
        self.assertIn("trend unclear", unclear["image_prompt"].lower())
        self.assertNotIn("paper zibble", unclear["image_prompt"].lower())

    def test_common_name_does_not_inherit_unrelated_news(self):
        groups = cluster_tokens([
            token(name="Alice", symbol="ALICE", address="alice", description="", volume_usd=2_000_000),
        ])
        evidence = {
            "trends": [],
            "wiki": [],
            "token:solana:alice": {
                "news": [{
                    "title": "Alice J. Pecor Barton funeral service",
                    "url": "https://news.example/funeral",
                    "description": "",
                    "source_name": "Example",
                }],
            },
        }
        idea = build_ideas(groups, evidence, now=NOW)[0]
        self.assertEqual(idea["trend_context"]["status"], "trend unclear")
        self.assertEqual(idea["trend_context"]["why"], "trend unclear")
        self.assertNotIn("funeral", idea["image_prompt"].lower())

    def test_digit_ticker_can_use_a_matching_headline(self):
        groups = cluster_tokens([
            token(name="GTA6", symbol="GTA6", address="gta", description="", volume_usd=4_000_000),
        ])
        evidence = {
            "trends": [],
            "wiki": [],
            "token:solana:gta": {
                "news": [{
                    "title": "New GTA6 screenshots compare in-game cars",
                    "url": "https://news.example/gta6",
                    "description": "",
                    "source_name": "RockstarINTEL",
                }],
            },
        }
        idea = build_ideas(groups, evidence, now=NOW)[0]
        self.assertEqual(idea["trend_context"]["status"], "sourced")
        self.assertIn("GTA6 screenshots", idea["trend_context"]["why"])
        self.assertNotIn("gta", idea["token_name"].lower())
        self.assertIn("Rockstar", idea["risk_note"])

    def test_generic_state_is_not_the_meta_name(self):
        groups = cluster_tokens([
            token(name="State of Leonida", symbol="LEON", address="l1", description="The home state of GTA VI"),
            token(name="Leonida State", symbol="LEO2", address="l2", description=""),
            token(name="State of Mika", symbol="MIKA", address="m1", description=""),
        ])
        themes = {group["theme_key"] for group in groups if group["classification"] == "META"}
        self.assertIn("leonida", themes)
        self.assertNotIn("state", themes)

    def test_news_must_mention_the_theme(self):
        groups = cluster_tokens([
            token(name="Orbit Finch", symbol="OFIN", address="o1", description=""),
            token(name="Orbit Nest", symbol="ONES", address="o2", description=""),
        ])
        evidence = {
            "trends": [],
            "wiki": [],
            "orbit": {
                "news": [
                    {"title": "City council meets Tuesday", "url": "https://news.example/a", "description": "", "source_name": "Example"},
                    {"title": "Orbit finch video spreads", "url": "https://news.example/b", "description": "", "source_name": "Example"},
                ],
            },
        }
        idea = build_ideas(groups, evidence, now=NOW)[0]
        self.assertIn("Orbit finch video spreads", idea["trend_context"]["why"])
        self.assertNotIn("City council", idea["trend_context"]["why"])
        urls = [source["url"] for source in idea["trend_context"]["sources"]]
        self.assertIn("https://news.example/b", urls)
        self.assertNotIn("https://news.example/a", urls)

    def test_top_10_cap_and_rank(self):
        names = [
            "Alphaaa", "Bravooo", "Charlii", "Deltaaa", "Echoooo", "Foxtrot",
            "Golffff", "Hotelll", "Indiaaa", "Juliett", "Kiloaaa", "Limaaaa",
        ]
        tokens = []
        for index, name in enumerate(names):
            tokens.append(token(
                name=name,
                symbol=name[:4].upper(),
                address=f"addr{index}",
                volume_usd=1000 * (12 - index),
            ))
        ideas = build_ideas(cluster_tokens(tokens), now=NOW)
        self.assertEqual(len(ideas), 10)
        self.assertEqual([idea["rank"] for idea in ideas], list(range(1, 11)))
        self.assertGreaterEqual(ideas[0]["score"], ideas[-1]["score"])

    def test_risk_note_on_every_idea(self):
        groups = cluster_tokens([
            token(name="Marble Ferry", symbol="MFER", address="m", description="A marble boat joke."),
        ])
        for idea in build_ideas(groups, now=NOW):
            self.assertIn("Trademark and impersonation risk", idea["risk_note"])
            self.assertTrue(idea["ticker"].isalpha())
            self.assertGreaterEqual(len(idea["ticker"]), 4)
            self.assertNotIn(idea["name"].split()[0].lower(), BRANDS)

    def test_interval_is_thirty_minutes(self):
        document = build_document([], now=NOW)
        self.assertEqual(SCAN_INTERVAL_SECONDS, 1800)
        self.assertEqual(document["scan_interval_seconds"], 1800)
        self.assertEqual(document["next_scan_at"], "2026-11-07T15:30:00+00:00")

    def test_example_file_is_labeled(self):
        document = example_document(NOW)
        self.assertEqual(document["data_origin"], "example")
        self.assertIn("EXAMPLE", document["label"])
        self.assertIsNone(document["ideas"][0]["source_tokens"][0]["volume_usd"])

    def test_queue_dedupes_concept_ids(self):
        groups = cluster_tokens([
            token(name="Pebble Kite", symbol="PKIT", address="p1", description="Kids flying a pebble kite."),
            token(name="Pebble Kite Two", symbol="PKI2", address="p2"),
        ])
        ideas = build_ideas(groups, now=NOW)
        first = merge_queue({"items": []}, ideas, now=NOW)
        second = merge_queue(first, ideas, now=NOW)
        ids = [item["concept_id"] for item in second["items"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), len(ideas))
        self.assertTrue(all(item["status"] == "pending" for item in second["items"]))
        self.assertEqual(second["items"][0]["target_width"], 1000)
        done = json.loads(json.dumps(second))
        done["items"][0]["status"] = "done"
        done["items"][0]["prompt"] = "keep me"
        again = merge_queue(done, ideas, now=NOW)
        self.assertEqual(again["items"][0]["prompt"], "keep me")
        self.assertEqual(again["items"][0]["status"], "done")


class ParserTests(unittest.TestCase):
    def test_dex_boost_and_pairs(self):
        boosts = parse_dex_list(json.dumps([{
            "url": "https://dexscreener.com/solana/mint",
            "chainId": "solana",
            "tokenAddress": "Mint111",
            "description": "A paper kite meme.",
            "links": [{"type": "twitter", "url": "https://x.com/kitefans"}],
        }]), "dexscreener-boosts-top")
        self.assertEqual(boosts[0]["description"], "A paper kite meme.")
        self.assertEqual(boosts[0]["links"][0]["url"], "https://x.com/kitefans")
        pairs = parse_dex_pairs(json.dumps({"pairs": [{
            "chainId": "solana",
            "url": "https://dexscreener.com/solana/pair",
            "baseToken": {"address": "Mint111", "name": "Kite", "symbol": "KITE"},
            "volume": {"h24": 1234},
            "marketCap": 9999,
            "priceChange": {"h24": 12.5},
            "pairCreatedAt": 1762524000000,
        }]}))
        self.assertEqual(pairs[0]["symbol"], "KITE")
        self.assertEqual(pairs[0]["volume_usd"], 1234)
        self.assertIsNotNone(pairs[0]["pair_created_at"])

    def test_gecko_pool(self):
        payload = json.dumps({"data": [{
            "attributes": {
                "name": "KITE / SOL",
                "volume_usd": {"h24": "42.5"},
                "market_cap_usd": None,
                "fdv_usd": "1000",
                "price_change_percentage": {"h24": "-3.5"},
                "pool_created_at": "2026-11-07T14:00:00Z",
            },
            "relationships": {"base_token": {"data": {"id": "solana_Mint111"}}},
        }]})
        parsed = parse_gecko_pools(payload)
        self.assertEqual(parsed[0]["address"], "Mint111")
        self.assertEqual(parsed[0]["volume_usd"], 42.5)
        self.assertEqual(parsed[0]["market_cap_usd"], 1000)
        self.assertEqual(parsed[0]["price_change_h24"], -3.5)

    def test_trends_rss_wiki_and_reddit(self):
        rss = """<?xml version="1.0"?>
        <rss xmlns:ht="https://trends.google.com/trending/rss"><channel>
          <item>
            <title>kite festival</title>
            <link>https://trends.google.com/trending/rss?geo=US</link>
            <ht:news_item>
              <ht:news_item_title>Town kite festival opens</ht:news_item_title>
              <ht:news_item_url>https://news.example/kite</ht:news_item_url>
              <ht:news_item_source>Town Paper</ht:news_item_source>
            </ht:news_item>
          </item>
        </channel></rss>"""
        items = parse_rss_items(rss)
        self.assertEqual(items[0]["title"], "kite festival")
        self.assertEqual(items[0]["news"][0]["title"], "Town kite festival opens")
        wiki = parse_wiki_mostread(json.dumps({"mostread": {"articles": [{
            "title": "Kite_festival",
            "extract": "A festival.",
            "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Kite_festival"}},
        }]}}))
        self.assertEqual(wiki[0]["title"], "Kite festival")
        posts = parse_reddit_search(json.dumps({"data": {"children": [{"data": {
            "title": "Kite festival thread",
            "permalink": "/r/hobbies/comments/abc/kite/",
            "subreddit_name_prefixed": "r/hobbies",
            "selftext": "Bring string.",
        }}]}}))
        self.assertEqual(posts[0]["url"], "https://www.reddit.com/r/hobbies/comments/abc/kite/")

    def test_context_cites_trends_and_ignores_unrelated_wiki(self):
        context = build_trend_context(
            "META",
            "kite",
            [token(name="Kite Day", symbol="KDAY", address="k", description="")],
            trends=[{
                "title": "kite festival",
                "url": "https://trends.google.com/trending/rss?geo=US",
                "news": [{"title": "Town kite festival opens", "url": "https://news.example/kite"}],
            }],
            wiki=[{"title": "Russell Brand", "url": "https://en.wikipedia.org/wiki/Russell_Brand", "snippet": ""}],
            now=NOW,
        )
        self.assertEqual(context["status"], "sourced")
        self.assertIn("Town kite festival opens", context["why"])
        self.assertNotIn("Russell", context["why"])
        self.assertEqual(context["freshness"]["phase"], "rising")


class ImportTests(unittest.TestCase):
    def test_import_validates_size_and_marks_done(self):
        from import_images import import_images

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "in"
            inbox.mkdir()
            (root / "data").mkdir()
            idea = build_ideas(cluster_tokens([
                token(name="Pebble Kite", symbol="PKIT", address="p1", description="Kids flying a pebble kite."),
                token(name="Pebble Kite Two", symbol="PKI2", address="p2"),
            ]), now=NOW)[0]
            queue = merge_queue({"items": []}, [idea], now=NOW)
            (root / "data" / "image_queue.json").write_text(json.dumps(queue))
            write_png(inbox / f"{idea['id']}.png", 1000, 1000)
            write_png(inbox / "tiny.png", 32, 32)
            (inbox / "notes.txt").write_text("ignore")
            result = import_images(inbox, root=root, publish=False)
            self.assertEqual(result["imported"], [idea["id"]])
            self.assertEqual(len(result["rejected"]), 1)
            saved = load_queue(root / "data" / "image_queue.json")
            self.assertEqual(saved["items"][0]["status"], "done")
            self.assertTrue((root / "images" / f"{idea['id']}.png").exists())
            self.assertFalse((root / "images" / "tiny.png").exists())


if __name__ == "__main__":
    unittest.main()

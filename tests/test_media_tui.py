import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils.media_name import parse_media_name
from differential.utils.media_search import MediaSearchResult
from differential.utils.media_tui import MediaSearchApp
from textual.widgets import Input


class FakeClient:
    def __init__(self):
        self.calls = []

    def search_parsed(
        self,
        parsed,
        limit=10,
        ptgen_source=None,
        ptgen_fields="title_aliases",
        search_hint="",
        search_query="",
    ):
        self.calls.append(
            {
                "limit": limit,
                "ptgen_source": ptgen_source,
                "ptgen_fields": ptgen_fields,
                "search_hint": search_hint,
                "search_query": search_query,
            }
        )
        return [
            MediaSearchResult(
                id="douban-35376457",
                kind="work",
                sources=["douban"],
                source_ids={"douban": "35376457"},
                titles=["爱情神话", "B for Busy"],
                year=2021,
            )
        ]


class MultiResultClient:
    def search_parsed(
        self,
        parsed,
        limit=10,
        ptgen_source=None,
        ptgen_fields="title_aliases",
        search_hint="",
        search_query="",
    ):
        return [
            MediaSearchResult(
                id="douban-1",
                kind="movie",
                sources=["douban"],
                source_ids={"douban": "1"},
                titles=["First"],
                year=2021,
            ),
            MediaSearchResult(
                id="douban-2",
                kind="movie",
                sources=["douban"],
                source_ids={"douban": "2"},
                titles=["Second"],
                year=2021,
            ),
        ]


class MediaSearchTuiTest(unittest.TestCase):
    def test_headless_app_selects_highlighted_result(self):
        async def autopilot(pilot):
            await pilot.pause()
            await pilot.press("enter")

        client = FakeClient()
        app = MediaSearchApp(
            parse_media_name("B.for.Busy.2021.1080p.WEB-DL.mkv"),
            client,
            ptgen_source="douban",
            search_hint="爱情神话",
        )

        result = app.run(headless=True, auto_pilot=autopilot)

        self.assertIsNotNone(result)
        self.assertEqual(result.id, "douban-35376457")
        self.assertEqual(client.calls[0]["search_query"], "B for Busy 爱情神话")
        self.assertEqual(client.calls[0]["ptgen_fields"], "title_aliases")
        self.assertEqual(client.calls[0]["search_hint"], "")

    def test_headless_app_live_searches_after_typing(self):
        async def autopilot(pilot):
            await pilot.pause()
            await pilot.press("/")
            pilot.app.query_one("#search", Input).value = "爱情神话"
            await pilot.pause(0.35)
            await pilot.press("enter")
            await pilot.press("enter")

        client = FakeClient()
        app = MediaSearchApp(
            parse_media_name("B.for.Busy.2021.1080p.WEB-DL.mkv"),
            client,
            ptgen_source="douban",
        )

        result = app.run(headless=True, auto_pilot=autopilot)

        self.assertIsNotNone(result)
        self.assertEqual(result.id, "douban-35376457")
        self.assertEqual(client.calls[-1]["search_query"], "爱情神话")

    def test_headless_app_uses_custom_ptgen_fields(self):
        async def autopilot(pilot):
            await pilot.pause()
            await pilot.press("enter")

        client = FakeClient()
        app = MediaSearchApp(
            parse_media_name("B.for.Busy.2021.1080p.WEB-DL.mkv"),
            client,
            ptgen_fields="all",
        )

        result = app.run(headless=True, auto_pilot=autopilot)

        self.assertIsNotNone(result)
        self.assertEqual(client.calls[0]["ptgen_fields"], "all")

    def test_headless_app_cycles_ptgen_fields(self):
        async def autopilot(pilot):
            await pilot.pause()
            await pilot.press("f")
            await pilot.press("enter")

        client = FakeClient()
        app = MediaSearchApp(
            parse_media_name("B.for.Busy.2021.1080p.WEB-DL.mkv"),
            client,
        )

        result = app.run(headless=True, auto_pilot=autopilot)

        self.assertIsNotNone(result)
        self.assertEqual(client.calls[-1]["ptgen_fields"], "people")

    def test_headless_app_seeds_search_with_chinese_candidate(self):
        async def autopilot(pilot):
            await pilot.pause()
            await pilot.press("enter")

        client = FakeClient()
        app = MediaSearchApp(
            parse_media_name("[两心不疑].No.Doubt.in.Us.2026.S01.Complete.1080p.WEB-DL.H265.AAC-UBWEB"),
            client,
            ptgen_source="douban",
        )

        result = app.run(headless=True, auto_pilot=autopilot)

        self.assertIsNotNone(result)
        self.assertEqual(client.calls[0]["search_query"], "两心不疑")

    def test_headless_app_arrow_down_selects_next_result(self):
        async def autopilot(pilot):
            await pilot.pause()
            await pilot.press("down")
            await pilot.press("enter")

        app = MediaSearchApp(
            parse_media_name("First.2021.1080p.WEB-DL.mkv"),
            MultiResultClient(),
        )

        result = app.run(headless=True, auto_pilot=autopilot)

        self.assertIsNotNone(result)
        self.assertEqual(result.id, "douban-2")


if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils.media_name import parse_media_name
from differential.utils.media_search import (
    DEFAULT_MEDIA_SEARCH_FIELDS,
    MediaSearchClient,
    MediaSearchError,
    MediaSearchResult,
    MediaSelectionError,
    auto_select_media_result,
    result_to_ptgen_reference,
    score_media_result,
)


class FakeResponse:
    ok = True
    reason = "OK"
    status_code = 200

    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(
            {
                "hits": [
                    {
                        "id": "douban-35376457",
                        "kind": "movie",
                        "source_ids": {"douban": "35376457"},
                        "titles": ["爱情神话", "B for Busy"],
                        "year": 2021,
                    }
                ]
            }
        )


class NativeExactSession:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        q = kwargs["params"]["q"]
        year = kwargs["params"].get("year")
        kind = kwargs["params"].get("kind")
        if q == "两心不疑" and year == 2026 and kind is None:
            hits = [
                {
                    "id": "douban-37227662",
                    "kind": "work",
                    "source_ids": {"douban": "37227662"},
                    "titles": ["两心不疑", "两不疑"],
                    "year": 2026,
                }
            ]
        else:
            hits = []
        return FakeResponse({"hits": hits})


class FailingSession:
    def get(self, url, **kwargs):
        raise requests.Timeout("forced timeout")


class EmptySession:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse({"hits": []})


class MediaSearchSelectionTest(unittest.TestCase):
    def test_search_parsed_appends_hint_and_restricts_ptgen_source(self):
        parsed = parse_media_name("B.for.Busy.2021.2160p.WEB-DL.H265-GROUP")
        session = FakeSession()
        client = MediaSearchClient("https://ptgen.test", session=session)

        results = client.search_parsed(
            parsed,
            limit=5,
            ptgen_source="douban",
            search_hint="爱情神话",
        )

        self.assertEqual(results[0].id, "douban-35376457")
        self.assertEqual(session.calls[0][0], "https://ptgen.test/api/search")
        self.assertEqual(
            session.calls[0][1]["params"],
            {
                "q": "B for Busy 爱情神话",
                "limit": 5,
                "offset": 0,
                "kind": "movie",
                "year": 2021,
                "source": "douban",
                "fields": DEFAULT_MEDIA_SEARCH_FIELDS,
            },
        )

    def test_search_parsed_search_query_overrides_title_and_hint(self):
        parsed = parse_media_name("B.for.Busy.2021.2160p.WEB-DL.H265-GROUP")
        session = FakeSession()
        client = MediaSearchClient("https://ptgen.test", session=session)

        client.search_parsed(
            parsed,
            limit=5,
            ptgen_source="douban",
            search_hint="ignored",
            search_query="爱情神话",
        )

        self.assertEqual(session.calls[0][1]["params"]["q"], "爱情神话")
        self.assertEqual(session.calls[0][1]["params"]["source"], "douban")
        self.assertEqual(session.calls[0][1]["params"]["fields"], DEFAULT_MEDIA_SEARCH_FIELDS)

    def test_search_parsed_accepts_ptgen_fields_override(self):
        parsed = parse_media_name("The.Matrix.1999.1080p.BluRay.x264-GROUP")
        session = FakeSession()
        client = MediaSearchClient("https://ptgen.test", session=session)

        client.search_parsed(parsed, limit=5, ptgen_fields="all")

        self.assertEqual(session.calls[0][1]["params"]["fields"], "all")

    def test_search_accepts_fields_for_direct_source_id_lookup(self):
        session = FakeSession()
        client = MediaSearchClient("https://ptgen.test", session=session)

        client.search("tt0133093", fields="source_ids")

        self.assertEqual(session.calls[0][1]["params"]["fields"], "source_ids")

    def test_search_rejects_unsupported_fields(self):
        client = MediaSearchClient("https://ptgen.test", session=FakeSession())

        with self.assertRaises(MediaSearchError):
            client.search("matrix", fields="bad_field")

    def test_search_parsed_tries_chinese_candidate_before_english_candidate(self):
        parsed = parse_media_name(
            "[两心不疑].No.Doubt.in.Us.2026.S01.Complete.1080p.WEB-DL.H265.AAC-UBWEB"
        )
        session = FakeSession()
        client = MediaSearchClient("https://ptgen.test", session=session)

        client.search_parsed(parsed, limit=5, ptgen_source="douban")

        queries = [call[1]["params"]["q"] for call in session.calls]
        self.assertEqual(queries[0], "两心不疑")
        self.assertIn("No Doubt in Us", queries)
        self.assertGreater(queries.index("No Doubt in Us"), queries.index("两心不疑"))

    def test_search_parsed_skips_bare_year_candidates(self):
        parsed = parse_media_name("Dr.STONE.S04.2025.1080p.CR.WEB-DL.H.264.AAC-FROGWeb")
        session = EmptySession()
        client = MediaSearchClient("https://ptgen.test", session=session)

        client.search_parsed(parsed, limit=5)

        queries = [call[1]["params"]["q"] for call in session.calls]
        self.assertIn("Dr. STONE", queries)
        self.assertNotIn("2025", queries)

    def test_search_parsed_stops_before_english_when_chinese_candidate_is_confident(self):
        parsed = parse_media_name(
            "[两心不疑].No.Doubt.in.Us.2026.S01.Complete.1080p.WEB-DL.H265.AAC-UBWEB"
        )
        session = NativeExactSession()
        client = MediaSearchClient("https://ptgen.test", session=session)

        results = client.search_parsed(parsed, limit=5, ptgen_source="douban")

        queries = [call[1]["params"]["q"] for call in session.calls]
        self.assertEqual(results[0].id, "douban-37227662")
        self.assertIn("两心不疑", queries)
        self.assertNotIn("No Doubt in Us", queries)

    def test_search_wraps_request_errors(self):
        client = MediaSearchClient("https://ptgen.test", session=FailingSession())

        with self.assertRaises(MediaSearchError):
            client.search("两心不疑", source="douban")

    def test_movie_reference_prefers_douban_linked_source_id(self):
        result = MediaSearchResult(
            id="imdb-tt0133093",
            kind="movie",
            sources=["imdb"],
            source_ids={"imdb": "tt0133093", "douban": "1291843"},
            titles=["The Matrix"],
            year=1999,
        )

        reference = result_to_ptgen_reference(result)

        self.assertEqual((reference.site, reference.sid), ("douban", "1291843"))
        self.assertEqual(reference.original_url, "https://movie.douban.com/subject/1291843/")

    def test_anime_reference_prefers_bangumi(self):
        result = MediaSearchResult(
            id="bangumi-81582",
            kind="anime",
            sources=["bangumi"],
            source_ids={"bangumi": "81582", "imdb": "tt0000001"},
            titles=["魔法のプリンセス"],
            year=1982,
        )

        reference = result_to_ptgen_reference(result)

        self.assertEqual((reference.site, reference.sid), ("bangumi", "81582"))

    def test_non_interactive_accepts_clear_exact_match(self):
        parsed = parse_media_name("The.Matrix.1999.1080p.BluRay.x264-GROUP")
        results = [
            MediaSearchResult(
                id="imdb-tt0133093",
                kind="movie",
                sources=["imdb"],
                source_ids={"imdb": "tt0133093", "douban": "1291843"},
                titles=["The Matrix"],
                year=1999,
                rating_votes=2_000_000,
            ),
            MediaSearchResult(
                id="imdb-tt0365467",
                kind="movie",
                sources=["imdb"],
                source_ids={"imdb": "tt0365467"},
                titles=["Making 'The Matrix'"],
                year=1999,
                rating_votes=14_000,
            ),
        ]

        selected = auto_select_media_result(results, parsed)

        self.assertEqual(selected.id, "imdb-tt0133093")

    def test_non_interactive_accepts_generic_work_kind_for_clear_douban_match(self):
        parsed = parse_media_name("[爱情神话].B.for.Busy.2021.2160p.WEB-DL.H265-GROUP")
        results = [
            MediaSearchResult(
                id="douban-35376457",
                kind="work",
                sources=["douban"],
                source_ids={"douban": "35376457", "imdb": "tt16606348"},
                titles=["爱情神话", "B for Busy"],
                year=2021,
                rating_votes=848_081,
            ),
            MediaSearchResult(
                id="douban-35172465",
                kind="work",
                sources=["douban"],
                source_ids={"douban": "35172465"},
                titles=["我的名字", "My Name"],
                year=2021,
                rating_votes=54_648,
            ),
        ]

        selected = auto_select_media_result(results, parsed)

        self.assertEqual(selected.id, "douban-35376457")

    def test_non_interactive_ignores_equivalent_linked_source_rows(self):
        parsed = parse_media_name("K-PAX.2001.1080p.BluRay.x264-GROUP")
        results = [
            MediaSearchResult(
                id="imdb-tt0272152",
                kind="movie",
                sources=["imdb"],
                source_ids={"imdb": "tt0272152", "douban": "1306607"},
                titles=["K-PAX"],
                year=2001,
                rating_votes=196_314,
            ),
            MediaSearchResult(
                id="douban-1306607",
                kind="movie",
                sources=["douban"],
                source_ids={"douban": "1306607", "imdb": "tt0272152"},
                titles=["K星异客", "K-PAX"],
                year=2001,
                rating_votes=102_859,
            ),
        ]

        selected = auto_select_media_result(results, parsed)

        self.assertEqual(selected.id, "imdb-tt0272152")

    def test_non_interactive_ignores_same_title_year_source_duplicates(self):
        parsed = parse_media_name("Cyberpunk.Edgerunners.S01.1080p.NF.WEB-DL.H.264-GROUP")
        results = [
            MediaSearchResult(
                id="imdb-tt12590266",
                kind="tv",
                source_ids={"imdb": "tt12590266"},
                titles=["Cyberpunk: Edgerunners"],
                year=2022,
                rating_votes=101_969,
            ),
            MediaSearchResult(
                id="bangumi-309311",
                kind="anime",
                source_ids={"bangumi": "309311"},
                titles=["Cyberpunk: Edgerunners", "赛博朋克：边缘行者"],
                year=2022,
                rating_votes=23_847,
            ),
        ]

        selected = auto_select_media_result(results, parsed)

        self.assertEqual(selected.id, "imdb-tt12590266")

    def test_bare_year_result_does_not_score_as_exact_title_match(self):
        parsed = parse_media_name("Dr.STONE.S04.2025.1080p.CR.WEB-DL.H.264.AAC-FROGWeb")
        result = MediaSearchResult(
            id="douban-37465949",
            kind="tv",
            source_ids={"douban": "37465949"},
            titles=["2025/26欧冠联赛", "2025"],
            year=2025,
            rating_votes=16,
        )

        self.assertLess(score_media_result(result, parsed), 80)

    def test_non_interactive_accepts_base_title_with_matching_season_marker(self):
        parsed = parse_media_name("巴比伦柏林S04.Babylon.Berlin.2022.1080p.Blu-ray.x265.AC3-GROUP")
        results = [
            MediaSearchResult(
                id="douban-34997761",
                kind="tv",
                source_ids={"douban": "34997761"},
                titles=["巴比伦柏林 第四季", "Babylon Berlin Season 4"],
                year=2022,
                rating_votes=6196,
            )
        ]

        selected = auto_select_media_result(results, parsed)

        self.assertEqual(selected.id, "douban-34997761")

    def test_season_mismatch_penalizes_other_seasons(self):
        parsed = parse_media_name("Babylon.Berlin.S04.2022.1080p.WEB-DL.H264-GROUP")
        result = MediaSearchResult(
            id="douban-27016555",
            kind="tv",
            source_ids={"douban": "27016555"},
            titles=["Babylon Berlin Season 2"],
            year=2022,
        )

        self.assertLess(score_media_result(result, parsed), 80)

    def test_non_interactive_rejects_ambiguous_exact_matches(self):
        parsed = parse_media_name("Love.2015.1080p.BluRay.x264-GROUP")
        results = [
            MediaSearchResult(
                id="imdb-tt001",
                kind="movie",
                sources=["imdb"],
                source_ids={"imdb": "tt001"},
                titles=["Love"],
                year=2015,
            ),
            MediaSearchResult(
                id="imdb-tt002",
                kind="movie",
                sources=["imdb"],
                source_ids={"imdb": "tt002"},
                titles=["Love"],
                year=2015,
            ),
        ]

        with self.assertRaises(MediaSelectionError):
            auto_select_media_result(results, parsed)


if __name__ == "__main__":
    unittest.main()

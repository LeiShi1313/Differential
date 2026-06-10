import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils.ptgen.douban import DoubanData
from differential.utils.ptgen.formatter import build_ptgen_format
from differential.utils.ptgen.imdb import IMDBData
from differential.utils.ptgen.providers import (
    ApiPtGenProvider,
    DEFAULT_PTGEN_PROVIDERS,
    PTGenProviderError,
    StaticPtGenProvider,
)
from differential.utils.ptgen.reference import PTGenReference, parse_ptgen_reference
from differential.utils.ptgen_handler import PTGenHandler, normalize_ptgen_payload


class FakeResponse:
    def __init__(self, data, ok=True, status_code=200, reason="OK"):
        self._data = data
        self.ok = ok
        self.status_code = status_code
        self.reason = reason

    def json(self):
        return self._data


class InvalidJsonResponse(FakeResponse):
    def json(self):
        raise ValueError("bad json")


class FakeSession:
    def __init__(self, data):
        self.data = data
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.data)


class FailingProvider:
    name = "failing"

    def fetch(self, reference, session, timeout):
        raise PTGenProviderError("forced failure")


class MappingProvider:
    name = "mapping"

    def __init__(self, payloads):
        self.payloads = payloads
        self.references = []

    def fetch(self, reference, session, timeout):
        self.references.append(reference)
        key = (reference.site, reference.sid)
        if key not in self.payloads:
            raise PTGenProviderError(f"missing {key}")
        return self.payloads[key]


class PTGenProviderTest(unittest.TestCase):
    def test_reference_parser_supports_archive_sites(self):
        cases = {
            "https://movie.douban.com/subject/1292052/": ("douban", "1292052"),
            "https://movie.douban.com/celebrity/1054521/": ("douban_celebrity", "1054521"),
            "https://www.douban.com/personage/27205857/": ("douban_personage", "27205857"),
            "https://www.imdb.com/title/tt0111161/": ("imdb", "tt0111161"),
            "https://bgm.tv/subject/81582": ("bangumi", "81582"),
            "https://store.steampowered.com/app/252950/Rocket_League/": ("steam", "252950"),
            "https://indienova.com/game/my-hidden-things": ("indienova", "my-hidden-things"),
            "https://www.epicgames.com/store/zh-CN/product/control/home": ("epic", "control"),
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                reference = parse_ptgen_reference(url)
                self.assertIsNotNone(reference)
                self.assertEqual((reference.site, reference.sid), expected)

    def test_static_provider_builds_archive_url(self):
        provider = StaticPtGenProvider("static", "https://example.test/ptgen")
        reference = PTGenReference("douban", "1292052", "")
        self.assertEqual(
            provider.url_for(reference),
            "https://example.test/ptgen/douban/1292052.json",
        )

    def test_default_provider_order_is_static_static_api(self):
        self.assertEqual(
            [provider.name for provider in DEFAULT_PTGEN_PROVIDERS],
            ["ourhelp-cdn", "github-pages", "ourhelp-api"],
        )
        self.assertEqual(
            DEFAULT_PTGEN_PROVIDERS[0].base_url,
            "https://cdn.ourhelp.club/ptgen",
        )
        self.assertEqual(
            DEFAULT_PTGEN_PROVIDERS[1].base_url,
            "https://ourbits.github.io/PtGen",
        )
        self.assertEqual(
            DEFAULT_PTGEN_PROVIDERS[2].base_url,
            "https://api.ourhelp.club/infogen",
        )

    def test_api_provider_sends_site_and_sid(self):
        provider = ApiPtGenProvider("api", "https://example.test/infogen")
        session = FakeSession({"site": "imdb", "sid": "tt0111161"})
        reference = PTGenReference("imdb", "tt0111161", "")

        provider.fetch(reference, session, 5)

        self.assertEqual(session.calls[0][0], "https://example.test/infogen")
        self.assertEqual(
            session.calls[0][1]["params"],
            {"site": "imdb", "sid": "tt0111161"},
        )

    def test_normalize_static_payload_sets_success_and_format(self):
        reference = PTGenReference("imdb", "tt0111161", "")
        payload = normalize_ptgen_payload(
            {
                "site": "imdb",
                "sid": "tt0111161",
                "name": "The Shawshank Redemption",
                "description": "A banker keeps hope alive.",
            },
            reference,
        )

        self.assertTrue(payload["success"])
        self.assertIn("Title: The Shawshank Redemption", payload["format"])
        self.assertIn("Introduction", payload["format"])

    def test_normalize_preserves_api_format(self):
        reference = PTGenReference("douban", "1292052", "")
        payload = normalize_ptgen_payload(
            {
                "site": "douban",
                "sid": "1292052",
                "success": True,
                "format": "remote format",
            },
            reference,
        )
        self.assertEqual(payload["format"], "remote format")

    def test_normalize_rejects_provider_failures(self):
        reference = PTGenReference("imdb", "tt0111161", "")
        with self.assertRaises(PTGenProviderError):
            normalize_ptgen_payload(
                {"site": "douban", "sid": "1292052"},
                reference,
            )
        with self.assertRaises(PTGenProviderError):
            normalize_ptgen_payload(
                {"site": "imdb", "sid": "tt0111161", "success": False, "error": "nope"},
                reference,
            )

    def test_provider_rejects_invalid_and_non_object_json(self):
        provider = StaticPtGenProvider("static", "https://example.test/ptgen")
        reference = PTGenReference("imdb", "tt0111161", "")

        invalid_session = FakeSession({})
        invalid_session.get = lambda *args, **kwargs: InvalidJsonResponse({})
        with self.assertRaises(PTGenProviderError):
            provider.fetch(reference, invalid_session, 5)

        non_object_session = FakeSession(["not", "object"])
        with self.assertRaises(PTGenProviderError):
            provider.fetch(reference, non_object_session, 5)

    def test_handler_falls_back_to_next_provider(self):
        provider = MappingProvider(
            {
                ("imdb", "tt0111161"): {
                    "site": "imdb",
                    "sid": "tt0111161",
                    "name": "The Shawshank Redemption",
                    "description": "A banker keeps hope alive.",
                }
            }
        )
        handler = PTGenHandler(
            "https://www.imdb.com/title/tt0111161/",
            providers=[FailingProvider(), provider],
        )

        ptgen, douban, imdb = handler.fetch_ptgen_info()

        self.assertIsInstance(ptgen, IMDBData)
        self.assertIsNone(douban)
        self.assertIsInstance(imdb, IMDBData)
        self.assertEqual(provider.references[0].site, "imdb")

    def test_handler_fetches_selected_reference_directly(self):
        provider = MappingProvider(
            {
                ("imdb", "tt0111161"): {
                    "site": "imdb",
                    "sid": "tt0111161",
                    "name": "The Shawshank Redemption",
                    "description": "A banker keeps hope alive.",
                }
            }
        )
        reference = PTGenReference(
            site="imdb",
            sid="tt0111161",
            original_url="https://www.imdb.com/title/tt0111161/",
        )
        handler = PTGenHandler("", providers=[provider])

        ptgen, douban, imdb = handler.fetch_ptgen_reference(reference)

        self.assertIsInstance(ptgen, IMDBData)
        self.assertIsNone(douban)
        self.assertIsInstance(imdb, IMDBData)
        self.assertEqual(handler.url, reference.original_url)
        self.assertEqual(provider.references[0], reference)

    def test_handler_supports_api_only_douban_personage_after_static_failures(self):
        provider = MappingProvider(
            {
                ("douban_personage", "27205857"): {
                    "site": "douban_personage",
                    "sid": "27205857",
                    "name": "Personage",
                    "introduction": "Biography",
                }
            }
        )
        handler = PTGenHandler(
            "https://www.douban.com/personage/27205857/",
            providers=[FailingProvider(), FailingProvider(), provider],
        )

        ptgen, douban, imdb = handler.fetch_ptgen_info()

        self.assertTrue(ptgen.success)
        self.assertEqual(ptgen.site, "douban_personage")
        self.assertIn("Personage", ptgen.format)
        self.assertIsNone(douban)
        self.assertIsNone(imdb)

    def test_handler_fetches_imdb_for_douban_payload(self):
        provider = MappingProvider(
            {
                ("douban", "1292052"): {
                    "site": "douban",
                    "sid": "1292052",
                    "chinese_title": "肖申克的救赎",
                    "foreign_title": "The Shawshank Redemption",
                    "imdb_link": "https://www.imdb.com/title/tt0111161/",
                },
                ("imdb", "tt0111161"): {
                    "site": "imdb",
                    "sid": "tt0111161",
                    "name": "The Shawshank Redemption",
                },
            }
        )
        handler = PTGenHandler(
            "https://movie.douban.com/subject/1292052/",
            providers=[provider],
        )

        ptgen, douban, imdb = handler.fetch_ptgen_info()

        self.assertIsInstance(ptgen, DoubanData)
        self.assertIsInstance(douban, DoubanData)
        self.assertIsInstance(imdb, IMDBData)
        self.assertEqual(
            [(ref.site, ref.sid) for ref in provider.references],
            [("douban", "1292052"), ("imdb", "tt0111161")],
        )

    def test_format_builder_has_output_for_each_supported_static_site(self):
        payloads = [
            {"site": "douban", "sid": "1292052", "chinese_title": "肖申克的救赎", "introduction": "简介"},
            {"site": "imdb", "sid": "tt0111161", "name": "The Shawshank Redemption", "description": "Intro"},
            {
                "site": "steam",
                "sid": "252950",
                "cover": "https://example.test/steam.jpg",
                "name": "Rocket League",
                "name_chs": "火箭联盟",
                "detail": "名称: Rocket League\n类型: 动作",
                "review": ["最近评测: 好评"],
                "descr": "Game intro",
                "sysreq": ["Windows\n最低配置:\n内存: 4 GB RAM"],
            },
            {
                "site": "epic",
                "sid": "control",
                "logo": "https://example.test/epic.png",
                "name": "Control",
                "desc": "![Banner Image] (https://example.test/banner.jpg)\n\nGame intro",
                "min_req": {"Windows": ["Memory: 8 GB"]},
            },
            {
                "site": "bangumi",
                "sid": "81582",
                "cover": "https://example.test/bangumi.jpg",
                "name": "魔法のプリンセス",
                "name_cn": "魔法公主明琪桃子",
                "rating": {"score": 7.8, "total": 21},
                "staff": [{"key": "导演", "value": "湯山邦彦"}],
                "cast": [{"name": "ミンキーモモ", "actors": [{"name": "林原めぐみ"}]}],
                "story": "Story",
            },
            {
                "site": "indienova",
                "sid": "my-hidden-things",
                "cover": "https://example.test/indienova.jpg",
                "chinese_title": "我藏起来的东西",
                "english_title": "My hidden things",
                "links": {"Steam": "https://store.steampowered.com/app/1304910/"},
                "descr": "Game intro",
            },
            {
                "site": "douban_celebrity",
                "sid": "1054521",
                "name_full": "Person Name",
                "birth_date": "1962年1月23日",
                "roles": ["演员"],
                "imdb_id": "nm0000001",
                "introduction": "Bio",
            },
            {
                "site": "douban_personage",
                "sid": "27205857",
                "name_full": "Personage Name",
                "gender": "女",
                "personage_link": "https://www.douban.com/personage/27205857/",
                "introduction": "Bio",
            },
        ]
        for payload in payloads:
            with self.subTest(site=payload["site"]):
                rendered = build_ptgen_format(payload)
                self.assertTrue(rendered)
                self.assertNotIn("None", rendered)

    def test_format_builder_uses_cfworker_style_sections(self):
        cases = [
            (
                "douban",
                {
                    "site": "douban",
                    "sid": "1292052",
                    "chinese_title": "肖申克的救赎",
                    "tags": ["剧情", "犯罪"],
                    "cast": [{"name": "蒂姆·罗宾斯"}, {"name": "摩根·弗里曼"}],
                    "introduction": "第一行\n第二行",
                },
                ["◎标　　签　剧情 | 犯罪", "◎主　　演　蒂姆·罗宾斯", "　　第二行"],
            ),
            (
                "steam",
                {
                    "site": "steam",
                    "sid": "252950",
                    "steam_id": "252950",
                    "name_chs": "火箭联盟",
                    "language": ["英语", "法语"],
                    "tags": ["多人", "足球"],
                    "screenshot": ["https://example.test/shot.jpg"],
                },
                ["【基本信息】", "游戏语种: 英语 | 法语", "标签: 多人 | 足球", "【游戏截图】"],
            ),
            (
                "bangumi",
                {
                    "site": "bangumi",
                    "sid": "81582",
                    "story": "Story",
                    "staff": [{"key": "导演", "value": "湯山邦彦"}],
                    "cast": [{"name": "ミンキーモモ", "actors": [{"name": "林原めぐみ"}]}],
                    "alt": "https://bgm.tv/subject/81582",
                },
                ["[b]Story: [/b]", "[b]Staff: [/b]", "[b]Cast: [/b]", "(来源于 https://bgm.tv/subject/81582 )"],
            ),
            (
                "indienova",
                {
                    "site": "indienova",
                    "sid": "my-hidden-things",
                    "chinese_title": "我藏起来的东西",
                    "links": {"Steam": "https://store.steampowered.com/app/1304910/"},
                    "price": ["Steam：￥35.00"],
                    "level": ["https://example.test/rating.png"],
                },
                ["中文名称：我藏起来的东西", "[url=https://store.steampowered.com/app/1304910/]Steam[/url]", "价格信息：Steam：￥35.00", "【游戏评级】"],
            ),
            (
                "epic",
                {
                    "site": "epic",
                    "sid": "control",
                    "logo": "https://example.test/logo.png",
                    "name": "Control",
                    "language": ["英语", "法语"],
                    "min_req": {"Windows": ["Memory: 8 GB"]},
                    "level": ["https://example.test/rating.png"],
                },
                ["游戏名称：Control", "【支持语言】", "Windows\nMemory: 8 GB", "【游戏评级】"],
            ),
        ]
        for site, payload, expected_parts in cases:
            with self.subTest(site=site):
                rendered = build_ptgen_format(payload)
                for expected in expected_parts:
                    self.assertIn(expected, rendered)

    def test_person_format_includes_person_fields(self):
        rendered = build_ptgen_format(
            {
                "site": "douban_celebrity",
                "sid": "1105626",
                "name_full": "彼得·科赫 Peter Koch",
                "gender": "男",
                "birth_date": "1962年1月23日",
                "birth_place": "美国,纽约,纳苏郡",
                "roles": ["演员"],
                "imdb_id": "nm0462387",
                "celebrity_link": "https://movie.douban.com/celebrity/1105626",
                "personage_link": "https://www.douban.com/personage/27311439/",
                "introduction": "暂无",
            }
        )

        self.assertIn("姓名: 彼得·科赫 Peter Koch", rendered)
        self.assertIn("出生日期: 1962年1月23日", rendered)
        self.assertIn("IMDb链接: https://www.imdb.com/name/nm0462387/", rendered)


if __name__ == "__main__":
    unittest.main()

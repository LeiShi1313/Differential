import re
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional


def build_ptgen_format(data: Mapping[str, Any]) -> str:
    current_format = _clean_text(data.get("format"))
    if current_format:
        return current_format

    formatter = _FORMATTERS.get(_clean_text(data.get("site")), _format_generic)
    rendered = formatter(data).strip()
    if rendered:
        return rendered
    return _format_generic(data).strip()


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _first_text(*values: Any) -> str:
    for value in values:
        text = _clean_text(value)
        if text:
            return text
    return ""


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _join(value: Any, sep: str = " / ") -> str:
    parts: List[str] = []
    seen = set()
    for item in _as_list(value):
        text = _clean_text(item)
        if text and text not in seen:
            parts.append(text)
            seen.add(text)
    return sep.join(parts)


def _people(value: Any, limit: Optional[int] = None) -> str:
    names: List[str] = []
    for item in _as_list(value):
        if isinstance(item, dict):
            name = _first_text(item.get("name"), item.get("value"), item.get("title"))
        else:
            name = _clean_text(item)
        if name:
            names.append(name)
    if limit:
        names = names[:limit]
    return " / ".join(names)


def _people_multiline(value: Any) -> str:
    names = _people(value).split(" / ")
    names = [name for name in names if name]
    if not names:
        return ""
    return ("\n" + "　" * 4 + "  　").join(names).strip()


def _field(lines: List[str], label: str, value: Any) -> None:
    text = _join(value) if isinstance(value, (list, tuple)) else _clean_text(value)
    if text:
        lines.append(f"{label}{text}")


def _section(lines: List[str], title: str, body: Any) -> None:
    body_text = _block_text(body)
    if not body_text:
        return
    lines.extend(["", title, "", body_text])


def _block_text(value: Any) -> str:
    if isinstance(value, dict):
        return "\n".join(_dict_lines(value))
    if isinstance(value, (list, tuple)):
        return "\n".join(_clean_text(v) for v in value if _clean_text(v))
    return _clean_text(value)


def _dict_lines(value: Mapping[str, Any]) -> List[str]:
    lines: List[str] = []
    for key, item in value.items():
        if isinstance(item, (list, tuple)):
            item_text = "\n".join(_clean_text(i) for i in item if _clean_text(i))
            if item_text:
                lines.append(f"{key}\n{item_text}")
        else:
            item_text = _clean_text(item)
            if item_text:
                lines.append(f"{key}: {item_text}")
    return lines


def _image(data: Mapping[str, Any]) -> str:
    url = _first_text(data.get("poster"), data.get("cover"), data.get("logo"))
    return f"[img]{url}[/img]" if url else ""


def _start_lines(data: Mapping[str, Any]) -> List[str]:
    image = _image(data)
    return [image, ""] if image else []


def _start_lines_with_url(url: str) -> List[str]:
    text = _clean_text(url)
    return [f"[img]{text}[/img]", ""] if text else []


def _indent_text(value: str, prefix: str) -> str:
    return _clean_text(value).replace("\n", "\n" + prefix)


def _rating(average: Any, votes: Any) -> str:
    avg = _clean_text(average)
    vote_count = _clean_text(votes)
    if avg and vote_count:
        return f"{avg}/10 from {vote_count} users"
    return avg


def _format_douban(data: Mapping[str, Any]) -> str:
    lines = _start_lines(data)
    sid = _clean_text(data.get("sid"))
    trans_title = _join(
        [
            data.get("chinese_title"),
            *_as_list(data.get("trans_title")),
            *_as_list(data.get("aka")),
        ]
    )
    douban_link = _first_text(
        data.get("douban_link"),
        f"https://movie.douban.com/subject/{sid}/" if sid else "",
    )
    _field(lines, "◎译　　名　", trans_title)
    _field(lines, "◎片　　名　", _first_text(data.get("foreign_title"), _join(data.get("this_title"))))
    _field(lines, "◎年　　代　", data.get("year"))
    _field(lines, "◎产　　地　", data.get("region"))
    _field(lines, "◎类　　别　", data.get("genre"))
    _field(lines, "◎语　　言　", data.get("language"))
    _field(lines, "◎上映日期　", data.get("playdate"))
    _field(
        lines,
        "◎IMDb评分  ",
        _first_text(
            data.get("imdb_rating"),
            _rating(data.get("imdb_rating_average"), data.get("imdb_votes")),
        ),
    )
    _field(lines, "◎IMDb链接  ", data.get("imdb_link"))
    _field(
        lines,
        "◎豆瓣评分　",
        _first_text(
            data.get("douban_rating"),
            _rating(data.get("douban_rating_average"), data.get("douban_votes")),
        ),
    )
    _field(lines, "◎豆瓣链接　", douban_link)
    _field(lines, "◎集　　数　", data.get("episodes"))
    _field(lines, "◎片　　长　", data.get("duration"))
    _field(lines, "◎导　　演　", _people(data.get("director")))
    _field(lines, "◎编　　剧　", _people(data.get("writer")))
    _field(lines, "◎主　　演　", _people_multiline(data.get("cast")))
    tags = _join(data.get("tags"), sep=" | ")
    if tags:
        lines.extend(["", f"◎标　　签　{tags}"])
    introduction = _clean_text(data.get("introduction"))
    if introduction:
        lines.extend(["", "◎简　　介", "", f"　　{_indent_text(introduction, '　　')}"])
    awards = _clean_text(data.get("awards"))
    if awards:
        lines.extend(["", "◎获奖情况", "", f"　　{_indent_text(awards, '　　')}"])
    return "\n".join(lines)


def _format_imdb(data: Mapping[str, Any]) -> str:
    lines = _start_lines(data)
    sid = _clean_text(data.get("sid"))
    _field(lines, "Title: ", data.get("name"))
    _field(lines, "Keywords: ", data.get("keywords"))
    _field(lines, "Date Published: ", data.get("datePublished"))
    _field(
        lines,
        "IMDb Rating: ",
        _first_text(
            data.get("imdb_rating"),
            _rating(data.get("imdb_rating_average"), data.get("imdb_votes")),
        ),
    )
    _field(
        lines,
        "IMDb Link: ",
        _first_text(data.get("imdb_link"), f"https://www.imdb.com/title/{sid}/" if sid else ""),
    )
    _field(lines, "Directors: ", _people(data.get("directors")))
    _field(lines, "Creators: ", _people(data.get("creators")))
    _field(lines, "Actors: ", _people(data.get("actors")))
    description = _clean_text(data.get("description"))
    if description:
        lines.extend(["", "Introduction", f"    {_indent_text(description, '　　')}"])
    return "\n".join(lines)


def _format_steam(data: Mapping[str, Any]) -> str:
    lines = _start_lines(data)
    lines.extend(["【基本信息】", ""])
    _field(lines, "中文名: ", data.get("name_chs"))
    detail = _clean_text(data.get("detail"))
    if detail:
        lines.append(detail)
    _field(lines, "官方网站: ", data.get("linkbar"))
    steam_page = _first_text(
        data.get("steam_link"),
        f"https://store.steampowered.com/app/{data.get('steam_id')}/" if data.get("steam_id") else "",
    )
    _field(lines, "Steam页面: ", steam_page)
    _field(lines, "游戏语种: ", _join(data.get("language"), sep=" | "))
    _field(lines, "标签: ", _join(data.get("tags"), sep=" | "))
    reviews = _block_text(data.get("review"))
    if reviews:
        lines.extend(["", reviews])
    lines.append("")
    descr = _clean_text(data.get("descr"))
    if descr:
        lines.extend(["【游戏简介】", "", descr, ""])
    sysreq = _block_text(data.get("sysreq"))
    if sysreq:
        lines.extend(["【配置需求】", "", sysreq, ""])
    screenshots = _image_list(data.get("screenshot"))
    if screenshots:
        lines.extend(["【游戏截图】", "", "\n".join(screenshots), ""])
    return "\n".join(lines).strip()


def _format_epic(data: Mapping[str, Any]) -> str:
    lines = _start_lines_with_url(_first_text(data.get("logo"), data.get("poster"), data.get("cover")))
    lines.extend(["【基本信息】", ""])
    _field(lines, "游戏名称：", data.get("name"))
    _field(lines, "商店链接：", data.get("epic_link"))
    lines.append("")
    language = _block_text(data.get("language"))
    if language:
        lines.extend(["【支持语言】", "", language, ""])
    desc = _markdown_images_to_bbcode(data.get("desc"))
    if desc:
        lines.extend(["【游戏简介】", "", desc, ""])
    for key, title in (("min_req", "【最低配置】"), ("max_req", "【推荐配置】")):
        req_text = _requirement_text(data.get(key))
        if req_text:
            lines.extend([title, "", req_text, ""])
    screenshots = _image_list(data.get("screenshot"))
    if screenshots:
        lines.extend(["【游戏截图】", "", "\n".join(screenshots), ""])
    levels = _image_list(data.get("level"))
    if levels:
        lines.extend(["【游戏评级】", "", "\n".join(levels), ""])
    return "\n".join(lines).strip()


def _format_bangumi(data: Mapping[str, Any]) -> str:
    lines = _start_lines(data)
    story = _clean_text(data.get("story"))
    if story:
        lines.extend(["[b]Story: [/b]", "", story, ""])
    staff = _key_value_list(data.get("staff"))[:15]
    if staff:
        lines.extend(["[b]Staff: [/b]", "", "\n".join(staff), ""])
    cast = _bangumi_cast(data.get("cast"))[:9]
    if cast:
        lines.extend(["[b]Cast: [/b]", "", "\n".join(cast), ""])
    alt = _clean_text(data.get("alt"))
    if alt:
        lines.append(f"(来源于 {alt} )")
    return "\n".join(lines).strip()


def _format_indienova(data: Mapping[str, Any]) -> str:
    lines = _start_lines_with_url(_first_text(data.get("cover"), data.get("poster")))
    lines.extend(["【基本信息】", ""])
    _field(lines, "中文名称：", data.get("chinese_title"))
    _field(lines, "英文名称：", data.get("english_title"))
    _field(lines, "其他名称：", data.get("another_title"))
    _field(lines, "发行时间：", data.get("release_date"))
    _field(lines, "评分：", data.get("rate"))
    _field(lines, "开发商：", _join(data.get("dev")))
    _field(lines, "发行商：", _join(data.get("pub")))
    intro_detail = _block_text(data.get("intro_detail"))
    if intro_detail:
        lines.append(intro_detail)
    tags = _join(_as_list(data.get("cat"))[:8], sep=" | ")
    _field(lines, "标签：", tags)
    links = _links_text(data.get("links"))
    if links:
        lines.append(f"链接地址：{links}")
    price = _join(data.get("price"))
    _field(lines, "价格信息：", price)
    lines.append("")
    descr = _clean_text(data.get("descr"))
    if descr:
        lines.extend(["【游戏简介】", "", descr, ""])
    screenshots = _image_list(data.get("screenshot"))
    if screenshots:
        lines.extend(["【游戏截图】", "", "\n".join(screenshots), ""])
    levels = _image_list(data.get("level"))
    if levels:
        lines.extend(["【游戏评级】", "", "\n".join(levels), ""])
    return "\n".join(lines).strip()


def _format_douban_person(data: Mapping[str, Any]) -> str:
    lines = _start_lines(data)
    imdb_id = _clean_text(data.get("imdb_id"))
    name = _first_text(data.get("name_full"), _join([data.get("name"), data.get("name_en")]), data.get("name"))
    _field(lines, "姓名: ", name)
    _field(lines, "更多中文名: ", data.get("name_more_cn"))
    _field(lines, "更多外文名: ", data.get("name_more_other"))
    _field(lines, "性别: ", data.get("gender"))
    _field(lines, "出生日期: ", data.get("birth_date"))
    _field(lines, "出生地: ", data.get("birth_place"))
    _field(lines, "职业: ", data.get("roles"))
    _field(lines, "IMDb编号: ", imdb_id)
    _field(lines, "IMDb链接: ", f"https://www.imdb.com/name/{imdb_id}/" if imdb_id else "")
    _field(lines, "豆瓣影人: ", data.get("celebrity_link"))
    _field(lines, "豆瓣人物: ", data.get("personage_link"))
    _section(lines, "简介", data.get("introduction"))
    _section(lines, "获奖情况", _person_awards(data.get("awards")))
    _section(lines, "近期作品", _movie_titles(data.get("last_movies")))
    return "\n".join(lines)


def _format_generic(data: Mapping[str, Any]) -> str:
    lines = _start_lines(data)
    _field(
        lines,
        "Title: ",
        _first_text(
            data.get("chinese_title"),
            data.get("name_cn"),
            data.get("name_chs"),
            data.get("name"),
            data.get("foreign_title"),
            data.get("sid"),
        ),
    )
    _field(lines, "Site: ", data.get("site"))
    _field(lines, "ID: ", data.get("sid"))
    for key in ("douban_link", "imdb_link", "steam_link", "epic_link", "alt"):
        _field(lines, f"{key}: ", data.get(key))
    _section(
        lines,
        "Introduction",
        _first_text(
            data.get("introduction"),
            data.get("description"),
            data.get("descr"),
            data.get("desc"),
            data.get("story"),
            data.get("intro"),
        ),
    )
    return "\n".join(lines)


def _image_list(value: Any) -> List[str]:
    return [f"[img]{url}[/img]" for url in _as_text_iter(value)]


def _as_text_iter(value: Any) -> Iterable[str]:
    for item in _as_list(value):
        text = _clean_text(item)
        if text:
            yield text


def _markdown_images_to_bbcode(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    # Handle the simple image syntax seen in the Epic archive without pulling in markdown.
    return re.sub(r"!\[[^\]]*\]\s*\(([^)]+)\)", r"[img]\1[/img]", text, count=1)


def _links_text(value: Any) -> str:
    if not isinstance(value, Mapping):
        return _join(value, sep="  ")
    links: List[str] = []
    for key, link in value.items():
        link_text = _clean_text(link)
        key_text = _clean_text(key)
        if key_text and link_text:
            links.append(f"[url={link_text}]{key_text}[/url]")
    return "  ".join(links)


def _requirement_text(value: Any) -> str:
    if not isinstance(value, Mapping):
        return _block_text(value)

    lines: List[str] = []
    for system, requirements in value.items():
        req_text = _block_text(requirements)
        if req_text:
            lines.append(f"{system}\n{req_text}")
    return "\n".join(lines)


def _key_value_list(value: Any) -> List[str]:
    lines: List[str] = []
    for item in _as_list(value):
        if isinstance(item, dict):
            line = _first_text(item.get("key"))
            item_value = _clean_text(item.get("value"))
            if line and item_value:
                lines.append(f"{line}: {item_value}")
            elif item_value:
                lines.append(item_value)
        else:
            text = _clean_text(item)
            if text:
                lines.append(text)
    return lines


def _bangumi_rating(value: Any) -> str:
    if not isinstance(value, dict):
        return _clean_text(value)
    score = _clean_text(value.get("score"))
    total = _clean_text(value.get("total"))
    if score and total:
        return f"{score}/10 from {total} users"
    return score


def _bangumi_cast(value: Any) -> List[str]:
    lines: List[str] = []
    for item in _as_list(value):
        if not isinstance(item, dict):
            text = _clean_text(item)
            if text:
                lines.append(text)
            continue

        name = _clean_text(item.get("name"))
        actors = _people(item.get("actors"))
        relation = _clean_text(item.get("relation"))
        chunks = [chunk for chunk in (name, actors, relation) if chunk]
        if chunks:
            lines.append(" / ".join(chunks))
    return lines


def _person_awards(value: Any) -> List[str]:
    lines: List[str] = []
    for item in _as_list(value):
        if isinstance(item, dict):
            text = _join([item.get("year"), item.get("title"), item.get("award"), item.get("result")])
        else:
            text = _clean_text(item)
        if text:
            lines.append(text)
    return lines


def _movie_titles(value: Any) -> List[str]:
    lines: List[str] = []
    for item in _as_list(value):
        if isinstance(item, dict):
            title = _clean_text(item.get("title"))
            year = _clean_text(item.get("year"))
            if title and year:
                lines.append(f"{title} ({year})")
            elif title:
                lines.append(title)
        else:
            text = _clean_text(item)
            if text:
                lines.append(text)
    return lines


_FORMATTERS: Dict[str, Callable[[Mapping[str, Any]], str]] = {
    "douban": _format_douban,
    "douban_celebrity": _format_douban_person,
    "douban_personage": _format_douban_person,
    "imdb": _format_imdb,
    "steam": _format_steam,
    "epic": _format_epic,
    "bangumi": _format_bangumi,
    "indienova": _format_indienova,
}

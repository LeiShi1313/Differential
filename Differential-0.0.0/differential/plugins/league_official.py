import string
import argparse

from differential.plugins.lemonhd import LemonHD
from differential.utils.mediainfo import get_track_attr, get_track_attrs


GROUP_QUOTES = {
    'LeagueTV': """
[quote][font=方正粗黑宋简体][size=5][color=Red][b]LeagueTV[/b][/color]高清电视录制小组出品！
[color=blue]本小组接受求片
内地 & 港台电视台 剧集、 电影、 纪录片等
有需求的会员请移步[url=https://lemonhd.org/forums.php?action=viewtopic&forumid=8&topicid=4255]LeagueTV 求片区[/url]跟帖[/size][/font][/quote]

""",
    'LeagueWEB': """
[quote][font=方正粗黑宋简体][size=5][color=Red][b]LeagueWEB[/b][/color]小组出品！
[color=blue]本小组接受求片
内地网络视频平台的 剧集、电影、纪录片等
有需求的会员请移步[url=https://lemonhd.org/forums.php?action=viewtopic&forumid=8&topicid=4557]LeagueWEB应求专用贴[/url]跟帖[/size][/font][/quote]

""",
    'LeagueNF': """
[quote][font=方正粗黑宋简体][size=5][color=Red][b]LeagueNF[/b][/color]小组出品！
[color=blue]本小组接受求片
Netflix流媒体平台 剧集、电影、纪录片、动漫等
有需求的会员请移步[url=https://lemonhd.org/forums.php?action=viewtopic&forumid=8&topicid=4622]LeagueNF小组应求专用贴[/url]跟帖[/size][/font][/quote]

"""
}

class LeagueOfficial(LemonHD):

    @classmethod
    def get_help(cls):
        return 'LeagueOfficial插件，适用于LeagueTV/LeagueWeb/LeagueNF官组电影及电视剧上传'

    @classmethod
    def add_parser(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        super().add_parser(parser)
        parser.add_argument('--source-name', type=str, help='资源来源，HDTV/WEB-DL等', default=argparse.SUPPRESS)
        parser.add_argument('--uploader', type=str, help="发布者者名字，默认Anonymous", default=argparse.SUPPRESS)
        parser.add_argument('--team', type=str, help="官组名，LeagueTV/LeagueWeb/LeagueNF等等", default=argparse.SUPPRESS)
        return parser

    def __init__(self, folder: str, url: str, source_name: str, team: str, uploader: str = "Anonymous", **kwargs):
        super().__init__(folder, url, **kwargs)
        self.team = team
        self.uploader = uploader
        self.source_name = source_name

    @property
    def subtitle(self):
        if not self._ptgen.get("site") == "douban":
            return ""
        subtitle = f"{'/'.join(self._ptgen.get('this_title', []) + self._ptgen.get('aka', []))} "
        if self._ptgen.get('cast'):
            subtitle += f"[主演: {'/'.join([c.get('name').strip(string.ascii_letters+string.whitespace) for c in self._ptgen.get('cast')[:3]])}]"
        return subtitle

    @property
    def mediaInfo(self):
        media_info = ""
        for track in self._mediainfo.general_tracks:
            media_info += f"File Name............: {track.file_name}\n"
            media_info += f"File Size............: {get_track_attr(track, 'file_size', True)}\n"
            media_info += f"Duration.............: {get_track_attr(track, 'duration', True)}\n"
            media_info += f"Bit Rate.............: {get_track_attr(track, 'overall_bit_rate', True)}\n"
        for track in self._mediainfo.video_tracks:
            media_info += f"Video Codec..........: {get_track_attr(track, 'format', True)} {get_track_attr(track, 'format profile', True)}\n"
            media_info += f"Frame Rate...........: {get_track_attr(track, 'frame rate', True)}\n"
            media_info += f"Resolution...........: {get_track_attr(track, 'width', True, False)} x {get_track_attr(track, 'height', True, False)}\n"
            media_info += f"Display Ratio........: {get_track_attr(track, 'display_aspect_ratio', True)}\n"
            media_info += f"Scan Type............: {get_track_attr(track, 'scan type', True)}\n"
            media_info += f"Bite Depth...........: {get_track_attr(track, 'bit depth', True)}\n"

        for track in self._mediainfo.audio_tracks:
            media_info += f"Audio #{get_track_attr(track, 'stream_identifier', True)}.............: {get_track_attrs(track, ['bit rate', 'bit rate mode','channel_s', 'format'])}\n"

        for track in self._mediainfo.text_tracks:
            media_info += f"Subtitle #{get_track_attr(track, 'stream_identifier', True)}..........: {get_track_attrs(track, ['format', 'title', 'language'])}\n"

        if self.source_name:
            media_info += f"Source...............: {self.source_name}\n"
        media_info += f"Uploader.............: {self.uploader} @ {self.team}"
        return media_info

    @property
    def description(self):
        return (
            "{}"
            "{}\n\n"
            "[img]https://imgbox.leaguehd.com/images/2021/01/04/info_01.png[/img]\n"
            "[quote][size=3][color=Navy][b]★★★ ★★ General Information ★★★ ★★ [/color][/size][/b]\n"
            "{}[/quote]\n\n"
            "[img]https://imgbox.leaguehd.com/images/2021/01/04/screens_01.png[/img]\n"
            "{}\n".format(
                GROUP_QUOTES.get(self.team, ''),
                self._ptgen.get("format"),
                self.mediaInfo,
                "\n".join([f"[img]{url}[/img]" for url in self._screenshots]),
            )
        )

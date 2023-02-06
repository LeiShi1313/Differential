import argparse
from pathlib import Path
from typing import Optional

from loguru import logger

from differential.plugins.chdbits import CHDBits
from differential.version import version

NOTEAM = """
Generate by Differential {} made by
 __   __   _____    _____   __  __ 
 \ \ / /  / ____|  / ____| |  \/  |
  \ V /  | |  __  | |      | \  / |
   > <   | | |_ | | |      | |\/| |
  / . \  | |__| | | |____  | |  | |
 /_/ \_\  \_____|  \_____| |_|  |_|
 
 
""".format(version)

CHD = """
Present by
 $$$$$$\    $$\   $$\   $$$$$$$\  
$$  __$$\   $$ |  $$ |  $$  __$$\ 
$$ /  \__|  $$ |  $$ |  $$ |  $$ |
$$ |        $$$$$$$$ |  $$ |  $$ |
$$ |        $$  __$$ |  $$ |  $$ |
$$ |  $$\   $$ |  $$ |  $$ |  $$ |
\$$$$$$  |  $$ |  $$ |  $$$$$$$  |
 \______/   \__|  \__|  \_______/ 
                              
Generate by Differential {}
 
""".format(version)

CHDPAD = """
Present by
  /$$$$$$  /$$   /$$ /$$$$$$$  /$$$$$$$   /$$$$$$  /$$$$$$$ 
 /$$__  $$| $$  | $$| $$__  $$| $$__  $$ /$$__  $$| $$__  $$
| $$  \__/| $$  | $$| $$  \ $$| $$  \ $$| $$  \ $$| $$  \ $$
| $$      | $$$$$$$$| $$  | $$| $$$$$$$/| $$$$$$$$| $$  | $$
| $$      | $$__  $$| $$  | $$| $$____/ | $$__  $$| $$  | $$
| $$    $$| $$  | $$| $$  | $$| $$      | $$  | $$| $$  | $$
|  $$$$$$/| $$  | $$| $$$$$$$/| $$      | $$  | $$| $$$$$$$/
 \______/ |__/  |__/|_______/ |__/      |__/  |__/|_______/ 
 
Generate by Differential {}
 
""".format(version)


class CHDBitsEncode(CHDBits):

    @classmethod
    def get_help(cls):
        return 'CHDBitsEncode插件，适用于CHDBits压制组'

    @classmethod
    def add_parser(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        super().add_parser(parser)
        parser.add_argument('--source-name', type=str, help='压制源名称', default=argparse.SUPPRESS)
        parser.add_argument('--encoder', type=str, help="压制者名字，默认Anonymous", default=argparse.SUPPRESS)
        parser.add_argument('--team', type=str, help="组名，默认CHD", default=argparse.SUPPRESS)

    def __init__(
        self,
        source_name: str,
        encoder: str = "Anonymous",
        team: str = "CHD",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.team = team
        self.encoder = encoder
        self.source_name = source_name

    @property
    def subtitle(self):
        if not self._ptgen.get("site") == "douban":
            return ""
        if 'chinese_title' in self._ptgen:
            return f"{'/'.join([self._ptgen.get('chinese_title')] + self._ptgen.get('aka', []))}"
        else:
            return f"{'/'.join(self._ptgen.get('aka', []))}"

    @property
    def media_info(self):
        media_info = f"{self._main_file.stem}\n"
        imdb_link = self._ptgen.get('imdb_link')
        if imdb_link:
            media_info += f"iMDB URL........: {imdb_link}\n"
        imdb_rating = self._ptgen.get("imdb_rating")
        if imdb_rating:
            media_info += f"iMDB RATiNG.....: {imdb_rating}\n"

        genre = self._imdb.get("genre")
        if genre:
            media_info += f"GENRE...........: {','.join(genre)}\n"
        else:
            genre = self._ptgen.get("genre")
            if genre:
                media_info += f"GENRE...........: {','.join(genre)}\n"

        if self.source_name:
            media_info += f"SOURCE..........: {self.source_name} (Thanks)\n"

        for track in self._mediainfo.general_tracks:
            # TODO(leshi1313): Format it by yourself
            media_info += f"RUNTiME.........: {track.other_duration[0]}\n"
            media_info += f"FilE SiZE.......: {track.other_file_size[0]}\n"
        for track in self._mediainfo.video_tracks:
            media_info += (
                f"ViDEO BiTRATE...: "
                f"{track.encoded_library_name if track.encoded_library_name else track.commercial_name} {track.format_profile} "
                f"@ {track.other_bit_rate[0]}\n"
            )
            media_info += f"FRAME RATE......: {track.other_frame_rate[0]}\n"
            media_info += f"ASPECT RATiO....: {track.other_display_aspect_ratio[0]}\n"
            media_info += f"RESOLUTiON......: {track.width}x{track.height}\n"

        for idx, track in enumerate(self._mediainfo.audio_tracks):
            if track.other_language and len(track.other_language) > 1:
                media_info += (
                    f"AUDiO...........: {'#'+str(idx+1) if len(self._mediainfo.audio_tracks) > 1 else ''} "
                    f"{track.other_language[0]} "
                    f"{track.commercial_name} {track.other_channel_s[0]} "
                    f"@ {track.other_bit_rate[0]}\n"
                )
            else:
                media_info += (
                    f"AUDiO...........: {'#'+str(idx+1) if len(self._mediainfo.audio_tracks) > 1 else ''} "
                    f"{track.commercial_name} {track.other_channel_s[0]} "
                    f"@ {track.other_bit_rate[0]}\n"
                )

        if len(self._mediainfo.text_tracks):
            media_info += "SUBTiTLES.......: {}\n".format(
            " | ".join(
                [
                    f"{track.other_language[0]} {track.format} {track.title if track.title else ''}"
                    if track.other_language and len(track.other_language) > 1
                    else f"{track.format} {track.title if track.title else ''}"
                    for track in self._mediainfo.text_tracks
                ]
            )
        )

        for track in self._mediainfo.menu_tracks:
            if track.chapters_pos_end and track.chapters_pos_begin:
                media_info += f"CHAPTERS........: {int(track.chapters_pos_end) - int(track.chapters_pos_begin)}\n"

        if self.encoder:
            media_info += f"ENCODER.........: {self.encoder} @ {self.team}"
        return media_info

    @property
    def description(self):
        return (
            "[quote][color=Red][size=4][b]"
            "资源及相关素材未经CHD许可 严禁提取发布或二压使用，请注意礼节!"
            "[/b][/color][/quote][/size]\n"
            "{}\n\n"
            "[img]https://www.z4a.net/images/2019/09/13/info.png[/img]"
            "[quote]{}[/quote]\n\n"
            "[img]https://www.z4a.net/images/2019/09/13/screens.png[/img]"
            "\n{}\n"
            "[quote][color=red][b]郑重声明："
            "本站提供的所有影视作品均是在网上搜集任何涉及商业盈利目的均不得使用，"
            "否则产生的一切后果将由您自己承担！本站将不对本站的任何内容负任何法律责任！"
            "该下载内容仅做宽带测试使用，请在下载后24小时内删除。请购买正版！[/b][/color][/quote]".format(
                self._ptgen.get("format"),
                self.media_info + "\n\n" + self.parsed_encoder_log,
                "\n".join([f"{uploaded}" for uploaded in self._screenshots]),
            )
        )

    @property
    def tags(self):
        tags = super(CHDBitsEncode, self).tags
        tags["official"] = True
        return tags

    def _generate_nfo(self):
        logger.info("正在生成nfo文件...")
        p = Path(self.folder)
        if p.is_file():
            with open(f"{p.parent.joinpath(p.stem)}.nfo", "wb") as f:
                if self.team == "CHD":
                    f.write(CHD.encode())
                elif self.team == "CHDPAD":
                    f.write(CHDPAD.encode())
                else:
                    f.write(NOTEAM.encode())
                f.write(self.media_info.encode())
        elif p.is_dir():
            with open(p.joinpath(f"{p.name}.nfo"), "wb") as f:
                if self.team == "CHD":
                    f.write(CHD.encode())
                elif self.team == "CHDPAD":
                    f.write(CHDPAD.encode())
                else:
                    f.write(NOTEAM.encode())
                f.write(self.media_info.encode())

    @property
    def easy_upload_torrent_info(self):
        torrent_info = super().easy_upload_torrent_info
        torrent_info["team"] = self.team.lower()
        return torrent_info

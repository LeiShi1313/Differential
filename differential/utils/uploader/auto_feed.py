from functools import reduce
from differential.torrent import TorrnetBase
from differential.utils.mediainfo import get_full_mediainfo


class AutoFeed(TorrnetBase):

    def __init__(self, plugin: TorrnetBase, seperator: str = '#seperator#'):
        self.plugin = plugin
        self.seperator = seperator

    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except NotImplementedError:
            if not name.startswith('__') and name in dir(TorrnetBase):
                return getattr(self.plugin, name)
            else:
                raise AttributeError(name)

    @property
    def category(self):
        category = self.plugin.category
        category_map = {
            'concert': '音乐',
            'movie': '电影',
            'documentary': '记录',
            'tvPack': '剧集'
        }
        if category in category_map:
            return category_map[category]
        return category

    @property
    def video_codec(self):
        return self.plugin.video_codec.upper()

    @property
    def audio_codec(self):
        return self.plugin.audio_codec.upper()

    @property
    def resolution(self):
        resolution = self.plugin.resolution
        if resolution == '4320p':
            return '4k'
        elif resolution == '480p':
            return 'SD'
        return resolution

    @property
    def area(self):
        area = self.plugin.area
        area_map = {
            "CN": "大陆",
            "HK": "港台",
            "TW": "港台",
            "US": "欧美",
            "JP": "日本",
            "KR": "韩国",
            "IN": "印度",
            "FR": "欧美",
            "IT": "欧美",
            "GE": "欧美",
            "ES": "欧美",
            "PT": "欧美",
        }
        if area in area_map:
            return area_map[area]
        return area

    @property
    def _raw_info(self) -> dict:
        return {
            # 填充类信息
            'name': self.title, # 主标题
            'small_descr': self.subtitle, # 副标题
            'url': self.imdb_url, # imdb链接
            'dburl': self.douban_url, # 豆瓣链接
            'descr': self.description, # 简介
            'log_info': '',  # 音乐特有
            'tracklist': '', # 音乐特有
            'music_type': '', # 音乐特有
            'music_media': '', # 音乐特有
            'animate_info': '', # 动漫特有|针对北邮人北洋U2的命名方式
            'anidb': '', # 动漫特有
            'torrent_name': '', # 动漫辅助
            'images': self.screenshots, #  截图

            # 选择类信息
            'type': self.category,  # type:可取值——电影/纪录/体育/剧集/动画/综艺……
            'source_sel': self.area, # 来源(地区)：可取值——欧美/大陆/港台/日本/韩国/印度……
            'standard_sel': self.resolution,  # 分辨率：可取值——4K/1080p/1080i/720p/SD
            'audiocodec_sel': self.audio_codec,  # 音频：可取值——AAC/AC3/DTS…………
            'codec_sel': self.video_codec, # 编码：可取值——H264/H265……
            'medium_sel': self.video_type, # 媒介：可取值——web-dl/remux/encode……

            # 其他
            'origin_site': '', # 记录源站点用于跳转后识别
            'origin_url': '', # 记录源站点用于跳转后识别
            'golden_torrent': False, # 主要用于皮转柠檬, 转过去之后会变成字符串
            'mediainfo_cmct': '', # 适用于春天的info
            'imgs_cmct': '', # 适用于春天的截图
            'full_mediainfo': get_full_mediainfo(self.plugin._mediainfo), # 完整的mediainfo有的站点有长短两种，如：铂金家、猫、春天
            'subtitles': [], # 针对皮转海豹，字幕

            'youtube_url': '', # 用于发布iTS
            'ptp_poster': '',  # 用于发布iTS
            'comparisons': '', # 用于海豹
        }

    @property
    def info(self) -> str:
        l = list(reduce(lambda k, v: k + v, self._raw_info.items()))
        return self.seperator + '#linkstr#'.join([str(i) for i in l])

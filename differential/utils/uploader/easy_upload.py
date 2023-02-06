
from differential.torrent import TorrnetBase


class EasyUpload(TorrnetBase):

    def __init__(self, plugin: TorrnetBase):
        self.plugin = plugin

    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except NotImplementedError:
            if not name.startswith('__') and name in dir(TorrnetBase):
                return getattr(self.plugin, name)
            else:
                raise AttributeError(name)

    @property
    def area(self):
        # map EU coutries to EU
        area = self.plugin.area
        area_map = {
            "FR": "EU",
            "IT": "EU",
            "GE": "EU",
            "ES": "EU",
            "PT": "EU",
        }
        if area in area_map:
            return area_map[area]
        return area

    @property
    def torrent_info(self) -> dict:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "description": self.description,
            "originalDescription": self.original_description,
            "doubanUrl": self.douban_url,
            "doubanInfo": self.douban_info,
            "imdbUrl": self.imdb_url,
            "mediaInfo": self.media_info,
            "mediaInfos": self.media_infos,
            "screenshots": self.screenshots,
            "poster": self.poster,
            "year": self.year,
            "category": self.category,
            "videoType": self.video_type,
            "format": self.format,
            "source": self.source,
            "videoCodec": self.video_codec,
            "audioCodec": self.audio_codec,
            "resolution": self.resolution,
            "area": self.area,
            "movieAkaName": self.movie_aka_name,
            "movieName": self.movie_name,
            "size": self.size,
            "tags": self.tags,
            "otherTags": self.other_tags,
            "comparisons": self.comparisons,
            "isForbidden": False,
            "sourceSiteType": "NexusPHP",
        }

from abc import abstractmethod


class TorrnetBase:

    @property
    @abstractmethod
    def title(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def subtitle(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def media_info(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def media_infos(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def description(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def original_description(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def douban_url(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def douban_info(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def imdb_url(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def screenshots(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def poster(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def year(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def category(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def video_type(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def format(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def source(self):
        raise NotImplementedError()
        return ""

    @property
    @abstractmethod
    def video_codec(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def audio_codec(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def resolution(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def area(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def movie_name(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def movie_aka_name(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def size(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def tags(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def other_tags(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def comparisons(self):
        raise NotImplementedError()

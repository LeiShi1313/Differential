

class ImageUploaded:
    def __init__(self, url, thumb=None):
        self.url = url
        self.thumb = thumb

    def __str__(self):
        if self.thumb:
            return f"[url={self.url}][img]{self.thumb}[/img][/url]"
        return f"[img]{self.url}[/img]"

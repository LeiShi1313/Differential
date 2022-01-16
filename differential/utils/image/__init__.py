
class ImageUploaded:
    def __init__(self, url, thumb=None):
        self.url = url
        self.thumb = thumb

    def __str__(self):
        if self.thumb:
            return f"[url={self.url}][img]{self.thumb}[/img][/url]"
        return f"[img]{self.url}[/img]"



from differential.utils.image.byr import byr_upload
from differential.utils.image.hdbits import hdbits_upload
from differential.utils.image.smms import smms_upload
from differential.utils.image.ptpimg import ptpimg_upload
from differential.utils.image.imgurl import imgurl_upload
from differential.utils.image.chevereto import chevereto_api_upload, chevereto_cookie_upload, chevereto_username_upload
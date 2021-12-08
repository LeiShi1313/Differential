import requests
import webbrowser

from loguru import logger
from differential.constants import URL_SHORTENER_PATH


def open_link(link: str, use_short_url: bool = False):
    if use_short_url:
        req = requests.post(f"{URL_SHORTENER_PATH}/new", {"url": link})
        if req.ok:
            link = f"{URL_SHORTENER_PATH}/dft/{req.text}"

    try:
        browser = webbrowser.get()
    except webbrowser.Error:
        browser = None

    if browser is None or isinstance(browser, webbrowser.GenericBrowser):
        logger.info(f"未找到浏览器，请直接复制以下链接：{link}")
    else:
        browser.open(link, new=1)

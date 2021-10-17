import webbrowser

from loguru import logger


def open_link(link: str):
    try:
        browser = webbrowser.get()
    except webbrowser.Error:
        browser = None

    if browser is None or isinstance(browser, webbrowser.GenericBrowser):
        logger.info(f"未找到浏览器，请直接复制以下链接：{link}")
    else:
        browser.open(link, new=1)
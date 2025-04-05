from typing import Any, Dict

from differential.utils.ptgen.base import PTGenData
from differential.utils.ptgen.douban import DoubanData
from differential.utils.ptgen.imdb import IMDBData
from differential.utils.ptgen.indienova import IndienovaData
from differential.utils.ptgen.steam import SteamData
from differential.utils.ptgen.epic import EpicData
from differential.utils.ptgen.bangumi import BangumiData

def parse_ptgen(data: Dict[str, Any]) -> PTGenData:
    site = data.get('site')
    if site == 'douban':
        return DoubanData.from_dict(data)
    elif site == 'imdb':
        return IMDBData.from_dict(data)
    elif site == 'steam':
        return SteamData.from_dict(data)
    elif site == 'epic':
        return EpicData.from_dict(data)
    elif site == 'bangumi':
        return BangumiData.from_dict(data)
    elif site == 'indienova':
        return IndienovaData.from_dict(data)
    else:
        # Fallback: just parse it into BaseData or raise error
        return PTGenData(
            site=data.get('site', 'unknown'),
            sid=data.get('sid', ''),
            success=data.get('success', False),
            error=data.get('error'),
            format=data.get('format', 'PTGen获取失败，请自行获取相关内容')
        )
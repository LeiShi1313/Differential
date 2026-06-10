import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils.media_name import parse_media_name


REAL_DOWNLOAD_CASES = [
    {
        "name": "IT狂人.The.IT.Crowd.S03.2008.1080p.WEB-DL.AAC.H264-HDSWEB",
        "title": "The IT Crowd",
        "primary": "IT狂人",
        "year": 2008,
        "kind": "tv",
        "season": 3,
        "candidates": ["IT狂人", "The IT Crowd"],
    },
    {
        "name": "Go.for.It.Nakamura-kun!!.S01.2026.1080p.CR.WEB-DL.H.264.AAC-FROGWeb",
        "title": "Go for It Nakamura kun!!",
        "year": 2026,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "Limitless.Live.Better.Now.S01.2025.1080p.DSNP.WEB-DL.H.264.DDP.5.1-FROGWeb",
        "title": "Limitless Live Better Now",
        "year": 2025,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "L.Arte.della.Gioia.S01.1080p.NOW.WEB-DL.DDP5.1.H.264-MeM.GP",
        "title": "L Arte della Gioia",
        "year": None,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "Eternity.2025.2160p.iT.WEB-DL.DV.HDR.H.265.DDP5.1.Atmos-BiVerse@ADWeb",
        "title": "Eternity",
        "year": 2025,
        "kind": "movie",
    },
    {
        "name": "情人.4K修复版.1992.KOR.1080p.法语中字￡CMCT风潇潇",
        "title": "情人",
        "year": 1992,
        "kind": "movie",
    },
    {
        "name": "我是山姆.2001.CAN.1080p.中英特效字幕￡CMCT轻语",
        "title": "我是山姆",
        "year": 2001,
        "kind": "movie",
    },
    {
        "name": "追随.1998.CC.1080p.中英字幕￡CMCT陆判",
        "title": "追随",
        "year": 1998,
        "kind": "movie",
    },
    {
        "name": "魔鬼代言人.1997.DC.1080p.国英双语.中英字幕￡CMCT风潇潇",
        "title": "魔鬼代言人",
        "year": 1997,
        "kind": "movie",
    },
    {
        "name": "移魂都市.导演剪切版.Dark.City.1998.Director‘s.Cut.2160p.UHD.Blu-ray.DoVi.HDR10.HEVC.TrueHD.7.1-DIY@HDSky",
        "title": "Dark City",
        "primary": "移魂都市",
        "year": 1998,
        "kind": "movie",
        "candidates": ["移魂都市", "Dark City"],
    },
    {
        "name": "异教峰S01-S03.Pagan.Peak.2019-2023.1080p.GER.Blu-ray.x265.AC3￡cXcY@FRDS",
        "title": "Pagan Peak",
        "primary": "异教峰",
        "year": 2019,
        "year_text": "2019-2023",
        "kind": "tv",
        "season": 1,
        "season_text": "S01-S03",
        "candidates": ["异教峰", "Pagan Peak"],
    },
    {
        "name": "摩登家庭S01-S11.Modern.Family.2009-2019.1080p.WEB-DL.x265.AC3￡cXcY@FRDS",
        "title": "Modern Family",
        "primary": "摩登家庭",
        "year": 2009,
        "year_text": "2009-2019",
        "kind": "tv",
        "season": 1,
        "season_text": "S01-S11",
        "candidates": ["摩登家庭", "Modern Family"],
    },
    {
        "name": "步履不停.Aruitemo.Aruitemo.AKA.Still.Walking.2008.1080p.Blu-ray.AVC.LPCM.2.0-bbba@HDSky",
        "title": "Still Walking",
        "primary": "步履不停",
        "year": 2008,
        "kind": "movie",
        "candidates": ["步履不停", "Aruitemo Aruitemo", "Still Walking"],
    },
    {
        "name": "Lao.hu.li.AKA.Old.Fox.2023.1080p.TWN.Blu-ray.AVC.DTS-HD.MA.7.1-CMCT",
        "title": "Old Fox",
        "year": 2023,
        "kind": "movie",
        "candidates": ["Lao hu li", "Old Fox"],
    },
    {
        "name": "密室大逃脱.第七季.Great.Escape.S07.2019.1080p.WEB-DL.H264.AAC-HHWEB",
        "title": "Great Escape",
        "primary": "密室大逃脱 第七季",
        "year": 2019,
        "kind": "tv",
        "season": 7,
        "candidates": ["密室大逃脱", "Great Escape"],
    },
    {
        "name": "[星辰变 第七季].Stellar.Transformation.2026.S07.Complete.2160p.WEB-DL.H265.AAC-UBWEB",
        "title": "Stellar Transformation",
        "primary": "星辰变 第七季",
        "year": 2026,
        "kind": "tv",
        "season": 7,
        "candidates": ["星辰变", "Stellar Transformation"],
    },
    {
        "name": "TIME_STILL_TURNS_THE_PAGES_2023_TWN_BD-CMCT",
        "title": "TIME STILL TURNS THE PAGES",
        "year": 2023,
        "kind": "movie",
    },
    {
        "name": "BLADES_OF_THE_GUARDIANS_2026_HKG_SE-CMCT",
        "title": "BLADES OF THE GUARDIANS",
        "year": 2026,
        "kind": "movie",
    },
    {
        "name": "'Tis.Time.for.Torture.Princess.S02.2024.1080p.Baha.WEB-DL.H.264.AAC-FROGWeb",
        "title": "'Tis Time for Torture Princess",
        "year": 2024,
        "kind": "tv",
        "season": 2,
    },
    {
        "name": "Dr.STONE.S04.2025.1080p.CR.WEB-DL.H.264.AAC-FROGWeb",
        "title": "Dr. STONE",
        "year": 2025,
        "kind": "tv",
        "season": 4,
    },
    {
        "name": "K-PAX 2001 1080p Blu-ray AVC DTS-HD MA 5.1",
        "title": "K PAX",
        "year": 2001,
        "kind": "movie",
    },
    {
        "name": "T2.Trainspotting.2017.2160p.UHD.CEE.Blu-ray.HEVC.Atmos.TrueHD.7.1-DiY@HDHome",
        "title": "T2 Trainspotting",
        "year": 2017,
        "kind": "movie",
    },
    {
        "name": "Me.And.Earl.And.The.Dying.Girl.2015.MULTi.COMPLETE.BLURAY-GMB",
        "title": "Me And Earl And The Dying Girl",
        "year": 2015,
        "kind": "movie",
    },
    {
        "name": "Love.Go.Go.1997.JAPANESE.COMPLETE.BLURAY-NOELLE",
        "title": "Love Go Go",
        "year": 1997,
        "kind": "movie",
    },
    {
        "name": "Cyberpunk.Edgerunners.S01.1080p.NF.WEB-DL.DUAL.DDP5.1.H.264-SMURF",
        "title": "Cyberpunk Edgerunners",
        "year": None,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "Great.Escape.S02.2020.WEB-DL.1080p.H264.AAC-HDCTV",
        "title": "Great Escape",
        "year": 2020,
        "kind": "tv",
        "season": 2,
    },
    {
        "name": "The Boy in the Striped Pyjamas 2008 FRA BluRay 1080p AVC DTS-HD MA 5.1-LianHH@CHDBits",
        "title": "The Boy in the Striped Pyjamas",
        "year": 2008,
        "kind": "movie",
    },
    {
        "name": "On Becoming a Guinea Fowl 2024 2160p AMZN WEB-DL DDP5 1 H 265-BYNDR",
        "title": "On Becoming a Guinea Fowl",
        "year": 2024,
        "kind": "movie",
    },
    {
        "name": "All.Her.Fault.S01.2160p.Peacock.WEB-DL.DDP.5.1.HDR10.H.265-CHDWEB",
        "title": "All Her Fault",
        "year": None,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "Poker.Face.S02.2160p.Stan.WEB-DL.DDP.5.1.HDR10.H.265-CHDWEB",
        "title": "Poker Face",
        "year": None,
        "kind": "tv",
        "season": 2,
    },
    {
        "name": "Prehistoric.Planet.S01.2160p.ATVP.WEB-DL.DDP.5.1.Atmos.HDR.HEVC-MiON",
        "title": "Prehistoric Planet",
        "year": None,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "RTHK31.Maiden.Rosé.1995.1080i.HDTV.H264-NGB",
        "title": "Maiden Rosé",
        "year": 1995,
        "kind": "movie",
    },
    {
        "name": "EO.2022.SUBPL.1080p.RKTN.WEB-DL.DDP5.1.H.264-inTGrity",
        "title": "EO",
        "year": 2022,
        "kind": "movie",
    },
    {
        "name": "[Re：从零开始的异世界生活 第四季].Re.Zero.Kara.Hajimeru.Isekai.Seikatsu.2026.S04.Complete.2160p.IQ.WEB-DL.H265.AAC-UBWEB",
        "title": "Re Zero Kara Hajimeru Isekai Seikatsu",
        "primary": "从零开始的异世界生活",
        "year": 2026,
        "kind": "tv",
        "season": 4,
        "candidates": ["从零开始的异世界生活", "Re Zero Kara Hajimeru Isekai Seikatsu"],
    },
    {
        "name": "主咖和Ta的朋友们.Main.Guest.and.Their.Friends.S01.2026.2160p.WEB-DL.H265.AAC-ADWeb",
        "title": "Main Guest and Their Friends",
        "primary": "主咖和Ta的朋友们",
        "year": 2026,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "捕风追影 The Shadows Edge 2025 2160p UHD GER Blu-ray DoVi HDR10 HEVC DTS-HD MA 5.1-Thor@HDSky",
        "title": "The Shadows Edge",
        "primary": "捕风追影",
        "year": 2025,
        "kind": "movie",
    },
    {
        "name": "粗野派 The Brutalist 2024 2160p UHD Blu-ray SDR HEVC DTS-HD MA 5.1-Thor@HDSky",
        "title": "The Brutalist",
        "primary": "粗野派",
        "year": 2024,
        "kind": "movie",
    },
    {
        "name": "疾速追杀：芭蕾杀姬.Ballerina.2025.2160p.WEB-DL.DDP5.1.Atmos.H265.HDR.DV-DIY@HDSWEB",
        "title": "Ballerina",
        "primary": "疾速追杀：芭蕾杀姬",
        "year": 2025,
        "kind": "movie",
    },
    {
        "name": "纽约提喻法.Synecdoche.New.York.2008.2160p.UHD.Blu-ray.HEVC.DTS-HD.MA.5.1-DIY@HDSky",
        "title": "Synecdoche New York",
        "primary": "纽约提喻法",
        "year": 2008,
        "kind": "movie",
    },
    {
        "name": "燃烧的巴黎圣母院 Notre-Dame Brule 2022 FRA UHD Blu-ray 2160p HEVC TrueHD Atmos7.1-Pete@HDSky",
        "title": "Notre Dame Brule",
        "primary": "燃烧的巴黎圣母院",
        "year": 2022,
        "kind": "movie",
    },
    {
        "name": "电影之旅.The.Movies.That.Made.Us.S01.1080p.NF.WEB-DL.x264.DDP2.0-PTerWEB",
        "title": "The Movies That Made Us",
        "primary": "电影之旅",
        "year": None,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "巴比伦柏林S04.Babylon.Berlin.2022.1080p.Blu-ray.x265.AC3￡cXcY@FRDS",
        "title": "Babylon Berlin",
        "primary": "巴比伦柏林",
        "year": 2022,
        "kind": "tv",
        "season": 4,
    },
    {
        "name": "古埃及未解之谜.Egypt.S01.2019.1080p.WEB-DL.H264.AAC-HHWEB",
        "title": "Egypt",
        "primary": "古埃及未解之谜",
        "year": 2019,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "无人生还.第一季.2015.1080p.中英字幕.￡CMCT玩偶",
        "title": "无人生还 第一季",
        "primary": "无人生还 第一季",
        "year": 2015,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "女尸谜案.2012.1080p.西班牙语.简繁中字￡CMCT陆判",
        "title": "女尸谜案",
        "year": 2012,
        "kind": "movie",
    },
    {
        "name": "美国队长4.Captain America Brave New World 2025 2160p UHD Blu-ray DoVi HDR10 HEVC TrueHD 7.1-x-man@HDSky",
        "title": "Captain America Brave New World",
        "primary": "美国队长4",
        "year": 2025,
        "kind": "movie",
    },
    {
        "name": "侏罗纪世界：重生.Jurassic World Rebirth 2025 V2 2160p UHD Blu-ray DoVi HDR10 HEVC TrueHD 7.1-x-man@HDSky",
        "title": "Jurassic World Rebirth",
        "primary": "侏罗纪世界：重生",
        "year": 2025,
        "kind": "movie",
    },
    {
        "name": "Star.Trek.Trilogy.2009-2016.UHD.BluRay.2160p.10bit.HDR.MultiAudio.TrueHD(Atmos).7.1.x265-beAst",
        "title": "Star Trek Trilogy",
        "year": 2009,
        "year_text": "2009-2016",
        "kind": "movie",
    },
    {
        "name": "BTS.Permission.to.Dance.on.Stage.-.LA.2022.2160p.DSNP.WEB-DL.HDR.H.265.DDP.5.1.Atmos-FROGWeb",
        "title": "BTS Permission to Dance on Stage LA",
        "year": 2022,
        "kind": "movie",
    },
    {
        "name": "Journey to the South Pacific 2013 2160 UHD Blu-ray IMAX Enhanced 7.1-Tsui",
        "title": "Journey to the South Pacific",
        "year": 2013,
        "kind": "movie",
    },
    {
        "name": "Tamon's.B-Side.S01.2026.1080p.Baha.WEB-DL.H.264.AAC-FROGWeb",
        "title": "Tamon's B Side",
        "year": 2026,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "There.Was.a.Cute.Girl.in.the.Hero's.Party.so.I.Tried.Confessing.to.Her.S01.2026.1080p.Baha.WEB-DL.H.264.AAC-FROGWeb",
        "title": "There Was a Cute Girl in the Hero's Party so I Tried Confessing to Her",
        "year": 2026,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "Noble.Reincarnation.Born.Blessed.So.I'll.Obtain.Ultimate.Power.S01.2026.1080p.CR.WEB-DL.H.264.AAC-FROGWeb",
        "title": "Noble Reincarnation Born Blessed So I'll Obtain Ultimate Power",
        "year": 2026,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "A.Gentle.Noble's.Vacation.Recommendation.S01.2026.1080p.CR.WEB-DL.H.264.AAC-FROGWeb",
        "title": "A Gentle Noble's Vacation Recommendation",
        "year": 2026,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "Talk.Show.2020.S03.Complete.1080p.WEB-DL.H264.AAC-TJUPT",
        "title": "Talk Show",
        "year": 2020,
        "kind": "tv",
        "season": 3,
    },
    {
        "name": "Dorohedoro.S02.2026.1080p.CR.WEB-DL.H.264.AAC-FROGWeb",
        "title": "Dorohedoro",
        "year": 2026,
        "kind": "tv",
        "season": 2,
    },
    {
        "name": "The.Last.Of.Sheila.1973.MULTi.COMPLETE.BLURAY-MONUMENT",
        "title": "The Last Of Sheila",
        "year": 1973,
        "kind": "movie",
    },
    {
        "name": "[薄荷].Mint.2026.S01.Complete.2160p.iP.WEB-DL.HLG.H265.10bit.AAC-UBWEB",
        "title": "Mint",
        "primary": "薄荷",
        "year": 2026,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "[真男人的旅行法 in 九州].Real.Mans.Travel.Guide.in.Kyushu.2026.S01.Complete.1080p.friDay.WEB-DL.H264.AAC-UBWEB",
        "title": "Real Mans Travel Guide in Kyushu",
        "primary": "真男人的旅行法",
        "year": 2026,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "[摩绪].MAO.2026.S01.Complete.2160p.IQ.WEB-DL.H265.AAC-UBWEB",
        "title": "MAO",
        "primary": "摩绪",
        "year": 2026,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "[礼物].GIFT.2026.S01.Complete.1080p.friDay.WEB-DL.H264.AAC-UBWEB",
        "title": "GIFT",
        "primary": "礼物",
        "year": 2026,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "[柔美的细胞小将 第三季].Yumi's.Cells.2026.S03.Complete.1080p.TVING.WEB-DL.50Fps.H264.AAC-UBWEB",
        "title": "Yumi's Cells",
        "primary": "柔美的细胞小将 第三季",
        "year": 2026,
        "kind": "tv",
        "season": 3,
    },
    {
        "name": "[如果有一天我将会离开你].Before.Next.Spring.2021.1080p.WEB-DL.AVC.AAC-QHstudIo",
        "title": "Before Next Spring",
        "primary": "如果有一天我将会离开你",
        "year": 2021,
        "kind": "movie",
    },
    {
        "name": "与我的园丁对话.Dialogue.avec.Mon.Jardinier.2007.FRA.BluRay.1080p.REMUX.AVC.DTS-HD.MA.5.1-UBits",
        "title": "Dialogue avec Mon Jardinier",
        "primary": "与我的园丁对话",
        "year": 2007,
        "kind": "movie",
    },
    {
        "name": "[行尸走肉：外面的世界 第一季].The.Walking.Dead.World.Beyond.2020.S01.Complete.1080p.AMZN.WEB-DL.H264.DDP5.1-UBWEB",
        "title": "The Walking Dead World Beyond",
        "primary": "行尸走肉：外面的世界 第一季",
        "year": 2020,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "[神墓 年番].Tomb.of.Fallen.Gods.2025.S03.Complete.2160p.WEB-DL.HQ.H265.10bit.AAC-UBWEB",
        "title": "Tomb of Fallen Gods",
        "primary": "神墓 年番",
        "year": 2025,
        "kind": "tv",
        "season": 3,
    },
    {
        "name": "[海底小纵队 第十季].Octonauts.2025.S10.Complete.2160p.WEB-DL.HQ.H265.10bit.AAC-UBWEB",
        "title": "Octonauts",
        "primary": "海底小纵队 第十季",
        "year": 2025,
        "kind": "tv",
        "season": 10,
    },
    {
        "name": "老无所依.No.Country.for.Old.Men.2007.Criterion.Collection.2160p.USA.UHD.BluRay.DV.HDR.HEVC.DTS-HD.MA 5.1-LuckDIY",
        "title": "No Country for Old Men",
        "primary": "老无所依",
        "year": 2007,
        "kind": "movie",
    },
    {
        "name": "[火线救援  第七季].Rescue.Me.2011.S07.Complete.1080p.NF.WEB-DL.H264.DDP5.1-UBWEB",
        "title": "Rescue Me",
        "primary": "火线救援 第七季",
        "year": 2011,
        "kind": "tv",
        "season": 7,
    },
    {
        "name": "[蜡笔小新外传 外星人vs新之助].Crayon.Shin-chan.Spin-off.Alien.vs.Shinnosuke.2016.S01.Complete.1080p.AMZN.WEB-DL.H264.DDP2.0.2Audios-UBWEB",
        "title": "Crayon Shin chan Spin off Alien vs Shinnosuke",
        "primary": "蜡笔小新外传 外星人vs新之助",
        "year": 2016,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "千寻小姐.2023.JPN.1080p.日语.简繁中字￡CMCT咕咕鸡",
        "title": "千寻小姐",
        "year": 2023,
        "kind": "movie",
    },
    {
        "name": "[和班上第二可爱的女孩成为朋友].Class.de.2.Banme.ni.Kawaii.Onnanoko.to.Tomodachi.ni.Natta.2026.S01.Complete.1080p.LINETV.WEB-DL.H264.AAC-UBWEB",
        "title": "Class de 2 Banme ni Kawaii Onnanoko to Tomodachi ni Natta",
        "primary": "和班上第二可爱的女孩成为朋友",
        "year": 2026,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "[上伊那牡丹，酒醉身姿似百合花般].Kamiina.Botan.Yoeru.Sugata.wa.Yuri.no.Hana.2026.S01.Complete.2160p.IQ.WEB-DL.H265.AAC-UBWEB",
        "title": "Kamiina Botan Yoeru Sugata wa Yuri no Hana",
        "primary": "上伊那牡丹，酒醉身姿似百合花般",
        "year": 2026,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "呼啸山庄.Wuthering.Heights.2026.1080p.USA.Blu-ray.AVC.Atmos.TrueHD.7.1-DIY@UBits",
        "title": "Wuthering Heights",
        "primary": "呼啸山庄",
        "year": 2026,
        "kind": "movie",
    },
    {
        "name": "[罪人].Den.skyldige.2018.FRA.BluRay.1080p.x265.10bit.AC3.2Audios-CMCT",
        "title": "Den skyldige",
        "primary": "罪人",
        "year": 2018,
        "kind": "movie",
    },
    {
        "name": "[斗罗大陆2：绝世唐门].Soul.Land.II.The.Peerless.Tang.Clan.2023.S02.Complete.2160p.WEB-DL.H265.AAC-UBWEB",
        "title": "Soul Land II The Peerless Tang Clan",
        "primary": "斗罗大陆2：绝世唐门",
        "year": 2023,
        "kind": "tv",
        "season": 2,
    },
    {
        "name": "创：战纪.TRON.Legacy.2010.2160p.Repack.USA.Blu-ray.Dolby.Vision.HEVC.DTS-HD.MA.TrueHD.7.1.Atmos-LINMENG@CHDBits",
        "title": "TRON Legacy",
        "primary": "创：战纪",
        "year": 2010,
        "kind": "movie",
    },
    {
        "name": "[茜茜皇后 第一季].Die.Kaiserin.2022.S01.Complete.NF.WEB-DL.1080p.H264.DDP5.1.Atmos-CMCTV",
        "title": "Die Kaiserin",
        "primary": "茜茜皇后 第一季",
        "year": 2022,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "年轻气盛 Youth.2015.V1.1080p.USA.Blu-ray.AVC.DTS-HD.MA.7.1-IWUBEN@OurBits",
        "title": "Youth",
        "primary": "年轻气盛",
        "year": 2015,
        "kind": "movie",
    },
    {
        "name": "[Travis Japan到美国放暑假].Travis.Japan.Summer.Vacation.in.the.USA.2026.S01.Complete.1080p.DSNP.WEB-DL.H264.AAC-UBWEB",
        "title": "Travis Japan Summer Vacation in the USA",
        "primary": "Travis Japan到美国放暑假",
        "year": 2026,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "[Running Man].Running.Man.2010.S01.Complete.1080p.friDay.WEB-DL.H264.AAC-UBWEB",
        "title": "Running Man",
        "year": 2010,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "[两天一夜 第四季].2.Days.and.1.Night.2019.S04.Complete.1080p.friDay.WEB-DL.H264.AAC-UBWEB",
        "title": "2 Days and 1 Night",
        "primary": "两天一夜 第四季",
        "year": 2019,
        "kind": "tv",
        "season": 4,
    },
    {
        "name": "[哦！英心].Oh!.Young-shim.2023.S01.Complete.1080p.Viu.WEB-DL.H264.AAC-UBWEB",
        "title": "Oh! Young shim",
        "primary": "哦！英心",
        "year": 2023,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "[山田君与7个魔女].Yamada-kun.to.7-nin.no.Majo.2015.S01.Complete.1080p.friDay.WEB-DL.H264.AAC-UBWEB",
        "title": "Yamada kun to 7 nin no Majo",
        "primary": "山田君与7个魔女",
        "year": 2015,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "[闲着干嘛呢？].How.Do.You.Play.2019.S01.Complete.1080p.friDay.WEB-DL.H264.AAC-UBWEB",
        "title": "How Do You Play",
        "primary": "闲着干嘛呢？",
        "year": 2019,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "[怪奇物语 第一季].Stranger.Things.2016.S01.Complete.2160p.NF.WEB-DL.DoVi.H265.10bit.DDP5.1-UBWEB",
        "title": "Stranger Things",
        "primary": "怪奇物语 第一季",
        "year": 2016,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "[石纪元 第四季].Dr.STONE.SCIENCE.FUTURE.2025.S04.Complete.1080p.friDay.WEB-DL.H264.AAC-UBWEB",
        "title": "Dr. STONE SCIENCE FUTURE",
        "primary": "石纪元 第四季",
        "year": 2025,
        "kind": "tv",
        "season": 4,
    },
    {
        "name": "[橘子郡男孩 第三季].The.O.C.2005.S03.Complete.1080p.AMZN.WEB-DL.H264.DDP2.0-UBWEB",
        "title": "The O.C.",
        "primary": "橘子郡男孩 第三季",
        "year": 2005,
        "kind": "tv",
        "season": 3,
    },
    {
        "name": "[所爱之人].LOVED.ONE.2026.S01.Complete.1080p.NF.WEB-DL.H264.AAC-UBWEB",
        "title": "LOVED ONE",
        "primary": "所爱之人",
        "year": 2026,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "[偶然与想象]Wheel of Fortune and Fantasy 2021 1080p USA Blu-ray AVC DTS-HD MA 5.1-Thor@HDSky",
        "title": "Wheel of Fortune and Fantasy",
        "primary": "偶然与想象",
        "year": 2021,
        "kind": "movie",
    },
    {
        "name": "道格拉斯被取消了S01.Douglas.Is.Cancelled.2024.1080p.AMZN.WEBrip.x265.AC3￡cXcY@FRDS",
        "title": "Douglas Is Cancelled",
        "primary": "道格拉斯被取消了",
        "year": 2024,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "Leila's.Brothers.2022.REPACK.1080p.BluRay.DD5.1.x264-PuTao",
        "title": "Leila's Brothers",
        "year": 2022,
        "kind": "movie",
    },
    {
        "name": "Digimon.Adventure.Last.Evolution.Kizuna.2020.RERiP.1080p.BluRay.x264.DTS-WiKi",
        "title": "Digimon Adventure Last Evolution Kizuna",
        "year": 2020,
        "kind": "movie",
    },
    {
        "name": "Happyend.2024.1080p.JPN.BluRay.AVC.DTS-HD.MA.5.1-DIY@Audies",
        "title": "Happyend",
        "year": 2024,
        "kind": "movie",
    },
    {
        "name": "Universal.Language.AKA.Une.langue.universelle.2024.1080p.USA.Blu-ray.AVC.LPCM.2.0-Parker@CHDBits",
        "title": "Une langue universelle",
        "year": 2024,
        "kind": "movie",
        "candidates": ["Universal Language", "Une langue universelle"],
    },
    {
        "name": "[身为悲剧始作俑者的最强邪恶BOSS女王为民竭心尽力。 第二季].Higeki.no.Genkyou.to.Naru.Saikyou.Gedou.Last.Boss.Joou.wa.Tami.no.Tame.ni.Tsukushimasu.2026.S02.Complete.2160p.IQ.WEB-DL.H265.AAC-UBWEB",
        "title": "Higeki no Genkyou to Naru Saikyou Gedou Last Boss Joou wa Tami no Tame ni Tsukushimasu",
        "primary": "身为悲剧始作俑者的最强邪恶BOSS女王为民竭心尽力。 第二季",
        "year": 2026,
        "kind": "tv",
        "season": 2,
    },
    {
        "name": "[In the SOOP：友情旅行].In.The.Soop.Friendcation.2022.S01.Complete.1080p.HamiVideo.WEB-DL.H264.AAC-UBWEB",
        "title": "In The Soop Friendcation",
        "primary": "友情旅行",
        "year": 2022,
        "kind": "tv",
        "season": 1,
        "candidates": ["友情旅行", "In The Soop Friendcation"],
    },
    {
        "name": "[Oh！三光公寓！].The.Lovers.of.Samgwang.Villa.2020.S01.Complete.1080p.NF.WEB-DL.H264.AAC-UBWEB",
        "title": "The Lovers of Samgwang Villa",
        "primary": "Oh！三光公寓！",
        "year": 2020,
        "kind": "tv",
        "season": 1,
        "candidates": ["Oh！三光公寓！", "The Lovers of Samgwang Villa"],
    },
    {
        "name": "[21世纪大君夫人].Perfect.Crown.2026.S01.Complete.1080p.DSNP.WEB-DL.H264.AAC-UBWEB",
        "title": "Perfect Crown",
        "primary": "21世纪大君夫人",
        "year": 2026,
        "kind": "tv",
        "season": 1,
        "candidates": ["21世纪大君夫人", "Perfect Crown"],
    },
    {
        "name": "[951号囚犯].Prisoner.951.2025.S01.Complete.1080p.NowPlayer.WEB-DL.H264.AAC-UBWEB",
        "title": "Prisoner 951",
        "primary": "951号囚犯",
        "year": 2025,
        "kind": "tv",
        "season": 1,
        "candidates": ["951号囚犯", "Prisoner 951"],
    },
    {
        "name": "英雌.Heroine.AKA.Late.Shift.2025.1080p.Blu-ray.AVC.DTS-HD.MA.5.1-DIY@HDSky",
        "title": "Late Shift",
        "primary": "英雌",
        "year": 2025,
        "kind": "movie",
        "candidates": ["英雌", "Late Shift"],
    },
    {
        "name": "[谈酒说爱].ate.account.Cast.&.crew.User.reviews.IMDbPro.All.the.Liquors.2023.S01.Complete.1080p.MyVideo.WEB-DL.H264.AAC-UBWEB",
        "title": "All the Liquors",
        "primary": "谈酒说爱",
        "year": 2023,
        "kind": "tv",
        "season": 1,
        "candidates": ["谈酒说爱", "All the Liquors"],
    },
    {
        "name": "神奇4侠 初露锋芒 The.Fantastic.Four.First.Steps.2025.2160p.USA.UHD.Blu-ray.DoVi.HDR10.HEVC.TrueHD.7.1-Thor@HDSky",
        "title": "The Fantastic Four First Steps",
        "primary": "神奇4侠 初露锋芒",
        "year": 2025,
        "kind": "movie",
        "candidates": ["神奇4侠 初露锋芒", "The Fantastic Four First Steps"],
    },
    {
        "name": "速度与激情7.Furious Seven 2015 2in1 2160p UHD Blu-ray HEVC DTS-X-x-man@HDSky",
        "title": "Furious Seven",
        "primary": "速度与激情7",
        "year": 2015,
        "kind": "movie",
        "candidates": ["速度与激情7", "Furious Seven"],
    },
    {
        "name": "1992.1992.2024.S01.2160p.NOW.WEB-DL.DDP5.1.HDR.H.265-MeM.GP",
        "title": "1992",
        "year": 2024,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "S.W.A.T.2017.S08.1080p.AMZN.WEB-DL.DDP5.1.H.264-FLUX",
        "title": "S.W.A.T.",
        "year": 2017,
        "kind": "tv",
        "season": 8,
    },
    {
        "name": "五月天人生无限公司.Mayday.Life.2019.BluRay.1080p.x264.DTS-HD.MA.5.1-UBits",
        "title": "Mayday Life",
        "primary": "五月天人生无限公司",
        "year": 2019,
        "kind": "movie",
        "candidates": ["五月天人生无限公司", "Mayday Life"],
    },
    {
        "name": "人生大事.Lighting.Up.The.Stars.2022.CHN.1080p.Blu-ray.AVC.TrueHD.5.1-BeiTai@HDSky",
        "title": "Lighting Up The Stars",
        "primary": "人生大事",
        "year": 2022,
        "kind": "movie",
        "candidates": ["人生大事", "Lighting Up The Stars"],
    },
    {
        "name": "傲慢与偏见.2005.USA.1080p.国英双语.双国配.中英字幕￡CMCT陆判",
        "title": "傲慢与偏见",
        "year": 2005,
        "kind": "movie",
    },
    {
        "name": "五月碧云天.1999.FRA.1080p.土耳其语.中英字幕￡CMCT小齐齐",
        "title": "五月碧云天",
        "year": 1999,
        "kind": "movie",
    },
    {
        "name": "[死神][久保带人][Vol.01-Vol.74+短篇][完结][bili]",
        "title": "死神",
        "year": None,
        "kind": None,
    },
    {
        "name": "Grave.Robbery.1080p.YOUKU.WEB-DL.AAC2.0.H.264-MWeb",
        "title": "Grave Robbery",
        "year": None,
        "kind": None,
    },
    {
        "name": "[女神 异世界转生想成为什么 我 勇者的肋骨].Megami.Isekai.Tensei.Nani.ni.Naritai.Desuka.Ore.Yuusha.no.Rokkotsu.de.2026.S01.Complete.1080p.CR.WEB-DL.H264.AAC-UBWEB",
        "title": "Megami Isekai Tensei Nani ni Naritai Desuka Ore Yuusha no Rokkotsu de",
        "primary": "女神 异世界转生想成为什么 我 勇者的肋骨",
        "year": 2026,
        "kind": "tv",
        "season": 1,
        "candidates": ["女神 异世界转生想成为什么 我 勇者的肋骨", "Megami Isekai Tensei Nani ni Naritai Desuka Ore Yuusha no Rokkotsu de"],
    },
    {
        "name": "[木头风纪委员和迷你裙JK的故事].Ponkotsu.Fuuki.Iin.to.Skirt-take.ga.Futekisetsu.na.JK.no.Hanashi.2026.S01.Complete.1080p.CR.WEB-DL.H264.AAC-UBWEB",
        "title": "Ponkotsu Fuuki Iin to Skirt take ga Futekisetsu na JK no Hanashi",
        "primary": "木头风纪委员和迷你裙JK的故事",
        "year": 2026,
        "kind": "tv",
        "season": 1,
        "candidates": ["木头风纪委员和迷你裙JK的故事", "Ponkotsu Fuuki Iin to Skirt take ga Futekisetsu na JK no Hanashi"],
    },
    {
        "name": "[蜡笔小新外传4 妖怪与新之助].Crayon.Shin-chan.Spin-off.O.O.O.No.Shinnosuke.2017.S01.Complete.1080p.AMZN.WEB-DL.H264.DDP2.0.2Audios-UBWEB",
        "title": "Crayon Shin chan Spin off O O O No Shinnosuke",
        "primary": "蜡笔小新外传4 妖怪与新之助",
        "year": 2017,
        "kind": "tv",
        "season": 1,
        "candidates": ["蜡笔小新外传4 妖怪与新之助", "Crayon Shin chan Spin off O O O No Shinnosuke"],
    },
    {
        "name": "[密阳].Secret.Sunshine.2007.JPN.4K.REMASTERED.BluRay.1080p.x264.DTS-CMCT",
        "title": "Secret Sunshine",
        "primary": "密阳",
        "year": 2007,
        "kind": "movie",
        "candidates": ["密阳", "Secret Sunshine"],
    },
    {
        "name": "创：战纪.TRON.Legacy.2010.2160p.Repack.USA.Blu-ray.Dolby.Vision.HEVC.DTS-HD.MA.TrueHD.7.1.Atmos-LINMENG@CHDBits",
        "title": "TRON Legacy",
        "primary": "创：战纪",
        "year": 2010,
        "kind": "movie",
        "candidates": ["创：战纪", "TRON Legacy"],
    },
    {
        "name": "2021.Snooker.UK.Championship.20211129.HDTV.1080i.H264-HDSTV.ts",
        "title": "Snooker UK Championship 20211129",
        "year": 2021,
        "kind": "movie",
    },
    {
        "name": "[芝加哥警署 第十三季].Chicago.P.D..2025.S13.Complete.1080p.NowPlayer.WEB-DL.H264.AAC-UBWEB",
        "title": "Chicago P.D.",
        "primary": "芝加哥警署 第十三季",
        "year": 2025,
        "kind": "tv",
        "season": 13,
        "candidates": ["芝加哥警署", "Chicago P.D."],
    },
    {
        "name": "One.Flew.Over.the.Cuckoo's.Nest.1975.2160p.GER.UHD.Blu-ray.HEVC.DTS-HD.MA5.1-DiY@HDHome",
        "title": "One Flew Over the Cuckoo's Nest",
        "year": 1975,
        "kind": "movie",
    },
    {
        "name": "Stargate.1994.Director's.Cut.1080p.BluRay.x264.DTS-WiKi",
        "title": "Stargate",
        "year": 1994,
        "kind": "movie",
    },
    {
        "name": "[你不是她].You're.Just.Not.Her.2023.S01.Complete.1080p.TVBAnywhere.WEB-DL.H264.AAC.4Audios-UBWEB",
        "title": "You're Just Not Her",
        "primary": "你不是她",
        "year": 2023,
        "kind": "tv",
        "season": 1,
        "candidates": ["你不是她", "You're Just Not Her"],
    },
    {
        "name": "Ray.2004.V2.2160p.USA.UHD.Blu-ray.DV.HDR.HEVC.DTS-HD.MA.5.1-DKK@HDSky",
        "title": "Ray",
        "year": 2004,
        "kind": "movie",
    },
    {
        "name": "查克的一生.The.Life.of.Chuck.2024.V2.ITA.UHD.Blu-ray.2160p.HEVC.DTS.HD.MA.5.1-sh@CHDBits",
        "title": "The Life of Chuck",
        "primary": "查克的一生",
        "year": 2024,
        "kind": "movie",
        "candidates": ["查克的一生", "The Life of Chuck"],
    },
    {
        "name": "了不起的麦瑟尔夫人.S01-S03.2017-2019.1080p.WEB-DL.x265.AC3￡cXcY@FRDS",
        "title": "了不起的麦瑟尔夫人",
        "year": 2017,
        "year_text": "2017-2019",
        "kind": "tv",
        "season": 1,
        "season_text": "S01-S03",
    },
    {
        "name": "爱在三部曲.1999-2013.CC.1080p.中英字幕￡CMCT风潇潇",
        "title": "爱在三部曲",
        "year": 1999,
        "year_text": "1999-2013",
        "kind": "movie",
    },
    {
        "name": "中央车站.1998.BRA.1080p.国葡双语.简繁中字￡CMCT风潇潇",
        "title": "中央车站",
        "year": 1998,
        "kind": "movie",
    },
    {
        "name": "国王的演讲.2010.1080p.国英双语.中英字幕￡CMCT风潇潇",
        "title": "国王的演讲",
        "year": 2010,
        "kind": "movie",
    },
    {
        "name": "巴尔扎克与小裁缝.2002.国语中字￡CMCT风潇潇",
        "title": "巴尔扎克与小裁缝",
        "year": 2002,
        "kind": "movie",
    },
    {
        "name": "克莱默夫妇.Kramer.vs.Kramer.1979.1080p.USA.Blu-ray.AVC.TrueHD.5.1-DIY@UBits",
        "title": "Kramer vs Kramer",
        "primary": "克莱默夫妇",
        "year": 1979,
        "kind": "movie",
        "candidates": ["克莱默夫妇", "Kramer vs Kramer"],
    },
    {
        "name": "Fleabag.S01.1080p.BluRay.x264-SHORTBREHD",
        "title": "Fleabag",
        "year": None,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "The.Grand.Tour.S01.2160p.AMZN.WEB-DL.DDP5.1.HDR.HEVC-HHWEB",
        "title": "The Grand Tour",
        "year": None,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "The.Office.US.S01.1080p.AMZN.WEB-DL.DDP2.0.H.264-playWEB",
        "title": "The Office US",
        "year": None,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "This.Is.Going.to.Hurt.S01.1080p.AMZN.WEB-DL.DDP2.0.H.264-HHWEB",
        "title": "This Is Going to Hurt",
        "year": None,
        "kind": "tv",
        "season": 1,
    },
    {
        "name": "The.Hitchhiker's.Guide.To.The.Galaxy.2005.Blu-ray.AVC.LPCM.5.1-DiY@HDHome",
        "title": "The Hitchhiker's Guide To The Galaxy",
        "year": 2005,
        "kind": "movie",
    },
    {
        "name": "Who's.Gone.2024.1080p.BluRay.x265.10bit-WiKi",
        "title": "Who's Gone",
        "year": 2024,
        "kind": "movie",
    },
]


class MediaNameParserTest(unittest.TestCase):
    def test_parses_numeric_title_movie_year(self):
        parsed = parse_media_name(
            "2001.A.Space.Odyssey.1968.PROPER.2160p.UHD.Blu-ray.HEVC.DTS-HD.MA.5.1-DiY@HDHome"
        )

        self.assertEqual(parsed.title, "2001 A Space Odyssey")
        self.assertEqual(parsed.year, 1968)
        self.assertEqual(parsed.kind_hint, "movie")

    def test_parses_second_numeric_title_movie_year(self):
        parsed = parse_media_name(
            "2010.the.Year.We.Make.Contact.1984.1080p.BluRay.VC-1.DTS-HD.MA.5.1-DIY@Audies"
        )

        self.assertEqual(parsed.title, "2010 the Year We Make Contact")
        self.assertEqual(parsed.year, 1984)

    def test_uses_latin_canonical_title_but_searches_chinese_first(self):
        parsed = parse_media_name(
            "[爱情神话].B.for.Busy.2021.2160p.WEB-DL.HQ.HDRVivid.H265.10bit.DTS5.1-UBWEB.mkv"
        )

        self.assertEqual(parsed.title, "B for Busy")
        self.assertEqual(parsed.primary_search_title, "爱情神话")
        self.assertEqual(parsed.year, 2021)
        self.assertEqual(parsed.title_candidates[:3], ["爱情神话", "爱情神话 B for Busy", "B for Busy"])

    def test_keeps_latin_candidate_after_chinese_number_title(self):
        parsed = parse_media_name(
            "300勇士：帝国崛起.300.Rise.of.an.Empire.2014.1080p.TWN.BluRay.REMUX.AVC.DTS-HD.MA.7.1-UBits"
        )

        self.assertEqual(parsed.title, "300 Rise of an Empire")
        self.assertEqual(parsed.primary_search_title, "300勇士：帝国崛起")
        self.assertEqual(parsed.year, 2014)
        self.assertEqual(
            parsed.title_candidates[:3],
            ["300勇士：帝国崛起", "300勇士：帝国崛起 300 Rise of an Empire", "300 Rise of an Empire"],
        )

    def test_prefers_non_ascii_candidate_for_mixed_script_title(self):
        parsed = parse_media_name(
            "Жизнь.и.судьба.Life.and.Fate.2012.S01.1080p.WEB-DL.x264-GROUP"
        )

        self.assertEqual(parsed.title, "Life and Fate")
        self.assertEqual(parsed.primary_search_title, "Жизнь и судьба")
        self.assertEqual(parsed.title_candidates[:3], ["Жизнь и судьба", "Жизнь и судьба Life and Fate", "Life and Fate"])

    def test_uses_latin_canonical_title_for_no_doubt_in_us_release(self):
        parsed = parse_media_name(
            "[两心不疑].No.Doubt.in.Us.2026.S01.Complete.1080p.WEB-DL.H265.AAC-UBWEB"
        )

        self.assertEqual(parsed.title, "No Doubt in Us")
        self.assertEqual(parsed.primary_search_title, "两心不疑")
        self.assertEqual(parsed.title_candidates[:3], ["两心不疑", "两心不疑 No Doubt in Us", "No Doubt in Us"])
        self.assertEqual(parsed.year, 2026)
        self.assertEqual(parsed.kind_hint, "tv")

    def test_to_dict_includes_primary_search_title(self):
        parsed = parse_media_name("[爱情神话].B.for.Busy.2021.2160p.WEB-DL.H265-GROUP")

        payload = parsed.to_dict()

        self.assertEqual(payload["title"], "B for Busy")
        self.assertEqual(payload["primary_search_title"], "爱情神话")

    def test_parses_tv_season_with_year(self):
        parsed = parse_media_name("Billions.S01.2016.1080p.NF.WEB-DL.H.264.DDP.5.1-FROGWeb")

        self.assertEqual(parsed.title, "Billions")
        self.assertEqual(parsed.year, 2016)
        self.assertEqual(parsed.kind_hint, "tv")
        self.assertEqual(parsed.season, 1)
        self.assertIsNone(parsed.episode)

    def test_parses_tv_episode_without_year(self):
        parsed = parse_media_name("The.Last.of.Us.S01E04.1080p.HMAX.WEB-DL.DDP5.1.x264-NTb.mkv")

        self.assertEqual(parsed.title, "The Last of Us")
        self.assertEqual(parsed.kind_hint, "tv")
        self.assertEqual(parsed.season, 1)
        self.assertEqual(parsed.episode, 4)
        self.assertIn("could not infer release year", parsed.warnings)

    def test_preserves_year_range_text_for_collection(self):
        parsed = parse_media_name(
            "Indiana Jones The Complete Adventures 1981-2008 UHD Blu-Ray 2160p HEVC-CHDBits"
        )

        self.assertEqual(parsed.title, "Indiana Jones The Complete Adventures")
        self.assertEqual(parsed.year, 1981)
        self.assertEqual(parsed.year_text, "1981-2008")

    def test_preserves_season_and_episode_ranges(self):
        parsed = parse_media_name("Arcane S02E01-E03 2024 V2 1080p NF WEB-DL x264-ADWeb")

        self.assertEqual(parsed.title, "Arcane")
        self.assertEqual(parsed.year_text, "2024")
        self.assertEqual(parsed.season_text, "S02")
        self.assertEqual(parsed.episode_text, "E01-E03")

    def test_parses_episode_only_as_first_season(self):
        parsed = parse_media_name("Fan.Ren.Xiu.Xian.Zhuan.E32.1080p.WEB-DL.H264.AAC-CHDWEB.mp4")

        self.assertEqual(parsed.title, "Fan Ren Xiu Xian Zhuan")
        self.assertEqual(parsed.season_text, "S01")
        self.assertEqual(parsed.episode_text, "E32")

    def test_parses_chinese_season_and_episode_words(self):
        parsed = parse_media_name("托马斯和他的朋友们第18季 第4集_3840x2160_H265.mp4")

        self.assertEqual(parsed.title, "托马斯和他的朋友们")
        self.assertEqual(parsed.primary_search_title, "托马斯和他的朋友们")
        self.assertEqual(parsed.season_text, "S18")
        self.assertEqual(parsed.episode_text, "E4")

    def test_keeps_slash_aka_release_name_as_raw_name(self):
        parsed = parse_media_name(
            "[鲁邦三世VS名侦探柯南 THE MOVIE]Lupin the 3rd vs Detective Conan THE MOVIE / "
            "Lupin Sansei vs. Meitantei Conan The Movie[ルパン三世vs名探偵コナン THE MOVIE][BDMV]"
        )

        self.assertIn("Lupin the 3rd vs Detective Conan THE MOVIE", parsed.title_candidates)

    def test_ignores_catalog_year_in_braces(self):
        parsed = parse_media_name("Bob Dylan - Bringing It All Back Home (1965) [FLAC] {2013 MFSL}")

        self.assertEqual(parsed.year_text, "1965")
        self.assertIn("Bob Dylan Bringing It All Back Home", parsed.title_candidates)

    def test_strips_broadcaster_prefix_from_title_candidate(self):
        parsed = parse_media_name("CCTV5+.2021.Snooker.UK.Championship.20211129.HDTV.1080i.H264-HDSTV.ts")

        self.assertEqual(parsed.year_text, "2021")
        self.assertIn("Snooker UK Championship 20211129", parsed.title_candidates)

    def test_restores_high_confidence_title_abbreviations(self):
        cases = [
            ("Mr.Robot.S01.2015.1080p.WEB-DL.H264-GROUP", "Mr. Robot"),
            ("Mrs.Davis.S01.2023.1080p.WEB-DL.H264-GROUP", "Mrs. Davis"),
            ("Ms.45.1981.720p.BluRay.FLAC1.0.x264-PTer", "Ms. 45"),
            ("Prof.T.S01.2021.1080p.WEB-DL.H264-GROUP", "Prof. T"),
            ("Robert.Downey.Jr.2020.1080p.WEB-DL.H264-GROUP", "Robert Downey Jr."),
            ("Robert.Downey.Sr.2022.1080p.WEB-DL.H264-GROUP", "Robert Downey Sr."),
            ("Thesis.Ph.D.2020.1080p.WEB-DL.H264-GROUP", "Thesis PhD"),
            ("Research.P.H.D.2020.1080p.WEB-DL.H264-GROUP", "Research PhD"),
        ]

        for name, title in cases:
            with self.subTest(name=name):
                parsed = parse_media_name(name)

                self.assertEqual(parsed.title, title)

    def test_long_raw_release_name_does_not_probe_as_path(self):
        release_name = (
            "[剧场版 Healin' Good 光之美少女 梦想的小镇心动不已! GoGo! 大变身!!]"
            "[Eiga Healin' Good Precure Yume no Machi de Kyun! Tto Go Go! Dai Henshin!!]"
            "[映画ヒーリングっど プリキュア ゆめのまちでキュン!っとGoGo!大変身!!/"
            "(短編)映画トロピカル~ジュ!プリキュアとびこめ!コラボダンスパーティ!][BDMV][MOVIE]"
        )

        parsed = parse_media_name(release_name)

        self.assertIn("Eiga Healin' Good Precure Yume no Machi de Kyun! Tto Go Go! Dai Henshin!!", parsed.title_candidates)

    def test_non_media_extension_lowers_confidence(self):
        parsed = parse_media_name("Nando Parrado - Miracle in the Andes.epub")

        self.assertIn("unsupported extension: .epub", parsed.warnings)
        self.assertLess(parsed.confidence, 0.5)

    def test_real_download_folder_names(self):
        for case in REAL_DOWNLOAD_CASES:
            with self.subTest(name=case["name"]):
                parsed = parse_media_name(case["name"])

                self.assertEqual(parsed.title, case["title"])
                self.assertEqual(parsed.primary_search_title, case.get("primary", case["title"]))
                self.assertEqual(parsed.year, case["year"])
                self.assertEqual(parsed.kind_hint, case["kind"])

                if "year_text" in case:
                    self.assertEqual(parsed.year_text, case["year_text"])
                if "season" in case:
                    self.assertEqual(parsed.season, case["season"])
                if "season_text" in case:
                    self.assertEqual(parsed.season_text, case["season_text"])
                for candidate in case.get("candidates", []):
                    self.assertIn(candidate, parsed.title_candidates)


if __name__ == "__main__":
    unittest.main()

import unittest
from vi.chatparser import parser_functions
from vi.chatparser.message import Message
from bs4 import BeautifulSoup
from vi.states import States
from vi.dotlan import Map
from vi.clipboard import evaluateClipboardData
from vi.evegate import getSvgFromDotlan

SVG_SYSTEM_USED = getSvgFromDotlan(region="providence", dark=True)
ALL_SYSTEMS_FROM_SVG = Map("Providence", SVG_SYSTEM_USED).systems


class TestIntel(unittest.TestCase):
    # Cache.PATH_TO_CACHE = os.path.join(os.path.expanduser("~"), "Documents", "EVE", "spyglass", "cache-2.sqlite3")
    # cache_used = Cache()
    # evegate.setEsiCharName("nele McCool")

    def test_zh_change_local(self):
        message = parser_functions.parseLocal(path="", char_name="", line=u"﻿[ 2023.12.09 08:09:32 ] EVE系统 > 频道更换为本地：撒了库瓦*")
        self.assertEqual(message.status, States.LOCATION, "System change should be detected.")
        self.assertIn(u'撒了库瓦', message.affectedSystems, "System 撒了库瓦 should be detected.")

    def test_jp_change_local(self):
        message = parser_functions.parseLocal(path="", char_name=u"", line=u"﻿[ 2023.12.09 10:45:29 ] EVE システム > チャンネル名が ローカル : ニューカルダリ* に変更されました")
        self.assertEqual(message.status, States.LOCATION, "System change should be detected.")
        self.assertIn(u'ニューカルダリ', message.affectedSystems, "System ニューカルダリ should be detected.")

    def test_ko_change_local(self):
        message = parser_functions.parseLocal(path="", char_name=u"", line=u"﻿[ 2023.12.09 10:49:22 ] 이브 시스템 > 지역 : 조사메토* 채널로 변경")
        self.assertEqual(message.status, States.LOCATION, "System change should be detected.")
        self.assertIn(u'조사메토', message.affectedSystems, "System 조사메토 should be detected.")

    def test_de_change_local(self):
        message = parser_functions.parseLocal(path="", char_name=u"", line=u"﻿[ 2023.12.09 10:55:14 ] EVE-System > Chatkanal geändert zu Lokal: Josameto*")
        self.assertEqual(message.status, States.LOCATION, "System change should be detected.")
        self.assertIn(u'Josameto', message.affectedSystems, "System Josameto should be detected.")

    def test_en_change_local(self):
        message = parser_functions.parseLocal(path="", char_name=u"", line=u"﻿[ 2023.12.09 11:08:14 ] EVE System > Channel changed to Local : Josameto")
        self.assertEqual(message.status, States.LOCATION, "System change should be detected.")
        self.assertIn(u'Josameto', message.affectedSystems, "System 撒了库瓦 should be detected.")

    def test_fr_change_local(self):
        message = parser_functions.parseLocal(path="", char_name=u"", line=u"﻿[ 2023.12.09 11:16:24 ] Système EVE > Canal changé en Local : Josameto*")
        self.assertEqual(message.status, States.LOCATION, "System change should be detected.")
        self.assertIn(u'Josameto', message.affectedSystems, "System Josameto should be detected.")

    def test_rus_change_local(self):
        message = parser_functions.parseLocal(path="", char_name=u"", line=u"﻿[ 2023.12.09 11:18:36 ] Система EVE > Канал изменен на Локальный: Josameto*")
        self.assertEqual(message.status, States.LOCATION, "System change should be detected.")
        self.assertIn(u'Josameto', message.affectedSystems, "System Josameto should be detected.")

    def test_es_change_local(self):
        message = parser_functions.parseLocal(path="", char_name=u"", line=u"﻿[ 2023.12.09 11:21:00 ] Sistema EVE > El canal ha cambiado a Local: Josameto*.")
        self.assertEqual(message.status, States.LOCATION, "System change should be detected.")
        self.assertIn(u'Josameto', message.affectedSystems, "System Josameto should be detected.")

    def test_mesage_parser_with(self):

        system = ALL_SYSTEMS_FROM_SVG.get("18-GZM")
        self.assertTrue(system.status != States.ALARM, "System 18-GSM status not alarm failed.")
        region_name = [sys.upper() for sys in ALL_SYSTEMS_FROM_SVG]
        msg = Message(room="", message="[2023.08.12 13:33:22 ]Ian McCool> 18-GZM Kesteri Patrouette nv")
        res = parser_functions.parseMessageForMap(ALL_SYSTEMS_FROM_SVG, msg)
        self.assertTrue(system.status == States.ALARM, "System 18-GSM status alarm failed.")

        msg = Message(room="", message="[2023.08.12 13:33:23 ]Ian McCool> Jita clr")
        res = parser_functions.parseMessageForMap(ALL_SYSTEMS_FROM_SVG, msg)
        self.assertTrue(system.status == States.ALARM, "System 18-GSM status alarm failed.")

        msg = Message(room="", message="[2023.08.12 13:33:23 ]Ian McCool> 18-GZM clr")
        res = parser_functions.parseMessageForMap(ALL_SYSTEMS_FROM_SVG, msg)
        self.assertTrue(system.status == States.CLEAR, "System 18-GSM status clear failed.")

    def test_system_parser_with_camel_case(self):
        region_name = [sys.upper() for sys in ALL_SYSTEMS_FROM_SVG]
        formatted_text = u"<rtext>{0}</rtext>".format("Dital clr")
        soup = BeautifulSoup(formatted_text, 'lxml-xml')
        rtext = soup.select("rtext")[0]
        res_systems = set()
        parser_functions.parseSystems(ALL_SYSTEMS_FROM_SVG, rtext, res_systems)
        self.assertFalse(res_systems == set(), "System name 'Dital' not fetched correct as Dital")
        if res_systems:
            for item in res_systems:
                self.assertEqual("Dital", item.name, "System name 'Dital' not fetched correct as Dital")

    def test_system_parser_two_system_one_read_one_clr(self):
        region_name = [sys.upper() for sys in ALL_SYSTEMS_FROM_SVG]
        formatted_text = u"<rtext>{0}</rtext>".format("18-GZM +6")
        soup = BeautifulSoup(formatted_text, 'lxml-xml')
        rtext = soup.select("rtext")[0]
        res_systems = set()
        while parser_functions.parseSystems(ALL_SYSTEMS_FROM_SVG, rtext, res_systems):
            pass
        res_state = parser_functions.parseStatus(rtext)
        self.assertFalse(res_systems == set(), "System name '18-GZM' not fetched correct as 18-GZM")
        if res_systems:
            for item in res_systems:
                self.assertEqual("18-GZM", item.name, "System name '18-GZM' not fetched correct as 18-GZM")
                self.assertEqual(States.ALARM, res_state, "System state for '18-GZM' not fetched correct as UNKNOWN")

        formatted_text = u"<rtext>{0}</rtext>".format("juk clr")
        soup = BeautifulSoup(formatted_text, 'lxml-xml')
        rtext = soup.select("rtext")[0]
        res_systems_two = set()
        while parser_functions.parseSystems(ALL_SYSTEMS_FROM_SVG, rtext, res_systems_two):
            pass

        self.assertFalse(res_systems_two == set(), "System name 'Juk' not correct fetched as empty set")

    def test_system_parser_with_upper_case(self):
        formatted_text = u"<rtext>{0}</rtext>".format("DITAL clr")
        soup = BeautifulSoup(formatted_text, 'lxml-xml')
        rtext = soup.select("rtext")[0]
        res_systems = set()
        parser_functions.parseSystems(ALL_SYSTEMS_FROM_SVG, rtext, res_systems)
        self.assertFalse(res_systems == set(), "System name 'DITAL' not fetched correct as Dital")
        if res_systems:
            for item in res_systems:
                self.assertEqual("Dital", item.name, "System name 'DITAL' not fetched correct as Dital")

    def test_system_parser_with_start_case(self):
        formatted_text = u"<rtext>{0}</rtext>".format("Dital* clr")
        soup = BeautifulSoup(formatted_text, 'lxml-xml')
        rtext = soup.select("rtext")[0]
        res_systems = set()
        parser_functions.parseSystems(ALL_SYSTEMS_FROM_SVG, rtext, res_systems)
        self.assertFalse(res_systems == set(), "System name 'Dital*' not fetched correct as Dital")
        if res_systems:
            for item in res_systems:
                self.assertEqual("Dital", item.name, "System name 'Dital*' not fetched correct as Dital")

    def test_system_parser_with_segment_case(self):
        formatted_text = u"<rtext>{0}</rtext>".format("TXJ clear")
        soup = BeautifulSoup(formatted_text, 'lxml-xml')
        rtext = soup.select("rtext")[0]
        res_systems = set()
        parser_functions.parseSystems(ALL_SYSTEMS_FROM_SVG, rtext, res_systems)
        self.assertFalse(res_systems == set(), "System name 'TXJ' not fetched correct as TXJ-II")
        if res_systems:
            for item in res_systems:
                self.assertEqual("TXJ-II", item.name, "System name 'TXJ' not fetched correct as TXJ-II")

    def test_system_parser_ship_names(self):
        formatted_text = u"<rtext>{0}</rtext>".format("TXJ Anna caldari navy hookbill")
        soup = BeautifulSoup(formatted_text, 'lxml-xml')
        rtext = soup.select("rtext")[0]
        res_systems = set()
        parser_functions.parseSystems(ALL_SYSTEMS_FROM_SVG, rtext, res_systems)
        self.assertFalse(res_systems == set(), "System name 'TXJ' not fetched correct as TXJ-II")
        if res_systems:
            for item in res_systems:
                self.assertEqual("TXJ-II", item.name, "System name 'TXJ' not fetched correct as TXJ-II")
        self.assertTrue(parser_functions.parseShips(rtext))

    def test_evaluateClipboardData(self):
        res, data = evaluateClipboardData("<url=showinfo:35832//1039859073627>2PG-KN - Churchwood</url>")
        self.assertEqual(res, "poi", "Structure should be POI")
        res, data = evaluateClipboardData("<url=showinfo:52678//60003760 alt='Current Station'>Jita IV - Moon 4 - Caldari Navy Assembly Plant</url>")
        self.assertEqual(res, "poi", "Structure should be POI")
        res, data = evaluateClipboardData("OX-S7P » 8CN-CH - Speedway 2")
        self.assertEqual(res, "jumpbridge", "Structure should be jumpbridge")

    def test_removeXmlData(self):
        soup = BeautifulSoup('<a style="color:#28a5ed;font-weight:medium" href="link/https://zkillboard.com/kill/112877325/">https://zkillboard.com/kill/112877325/</a><br/> Nani   <a  style="color:#d0d0d0;font-weight:bold" href="link/https://zkillboard.com/character/2118188243/">Aatoh Maken</a>  &lt;REKTD&gt; ( <a  style="color:#d0d0d0;font-weight:bold" href="link/https://zkillboard.com/alliance/99005338/">Pandemic Horde</a> ) lost a <a  style="color:#d95911;font-weight:bold" href="link/https://wiki.eveuniversity.org/Capsule">Capsule</a>', 'lxml-xml')
        [s.extract() for s in soup(['href', 'br'])]
        res = soup.getText()
        http_start = res.find("http")
        if http_start != -1:
            http_end = res.find(" ", http_start)
            substr = res[http_start:http_end]
            res = res.replace(substr, "")
        corp_start = res.find("<")
        if corp_start != -1:
            corp_end = res.find(" ", corp_start)
            substr = res[corp_start:corp_end]
            res = res.replace(substr, "")
        res = res.replace("(", "from ")
        res = res.replace(")", ", ")

        print(res)

import unittest
from vi.chatparser import parser_functions
from vi.chatparser.message import Message, formatZKillMessage
from bs4 import BeautifulSoup
from vi.states import States
from vi.dotlan import Map
from vi.clipboard import evaluateClipboardData
from vi.evegate import getSvgFromDotlan
SVG_SYSTEM_USED = getSvgFromDotlan(region="Providence", dark=True)
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

    def test_key_message_parser(self):
        test_data = [u"﻿[ 2025.02.16 16:43:28 ] Hullbeam > TDP-T3* clr",
                     u"﻿[ 2025.02.16 16:43:29 ] Hullbeam > TDP-T3* clr.",
                     u"﻿[ 2025.02.16 16:43:30 ] Hullbeam > TDP-T3* is clr now.",
                     u"﻿[ 2025.02.16 12:52:19 ] Hullbeam > TDP-T3*  clear",
                     u"﻿[ 2025.02.16 16:43:28 ] Mac4LL4N > TDP-T3 CLR",
                     u"﻿[ 2025.02.16 16:41:42 ] Mac4LL4N > TDP CLR",
                     u"﻿[ 2025.02.16 16:41:42 ] Mac4LL4N > TDP-T3  CLEAR"
                     ]

        SVG_SYSTEM_USED = getSvgFromDotlan(region="Perrigen Falls", dark=True)
        ALL_SYSTEMS_FROM_SVG = Map("Perrigen Falls", SVG_SYSTEM_USED).systems

        system = ALL_SYSTEMS_FROM_SVG.get("TDP-T3")
        self.assertIsNotNone(system,"System TDP-T3 is None.")
        self.assertTrue(system.status != States.ALARM, "System TDP-T3 status not alarm failed.")
        message_a = Message(room="", message=test_data[0])
        self.assertEqual(message_a,message_a,"equal failed")

        for msg_text in test_data[1:]:
            message_b = Message(room="", message=test_data[1])
            self.assertNotEqual(message_a, message_b, "not equal failed")
            a_hash = message_a.__hash__()
            b_hash = message_b.__hash__()
            self.assertNotEqual(message_a.__hash__(), message_b.__hash__(), "not equal hash failed")


    def test_well_formatted_message_parser_with_result_clr(self):
        test_data = [u"﻿[ 2025.02.16 16:43:28 ] Hullbeam > TDP-T3* clr",
                     u"﻿[ 2025.02.16 16:43:28 ] Hullbeam > TDP-T3* clr.",
                     u"﻿[ 2025.02.16 16:43:28 ] Hullbeam > TDP-T3* is clr now.",
                     u"﻿[ 2025.02.16 12:52:19 ] Hullbeam > TDP-T3*  clear",
                     u"﻿[ 2025.02.16 16:41:42 ] Mac4LL4N > TDP-T3 CLR",
                     u"﻿[ 2025.02.16 16:41:42 ] Mac4LL4N > TDP CLR",
                     u"﻿[ 2025.02.16 16:41:42 ] Mac4LL4N > TDP-T3  CLEAR"
                     ]

        SVG_SYSTEM_USED = getSvgFromDotlan(region="Perrigen Falls", dark=True)
        ALL_SYSTEMS_FROM_SVG = Map("Perrigen Falls", SVG_SYSTEM_USED).systems

        system = ALL_SYSTEMS_FROM_SVG.get("TDP-T3")
        self.assertIsNotNone(system,"System TDP-T3 is None.")
        self.assertTrue(system.status != States.ALARM, "System TDP-T3 status not alarm failed.")
        for msg_text in test_data:
            parser_functions.parseMessageForMap(ALL_SYSTEMS_FROM_SVG, Message(room="", message="﻿[ 2025.02.16 12:52:19 ] Hullbeam > TDP-T3*  +10"))
            self.assertTrue(system.status == States.ALARM, "System  status alarm failed.")
            parser_functions.parseMessageForMap(ALL_SYSTEMS_FROM_SVG, Message(room="", message=msg_text))
            self.assertTrue(system.status == States.CLEAR, "System  status alarm failed with message {}.".format(msg_text))
            system.clearIntel()


    def test_well_formatted_message_parser_with_result_alarm(self):
        test_data = ["﻿[ 2025.02.17 12:06:48 ] RazorDM > TDP-T3  Coco Divan  Hultaji Gogiko  Pleb  Stara Isu Plebowsky nv",
                     "﻿[ 2025.02.16 16:43:28 ] Hullbeam > MDL SP'Slave 3  TDP-T3  nv",
                     "﻿[ 2025.02.16 12:52:19 ] Hullbeam > TDP-T3*  AngelaBalzac  ashes of vanished  短剑级* *1 nv",
                     "﻿[ 2025.02.16 16:43:28 ] AustinG24 > Amarr Shuttle  TDP-T3  IJNUHB 2233",
                     "﻿[ 2025.02.16 16:42:00 ] Beca Benito Juarez > Keramika  TDP-T3 nv",
                     "﻿[ 2025.02.16 12:53:08 ] LeaMa Fox > TDP-T3*  Noriphe Oxasson",
                     "﻿[ 2025.02.16 12:59:14 ] KUAITAO > 送葬者级海军型*  短剑级*",
                     "﻿[ 2025.02.16 16:41:13 ] Mac4LL4N > TDP-T3  Bevien",
                     "﻿[ 2025.02.16 16:41:22 ] Letol > Goonswarm Federation  TDP-T3* 7+ nv",
                     "﻿[ 2025.02.16 16:41:42 ] Mac4LL4N > TDP-T3  Bevien"
                     ]

        SVG_SYSTEM_USED = getSvgFromDotlan(region="Perrigen Falls", dark=True)
        ALL_SYSTEMS_FROM_SVG = Map("Perrigen Falls", SVG_SYSTEM_USED).systems

        system = ALL_SYSTEMS_FROM_SVG.get("TDP-T3")
        self.assertIsNotNone(system,"System TDP-T3 is None.")
        self.assertTrue(system.status != States.ALARM, "System TDP-T3 status not alarm failed.")
        for msg_text in test_data:
            parser_functions.parseMessageForMap(ALL_SYSTEMS_FROM_SVG, Message(room="", message="﻿[ 2025.02.16 12:52:19 ] Hullbeam > TDP-T3*  clear"))
            self.assertTrue(system.status == States.CLEAR, "System status clear failed.")
            parser_functions.parseMessageForMap(ALL_SYSTEMS_FROM_SVG, Message(room="", message=msg_text))
            self.assertTrue(system.status == States.ALARM, "System  status alarm failed with message {}.".format(msg_text))
            msg_gui = system.getTooltipText()
            system.clearIntel()



    def test_removeXmlData(self):
        res = formatZKillMessage('<a style="color:#28a5ed;font-weight:medium" href="link/https://zkillboard.com/kill/123332493/">https://zkillboard.com/kill/123332493/</a><br/> <a  style="color:#d0d0d0;font-weight:medium" href="link/https://zkillboard.com/character/2120227048/">Khorum MkII</a> &lt;REKTD&gt;( <a  style="color:#d0d0d0;font-weight:medium" href="link/https://zkillboard.com/alliance/99005338/">Pandemic Horde</a>) lost their <a  style="color:#d95911;font-weight:medium" href="link/https://wiki.eveuniversity.org/Capsule">Capsule</a> in  AD144 .<a style="color:#d0d0d0;font-weight:medium"><br/>Total Value : 320,866,530.18 ISK</a>')
        res = formatZKillMessage('<a style="color:#28a5ed;font-weight:medium" href="link/https://zkillboard.com/kill/112877325/">https://zkillboard.com/kill/112877325/</a><br/> Nani   <a  style="color:#d0d0d0;font-weight:bold" href="link/https://zkillboard.com/character/2118188243/">Aatoh Maken</a>  &lt;REKTD&gt; ( <a  style="color:#d0d0d0;font-weight:bold" href="link/https://zkillboard.com/alliance/99005338/">Pandemic Horde</a> ) lost a <a  style="color:#d95911;font-weight:bold" href="link/https://wiki.eveuniversity.org/Capsule">Capsule</a>')
        self.assertEqual(res, "System Nani, Aatoh Maken, from Pandemic Horde, lost a Capsule")
        res = formatZKillMessage(
            '<a style="color:#28a5ed;font-weight:medium" href="link/https://zkillboard.com/kill/112877325/">https://zkillboard.com/kill/112877325/</a><br/> Nani   <a  style="color:#d0d0d0;font-weight:bold" href="link/https://zkillboard.com/character/2118188243/">Aatoh Maken</a>  &lt;REKTD&gt; ( <a  style="color:#d0d0d0;font-weight:bold" href="link/https://zkillboard.com/alliance/99005338/">Pandemic Horde</a> ) lost a <a  style="color:#d95911;font-weight:bold" href="link/https://wiki.eveuniversity.org/Capsule">Capsule</a>')
        print(res)


import unittest
import os
from vi.cache import Cache
import vi.evegate as evegate
from vi.dotlan import Map, System
from vi.chatparser import parser_functions
from bs4 import BeautifulSoup
from vi.universe import Universe
import json

from vi.clipboard import evaluateClipboardData


class TestIntel(unittest.TestCase):
    # Cache.PATH_TO_CACHE = "/home/jkeymer/Documents/EVE/spyglass/cache-2.sqlite3"
    # cache_used = Cache()
    # evegate.setEsiCharName("nele McCool")

    def test_system_parser_with_camel_case(self):
        all_systems = Map("providence").systems
        region_name = [sys.upper() for sys in all_systems]
        formatted_text = u"<rtext>{0}</rtext>".format("Dital clr")
        soup = BeautifulSoup(formatted_text, 'html.parser')
        rtext = soup.select("rtext")[0]
        res_systems = set()
        parser_functions.parseSystems(all_systems, rtext, res_systems)
        self.assertFalse(res_systems == set(), "System name 'Dital' not fetched correctas Dital")
        if res_systems:
            for item in res_systems:
                self.assertEqual("Dital", item.name, "System name 'Dital' not fetched correctas Dital")

    def test_system_parser_with_upper_case(self):
        all_systems = Map("providence").systems
        formatted_text = u"<rtext>{0}</rtext>".format("DITAL clr")
        soup = BeautifulSoup(formatted_text, 'html.parser')
        rtext = soup.select("rtext")[0]
        res_systems = set()
        parser_functions.parseSystems(all_systems, rtext, res_systems)
        self.assertFalse(res_systems == set(), "System name 'DITAL' not fetched correct as Dital")
        if res_systems:
            for item in res_systems:
                self.assertEqual("Dital", item.name, "System name 'DITAL' not fetched correct as Dital")

    def test_system_parser_with_start_case(self):
        all_systems = Map("providence").systems
        formatted_text = u"<rtext>{0}</rtext>".format("Dital* clr")
        soup = BeautifulSoup(formatted_text, 'html.parser')
        rtext = soup.select("rtext")[0]
        res_systems = set()
        parser_functions.parseSystems(all_systems, rtext, res_systems)
        self.assertFalse(res_systems == set(), "System name 'Dital*' not fetched correct as Dital")
        if res_systems:
            for item in res_systems:
                self.assertEqual("Dital", item.name, "System name 'Dital*' not fetched correct as Dital")

    def test_system_parser_with_segment_case(self):
        all_systems = Map("providence").systems
        formatted_text = u"<rtext>{0}</rtext>".format("TXJ clear")
        soup = BeautifulSoup(formatted_text, 'html.parser')
        rtext = soup.select("rtext")[0]
        res_systems = set()
        parser_functions.parseSystems(all_systems, rtext, res_systems)
        self.assertFalse(res_systems == set(), "System name 'TXJ' not fetched correct as TXJ-II")
        if res_systems:
            for item in res_systems:
                self.assertEqual("TXJ-II", item.name, "System name 'TXJ' not fetched correct as TXJ-II")

    def test_system_parser_ship_names(self):
        all_systems = Map("providence").systems
        formatted_text = u"<rtext>{0}</rtext>".format("TXJ Anna Succubus")
        soup = BeautifulSoup(formatted_text, 'html.parser')
        rtext = soup.select("rtext")[0]
        res_systems = set()
        parser_functions.parseSystems(all_systems, rtext, res_systems)
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

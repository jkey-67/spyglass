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

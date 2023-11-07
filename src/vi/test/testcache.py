import unittest
import os
from vi.cache import Cache
import vi.evegate as evegate
from vi.universe import Universe
import json
from vi.clipboard import evaluateClipboardData


class TestCache(unittest.TestCase):
    use_outdated_cache = False
    curr_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "universe")
    Cache.PATH_TO_CACHE = "/home/jkeymer/Documents/EVE/spyglass/cache-2.sqlite3"
    cache_used = Cache()
    evegate.setEsiCharName("nele McCool")

    def test_checkSpyglassVersionUpdate(self):
        res = evegate.checkSpyglassVersionUpdate(current_version="1.0.0", force_check=True)
        self.assertIsNotNone(res)

    def test_getSpyglassUpdateLink(self):
        res = evegate.getSpyglassUpdateLink()
        self.assertIsNotNone(res)

    def text_regionNameFromSystemID(self):
        res = Universe.regionNameFromSystemID(30000734)
        self.assertIsNotNone(res)

    def test_SystemNames(self):
        res = Universe.systemNames()
        self.assertIsNotNone(res)
        res = Universe.systemIdByName("Jita")
        self.assertIsNone(res)

    def test_intelSystems(self):
        res = Universe.monitoredSystems(30000734, 0)
        self.assertIn(30000734, res)
        res = Universe.monitoredSystems(30000734, 1)
        self.assertIn(30000734, res)
        self.assertIn(30000730, res)
        self.assertIn(30000732, res)
        self.assertIn(30000735, res)
        res = Universe.monitoredSystems(30000734, 12)
        res = Universe.monitoredSystems(12331, 1)
        self.assertIsNone(res)

    def test_loadStargates(self):
        with open(os.path.join(self.curr_path, "evestargates.json"), "r") as fp:
            res = json.load(fp)
            ids = {30000734: {"dist": 0}}
            for distance in range(0, 3):
                for i in [{sys["destination"]["system_id"]:{"dist": distance+1}}for sys in res if sys["system_id"] in ids.keys()]:
                    for key in list(i.keys()):
                        if key not in ids.keys():
                            ids.update(i)

        self.assertIsNotNone(ids)

    def test_loadSystems(self):
        with open(os.path.join(self.curr_path, "evesystems.json"), "r") as fp:
            res = json.load(fp)
            systems = [sys["system_id"] for sys in res if sys["constellation_id"] == 20000107]
        self.assertIsNotNone(systems)

    def test_update_all_json_files(self):
        use_outdated_cache = True
        self.test_generateShipnames()
        self.test_generateRegions()
        self.test_generateConstellations()
        use_outdated_cache = False
        self.test_generateStargates()
        use_outdated_cache = True

    def test_generateShipnames(self):
        res = evegate.esiUniverseCategories(6, use_outdated=self.use_outdated_cache)
        with open(os.path.join(self.curr_path, "shipnames.py"), "w") as ships_file:
            ships_file.write("# generated, do not modify\n")
            ships_file.write("SHIPNAMES = (")
            max_len = 80
            eol_txt = "\n        "
            ships_file.write(eol_txt)
            curr_len = len(eol_txt)
            cnt = 6
            first_entry = True
            for itm in res["groups"]:
                res = evegate.esiUniverseGroups(itm, use_outdated=self.use_outdated_cache)
                self.assertIsNotNone(res, "esiUniverseGroups should never return None")
                for res_type in res["types"]:
                    res = evegate.esiUniverseTypes(res_type, use_outdated=self.use_outdated_cache)
                    self.assertIsNotNone(res, "esiUniverseTypes should never return None")
                    ship_text = u'{{"id": {}, "name": "{}"}}'.format(res["type_id"], res["name"].upper())
                    curr_len = curr_len + len(ship_text)
                    if curr_len > max_len:
                        first_entry = True
                        ships_file.write(",")
                        ships_file.write(eol_txt)
                        curr_len = len(eol_txt) + 1
                    if first_entry:
                        first_entry = False
                        ships_file.write(ship_text)
                    else:
                        ships_file.write(", ")
                        ships_file.write(ship_text)

            ships_file.write(")\n")

    def test_generateRegions(self):
        res = evegate.esiUniverseGetAllRegions(use_outdated=self.use_outdated_cache)
        with open(os.path.join(self.curr_path, "everegions.json"), "w") as ships_file:
            ships_file.write("[")
            max_len = 80
            eol_txt = "\n        "
            ships_file.write(eol_txt)
            curr_len = len(eol_txt)
            cnt = 6
            first_entry = True
            for itm in res:
                res = evegate.esiUniverseRegions(itm, use_outdated=self.use_outdated_cache)
                ship_text = u'{}'.format(json.dumps(res))
                curr_len = curr_len + len(ship_text)
                if curr_len > max_len:
                    if not first_entry:
                        first_entry = True
                        ships_file.write(",")
                        ships_file.write(eol_txt)
                        curr_len = len(eol_txt) + 1
                if first_entry:
                    first_entry = False
                    ships_file.write(ship_text)
                else:
                    ships_file.write(", ")
                    ships_file.write(ship_text)

            ships_file.write("]\n")

    def test_generateConstellations(self):
        res = evegate.esiUniverseGetAllRegions(use_outdated=self.use_outdated_cache)
        with open(os.path.join(self.curr_path, "eveconstellations.json"), "w") as ships_file:
            ships_file.write("[")
            max_len = 80
            eol_txt = "\n        "
            ships_file.write(eol_txt)
            curr_len = len(eol_txt)
            cnt = 6
            first_entry = True
            for itm in res:
                res = evegate.esiUniverseRegions(itm, use_outdated=self.use_outdated_cache)
                self.assertIsNotNone(res, "esiUniverseGroups should never return None")
                for constellation_id in res["constellations"]:
                    res = evegate.esiUniverseConstellations(constellation_id, use_outdated=self.use_outdated_cache)
                    ship_text = u'{}'.format(json.dumps(res))
                    curr_len = curr_len + len(ship_text)
                    if curr_len > max_len:
                        if not first_entry:
                            first_entry = True
                            ships_file.write(",")
                            ships_file.write(eol_txt)
                            curr_len = len(eol_txt) + 1
                    if first_entry:
                        first_entry = False
                        ships_file.write(ship_text)
                    else:
                        ships_file.write(", ")
                        ships_file.write(ship_text)

            ships_file.write("]\n")

    def test_generateSystems(self):
        res = evegate.esiUniverseGetAllRegions(use_outdated=self.use_outdated_cache)
        with open(os.path.join(self.curr_path, "evesystems.json"), "w") as ships_file:
            ships_file.write("[")
            max_len = 80
            eol_txt = "\n        "
            ships_file.write(eol_txt)
            curr_len = len(eol_txt)
            cnt = 6
            first_entry = True
            for itm in res:
                res = evegate.esiUniverseRegions(itm, use_outdated=self.use_outdated_cache)
                self.assertIsNotNone(res, "esiUniverseGroups should never return None")
                for constellation_id in res["constellations"]:
                    res = evegate.esiUniverseConstellations(constellation_id, use_outdated=self.use_outdated_cache)
                    for sys_id in res["systems"]:
                        res = evegate.esiUniverseSystems(sys_id, use_outdated=self.use_outdated_cache)
                        ship_text = u'{}'.format(json.dumps(res))
                        curr_len = curr_len + len(ship_text)
                        if curr_len > max_len:
                            if not first_entry:
                                first_entry = True
                                ships_file.write(",")
                                ships_file.write(eol_txt)
                                curr_len = len(eol_txt) + 1
                        if first_entry:
                            first_entry = False
                            ships_file.write(ship_text)
                        else:
                            ships_file.write(", ")
                            ships_file.write(ship_text)

            ships_file.write("]\n")

    def test_generateStargates(self):
        res = evegate.esiUniverseGetAllRegions(use_outdated=self.use_outdated_cache)
        with open(os.path.join(self.curr_path, "evestargates.json"), "w") as ships_file:
            ships_file.write("[")
            max_len = 80
            eol_txt = "\n        "
            ships_file.write(eol_txt)
            curr_len = len(eol_txt)
            cnt = 6
            first_entry = True
            for itm in res:
                res = evegate.esiUniverseRegions(itm, use_outdated=self.use_outdated_cache)
                self.assertIsNotNone(res, "esiUniverseGroups should never return None")
                for constellation_id in res["constellations"]:
                    res = evegate.esiUniverseConstellations(constellation_id, use_outdated=self.use_outdated_cache)
                    for sys_id in res["systems"]:
                        res = evegate.esiUniverseSystems(sys_id, use_outdated=self.use_outdated_cache)
                        if res is None or "stargates" not in res:
                            continue
                        for stargate_id in res["stargates"]:
                            res = evegate.esiUniverseStargates(stargate_id, use_outdated=self.use_outdated_cache)
                            ship_text = u'{}'.format(json.dumps(res))
                            curr_len = curr_len + len(ship_text)
                            if curr_len > max_len:
                                if not first_entry:
                                    first_entry = True
                                    ships_file.write(",")
                                    ships_file.write(eol_txt)
                                    curr_len = len(eol_txt) + 1
                            if first_entry:
                                first_entry = False
                                ships_file.write(ship_text)
                            else:
                                ships_file.write(", ")
                                ships_file.write(ship_text)

            ships_file.write("]\n")

    def test_KnownPlayerNames(self):
        self.cache_used.removeAPIKey("Mr A")
        self.cache_used.removeAPIKey("Mr B")
        self.cache_used.removeAPIKey("Mr C")
        self.cache_used.removeAPIKey("Mr D")
        self.cache_used.removeAPIKey("Mr E")
        res = self.cache_used.getKnownPlayerNames()
        init_res = len(res)
        self.assertEqual(len(res), init_res)
        res.add("Mr B")
        res.add("Mr C")
        res.add("Mr D")
        self.assertEqual(len(res), init_res+3)
        self.cache_used.removeAPIKey({"Mr B", "Mr C", "Mr D"})
        res = self.cache_used.getKnownPlayerNames()
        self.assertEqual(len(res), init_res+0)
        res.add("Mr B")
        res.add("Mr C")
        res.add("Mr D")
        self.assertEqual(len(res), init_res+3)
        self.cache_used.setKnownPlayerNames(res)
        res = self.cache_used.getKnownPlayerNames()
        self.assertIn("Mr B", res)
        self.assertIn("Mr C", res)
        self.assertIn("Mr D", res)
        self.assertNotIn("Mr E", res)
        res.add("Mr C")
        self.cache_used.setActivePlayerNames(res)
        res.add("Mr E")
        self.cache_used.setActivePlayerNames(res)
        res = self.cache_used.getActivePlayerNames()
        self.assertIn("Mr B", res)
        self.assertIn("Mr C", res)
        self.assertIn("Mr D", res)
        self.assertIn("Mr E", res)

        self.cache_used.removeAPIKey("Mr A")
        self.cache_used.removeAPIKey("Mr B")
        self.cache_used.removeAPIKey("Mr C")
        self.cache_used.removeAPIKey("Mr D")
        self.cache_used.removeAPIKey("Mr E")

    def test_clipboard_parser(self):
        jb_list = [
            '<a href="showinfo:35841//1037567076715">8CN-CH » OX-S7P - Speedway</a> in 8CN-CH',
            'DUO-51 » L-FM3P',
            'OX-S7P » 8CN-CH - Speedway 2'
        ]
        for itm in jb_list:
            res_type, res = evaluateClipboardData(itm)
            self.assertEqual(res_type, "jumpbridge", "Result of '{}'is not jumpbridge".format(itm))

        pos_list = [
            'OX-S7P - Terrapin Station',
            "1-7HVI - Checkpoint BlackRose\n0 m",
            "<url=showinfo:35832//1035714265751 alt='Current Station'>1-7HVI - Checkpoint BlackRose</url>",
            "<url=showinfo:1531//60002476 alt='Current Station'>Vittenyn IV - Moon 6 - Expert Distribution Warehouse</url>",
            "Vittenyn IV - Moon 6 - Expert Distribution Warehouse\n0 m",
            'Trossere VII - Moon 3 - University of Caille',
            "Jita IV - Moon 4 - Caldari Navy Assembly Plant"
            ]
        for itm in pos_list:
            res_type, res = evaluateClipboardData(itm)
            self.assertEqual(res_type, "poi", "Result of '{}' is not poi".format(itm))

    def test_esi(self):
        res = evegate.esiStatus()
        self.assertIsNotNone(res, "esiStatus should never return None")
        res = evegate.esiUniverseGetAllRegions()
        self.assertIsNotNone(res, "esiUniverseGetAllRegions should never return None")
        res = evegate.esiUniverseAllConstellations()
        self.assertIsNotNone(res, "esiUniverseAllConstellations should never return None")
        res = evegate.esiUniverseAllCategories()
        self.assertIsNotNone(res, "esiUniverseAllCategories should never return None")
        res = evegate.esiUniverseCategories(6)
        self.assertIsNotNone(res, "esiUniverseCategories should never return None")
        self.cache_used.removeFromCache("name_id_nele McCool")
        res = evegate.esiCharNameToId("nele McCool")
        self.assertEqual(1350114619, res)
        res = evegate.esiCharNameToId("nele McCool")
        self.assertEqual(1350114619, res)
        self.cache_used.removeFromCache("name_id_Bifrost")
        res = evegate.esiUniverseIds({"Bifrost", "Drake", "nele McCool"})
        self.assertTrue("inventory_types" in res.keys(), "Missing inventory type")
        res = evegate.esiUniverseIds({"Bifrost"})
        self.assertTrue("inventory_types" in res.keys(), "Missing inventory type")
        res = evegate.esiUniverseNames([37480])
        self.assertTrue(res[37480] == "Bifrost", "Missing inventory type Bifrost")
        res = evegate.esiImageEvetechNet(1350114619, evegate.evetech_image.characters, 32)
        self.assertIsNotNone(res)
        res = evegate.esiGetCharsOnlineStatus()
        self.assertIsNotNone(res)
        res = evegate.esiCharactersCorporationHistory(1350114619)
        self.assertIsNotNone(res)
        res = evegate.getCurrentCorpForCharId(1350114619)
        self.assertIsNotNone(res)
        res = evegate.getTokenOfChar(1350114619)
        self.assertIsNotNone(res)
        res = evegate.refreshToken(res)
        self.assertIsNotNone(res)
        res = evegate.checkTokenTimeLine(res)
        self.assertIsNotNone(res)
        res = evegate.checkTokenTimeLine(None)
        self.assertIsNone(res)
        res = evegate.refreshToken(None)
        self.assertIsNone(res)


if __name__ == '__main__':
    unittest.main()
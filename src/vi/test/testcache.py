import unittest
import os
import json
import uuid

from vi.cache import Cache
from vi.universe import Universe
from vi.clipboard import evaluateClipboardData
from vi.redoundoqueue import RedoUndoQueue
from vi import Map
from vi import evegate


class FileName:
    def __init__(self, curr_path, file_name):
        self.temp_name = os.path.join(curr_path, str(uuid.uuid4()) )
        self.file_name = os.path.join(curr_path, file_name )

    def __del__(self):
        if os.path.exists(self.temp_name):
            os.remove(self.temp_name)
            print('Delete file ', self.temp_name)

    def prepare(self):
        if os.path.exists(self.temp_name):
            os.remove(self.temp_name)

    def update(self):
        if os.path.exists(self.temp_name):
            if os.path.exists(self.file_name):
                os.remove(self.file_name)
            os.renames(self.temp_name, self.file_name)

    def __str__(self):
        return self.temp_name


class TestCache(unittest.TestCase):
    use_outdated_cache = True
    curr_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "universe")
    Cache.PATH_TO_CACHE = os.path.join(os.path.expanduser("~"), "Documents", "EVE", "spyglass", "cache-2.sqlite3")
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
        self.assertIsNotNone(res)

    def test_intelSystems(self):
        # timeit.Timer()
        res = Universe.monitoredSystems(30000734, 0)
        self.assertIn(30000734, res)
        res = Universe.monitoredSystems(30000734, 1)
        self.assertIn(30000734, res)
        self.assertIn(30000730, res)
        self.assertIn(30000732, res)
        self.assertIn(30000735, res)
        # res = Universe.monitoredSystems(30000734, 12)
        res = Universe.monitoredSystems(12331, 1)
        self.assertIsNone(res)

    def test_loadStargates(self):
        with open(os.path.join(self.curr_path, "evestargates.json"), "r") as fp:
            res = json.load(fp)
            ids = {30000734: {"dist": 0}}
            for distance in range(0, 3):
                for i in [{sys["destination"]["system_id"]: {"dist": distance+1}}
                          for sys in res if sys["system_id"] in ids.keys()]:
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
        self.use_outdated_cache = False
        self.test_generateSystems()
        self.test_generateShipnames()
        self.test_generateRegions()
        self.test_generateConstellations()
        self.test_generateStargates()
        self.use_outdated_cache = True

    def test_generateShipnames(self):
        res = evegate.esiUniverseCategories(6, use_outdated=self.use_outdated_cache)
        with open(os.path.join(self.curr_path, "shipnames.py"), "w") as ships_file:
            ships_file.write("# generated, do not modify\n")
            ships_file.write("SHIPNAMES = (")
            max_len = 80
            eol_txt = "\n        "
            ships_file.write(eol_txt)
            curr_len = len(eol_txt)
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
        name = FileName(self.curr_path, "everegions.json")
        name.prepare()
        res = evegate.esiUniverseGetAllRegions(use_outdated=self.use_outdated_cache)
        with open(name.temp_name, "w") as ships_file:
            ships_file.write("[")
            max_len = 80
            eol_txt = "\n        "
            ships_file.write(eol_txt)
            curr_len = len(eol_txt)
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
        name.update()

    def test_generateConstellations(self):
        name = FileName(self.curr_path, "eveconstellations.json")
        name.prepare()
        res = evegate.esiUniverseGetAllRegions(use_outdated=self.use_outdated_cache)
        with open(name.temp_name, "w") as ships_file:
            ships_file.write("[")
            max_len = 80
            eol_txt = "\n        "
            ships_file.write(eol_txt)
            curr_len = len(eol_txt)
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
        name.update()

    def test_generateSystems(self):
        name = FileName(self.curr_path, "evesystems.json")
        name.prepare()
        res = evegate.esiUniverseGetAllRegions(use_outdated=self.use_outdated_cache)
        with open(name.temp_name, "w") as ships_file:
            ships_file.write("[")
            max_len = 80
            eol_txt = "\n        "
            ships_file.write(eol_txt)
            curr_len = len(eol_txt)
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
        name.update()

    def test_generateStargates(self):
        filename = FileName(self.curr_path, "evestargates.json")
        filename.prepare()
        res = evegate.esiUniverseGetAllRegions(use_outdated=self.use_outdated_cache)
        with open(filename.temp_name, "w") as ships_file:
            ships_file.write("[")
            max_len = 80
            eol_txt = "\n        "
            ships_file.write(eol_txt)
            curr_len = len(eol_txt)

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
        filename.update()

    def test_GetDotlanFiles(self):
        for region in Universe.REGIONS:
            filename = os.path.join(self.curr_path, "..", "ui", "res", "mapdata", "{}.svg".format(
                evegate.convertRegionNameForDotlan(region["name"])))
            svg = evegate.getSvgFromDotlan(region=region["name"], dark=True)
            region_name = region["name"]
            # self.assertEqual(svg.find("region not found"), -1, "Unable to get svg for region {}".format(region_name))
            # self.assertIsNotNone(Map(region_name, svg), "Unable to create map for region {}".format(region_name))
            if svg.find("region not found") == -1:
                with open(filename, "w") as f:
                    f.write(svg)

    def test_generateNPCNames(self):
        factions = dict()
        with open(os.path.join(self.curr_path, "blal.py"), "w") as f:
            f.write("NPCNAMES = {")
            for faction in evegate.esiGetFactions():
                factions.update({faction["faction_id"]: {"name": faction["name"]}})
                f.write('{} : "{}",\n'.format(faction["faction_id"], faction["name"]))
            f.write("}\n")

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
        res = evegate.esiUniverseNames({37480, 37480})
        self.assertTrue(res[37480] == "Bifrost", "Missing inventory type Bifrost")
        res = evegate.esiImageEvetechNet(1350114619, evegate.EvetechImage.characters, 32)
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

    def test_region_queue(self):
        dq = RedoUndoQueue()
        self.assertEqual(dq.undo(), None)
        dq.enqueue("A")
        self.assertEqual(dq.pop(), "A")
        dq.enqueue("A")
        dq.enqueue("B")
        dq.enqueue("C")
        self.assertEqual(dq.undo(), "B")
        self.assertEqual(dq.undo(), "A")
        self.assertEqual(dq.redo(), "B")
        self.assertEqual(dq.redo(), "C")
        self.assertEqual(dq.redo(), "C")
        self.assertEqual(dq.undo(), "B")
        self.assertEqual(dq.undo(), "A")
        self.assertEqual(dq.undo(), "A")
        self.assertEqual(dq.undo(), "A")
        self.assertEqual(dq.redo(), "B")
        dq.enqueue("C")
        dq.enqueue("D")
        dq.enqueue("E")
        dq.enqueue("F")

        pass


if __name__ == '__main__':
    unittest.main()

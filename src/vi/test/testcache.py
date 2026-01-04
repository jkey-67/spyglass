import unittest
import os
import json
import uuid
import jsonlines
from vi.cache import Cache
from vi.universe import Universe
from vi.redoundoqueue import RedoUndoQueue
from vi import evegate

class FileName:
    def __init__(self, curr_path, file_name):
        self.temp_name = os.path.join(curr_path, "{}-{}".format(str(uuid.uuid4()),file_name))
        self.file_name = os.path.join(curr_path, file_name)

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

    def appendText(self,file,text):
        pass

class GenerateJsonlFiles(unittest.TestCase):
    STATIC_DATA_FOLDER = "../sde/eve-online-static-data-latest-jsonl"
    STATIC_DATA_INFO = "# This file was automatically generated, please do not edit it.\n"
    curr_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "universe")

    def test_generateShipnamesJsonl(self):
        groups_category_id_6 = dict()
        jsonl_in_filename = "{path}/groups.jsonl".format(path=self.STATIC_DATA_FOLDER)
        self.assertTrue( os.path.exists(jsonl_in_filename) )
        with jsonlines.open(jsonl_in_filename, mode='r') as reader:
            for obj in reader:
                if obj["categoryID"] == 6:
                    self.assertIn("categoryID", obj.keys())
                    self.assertIn("name", obj.keys())
                    elem = dict()
                    elem["categoryID"] = obj["categoryID"]
                    elem["name"] = obj["name"]
                    groups_category_id_6[obj["_key"]] = elem
        self.assertNotEqual(groups_category_id_6,{})
        ship_types = dict()
        jsonl_in_filename = "{path}/types.jsonl".format(path=self.STATIC_DATA_FOLDER)
        self.assertTrue(os.path.exists(jsonl_in_filename))
        with jsonlines.open(jsonl_in_filename, mode='r') as reader:
            for obj in reader:
                if obj["groupID"] in groups_category_id_6.keys():
                    elem = dict()
                    for key in ["groupID", "name"]:
                        if key in obj.keys():
                            elem[key] = obj[key]
                    ship_types[obj["_key"]] = elem
        self.assertNotEqual(ship_types, {})
        file_name = FileName(self.curr_path, "shipnames.py")
        file_name.prepare()
        with open(file_name.temp_name, "w") as writer:
            writer.write(self.STATIC_DATA_INFO)
            writer.write("SHIPNAMES = {")
            max_len = 80
            eol_txt = "\n        "
            writer.write(eol_txt)
            curr_len = len(eol_txt)
            first_entry = True
            for key,itm in ship_types.items():
                ship_text = u' {}: u"{}"'.format(key, itm["name"]["en"])
                curr_len = curr_len + len(ship_text)
                if curr_len > max_len:
                    first_entry = True
                    writer.write(",")
                    writer.write(eol_txt)
                    curr_len = len(eol_txt) + 1
                if first_entry:
                    first_entry = False
                    writer.write(ship_text)
                else:
                    writer.write(", ")
                    writer.write(ship_text)

            writer.write("}\n\n")
            ship_names = dict()
            for key, itm in ship_types.items():
                for lang, name in itm["name"].items():
                    ship_names[name.upper()] = key

            writer.write("ID_BY_SHIPNAMES = {{{}".format(eol_txt))
            cnt  = len(ship_names)
            for item_name,item_id in ship_names.items():
                cnt -= 1
                if cnt>0:
                    writer.write(u'u"{}": {},{}'.format(item_name,item_id,eol_txt))
                else:
                    writer.write(u'u"{}": {} '.format(item_name,item_id))

            writer.write("}\n")
        file_name.update()

    def test_generateAllJsonl(self):
        self.assertTrue( os.path.exists(self.STATIC_DATA_FOLDER) )
        self.test_generateSEDpy()
        self.test_generateShipnamesJsonl()
        self.test_generateRegionsJsonl()
        self.test_generateConstellationsJson()
        self.test_generateSystemsJson()
        self.test_generateStargatesJson()
        self.test_generateNPCNamesJson()

    def test_generateRegionsJsonl(self):
        name = FileName(self.curr_path, "everegions.jsonl")
        name.prepare()
        all_regions = dict()
        region_id_by_name = dict()
        region_name_by_id = dict()
        jsonl_in_filename = "{path}/mapRegions.jsonl".format(path=self.STATIC_DATA_FOLDER)
        self.assertTrue(os.path.exists(jsonl_in_filename))
        with jsonlines.open(jsonl_in_filename, mode='r') as reader:
            for obj in reader:
                self.assertIn("constellationIDs", obj.keys())
                self.assertIn("name", obj.keys())
                self.assertIn("en", obj["name"].keys())
                self.assertIn("position", obj.keys())
                elem = dict()
                elem["constellations"] = obj["constellationIDs"]
                elem["name"] = obj["name"]["en"]
                elem["names"] = obj["name"]
                elem["position"] = obj["position"]
                elem["region_id"] = obj["_key"]
                all_regions[int(obj["_key"])] = elem
                region_name_by_id[int(obj["_key"])] = obj["name"]["en"]
                for _,rgn_name in obj["name"].items():
                    region_id_by_name[rgn_name] = obj["_key"]

        with jsonlines.open(name.temp_name, mode= 'w') as writer:
            writer.write_all(all_regions.items())
        name.update()

        regionnames_py = FileName(self.curr_path, "regionnames.py")
        regionnames_py.prepare()
        with open(regionnames_py.temp_name, "w", encoding="UTF-8") as writer:
            writer.write(self.STATIC_DATA_INFO)
            writer.write('REGION_IDS_BY_NAME = {\n')
            last = len(region_id_by_name)
            for key, val in region_id_by_name.items():
                if last == 1:
                    writer.write('   "{}": {}\n'.format(key, val))
                else:
                    writer.write('   "{}": {},\n'.format(key, val))
                last -= 1
            writer.write('}\n')
            writer.write('REGION_NAME_BY_ID = {\n')
            last = len(region_name_by_id)
            for key, val in region_name_by_id.items():
                if last == 1:
                    writer.write('   {}: "{}"\n'.format(key, val))
                else:
                    writer.write('   {}: "{}",\n'.format(key, val))
                last -= 1
            writer.write('}\n')
        regionnames_py.update()

    def test_generateConstellationsJson(self):
        name = FileName(self.curr_path, "eveconstellations.jsonl")
        name.prepare()
        all_constellations = dict()
        all_constellations_names = dict()
        jsonl_in_filename = "{path}/mapConstellations.jsonl".format(path=self.STATIC_DATA_FOLDER)
        self.assertTrue(os.path.exists(jsonl_in_filename))
        with jsonlines.open(jsonl_in_filename, mode='r') as reader:
            for obj in reader:
                self.assertIn("solarSystemIDs", obj.keys())
                self.assertIn("name", obj.keys())
                self.assertIn("en", obj["name"].keys())
                self.assertIn("position", obj.keys())
                self.assertIn("regionID", obj.keys())
                elem = dict()
                elem["constellation_id"] = obj["_key"]
                elem["names"] = obj["name"]
                elem["name"] = obj["name"]["en"]
                elem["position"] = obj["position"]
                elem["region_id"] = obj["regionID"]
                elem["systems"] = obj["solarSystemIDs"]
                all_constellations[obj["_key"]] = elem
                for key,const_name in obj["name"].items():
                    all_constellations_names[const_name] = obj["_key"]

        with jsonlines.open(name.temp_name, mode= 'w') as writer:
            writer.write_all(all_constellations.items())
        name.update()
        conste_name = FileName(self.curr_path, "constellationnames.py")
        conste_name.prepare()
        with open(conste_name.temp_name, "w", encoding="utf-8") as writer:
            writer.write(self.STATIC_DATA_INFO)
            writer.write('CONSTELLATION_IDS_BY_NAME = {\n')
            data_out = set(all_constellations_names.items())
            last = len(data_out)
            for key, data in set(all_constellations_names.items()):
                if last == 1:
                    writer.write('   u"{}": {}\n'.format(key, data))
                else:
                    writer.write('   u"{}": {},\n'.format(key, data))
                last -= 1
            writer.write('}\n')
        conste_name.update()

    def test_generateSystemsJson(self):
        systems_file_name = FileName(self.curr_path, "evesystems.jsonl")
        systems_file_name.prepare()
        systems_name_file_name = FileName(self.curr_path, "systemnames.jsonl")
        systems_name_file_name.prepare()
        all_systems = dict()
        all_systems_name = dict()
        jsonl_in_filename = "{path}/mapSolarSystems.jsonl".format(path=self.STATIC_DATA_FOLDER)
        self.assertTrue(os.path.exists(jsonl_in_filename))
        with jsonlines.open(jsonl_in_filename, mode='r') as reader:
            for obj in reader:
                self.assertIn("_key", obj.keys())
                self.assertIn("constellationID",obj.keys())
                self.assertIn("name", obj.keys())
                self.assertIn("en", obj["name"].keys())
                self.assertIn("position", obj.keys())
                self.assertIn("regionID", obj.keys())
                elem = dict()
                elem["constellation_id"] = obj["constellationID"]
                elem["names"] = obj["name"]
                elem["name"] = obj["name"]["en"]
                elem["planets"] = obj["planetIDs"] if "planetIDs" in obj.keys() else list()
                if "position2D" in obj.keys():
                    elem["position"] = obj["position2D"]
                else:
                    elem["position"] = { "x": obj["position"]["x"],"y": -obj["position"]["z"]}
                elem["security_class"] = obj["securityClass"] if "securityClass" in obj.keys() else ""
                if "securityStatus" in obj.keys():
                    elem["security_status"] = obj["securityStatus"]
                if "starID" in obj.keys():
                    elem["star_ID"] = obj["starID"]
                elem["stargates"] = obj["stargateIDs"] if "stargateIDs" in obj.keys() else list()
                elem["system_id"] = obj["_key"]
                elem["region_id"] = obj["regionID"]
                all_systems[obj["_key"]] = elem
                for key,name in obj["name"].items():
                    all_systems_name[name] = obj["_key"]

        with jsonlines.open(systems_file_name.temp_name, mode= 'w') as writer:
            writer.write_all(all_systems.items())

        with jsonlines.open(systems_name_file_name.temp_name, mode= 'w') as writer:
            writer.write_all(all_systems_name.items())

        systems_file_name.update()
        systems_name_file_name.update()

    def test_generateStargatesJson(self):
        filename = FileName(self.curr_path, "evestargates.jsonl")
        filename.prepare()
        all_stargates = dict()
        jsonl_in_filename = "{path}/mapStargates.jsonl".format(path=self.STATIC_DATA_FOLDER)
        self.assertTrue(os.path.exists(jsonl_in_filename))
        with jsonlines.open(jsonl_in_filename, mode='r') as reader:
            for obj in reader:
                self.assertIn("destination", obj.keys())
                self.assertIn("stargateID", obj["destination"].keys())
                self.assertIn("position", obj.keys())
                self.assertIn("solarSystemID", obj.keys())
                elem = dict()
                elem["destination"] = {"system_id": obj["destination"]["solarSystemID"],"stargate_id": obj["destination"]["stargateID"]}
                elem["position"] = obj["position"]
                elem["system_id"] = obj["solarSystemID"]
                all_stargates[obj["_key"]] = elem

        with jsonlines.open(filename.temp_name, mode= 'w') as writer:
            writer.write_all(all_stargates.items())
        filename.update()

    def test_generateNPCNamesJson(self):
        name = FileName(self.curr_path, "npcnames.py")
        name.prepare()
        factions = dict()
        jsonl_in_filename = "{path}/factions.jsonl".format(path=self.STATIC_DATA_FOLDER)
        self.assertTrue( os.path.exists(jsonl_in_filename) )
        with jsonlines.open(jsonl_in_filename, mode='r') as reader:
            for obj in reader:
                self.assertIn("name", obj.keys())
                self.assertIn("en", obj["name"].keys())
                factions[obj["_key"]] = obj["name"]["en"]

        for tok in ["State","Republic","Empire","Federation","Assembly","Mandate","Pirates","Covenant","Collective","Cartel","Kingdom","Circle","Command","of Conscious Thought"]:
            for key, faction in factions.items():
                factions[key] = faction.replace(tok,"").strip()
        factions[500009] = 'Syndicate'
        factions[500016] = 'SOE'
        factions[500028] = 'AIR'
        with open(name.temp_name, "w") as writer:
            writer.write(self.STATIC_DATA_INFO)
            writer.write("NPCNAMES = {\n")
            cnt = len(factions)
            for key, faction in factions.items():
                if cnt > 1:
                    writer.write("    {}:\"{}\",\n".format(key,faction))
                else:
                    writer.write("    {}:\"{}\"".format(key, faction))
                cnt = cnt-1
            writer.write("}\n")
        name.update()

    def test_generateSEDpy(self):
        name = FileName(self.curr_path, "sde.py")
        name.prepare()
        jsonl_in_filename = "{path}/_sde.jsonl".format(path=self.STATIC_DATA_FOLDER)
        self.assertTrue( os.path.exists(jsonl_in_filename) )
        with jsonlines.open(jsonl_in_filename, mode='r') as reader:
            for obj in reader:
                buildNumber_client = obj["buildNumber"]
                buildNumber_server = evegate.getStaticDataVersion()
                self.STATIC_DATA_INFO = "# This file was automatically generated with eve-online-static-data-{}-jsonl, please do not modify the file.\n".format(buildNumber_client)
                self.assertEqual(buildNumber_client,buildNumber_server,"The static data version {}did not match the server version {}.".format(buildNumber_client,buildNumber_server))
                with open(name.temp_name, "w") as writer:
                    writer.write(self.STATIC_DATA_INFO)
                    writer.write("SDE_VERSION = {}\n".format(obj["buildNumber"]))
                    writer.write("SDE_DATE = '{}'\n".format(obj["releaseDate"]))
                name.update()
                return buildNumber_server


class TestCache(unittest.TestCase):
    use_cache = True
    use_outdated_cache = True
    curr_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "universe")
    Cache.PATH_TO_CACHE = os.path.join(os.path.expanduser("~"), "Documents", "EVE", "spyglass", "cache-test.sqlite3")
    cache_used = Cache()
    evegate.setEsiCharName("nele McCool")

    # https://developers.eveonline.com/static-data/eve-online-static-data-latest-jsonl.zip

    def test_sortPoi(self):
        self.cache_used.swapPOIs(1, 11)
        self.cache_used.swapPOIs(1, 1)
        self.cache_used.swapPOIs(3, 4)

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

    def test_esi_with_token_requested(self):
        res = evegate.getTokenOfChar(1350114619)
        if res:
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

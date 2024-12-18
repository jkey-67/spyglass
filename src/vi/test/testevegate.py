import unittest
import os
from vi.cache import Cache
from vi import evegate


class TestEvegate(unittest.TestCase):
    use_outdated_cache = True
    curr_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "universe")
    Cache.PATH_TO_CACHE = os.path.join(os.path.expanduser("~"), "Documents", "EVE", "spyglass", "cache-2.sqlite3")
    cache_used = Cache()
    evegate.setEsiCharName("nele McCool")

    @staticmethod
    def _ListEqualUnorderd(lst_a: list, lst_b: list) -> bool:
        for elem in lst_a:
            if elem in lst_b:
                continue
            else:
                return False
        for elem in lst_b:
            if elem in lst_a:
                continue
            else:
                return False
        return True

    def assertListEqualUnorderd(self, lst_a: list, lst_b: list, msg="Both lists dit not hold the same elements."):
        self.assertTrue(self._ListEqualUnorderd(lst_a,lst_a), msg=msg)

    def test_assertListEqualUnorderd(self):
        self.assertTrue(self._ListEqualUnorderd([1, 2], [1, 2]))
        self.assertTrue(self._ListEqualUnorderd([1, 2], [2, 1]))
        self.assertTrue(self._ListEqualUnorderd([3, 1, 2], [1, 3, 2]))

        self.assertFalse(self._ListEqualUnorderd([1, 2], [3, 1, 2]))
        self.assertFalse(self._ListEqualUnorderd([1, 2, 3], [2, 1]))
        self.assertFalse(self._ListEqualUnorderd([1, 2, 3], []))

    def test_esiStatus(self):
        self.assertIsNotNone(evegate.esiStatus())

    def test_esiStatusJson(self):
        self.assertIsNotNone(evegate.esiStatusJson())

    def test_is_null_sec_system_name(self):
        self.assertFalse(evegate.is_null_sec_system_name("12"))
        self.assertTrue(evegate.is_null_sec_system_name("ZEQ-12"))
        self.assertFalse(evegate.is_null_sec_system_name("Jita"))
        self.assertFalse(evegate.is_null_sec_system_name("J120010"))

    def test_dumpSpyglassDownloadStats(self):
        self.assertIsNotNone(evegate.dumpSpyglassDownloadStats())

    def test_checkResponseNotNone(self):
        self.assertIsNotNone(evegate.esiGetFactions())
        self.assertIsNotNone(evegate.getSvgFromDotlan("Curse"))
        self.assertIsNotNone(evegate.getSvgFromDotlan("Curse", dark=True))

    def test_convertRegionNameForDotlan(self):
        self.assertEqual(evegate.convertRegionNameForDotlan("great wildlands"), "Great_Wildlands")

    def test_DifferentFunctions(self):
        self.assertIsNotNone(evegate.ESAPIRouteToHighSec("66U-1P"))
        self.assertEqual(type(evegate.ESAPIListSystems("66")), list)
        self.assertEqual(type(evegate.ESAPIListWormholeTypes()), list)
        self.assertEqual(type(evegate.ESAPIListPublicSignatures()), list)
        self.assertEqual(type(evegate.ESAPIListPublicObservationsRecords()), list)
        self.assertEqual(type(evegate.ESAPIHealth()), dict)
        self.assertEqual(type(evegate.esiCharactersStanding("nele McCool", use_cache=False)), list)
        self.assertEqual(evegate.esiCharNameToId("nele McCool", use_cache=False), 1350114619)

    def test_esiUniverseIds(self):
        self.assertListEqualUnorderd(evegate.esiUniverseIds(["Eagle", "Bantam"], use_cache=False)["inventory_types"],
                                     [{'id': 582, 'name': 'Bantam'}, {'id': 12011, 'name': 'Eagle'}])
        self.assertListEqualUnorderd(evegate.esiUniverseIds(["Bantam", "Eagle"], use_cache=False)["inventory_types"],
                                     [{'id': 582, 'name': 'Bantam'}, {'id': 12011, 'name': 'Eagle'}])

        self.assertListEqualUnorderd(evegate.esiUniverseIds({"Bantam", "Eagle"})["inventory_types"],
                                     [{'id': 582, 'name': 'Bantam'}, {'id': 12011, 'name': 'Eagle'}])
        self.assertListEqualUnorderd(evegate.esiUniverseIds({"Eagle", "Bantam"})["inventory_types"],
                                     [{'id': 582, 'name': 'Bantam'}, {'id': 12011, 'name': 'Eagle'}])

    def test_esiCharNameToId(self):
        self.assertEqual(evegate.esiCharNameToId("nele McCool", use_cache=False), 1350114619)
        self.assertEqual(evegate.esiCharNameToId("", use_cache=False), None)


if __name__ == '__main__':
    try:
        if evegate.esiPing():
            unittest.main()
    except (Exception,) as ex:
        pass

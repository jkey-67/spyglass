import unittest
import os

from vi.cache import Cache
from vi.universe import Universe
from vi.system import ALL_SYSTEMS


class TestUniverse(unittest.TestCase):
    use_outdated_cache = True
    curr_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "universe")
    Cache.PATH_TO_CACHE = os.path.join(os.path.expanduser("~"), "Documents", "EVE", "spyglass", "cache-2.sqlite3")
    cache_used = Cache()

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
        self.assertTrue(self._ListEqualUnorderd(lst_a, lst_a), msg=msg)

    def test_regionIDFromSystemID(self):
        system = ALL_SYSTEMS[30002860]
        self.assertEqual(system.region_name, "The Kalevala Expanse")
        self.assertEqual(Universe.regionIDFromSystemID(30002860), 10000034)

    def test_system(self):
        system_a = ALL_SYSTEMS[30005132] # System:	Z-ENUD
        self.assertEqual(system_a.name, "Z-ENUD")
        self.assertFalse(system_a.isMonitored)

        system_a.addLocatedCharacter("test1", 5)
        self.assertTrue(system_a.isMonitored)

        system_b = ALL_SYSTEMS[30005133] # System:	MJ-5F9
        system_b.addLocatedCharacter("test2", 5)
        self.assertEqual(system_b.name, "MJ-5F9")

        self.assertEqual(system_a.monitoredRange, 0)
        self.assertEqual(system_b.monitoredRange, 0)

        system_c = ALL_SYSTEMS[30005134]  # System:	M5NO-B
        self.assertEqual(system_c.name, "M5NO-B")
        self.assertTrue(system_c.isMonitored)
        self.assertEqual(system_c.monitoredRange, 1)
        system_a.removeLocatedCharacter("test1",5)
        self.assertEqual(system_c.monitoredRange, 2)
        system_a.removeLocatedCharacter("test1", 5)
        self.assertEqual(system_c.monitoredRange, 2)
        system_b.removeLocatedCharacter("test2", 5)
        self.assertFalse(system_c.isMonitored)

    if __name__ == '__main__':
        try:
            unittest.main()
        except (Exception,) as ex:
            pass

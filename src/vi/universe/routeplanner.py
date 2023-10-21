import networkx as nx
from vi.cache import cache
from vi.universe import Universe

def Init_Universe_Graph():
    g = nx.Graph()
    for itm in Universe.SYSTEMS:
        g.add_node(int(itm["system_id"]), system=itm)

    for itm in Universe.STARGATES:
        id_src = int(itm["system_id"])
        id_dst = int(itm["destination"]["system_id"])
        g.add_edge(id_src, id_dst)

    return g


class RoutPlanner(object):
    UNIVERSE = Init_Universe_Graph()

    def __init__(self):
        return

    @staticmethod
    def findRouteByID(src_id, dst_id, use_ansi=False, use_thera=False):
        try:
            graph = RoutPlanner.UNIVERSE.copy()
            if use_ansi:
                for itm in cache.Cache().getJumpGates():
                    graph.add_edge(Universe.systemIdByName(itm[0]), Universe.systemIdByName(itm[2]))

            if use_thera:
                for itm in cache.Cache().getThreaConnections():
                    id_src = itm["sourceSolarSystem"]["id"]
                    id_dst = itm["destinationSolarSystem"]["id"]
                    graph.add_edge(id_src, id_dst)

            return nx.shortest_path(graph, source=src_id, target=dst_id)
        except:
            return list()

    @staticmethod
    def findRouteByName(src_name, dst_name, use_ansi=False, use_thera=False):
        src_id = Universe.systemIdByName(src_name)
        dst_id = Universe.systemIdByName(dst_name)
        return RoutPlanner.findRouteByID(src_id, dst_id, use_ansi, use_thera)


if __name__ == '__main__':
    from vi.evegate import checkTheraConnections
    checkTheraConnections()
    res = RoutPlanner.findRouteByName('MJ-5F9', 'C3J0-O')
    print('The shortest path : %s' %(res[::-1]))
    res = RoutPlanner.findRouteByName('MJ-5F9', 'C3J0-O', use_ansi=True)
    print('The shortest path : %s' %(res[::-1]))
    res = RoutPlanner.findRouteByName('MJ-5F9', 'Thera', use_ansi=True, use_thera=True)
    print('The shortest path : %s' %(res[::-1]))
    res = RoutPlanner.findRouteByName('MJ-5F9', 'Thera', use_ansi=False)
    print('The shortest path : %s' %(res[::-1]))
    res = RoutPlanner.findRouteByName('MJ-5F9', 'Thera')
    print('The shortest path : %s' %(res[::-1]))



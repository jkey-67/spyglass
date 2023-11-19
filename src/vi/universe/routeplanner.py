import logging

import networkx as nx
from vi.cache import cache
from vi.universe import Universe


def Init_Universe_Graph():
    g = nx.Graph()
    for key, itm in Universe.SYSTEMS.items():
        g.add_node(key, system=itm)

    for itm in Universe.STARGATES:
        id_src = int(itm["system_id"])
        id_dst = int(itm["destination"]["system_id"])
        g.add_edge(id_src, id_dst, type="Gate")

    # res = nx.kamada_kawai_layout(g)

    return g


class Route(object):
    """
        Attributes:
            info:str
                Information text showing source destination and length of th route.

            attr:list
                A list of system ids and additional info describing the route.

            route:list
                A list of system ids describing the route.

            src_id:int
                The source system id.

            src_name:str
                The source system name.

            dst_id:int
                The destination system id.

            dst_name:
                The destination system name.


    """
    def __init__(self, **kwargs):
        self.info = ""  """ Information text"""
        self.attr = list()
        self.route = list()
        self.src_id = None
        self.src_name = None
        self.dst_id = None
        self.dst_name = None
        self.__dict__.update(kwargs)


class RoutPlanner(object):
    UNIVERSE = Init_Universe_Graph()

    def __init__(self):
        return

    @staticmethod
    def findRoute(**kwargs) -> Route:
        try:
            graph = RoutPlanner.UNIVERSE.copy()

            use_ansi = 'use_ansi' in kwargs and kwargs['use_ansi']
            use_thera = 'use_thera' in kwargs and kwargs['use_thera']

            if 'src_name' in kwargs:
                kwargs.update(src_id=Universe.systemIdByName(kwargs['src_name']))
            elif 'src_id' in kwargs:
                kwargs.update(src_name=Universe.systemNameById(kwargs['src_id']))
            else:
                raise RuntimeError("Define src_id= or src_name= to get a route.")

            if 'dst_name' in kwargs:
                kwargs.update(dst_id=Universe.systemIdByName(kwargs['dst_name']))
            elif 'dst_id' in kwargs:
                kwargs.update(dst_name=Universe.systemNameById(kwargs['dst_id']))
            else:
                raise RuntimeError("Define dst_id= or dst_name= to get a route.")

            if use_ansi:
                for itm in cache.Cache().getJumpGates():
                    src = Universe.systemIdByName(itm[0])
                    dst = Universe.systemIdByName(itm[2])
                    if src is not None and dst is not None:
                        graph.add_edge(src, dst, type='Ansi')
                    else:
                        logging.info("Invalid jump bridge data")

            if use_thera:
                for itm in cache.Cache().getThreaConnections():
                    id_src = itm["in_system_id"]
                    id_dst = itm["out_system_id"]
                    graph.add_edge(id_src, id_dst, type='Thera')

            path = nx.shortest_path(graph, source=kwargs['src_id'], target=kwargs['dst_id'])
            attr = [dict(node=u, type=graph[u][v]['type'], name=Universe.systemNameById(u)) for u, v in zip(path, path[1:])]
            attr.append(dict(node=path[-1], type="System", name=Universe.systemNameById(path[-1])))
            kwargs.update(route=path)
            kwargs.update(attr=attr)
            kwargs.update(info="Route from {} to {} {} Jumps{}{}.".format(
                kwargs['src_name'],
                kwargs['dst_name'],
                len(kwargs['route']),
                ", using Ansiblex" if use_ansi else "",
                ", using Thera" if use_thera else ""))

        except (Exception,) as e:
            kwargs.update(info="Route not found, {}".format(e))
            kwargs.update(route=list())

        return Route(**kwargs)


if __name__ == '__main__':
    from vi.evegate import checkTheraConnections
    checkTheraConnections()

    res = RoutPlanner.findRoute(src_name='MJ-5F9', dst_name='C3J0-O')
    print('{} %s'.format(res.info) % (res.route[::-1]))

    res = RoutPlanner.findRoute(src_name='MJ-5F9', dst_name='Todaki', use_ansi=True, use_thera=True)
    for sys in res.attr:
        if sys["name"] != "Thera" and (sys["type"] == "Gate" or sys["type"] == "Ansi"):
            continue
        print('{} {}'.format(sys["name"], sys["type"]))

    print('{} %s'.format(res.info) % (res.route[::-1]))

    res = RoutPlanner.findRoute(src_name='MJ-5F9', dst_name='Thera', use_ansi=True, use_thera=True)
    print('{} %s'.format(res.info) % (res.route[::-1]))

    res = RoutPlanner.findRoute(src_name='MJ-5F9', dst_name='Jita', use_ansi=False, use_thera=True)
    print('{} %s'.format(res.info) % (res.route[::-1]))

    res = RoutPlanner.findRoute(src_name='MJ-5F9', dst_name='Jita', use_ansi=True, use_thera=True)
    print('{} %s'.format(res.info) % (res.route[::-1]))

    res = RoutPlanner.findRoute(src_name='MJ-5F9', dst_name='Jita', use_ansi=True, use_thera=False)
    print('{} %s'.format(res.info) % (res.route[::-1]))

    res = RoutPlanner.findRoute(src_name='MJ-5F9', dst_name='Jita', use_ansi=False, use_thera=False)
    print('{} %s'.format(res.info) % (res.route[::-1]))

    res = RoutPlanner.findRoute(src_name='MJ-5F9', dst_name='Thera', use_ansi=False)
    print('{} %s'.format(res.info) % (res.route[::-1]))

    res = RoutPlanner.findRoute(src_name='MJ-5F9', dst_name='Thera')
    print('{} %s'.format(res.info) % (res.route[::-1]))

    res = RoutPlanner.findRoute(src_name='MJ-5F9')
    print('{} %s'.format(res.info) % (res.route[::-1]))

    res = RoutPlanner.findRoute(src_name='MJ-5F9', dst_name="Zarzakh")
    print('{} %s'.format(res.info) % (res.route[::-1]))


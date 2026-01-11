"""Route planning utilities for Spyglass universe maps."""

import logging
from functools import lru_cache
from enum import Enum

import networkx as nx

from vi.cache import cache
from vi.universe import Universe

class Route(object):
    """Container for route calculation results.

    Attributes:
        info: Human-readable description of the route and settings.
        attr: List of hop dictionaries with node id, edge type, and name.
        route: Ordered list of system ids forming the path.
        src_id: Source system id.
        src_name: Source system name.
        dst_id: Destination system id.
        dst_name: Destination system name.
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


@lru_cache(maxsize=1)
def _base_universe_graph() -> nx.Graph:
    """Build a reusable base graph of all systems and stargate links."""
    g = nx.Graph()
    for key in Universe.SYSTEMS.keys():
        g.add_node(key)
    for _, itm in Universe.STARGATES_ID_OBJ.items():
        id_src = itm.system_id
        id_dst = itm.destination.system_id
        g.add_edge(id_src, id_dst, type="Stargate")
    return g


class RoutPlanner(object):
    """Utility to compute routes through the universe graph."""
    def __init__(self,**kwargs):
        """Prepare a working graph with optional Ansiblex and Thera links.

        Args:
            **kwargs: Flags controlling graph enrichment:
                use_ansi (bool): Include Ansiblex jump bridges from cache.
                use_thera (bool): Include Thera connections from cache.

        Returns:
            networkx.Graph: Copy of the universe graph with optional extras.
        """
        super(RoutPlanner, self).__init__()
        self.use_ansi = kwargs.get('use_ansi',False)
        self.use_thera = kwargs.get('use_thera',False)
        self.use_wormholes = kwargs.get('use_worm_holes', kwargs.get('use_wormholes', False))
        # Copy the cached base graph so we do not rebuild thousands of nodes/edges for every planner.
        self.graph = self._Init_Universe_Graph()

        with cache.Cache() as used_cache:
            if self.use_ansi:
                for itm in used_cache.getJumpGates():
                    src = Universe.systemIdByName(itm[0])
                    dst = Universe.systemIdByName(itm[2])
                    if src is not None and dst is not None:
                        self.graph.add_edge(src, dst, type="Ansiblex")
                    else:
                        logging.info("Invalid jump bridge data")

            if self.use_thera:
                for itm in used_cache.getThreaConnections():
                    id_src = itm["in_system_id"]
                    id_dst = itm["out_system_id"]
                    self.graph.add_edge(id_src, id_dst, type="Thera")

            if self.use_wormholes:
                for itm in used_cache.getWormholeConnections():
                    id_src = itm["in_system_id"]
                    id_dst = itm["out_system_id"]
                    self.graph.add_edge(id_src, id_dst, type="Wormhole")

    @staticmethod
    def _Init_Universe_Graph() -> nx.Graph:
        """Create the base universe graph with systems and stargate edges.

        Returns:
            networkx.Graph: Graph containing all systems and gate edges.
        """
        return _base_universe_graph().copy(as_view=False)

    def findRoute(self, **kwargs) -> Route:
        """Compute a shortest path between systems with optional extras.

        Args:
            graph: Working graph returned by `prepareUnivers`.
            **kwargs: Route options:
                src_id (int) or src_name (str): Source system identifier.
                dst_id (int) or dst_name (str): Destination system identifier.
                use_ansi (bool): Whether Ansiblex was included (for labeling).
                use_thera (bool): Whether Thera was included (for labeling).

        Returns:
            Route: Populated route object. On failure, `route` is empty and
            `info` contains the error message.
        """
        try:
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


            path = nx.shortest_path(self.graph, source=kwargs['src_id'], target=kwargs['dst_id'])
            attr = [dict(node=u, type=self.graph[u][v].get('type', 'Stargate'),
                         name=Universe.systemNameById(u)) for u, v in zip(path, path[1:])]
            attr.append(dict(node=path[-1], type="System", name=Universe.systemNameById(path[-1])))
            kwargs.update(route=path)
            kwargs.update(attr=attr)
            kwargs.update(info="Route from {} to {} {} Jumps{}{}.".format(
                kwargs['src_name'],
                kwargs['dst_name'],
                len(kwargs['route']),
                ", using Ansiblex" if self.use_ansi else "",
                ", using Thera" if self.use_thera else ""))

        except (Exception,) as e:
            kwargs.update(info="Route not found, {}".format(e))
            kwargs.update(route=list())

        return Route(**kwargs)

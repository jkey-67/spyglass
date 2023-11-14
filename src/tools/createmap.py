###########################################################################
#  EVE-Spyglass - Visual Intel Chat Analyzer                              #
#  Copyright (C) 2022 Nele McCool (nele.mccool@gmx.net)                   #
#                                                                         #
#  This program is free software: you can redistribute it and/or modify   #
#  it under the terms of the GNU General Public License as published by   #
#  the Free Software Foundation, either version 3 of the License, or      #
#  (at your option) any later version.                                    #
#                                                                         #
#  This program is distributed in the hope that it will be useful,        #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the           #
#  GNU General Public License for more details.                           #
#                                                                         #
#                                                                         #
#  You should have received a copy of the GNU General Public License      #
#  along with this program. If not, see <https://www.gnu.org/licenses/>.  #
###########################################################################


from __future__ import print_function

import os
import sys

import networkx as nx
import numpy
from math import sqrt
from bs4 import BeautifulSoup
from vi import evegate
from vi.universe import Universe
from vi.dotlan import convertRegionName

from layout import fruchterman_reingold_layout, kamada_kawai_layout

sys.path.append('../')


def checkArguments(args):
    error = False
    for path in args[1:3]:
        if not os.path.exists(path):
            errout("ERROR: {0} does not exist!".format(path))
            error = True
    if error:
        sys.exit(2)


def loadSvg(path):
    with open(path) as f:
        content = f.read()
    return BeautifulSoup(content)


def is_diffrent_region(src, dst):
    rgn_src = evegate.esiUniverseConstellations(src["constellation_id"], True)
    rgn_dst = evegate.esiUniverseConstellations(dst["constellation_id"], True)
    return rgn_src["region_id"] != rgn_dst["region_id"]


def is_different_constellation(src, dst):
    return src["constellation_id"] != dst["constellation_id"]


missing_sys = list()


def addJumpsToSvgFile(system, jumps, svg_template, use_cache=True):
    if "stargates" in system:
        for gate_id in system["stargates"]:
            gates = Universe.stargateByID(gate_id)
            src = system["system_id"]
            dst = gates["destination"]["system_id"]
            revert = svg_template.find(id="j-{}-{}".format(dst, src))
            src_pos = svg_template.find(id="sys{}".format(str(src)))
            dst_pos = svg_template.find(id="sys{}".format(str(dst)))
            if src_pos and dst_pos and revert is None:
                line_tag = svg_template.new_tag("line", id="j-{}-{}".format(src, dst), x1=float(src_pos["x"])+31.25, y1=float(src_pos["y"])+15,x2=float(dst_pos["x"])+31.25, y2=float(dst_pos["y"])+15,)
                src_system = Universe.systemById(src)
                dst_system = Universe.systemById(dst)
                if is_diffrent_region(src_system, dst_system):
                    line_tag["class"] = "jr"
                elif is_different_constellation(src_system, dst_system):
                    line_tag["class"] = "jc"
                else:
                    line_tag["class"] = "j"
                jumps.append(line_tag)
            elif dst_pos is None:
                missing_sys.append(dst)


def addIceBeltsToSvgFile(system, svg_template, use_cache=True):
    for sysuse in svg_template.select("use"):
        sysuse["system_id"]


def addSystemToSvg(svg_template, systems, x=0, y=0, use_cache=True):
    for system_id in systems:
        systemUses = svg_template.select("#sysuse")[0]
        system = evegate.esiUniverseSystems(system_id, use_cache)
        a_tag = svg_template.new_tag("a")
        a_tag["xlink:href"] = "http://evemaps.dotlan.net/system/{}".format(system["name"])
        a_tag["class"] = "sys link-5-{}".format(system_id)
        sys_rect = svg_template.new_tag("rect", height="22", id="rect{}".format(system_id),
                                        rx="11", ry="11", width="50", x="4", y="3.5")
        sys_rect["class"] = "s"
        sys_text = svg_template.new_tag("text", x="28", y="14")
        sys_text["class"] = "ss"
        sys_text["text-anchor"] = "middle"
        sys_text.string = system["name"]
        sys_text_id = svg_template.new_tag("text", x="28", y="21.7", id="txt{}".format(system_id))
        sys_text_id["class"] = "st"
        sys_text_id["text-anchor"] = "middle"
        sys_text_id.string = "ORE"

        a_tag.append(sys_rect)
        a_tag.append(sys_text)
        a_tag.append(sys_text_id)
        sys_tag = svg_template.new_tag("symbol", id="def{}".format(system_id))
        sys_tag.append(a_tag)
        svg_template.defs.append(sys_tag)
        x = x + 62.5
        y = 0
        use_tag = svg_template.new_tag("use", height="30", id="sys{}".format(system_id), width="62.5")
        use_tag["xlink:href"] = "#def{}".format(system_id)
        use_tag["x"] = round(x / 62.5) * 62.5
        use_tag["y"] = round(y / 30.0) * 30.0
        systemUses.append(use_tag)


def updateSvgFile(filename):
    use_cache = True
    svg_template = loadSvg(filename)
    jumps = svg_template.select("#jumps")[0]
    systemUses = svg_template.select("#sysuse")[0]

    jumps.clear()
    # return svg_template

    trans_map = ['0.0', '0.0']
    try:
        the_map = svg_template.select("#map")[0]
        trans_map = the_map.attrs["transform"][10:-1].split(",")
        del the_map.attrs["transform"]
    except (Exception,):
        pass
    for sysuse in systemUses.select("use"):
        symbol_id = sysuse["id"]
        sysuse.attrs["x"] = str(float(sysuse.attrs["x"]) + float(trans_map[0]))
        sysuse.attrs["y"] = str(float(sysuse.attrs["y"]) + float(trans_map[1]))
        if sysuse.has_attr("transform"):
            trans_sys = sysuse.attrs["transform"][10:-1].split(",")
            sysuse.attrs["x"] = str(float(sysuse.attrs["x"]) + float(trans_sys[0]))
            sysuse.attrs["y"] = str(float(sysuse.attrs["y"]) + float(trans_sys[1]))
            del sysuse.attrs["transform"]

        sysuse.attrs["x"] = str(round(float(sysuse.attrs["x"])/62.5)*62.5)
        sysuse.attrs["y"] = str(round(float(sysuse.attrs["y"])/35.0)*35.0)

    for sysuse in systemUses.select("use"):
        symbol_id = sysuse["id"]
        system_id = symbol_id[3:]
        system = evegate.esiUniverseSystems(system_id, use_cache)
        addJumpsToSvgFile(system, jumps, svg_template, use_cache)

    return svg_template


def svgFileToDot(filename):
    result = "graph Beziehungen {\n"
    svg_template = loadSvg(filename)
    systemUses = svg_template.select("#sysuse")[0]

    for sysuse in systemUses.select("use"):
        itm_id = sysuse["xlink:href"]
        name = svg_template.select(itm_id)[0]
        sysname = name.text[10:16]
        result += "{} [shape=circle label=\"{}\"]\n".format(sysuse["id"], sysname)

    for sysuse in svg_template.select("#jumps")[0]:
        try:
            svg_systems = sysuse.attrs["id"][2:].split("-")
            result += "sys{} -> sys{}\n".format(svg_systems[0], svg_systems[1])
        except (Exception,):
            pass

    result += "}\n"
    return result


class RegionObject(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def createSvgFile(region_ids):
    use_cache = True
    map_template = os.path.join(os.path.expanduser("~"), "projects", "spyglass", "src", "vi", "ui", "res", "mapdata","MapTemplate.svg")
    svg_template = loadSvg(map_template)

    jumps = svg_template.select("#jumps")[0]
    systemUses = svg_template.select("#sysuse")[0]

    x_max = None
    y_min = None
    y_max = None
    x_min = None

    affected_systems = set()
    region_name = ""
    for region_id in region_ids:
        region_used = RegionObject(**Universe.regionByID(region_id))
        region_name = region_name + region_used.name if region_name =="" else region_name + ", " + region_used.name
        for const_id in region_used.constellations:
            constellation_used = Universe.constellationByID(const_id)
            for system_id in constellation_used["systems"]:
                affected_systems.add(system_id)
                for stargate_system in Universe.stargatesBySystemID(system_id):
                    affected_systems.add(stargate_system["destination"]["system_id"])

    g = nx.Graph()
    initialpos = dict()
    fixed_pos = list()
    for system_id in affected_systems:
        system = Universe.systemById(system_id)
        constellation_used = Universe.constellationByID(system["constellation_id"])
        region_id = constellation_used["region_id"]
        constellation_used = Universe.constellationByID(system["constellation_id"])
        x_cur = constellation_used["position"]["x"] + system["position"]["x"]
        y_cur = constellation_used["position"]["y"] + system["position"]["y"]
        z_cur = constellation_used["position"]["z"] + system["position"]["z"]

        subset = system["constellation_id"] if 'constellation_id' in system else -1
        g.add_node(system_id, subset=subset)

        initialpos.update({system_id: (x_cur, y_cur, z_cur)})
        if region_id not in region_ids:
            fixed_pos.append(system_id)

    for itm in Universe.STARGATES:
        if itm["system_id"] in affected_systems and itm["destination"]["system_id"] in affected_systems:
            id_src = int(itm["system_id"])
            id_dst = int(itm["destination"]["system_id"])
            g.add_edge(id_src, id_dst, type="Gate")

    graph_positions = initialpos

    #graph_positions = fruchterman_reingold_layout(g, dim=3, seed=0)
    graph_positions = nx.spring_layout(g, dim=3, seed=7)

    x_max = None
    y_min = None
    y_max = None
    x_min = None

    for system_id in affected_systems:
        x_cur = graph_positions[system_id][0]
        y_cur = graph_positions[system_id][1]

        if x_min is None:
            x_min = x_cur
            x_max = x_cur
        elif x_cur < x_min:
            x_min = x_cur
        elif x_cur > x_max:
            x_max = x_cur

        if y_min is None:
            y_min = y_cur
            y_max = y_cur
        elif y_cur < y_min:
            y_min = y_cur
        elif y_cur > y_max:
            y_max = y_cur

    width = (x_max - x_min)
    height = (y_max - y_min)
    for system_id in affected_systems:
        graph_positions.update(
            {system_id: (graph_positions[system_id][0] - x_min, graph_positions[system_id][1] - y_min)})


    for system_id in affected_systems:
        system = Universe.systemById(system_id)
        constellation_used = Universe.constellationByID(system["constellation_id"])
        region_id = constellation_used["region_id"]
        a_tag = svg_template.new_tag("a")
        a_tag["xlink:href"] = "http://evemaps.dotlan.net/system/{}".format(system["name"])
        a_tag["constellation"] = system["constellation_id"]
        a_tag["region"] = region_id
        a_tag["class"] = "sys link-5-{}".format(system_id)
        if region_id in region_ids:
            sys_rect = svg_template.new_tag("rect", height="22", id="rect{}".format(system_id), rx="11", ry="11", width="50", x="4", y="3.5")
            sys_rect["class"] = "s"
            sys_text = svg_template.new_tag("text", x="28", y="14")
            sys_text["class"] = "ss"
            sys_text["text-anchor"] = "middle"
            sys_text.string = system["name"]
            sys_text_id = svg_template.new_tag("text", x="28", y="21.7", id="txt{}".format(system_id))
            sys_text_id["class"] = "st"
            sys_text_id["text-anchor"] = "middle"
            sys_text_id.string = "ORE"
        else:
            sys_rect = svg_template.new_tag("rect", height="22", id="rect{}".format(system_id), width="50", x="4", y="3.5")
            sys_rect["class"] = "e"
            sys_text = svg_template.new_tag("text", x="28", y="14")
            sys_text["class"] = "es"
            sys_text["text-anchor"] = "middle"
            sys_text.string = system["name"]
            sys_text_id = svg_template.new_tag("text", x="28", y="21.7", id="txt{}".format(system_id))
            sys_text_id["class"] = "er"
            sys_text_id["text-anchor"] = "middle"
            sys_text_id.string = Universe.regionNameFromSystemID(system_id)

        svg_w = 1024*1.2
        svg_h = 768*1.2
        a_tag.append(sys_rect)
        a_tag.append(sys_text)
        a_tag.append(sys_text_id)
        sys_tag = svg_template.new_tag("symbol", id="def{}".format(system_id))
        sys_tag.append(a_tag)
        svg_template.defs.append(sys_tag)
        x = graph_positions[system_id][0]*(svg_w-64)/width
        y = graph_positions[system_id][1]*(svg_h-32)/height
        use_tag = svg_template.new_tag("use", height="30", id="sys{}".format(system_id), width="62.5")
        use_tag["xlink:href"] = "#def{}".format(system_id)
        if False:
            use_tag["x"] = str(round(x/62.5)*62.5)
            use_tag["y"] = str(round(y/30.0)*30.0)
        else:
            use_tag["x"] = str(x) # str(round(x/62.5)*62.5)
            use_tag["y"] = str(y) # str(round(y/30.0)*30.0)

        systemUses.append(use_tag)

    for system_id in affected_systems:
        system = Universe.systemById(system_id)
        addJumpsToSvgFile(system, jumps, svg_template, use_cache)

    svg_template.svg["width"] = str(svg_w)
    svg_template.svg["height"] = str(svg_h)
    svg_template.svg["viewbox"] = "0 0 {} {}".format(svg_w, svg_h)
    svg_template.find(string='Outer Ring').string.replace_with(region_name)
    return svg_template


def main():
    base_path = os.path.join(os.path.expanduser("~"), "projects", "spyglass", "src", "vi", "ui", "res", "mapdata","generated")

    if False:  # create a dot file
        result = svgFileToDot(os.path.join(base_path,"New_Combined-step_6.svg"))
        with open(os.path.join(base_path,"Denci_Tactical.dot"), "wb") as svgFile:
            svgFile.write(result.encode("utf-8"))
            svgFile.close()
        return

    if True:

        for region in [Universe.regionByID(Universe.regionIDFromSystemID(Universe.systemIdByName("Zarzakh"))),
                       Universe.regionByID(Universe.regionIDFromSystemID(Universe.systemIdByName("Z-ENUD"))),
                       Universe.regionByID(Universe.regionIDFromSystemID(Universe.systemIdByName("Jita"))),
                       Universe.regionByID(Universe.regionIDFromSystemID(Universe.systemIdByName("D-GTMI"))),
                       ]: # Universe.REGIONS:
            region_name = region["name"]
            region_id = region["region_id"]
            newSvg = createSvgFile(list({region_id}))
            result = newSvg.encode("utf-8")
            fname = "{}.svg".format(convertRegionName(region_name))
            with open(os.path.join(base_path, fname), "wb") as svgFile:
                svgFile.write(result)
                svgFile.close()
        return

        #system_id = Universe.systemIdByName("Jita" )
        #system_id = Universe.systemIdByName("Zarzakh")
        system_id = Universe.systemIdByName("Z-ENUD")
        system_id = Universe.systemIdByName('1M7-RK')
        rgn_name = Universe.regionNameFromSystemID(Universe.systemIdByName("Zarzakh"))
        rgn_id = Universe.regionIDFromSystemID(system_id)
        catch_id = Universe.regionIDFromSystemID(30001168)
        newSvg = createSvgFile(list({rgn_id, catch_id}))
        result = newSvg.prettify().encode("utf-8")
        fname = "{}.svg".format(convertRegionName(rgn_name))
        with open(os.path.join(base_path, fname), "wb") as svgFile:
            svgFile.write(result)
            svgFile.close()
        return
        newSvg = updateSvgFile(os.path.join(base_path, fname))
        result = newSvg.prettify().encode("utf-8")
        with open(os.path.join(base_path, fname), "wb") as svgFile:
            svgFile.write(result)
            svgFile.close()


def errout(*objs):
    print(*objs, file=sys.stderr)


if __name__ == "__main__":
    main()

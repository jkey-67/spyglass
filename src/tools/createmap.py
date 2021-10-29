###########################################################################
#  createmap - Tool to create a dotlan compaltibe  map
#  Copyright (C) 2021 J.Keymer  (@gmx.com )             #
#																		  #
#  This program is free software: you can redistribute it and/or modify	  #
#  it under the terms of the GNU General Public License as published by	  #
#  the Free Software Foundation, either version 3 of the License, or	  #
#  (at your option) any later version.									  #
#																		  #
#  This program is distributed in the hope that it will be useful,		  #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of		  #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the		  #
#  GNU General Public License for more details.							  #
#																		  #
#																		  #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.	 If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

from __future__ import print_function

import os
import sys

from bs4 import BeautifulSoup
sys.path.append('../')
from vi import evegate

def checkArguments(args):
    error = False
    for path in args[1:3]:
        if not os.path.exists(path):
            errout("ERROR: {0} does not exist!".format(path))
            error = True
    if error:
        sys.exit(2)

def loadSvg(path):
    content = None
    with open(path) as f:
        content = f.read()
    return BeautifulSoup(content)

def is_diffrent_region( src, dst):
    rgn_src = evegate.getConstellationInformation(src["constellation_id"], True)
    rgn_dst = evegate.getConstellationInformation(dst["constellation_id"], True)
    return rgn_src["region_id"] != rgn_dst["region_id"]

def is_different_constellation(src, dst):
    return src["constellation_id"] != dst["constellation_id"]

missing_sys = list()

def addJumpsToSvgFile( system, jumps, svg_template, use_cache=True):

    for gate_id in system["stargates"]:
        gates = evegate.getStargateInformation(gate_id, use_cache)
        src = system["system_id"]
        dst = gates["destination"]["system_id"]
        revert = svg_template.find(id="j-{}-{}".format(dst, src))
        src_pos = svg_template.find(id="sys{}".format(str(src)))
        dst_pos = svg_template.find(id="sys{}".format(str(dst)))
        if src_pos and dst_pos and revert is None:
            line_tag = svg_template.new_tag("line", id="j-{}-{}".format(src, dst), x1=float(src_pos["x"])+31.25, y1=float(src_pos["y"])+15,x2=float(dst_pos["x"])+31.25, y2=float(dst_pos["y"])+15,)
            src_system = evegate.getSolarSystemInformation(src, use_cache)
            dst_system = evegate.getSolarSystemInformation(dst, use_cache)
            if is_diffrent_region(src_system, dst_system):
                line_tag["class"] ="jr"
            elif is_different_constellation(src_system, dst_system):
                line_tag["class"] ="jc"
            else:
                line_tag["class"] = "j"
            jumps.append(line_tag)
        elif dst_pos == None:
            missing_sys.append((dst))

def addIceBeltsToSvgFile( system, svg_template, use_cache=True):
    for sysuse in svg_template.select("use"):
        src = sysuse["system_id"]
        #<rect class="i" height="28" id="ice30001171" rx="14" ry="13" style="fill: #31363B;" width="56" x="1" y="0.5"></rect>



def addSystemToSvg(svg_template, systems, x=0, y=0, use_cache=True):
    for system_id in systems:
        systemUses = svg_template.select("#sysuse")[0]
        system = evegate.getSolarSystemInformation(system_id, use_cache)
        a_tag = svg_template.new_tag("a")
        a_tag["xlink:href"] = "http://evemaps.dotlan.net/system/{}".format(system["name"])
        a_tag["class"] = "sys link-5-{}".format(system_id)
        sys_rect = svg_template.new_tag("rect", height="22", id="rect{}".format(system_id), rx="11", ry="11", width="50",
                                    x="4", y="3.5")
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

""" updates all jump connection"""

def updateSvgFile(filename):
    use_cache = True
    svg_template = loadSvg(filename)
    jumps = svg_template.select("#jumps")[0]
    systemUses = svg_template.select("#sysuse")[0]

    jumps.clear()
    #return svg_template

    trans_map = ['0.0', '0.0']
    try:
       the_map = svg_template.select("#map")[0]
       trans_map =the_map.attrs["transform"][10:-1].split(",")
       del the_map.attrs["transform"]
    except:
        pass
    for sysuse in systemUses.select("use"):
        symbol_id = sysuse["id"]
        system_id = symbol_id[3:]
        sysuse.attrs["x"] = float(sysuse.attrs["x"]) + float(trans_map[0])
        sysuse.attrs["y"] = float(sysuse.attrs["y"]) + float(trans_map[1])
        if sysuse.has_attr("transform"):
            trans_sys = sysuse.attrs["transform"][10:-1].split(",")
            sysuse.attrs["x"] = float(sysuse.attrs["x"]) + float(trans_sys[0])
            sysuse.attrs["y"] = float(sysuse.attrs["y"]) + float(trans_sys[1])
            del sysuse.attrs["transform"]

        sysuse.attrs["x"] = round(float(sysuse.attrs["x"])/62.5)*62.5
        sysuse.attrs["y"] = round(float(sysuse.attrs["y"])/35.0)*35.0


    for sysuse in systemUses.select("use"):
        symbol_id = sysuse["id"]
        system_id = symbol_id[3:]
        system = evegate.getSolarSystemInformation(system_id, use_cache)
        addJumpsToSvgFile(system, jumps, svg_template, use_cache)

    #addSystemToSvg( svg_template, missing_sys, 0, -30, True)
    #print(missing_sys)
    return svg_template

def svgFileToDot(filename):
    result = "graph Beziehungen {\n"
    use_cache = True
    svg_template = loadSvg(filename)
    jumps = svg_template.select("#jumps")[0]
    systemUses = svg_template.select("#sysuse")[0]

    for sysuse in systemUses.select("use"):
        id = sysuse["xlink:href"]
        name = svg_template.select(id)[0]
        sysname= name.text[10:16]
        result += "{} [shape=circle label=\"{}\"]\n".format(sysuse["id"],sysname)

    for sysuse in svg_template.select("#jumps")[0]:
        try:
            systems = sysuse.attrs["id"][2:].split("-")
            result += "sys{} -> sys{}\n".format(systems[0],systems[1])
        except :
            pass

    result += "}\n"
    return result


def createSvgFile( region_ids ):
    use_cache=True
    svg_template = loadSvg("~/projects/spyglass/src/vi/ui/res/mapdata/MapTemplate.svg")
    jumps = svg_template.select("#jumps")[0]
    systemUses = svg_template.select("#sysuse")[0]

    x_max = None
    y_min = None
    y_max = None
    x_min = None

    for region_id in region_ids:
        region_json = evegate.getRegionInformation(region_id, use_cache)
        for const_id in region_json["constellations"]:
            systems_json = evegate.getConstellationInformation(const_id, use_cache)
            for system_id in systems_json["systems"]:
                system = evegate.getSolarSystemInformation( system_id, use_cache )
                x_cur = float(systems_json["position"]["x"]) + float(system["position"]["x"])
                y_cur = float(systems_json["position"]["y"]) + float(system["position"]["y"])
                if x_min is None:
                    x_min = x_max = x_cur
                elif x_min > x_cur:
                    x_min = x_cur
                elif x_max < x_cur:
                    x_max = x_cur

                if y_min is None:
                    y_min = y_max = y_cur
                elif y_min > y_cur:
                    y_min = y_cur
                elif y_max < y_cur:
                    y_max = y_cur


    for region_id in region_ids:
        region_json = evegate.getRegionInformation(region_id, use_cache)
        for const_id in region_json["constellations"]:
            systems_json = evegate.getConstellationInformation(const_id, use_cache)
            for system_id in systems_json["systems"]:
                system = evegate.getSolarSystemInformation( system_id, use_cache )
                a_tag = svg_template.new_tag("a")
                a_tag["xlink:href"] = "http://evemaps.dotlan.net/system/{}".format(system["name"])
                a_tag["constellation"] = system["constellation_id"]
                a_tag["region"] = region_id
                a_tag["class"] ="sys link-5-{}".format(system_id)
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

                a_tag.append(sys_rect)
                a_tag.append(sys_text)
                a_tag.append(sys_text_id)
                sys_tag = svg_template.new_tag("symbol", id="def{}".format(system_id))
                sys_tag.append(a_tag)
                svg_template.defs.append(sys_tag)
                x = (float(systems_json["position"]["x"]) + float(system["position"]["x"])-x_min)/(x_max-x_min)*1024*4
                y = (float(systems_json["position"]["y"]) + float(system["position"]["y"])-y_min)/(y_max-y_min)*768*4
                use_tag = svg_template.new_tag("use", height="30",id="sys{}".format(system_id), width="62.5")
                use_tag["xlink:href"] = "#def{}".format(system_id)
                use_tag["x"] = round(x/62.5)*62.5
                use_tag["y"] = round(y/30.0)*30.0
                systemUses.append(use_tag)

    for region_id in region_ids:
        region_json = evegate.getRegionInformation(region_id, use_cache)
        for const_id in region_json["constellations"]:
            systems_json = evegate.getConstellationInformation(const_id, use_cache)
            for system_id in systems_json["systems"]:
                system = evegate.getSolarSystemInformation(system_id, use_cache)
                addJumpsToSvgFile(system, jumps,svg_template,use_cache )

    svg_template.svg["width"] = "4096"
    svg_template.svg["height"] = "3097"
    svg_template.svg["viewbox"]="0 0 4096 3097"
    return svg_template


def main():
    base_path = os.path.join(os.path.expanduser("~"),"projects","spyglass","src","vi","ui","res","mapdata" )
    if False: #create a dot file
        result = svgFileToDot(os.path.join(base_path,"New_Combined-step_6.svg"))
        with open(os.path.join(base_path,"Denci_Tactical.dot"), "wb") as svgFile:
            svgFile.write(result.encode("utf-8"))
            svgFile.close()
        return

    if False:
        newSvg = createSvgFile(list({10000006,10000009, 10000008, 10000011}))
        result = newSvg.body.next.prettify().encode("utf-8")
        with open(os.path.join(base_path, "New_Combined-step_1.svg"), "wb") as svgFile:
            svgFile.write(result)
            svgFile.close()

    if True:#only rout jump lines
        newSvg = updateSvgFile(os.path.join(base_path, "New_Combined-step_9.svg"))
        result = newSvg.body.next.prettify().encode("utf-8")
        with open(os.path.join(base_path, "Denci_Tactical.svg"), "wb") as svgFile:
            svgFile.write(result)
            svgFile.close()


def errout(*objs):
    print(*objs, file=sys.stderr)


if __name__ == "__main__":
    main()

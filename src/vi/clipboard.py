###########################################################################
#  EVE-Spyglass - Visual Intel Chat Analyzer                              #
#  Copyright (C) 2022 Nele McCool (nele.mccool @ gmx.net)                 #
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

from parse import parse
import vi.evegate as evegate
from vi.universe import Universe


def evaluateClipboardData(content):
    """
     the content of the clip board is used to set jump bridge and poi

    Args:
        content: current clipboard content

    Returns:
        list :[type,dict(structure|station|JB-Info)] where type is 'pio', 'jumpbridge' or None
    """

    jump_bridge_text = parse("{src} » {dst} - {name}<br>{}", content)

    if jump_bridge_text is None:
        jump_bridge_text = parse('<a href="showinfo:{type_id}//{structure_id}">{src} » {dst} - {name}</a>{}', content)

    if jump_bridge_text is None:
        jump_bridge_text = parse("{src} » {dst} - {name}\n{}", content)

    if jump_bridge_text is None:
        jump_bridge_text = parse('{src} » {dst} - {name}', content)

    if jump_bridge_text is None:
        jump_bridge_text = parse("{src} » {dst}", content)
        if jump_bridge_text and len(jump_bridge_text.named) == 2:
            jump_bridge_text.named["name"] = None
        else:
            jump_bridge_text = None

    if jump_bridge_text is None:
        jump_bridge_text = parse('{src} » {dst} - {name}', content)

    if jump_bridge_text is None:
        jump_bridge_text = parse('{src} {p1} --> {dst} {p2}', content)

    if jump_bridge_text is None:
        jump_bridge_text = parse('{structure_id} {src} --> {dst}', content)

    if jump_bridge_text and len(jump_bridge_text.named) > 2:
        if jump_bridge_text.named["src"].upper() in Universe.SYSTEM_IDS_BY_UPPER_NAME and \
                jump_bridge_text.named["dst"].upper() in Universe.SYSTEM_IDS_BY_UPPER_NAME:
            if "structure_id" in jump_bridge_text and jump_bridge_text["structure_id"] != 0:
                jump_bridge_text.named["id_src"] = jump_bridge_text["structure_id"]
            else:
                jump_bridge_text.named["id_src"] = Universe.systemIdByName(jump_bridge_text["src"])
            jump_bridge_text.named["id_dst"] = Universe.systemIdByName(jump_bridge_text["dst"])
            jump_bridge_text.named["json_src"] = None
            jump_bridge_text.named["json_dst"] = None
            return ["jumpbridge", jump_bridge_text.named]

    simple_text = parse("{name}<br>{}", content)
    if simple_text is None:
        simple_text = parse("<url=showinfo:{type_id}//{structure_id} alt='{}'>{name}</url>", content)
        if simple_text and len(simple_text.named) != 3:
            simple_text = None

    if simple_text is None:
        simple_text = parse("<url=showinfo:{type_id}//{structure_id}>{name}</url>", content)
        if simple_text and len(simple_text.named) != 3:
            simple_text = None

    if simple_text is None:
        simple_text = parse('{sys} - {name}\n{}', content)
        if simple_text and len(simple_text.named) != 2:
            simple_text = None

    if simple_text is None:
        simple_text = parse('{sys} {planet} - {name}', content)
        if simple_text and len(simple_text.named) != 3:
            simple_text = None

    if simple_text is None:
        simple_text = parse('{sys} - {name}', content)
        if simple_text and len(simple_text.named) != 2:
            simple_text = None

    if simple_text:
        info = simple_text.named
        if "structure_id" in info.keys():
            station_info = evegate.esiUniverseStations(info["structure_id"])
            if station_info:
                return ["poi", station_info]
            if evegate.esiCharName():
                structure_info = evegate.esiUniverseStructure(
                    esi_char_name=evegate.esiCharName(),
                    structure_id=info["structure_id"])
                if structure_info:
                    return ["poi", structure_info]
            else:
                return ["poi", simple_text.named]

        if "name" in info.keys() and "sys" in info.keys():
            structure_search = evegate.esiSearch(
                esi_char_name=evegate.esiCharName(),
                search_text="{} - {}".format(info["sys"], info["name"]),
                search_category=evegate.category.structure)
            if "structure" in structure_search:
                structure_info = evegate.esiUniverseStructure(
                    esi_char_name=evegate.esiCharName(),
                    structure_id=structure_search["structure"][0])
                if structure_info:
                    return ["poi", structure_info]
                return ["poi", structure_info]

            station_search = evegate.esiSearch(
                esi_char_name=evegate.esiCharName(),
                search_text="{} - {}".format(info["sys"], info["name"]),
                search_category=evegate.category.station)
            if "station" in station_search:
                station_info = evegate.esiUniverseStations(
                    station_id=station_search["station"][0])
                if station_info:
                    return ["poi", station_info]

    return [None, []]

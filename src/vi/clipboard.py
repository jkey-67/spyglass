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


def evaluateClipboardData(content):
    """
     the content of the clip board is used to set jump bridge and poi

    Args:
        content: current clipboard content

    Returns:
        list :[type,dict(structure|station|JB-Info)] where type is 'pio', 'jumpbridge' or None
    """

    jump_bridge_text = parse("{src} » {dst} - {info}<br>{}", content)

    if jump_bridge_text is None:
        jump_bridge_text = parse('<a href="showinfo:{type_id}//{structure_id}">{src} » {dst} - {info}</a>{}', content)

    if jump_bridge_text is None:
        jump_bridge_text = parse("{src} » {dst} - {info}\n{}", content)

    if jump_bridge_text is None:
        jump_bridge_text = parse('{src} » {dst} - {info}', content)

    if jump_bridge_text is None:
        jump_bridge_text = parse("{src} » {dst}", content)
        if jump_bridge_text and len(jump_bridge_text.named) == 2:
            jump_bridge_text.named["info"] = None
        else:
            jump_bridge_text = None

    if jump_bridge_text and len(jump_bridge_text.named) > 2:
        jb_data = dict()
        structure = evegate.esiSearch(
            esi_char_name=evegate.esiCharName(),
            search_text="{} » {}".format(jump_bridge_text["src"], jump_bridge_text["dst"]),
            search_category=evegate.category.structure)
        if structure:
            jb_data["src"] = jump_bridge_text["src"]
            jb_data["dst"] = jump_bridge_text["dst"]
            jb_data["id_src"] = structure["structure"][0]
            jb_data["id_dst"] = structure["structure"][1]
            jb_data["json_src"] = evegate.esiUniverseStructure(
                esi_char_name=evegate.esiCharName(),
                structure_id=structure["structure"][0])

            jb_data["json_dst"] = evegate.esiUniverseStructure(
                esi_char_name=evegate.esiCharName(),
                structure_id=structure["structure"][1])

            return ["jumpbridge", jb_data]
        else:
            return [None, []]

    simple_text = parse("{info}<br>{}", content)
    if simple_text is None:
        simple_text = parse("<url=showinfo:{type_id}//{structure_id} {}>{info}</url>", content)
        if simple_text and len(simple_text.named) != 3:
            simple_text = None

    if simple_text is None:
        simple_text = parse('{sys} - {info}\n{}', content)
        if simple_text and len(simple_text.named) != 2:
            simple_text = None

    if simple_text is None:
        simple_text = parse('{sys} - {info}', content)
        if simple_text and len(simple_text.named) != 2:
            simple_text = None

    if simple_text:
        info = simple_text.named
        if "structure_id" in info.keys():
            station_info = evegate.esiUniverseStations(info["structure_id"])
            if station_info:
                return ["poi", station_info]

            structure_info = evegate.esiUniverseStructure(
                esi_char_name=evegate.esiCharName(),
                structure_id=info["structure_id"])
            if structure_info:
                return ["poi", structure_info]

        if "info" in info.keys():
            structure_search = evegate.esiSearch(
                esi_char_name=evegate.esiCharName(),
                search_text="{} - {}".format(info["sys"], info["info"]),
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
                search_text="{} - {}".format(info["sys"], info["info"]),
                search_category=evegate.category.station)
            if "station" in station_search:
                station_info = evegate.esiUniverseStations(
                    station_id=station_search["station"][0])
                if station_info:
                    return ["poi", station_info]

    return [None, []]
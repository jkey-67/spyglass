###########################################################################
#  concatmaps - Tool to concat evemaps									  #
#  Copyright (C) 2014-15 Sebastian Meyer (sparrow.242.de+eve@gmail.com )  #
#                                                                         #
#  This program is free software: you can redistribute it and/or modify	  #
#  it under the terms of the GNU General Public License as published by	  #
#  the Free Software Foundation, either version 3 of the License, or	  #
#  (at your option) any later version.									  #
#                                                                         #
#  This program is distributed in the hope that it will be useful,		  #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of		  #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the		  #
#  GNU General Public License for more details.							  #
#                                                                         #
#                                                                         #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.	 If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

from __future__ import print_function

import os
import sys

from bs4 import BeautifulSoup


def checkArguments(args):
    error = False
    for path in args[1:3]:
        if not os.path.exists(path):
            errout("ERROR: {0} does not exist!".format(path))
            error = True
    if error:
        sys.exit(2)


def concat(first_file, second_file):
    first_svg = loadSvg(first_file)
    second_svg = loadSvg(second_file)
    symbols = []
    jumps = []
    system_uses = []

    for def_element in second_svg.select("defs"):
        for symbol in def_element.select("symbol"):
            symbols.append(symbol)

    for jumpgroup in second_svg.select("#jumps"):
        for jump in jumpgroup.select("line"):
            jump["x1"] = str(float(jump["x1"]) + 1024)
            jump["x2"] = str(float(jump["x2"]) + 1024)
            jump["y1"] = str(float(jump["y1"]) + 300)
            jump["y2"] = str(float(jump["y2"]) + 300)
            jumps.append(jump)

    for sysgroup in second_svg.select("#sysuse"):
        for sysuse in sysgroup.select("use"):
            sysuse["x"] = str(float(sysuse["x"]) + 1024)
            sysuse["y"] = str(float(sysuse["y"]) + 300)
            system_uses.append(sysuse)

    def_element = first_svg.select("defs")[0]
    for symbol in symbols:
        def_element.append(symbol)

    jumps_element = first_svg.select("#jumps")[0]
    for jump in jumps:
        jumps_element.append(jump)

    system_use_element = first_svg.select("#sysuse")[0]
    for system_use in system_uses:
        system_use_element.append(system_use)

    return first_svg


def loadSvg(path):
    with open(path) as f:
        content = f.read()
    return BeautifulSoup(content)


def main():
    if len(sys.argv) != 3:
        errout("Sorry, wrong number of arguments. Use this this way:")
        errout("{0} firstmap secondmap".format(sys.argv[0]))
        errout("All argumens are pathes to files")
        errout("The new map is written to stdout")
        sys.exit(1)
    checkArguments(sys.argv)
    new_svg = concat(sys.argv[1], sys.argv[2])
    result = new_svg.body.next.prettify().encode("utf-8")
    # Cache.PATH_TO_CACHE = os.path.join(os.path.expanduser("~"), "Documents", "EVE", "spyglass", "cache-2.sqlite3")
    # with open("/home/jkeymer/projects/spyglass/src/vi/ui/res/mapdata/Wickedcreek_Scaldingpass.svg", "wb") as svgFile:
    #    svgFile.write(result);
    #    svgFile.close()
    print(result)


def errout(*objs):
    print(*objs, file=sys.stderr)


if __name__ == "__main__":
    main()

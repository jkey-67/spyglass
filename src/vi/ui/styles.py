###########################################################################
#  Spyglass - Visual Intel Chat Analyzer								  #
#  Copyright (C) 2017 Crypta Eve (crypta@crypta.tech)                     #
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

import logging
import yaml
import os

from vi.resources import resourcePath, resourcePathExists


class Styles:
    defaultStyle = ""
    defaultCommons = ""

    darkStyle = ""
    darkCommons = ""

    styleList = ["light", "abyss"]

    currentStyle = "abyss"

    def __init__(self):
        try:
            # light theme
            if resourcePathExists(os.path.join("vi", "ui", "res", "styles", "light.css")):
                with open(resourcePath(os.path.join("vi", "ui", "res", "styles", "light.css"))) as default:
                    Styles.defaultStyle = default.read()
            if resourcePathExists(os.path.join("vi", "ui", "res", "styles", "light.yaml")):
                with open(resourcePath(os.path.join("vi", "ui", "res", "styles", "light.yaml"))) as default:
                    Styles.defaultCommons = yaml.full_load(default)

            # dark theme
            if resourcePathExists(os.path.join("vi", "ui", "res", "styles", "abyss.css")):
                with open(resourcePath(os.path.join("vi", "ui", "res", "styles", "abyss.css"))) as dark:
                    Styles.darkStyle = dark.read()

            if resourcePathExists(os.path.join("vi", "ui", "res", "styles", "abyss.yaml")):
                with open(resourcePath(os.path.join("vi", "ui", "res", "styles", "abyss.yaml"))) as dark:
                    Styles.darkCommons = yaml.full_load(dark)

        except Exception as e:
            logging.critical(e)

    @staticmethod
    def getStyles():
        return Styles.styleList

    @staticmethod
    def getStyle():
        if Styles.currentStyle == "light":
            return Styles.defaultStyle
        elif Styles.currentStyle == "abyss":
            return Styles.darkStyle
        else:
            return ""

    @staticmethod
    def getCommons():
        if Styles.currentStyle == "light" and Styles.defaultCommons != "":
            return Styles.defaultCommons
        elif Styles.currentStyle == "abyss" and Styles.darkCommons != "":
            return Styles.darkCommons
        else:
            def_commons = {
                "bg_colour": '#FFFFFF',
                "change_lines": False,
                "line_colour": '#000000',
                "alarm_colours": ["#FF0000", "#FF9B0F", "#FFFA0F", "#FFFDA2", "#FFFFFF"],
                "unknown_colour": "#FFFFF",
                "clear_colour": "#59FF6C",
                "text_colour": "#000000",
                "text_inverter": True}
            return def_commons

    @staticmethod
    def setStyle(style):
        if style in Styles.styleList:
            Styles.currentStyle = style
        else:
            logging.critical("Attempted to switch to unknown style: {}".format(style))


class TextInverter:
    @staticmethod
    def getTextColourFromBackground(colour):
        if colour[0] == '#':
            colour = colour[1:]
        if len(colour) == 8:
            colour = colour[2:]
        red = int(colour[0:2], 16)
        green = int(colour[2:4], 16)
        blue = int(colour[4:6], 16)

        # perceptive Luminance formula
        perc = 1 - (((0.299 * red) + (0.587 * green) + (0.114 * blue)) / 255)
        if perc < 0.5:
            return "#C0000000"
        else:
            return "#c0c0c0c0"

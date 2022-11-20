###########################################################################
#  Vintel - Visual Intel Chat Analyzer									  #
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

""" 12.02.2015
	I know this is a little bit dirty, but I prefer to have all the functions
	to parse the chat in this file together.
	Wer are now work directly with the html-formatted text, which we use to
	display it. We are using a HTML/XML-Parser to have the benefit, that we
	can only work and analyze those text, that is still not on tags, because
	all the text in tags was allready identified.
	f.e. the ship_parser:
		we call it from the chatparser and give them the rtext (richtext).
		if the parser hits a shipname, it will modifiy the tree by creating
		a new tag and replace the old text with it (calls tet_replace),
		than it returns True.
		The chatparser will call the function again until it return False
		(None is False) otherwise.
		We have to call the parser again after a hit, because a hit will change
		the tree and so the original generator is not longer stable.
"""


import vi.evegate as evegate
from vi.universe import Universe
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from vi import states


class CTX:
    EVE_SYSTEM = ("EVE-System", "EVE System", "Système EVE", "Система EVE")
    CHARS_TO_IGNORE = ("*", "?", ",", "!", ".")
    WORDS_TO_IGNORE = ("IN", "IS", "AS")
    FORMAT_URL = u"""<a style="color:#28a5ed;font-weight:bold" href="link/{0}">{0}</a>"""
    FORMAT_SHIP = u"""<a  style="color:#d95911;font-weight:bold" href="link/https://wiki.eveuniversity.org/{0}">{0}</a>"""
    FORMAT_SYSTEM = u"""<a style="color:#888880;font-weight:bold" href="mark_system/{0}">{1}</a>"""
    FORMAT_SYSTEM_IN_RERION = u"""<a style="color:#CC8800;font-weight:bold" href="mark_system/{0}">{1}</a>"""
    STATUS_CLEAR = {"CLEAR", "CLR", "CRL"}
    STATUS_STATUS = {"STAT", "STATUS"}
    STATUS_BLUE = {"BLUE", "BLUES ONLY", "ONLY BLUE" "STILL BLUE", "ALL BLUES"}


def textReplace(element, new_text):
    """

    Args:
        element(NavigableString):
        new_text:

    Returns:

    """
    new_text = "<t>" + new_text + "</t>"
    new_elements = []
    for newPart in BeautifulSoup(new_text, 'html.parser').select("t")[0].contents:
        new_elements.append(newPart)
    for newElement in new_elements:
        element.insert_before(newElement)
    element.replace_with("")
    # todo: try element.replaceWith(newElement)


def parseStatus(rtext):
    """

    Args:
        rtext: NavigableString

    Returns:

    """
    texts = [t for t in rtext.contents if isinstance(t, NavigableString)]
    for text in texts:
        upper_text = text.strip().upper()
        original_text = upper_text
        for char in CTX.CHARS_TO_IGNORE:
            upper_text = upper_text.replace(char, " ")
        upper_words = set(upper_text.split())
        if (len(upper_words & CTX.STATUS_CLEAR) > 0) and not original_text.endswith("?"):
            return states.CLEAR
        elif len(upper_words & CTX.STATUS_STATUS) > 0:
            return states.REQUEST
        elif "?" in original_text:
            return states.REQUEST
        elif text.strip().upper() in CTX.STATUS_BLUE:
            return states.CLEAR


def parseShips(rtext) -> bool:
    """
        parse all known ship name
    Args:
        rtext: test to parse

    Returns:

    """
    def formatShipName(in_text, in_word):
        return in_text.replace(in_word, CTX.FORMAT_SHIP.format(in_word))

    texts = [t for t in rtext.contents if isinstance(t, NavigableString)]
    for text in texts:
        upper_text = text.upper()
        for shipName in [shipName for shipName in Universe.shipNames() if shipName in upper_text]:
            start = upper_text.find(shipName)
            end = start + len(shipName)
            if ((start > 0 and upper_text[start - 1] not in (" ", "X")) or (
                            end < len(upper_text) - 1 and upper_text[end] not in ("S", " ", "*"))):
                continue

            ship_in_text = text[start:end]
            formatted = formatShipName(text, ship_in_text)
            textReplace(text, formatted)
            return True


def isCharName(name) -> bool:
    """

    Args:
        name(str):character name to be checked

    Returns:
        bool:True if the name is 100% match a character name

    """
    # todo:implement me
    name = name
    return False


def parseSystems(systems, rtext, systems_found):
    """
    Parse a message for system names
    Args:
        systems: systems to be monitored
        rtext: message to be parsed
        systems_found(set): systems found

    Returns:
        bool:
    """
    # todo:parse systems may run in a loop

    system_names = Universe.systemNamesUpperCase() #  systems.keys()
    maps_system_name = [sys.upper() for sys in systems]
    def formatSystem(in_text, in_word, in_system, in_rgn):
        if in_rgn:
            return in_text.replace(in_word, CTX.FORMAT_SYSTEM_IN_RERION.format(in_system, in_word))
        else:
            return in_text.replace(in_word, CTX.FORMAT_SYSTEM.format(in_system, in_word))

    texts = [t for t in rtext.contents if isinstance(t, NavigableString) and len(t)]
    for wtIdx, text in enumerate(texts):
        work_text = text
        for char in CTX.CHARS_TO_IGNORE:
            work_text = work_text.replace(char, " ")

        # Drop redundant whitespace so as to not throw off word index
        work_text = ' '.join(work_text.split())
        words = work_text.split(" ")

        for idx, word in enumerate(words):

            # Is this about another a system's gate?
            if len(words) > idx + 1:
                if words[idx + 1].upper() == 'GATE':
                    bailout = True
                    if len(words) > idx + 2:
                        if words[idx + 2].upper() == 'TO':
                            # Could be '___ GATE TO somewhere' so check this one.
                            bailout = False
                    if bailout:
                        # '_____ GATE' mentioned in message, which is not what we're
                        # interested in, so go to checking next word.
                        continue
                if words[idx + 1].upper() == 'CLR' or words[idx + 1].upper() == 'CLEAR':
                    if isCharName(words[idx] + " "+words[idx + 1]):
                        continue
            upper_word = word.upper()
            if upper_word != word and upper_word in CTX.WORDS_TO_IGNORE:
                continue
            match_system_id = Universe.systemIdByName(word)
            if match_system_id:  # - direct hit on name
                match_system_name = Universe.systemNameById(match_system_id)
                if match_system_name in systems.keys():
                    systems_found.add(systems[match_system_name])  # of the system?
                    formatted_text = formatSystem(text, word, match_system_name, True)
                else:
                    formatted_text = formatSystem(text, word, match_system_name, False)
                textReplace(text, formatted_text)
                return True
            elif 2 < len(upper_word) < 5:  # - upperWord < 4 chars.
                for system in system_names:  # system begins with?
                    if system.startswith(upper_word):
                        match_system_id = Universe.systemIdByName(system)
                        if match_system_id:  # - direct hit on name
                            match_system_name = Universe.systemNameById(match_system_id)
                            if match_system_name in systems.keys():
                                systems_found.add(systems[match_system_name])  # of the system?
                                formatted_text = formatSystem(text, word, match_system_name, True)
                            else:
                                formatted_text = formatSystem(text, word, match_system_name, False)
                            textReplace(text, formatted_text)
                            return True
            """
            elif "-" in upper_word and len(upper_word) > 2:  # - short with - (minus)
                upper_word_parts = upper_word.split("-")  # (I-I will match I43-IF3)
                for system in system_names:
                    system_parts = system.split("-")
                    if (len(upper_word_parts) == 2 and len(system_parts) == 2 and len(upper_word_parts[0]) > 1 and len(
                            upper_word_parts[1]) > 1 and len(system_parts[0]) > 1 and len(system_parts[1]) > 1 and len(
                            upper_word_parts) == len(system_parts) and upper_word_parts[0][0] == system_parts[0][0] and
                            upper_word_parts[1][0] == system_parts[1][0]):
                        if system in systems:
                            systems_found.add(systems[system])
                        formatted_text = formatSystem(text, word, system)
                        textReplace(text, formatted_text)
                        return True
            elif len(upper_word) > 2:  # what if F-YH58 is named FY?
                for system in system_names:
                    cleared_system = system.replace("-", "")
                    if cleared_system.startswith(upper_word):
                        if system in systems:
                            systems_found.add(systems[system])
                        formatted_text = formatSystem(text, word, system)
                        textReplace(text, formatted_text)
                        return True
    """
    # if ( len(foundSystems) > 1):
    # todo check for system name clear/clr here
    return False


def parseUrls(rtext):
    """Patch text format into an existing  http/https link found in a message.
    Args:
        rtext: The text to be patched

    Returns:
        str:The resulting patched text
    """
    def findUrls(s):
        # yes, this is faster than regex and less complex to read
        urls_found = []
        prefixes = ("http://", "https://")
        for prefix in prefixes:
            start = 0
            while start >= 0:
                start = s.find(prefix, start)
                if start >= 0:
                    stop = s.find(" ", start)
                    if stop < 0:
                        stop = len(s)
                    urls_found.append(s[start:stop])
                    start += 1
        return urls_found

    def formatUrl(in_text, in_url):
        return in_text.replace(in_url, CTX.FORMAT_URL.format(in_url))

    texts = [t for t in rtext.contents if isinstance(t, NavigableString)]
    for text in texts:
        urls = findUrls(text)
        for url in urls:
            textReplace(text, formatUrl(text, url))
            return True

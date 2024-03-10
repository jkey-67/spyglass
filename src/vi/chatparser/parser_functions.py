###########################################################################
#  Vintel - Visual Intel Chat Analyzer                                    #
#  Copyright (C) 2014-15 Sebastian Meyer (sparrow.242.de+eve@gmail.com )  #
#                                                                         #
#  This program is free software: you can redistribute it and/or modify   #
#  it under the terms of the GNU General Public License as published by   #
#  the Free Software Foundation, either version 3 of the License, or      #
#  (at your option) any later version.                                    #
#                                                                         #
#  This program is distributed in the hope that it will be useful,        #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.     See the       #
#  GNU General Public License for more details.                           #
#                                                                         #
#                                                                         #
#  You should have received a copy of the GNU General Public License      #
#  along with this program.   If not, see <http://www.gnu.org/licenses/>. #
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


from vi.evegate import checkPlayerName, EXISTS
from vi.universe import Universe
from vi.states import States
from vi.system import System, ALL_SYSTEMS
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from .message import Message
from .ctx import CTX


def textReplace(element, new_text):
    """
        replace the text
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


def parsePlayerNames(rtext) -> bool:
    texts = [t for t in rtext.contents if isinstance(t, NavigableString)]
    for text in texts:
        text.replace("  ", " ")
        tokens = text.strip().split()

        if len(tokens) == 0:
            continue

        if len(tokens) == 1:
            search_text = tokens[0].upper()
            if search_text in CTX.STATUS_CLEAR:
                return False
            if search_text in CTX.STATUS_BLUE:
                return False
            if search_text in CTX.STATUS_STATUS:
                return False
            if len(search_text) < 4:
                return False
            search_text = tokens[0]
            res, player_id = checkPlayerName(search_text)
            if res == EXISTS:
                textReplace(text, CTX.FORMAT_PLAYER_NAME.format(search_text, player_id))
                return True

        inx = 0
        while inx+1 < len(tokens):
            if len(tokens) > 1:
                search_text = "{} {}".format(tokens[inx], tokens[inx + 1])
                res, player_id = checkPlayerName(search_text)
                if res == EXISTS:
                    textReplace(text, text.replace(search_text, CTX.FORMAT_PLAYER_NAME.format(search_text, player_id)))
                    return True
            inx = inx + 1
        inx = 0
        while inx + 2 < len(tokens):
            if len(tokens) > 2:
                search_text = "{} {} {}".format(tokens[inx], tokens[inx + 1], tokens[inx + 2])
                res, player_id = checkPlayerName(search_text)
                if res == EXISTS:
                    textReplace(text, text.replace(search_text, CTX.FORMAT_PLAYER_NAME.format(search_text, player_id)))
                    return True
            inx = inx + 1

        if len(tokens) > 0:
            search_text = tokens[0]
            res, player_id = checkPlayerName(search_text)
            if res == EXISTS:
                textReplace(text, text.replace(search_text, CTX.FORMAT_PLAYER_NAME.format(search_text, player_id)))
                return True

    return False


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
            return States.CLEAR
        elif len(upper_words & CTX.STATUS_STATUS) > 0:
            return States.REQUEST
        elif "?" in original_text:
            return States.REQUEST
        elif text.strip().upper() in CTX.STATUS_BLUE:
            return States.CLEAR


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
    res = checkPlayerName(name)
    return res == EXISTS


def parseSystems(systems_on_map, rtext, systems_found) -> bool:
    """
    Parse a message for system names
    Args:
        systems_on_map: systems to be monitored
        rtext: message to be parsed
        systems_found(set): systems found

    Returns:
        bool:
    """
    # todo:parse systems may run in a loop

    system_names = Universe.systemNamesUpperCase()

    def formatSystem(in_text, in_word, in_system, in_rgn):
        if in_rgn:
            return in_text.replace(in_word, CTX.FORMAT_SYSTEM_IN_REGION.format(in_system, in_word))
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
                if words[idx + 1].upper() in CTX.STATUS_CLEAR:
                    if isCharName(words[idx] + " "+words[idx + 1]):
                        continue
            upper_word = word.upper()
            if upper_word != word and upper_word in CTX.WORDS_TO_IGNORE:
                continue
            match_system_id = Universe.systemIdByName(word)
            if match_system_id:  # - direct hit on name
                matched_system_name = Universe.systemNameById(match_system_id)
                systems_found.add(ALL_SYSTEMS[match_system_id])  # of the system?
                system_on_map = matched_system_name in systems_on_map.keys()
                formatted_text = formatSystem(text, word, matched_system_name, system_on_map)
                textReplace(text, formatted_text)
                return True
            elif 3 < len(upper_word) < 5:  # - upperWord < 4 chars.
                for system in system_names:  # system begins with?
                    if system.startswith(upper_word):
                        match_system_id = Universe.systemIdByName(system)
                        if match_system_id:  # - direct hit on name
                            matched_system_name = Universe.systemNameById(match_system_id)
                            systems_found.add(ALL_SYSTEMS[match_system_id])  # of the system?
                            system_on_map = matched_system_name in systems_on_map.keys()
                            formatted_text = formatSystem(text, word, matched_system_name, system_on_map)
                            textReplace(text, formatted_text)
                            return True

    # if ( len(foundSystems) > 1):
    # todo check for system name clear/clr here
    return False


def parseUrls(rtext) -> bool:
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


def parseLocal(path: str, char_name: str, line: str) -> Message:
    """
        Parse a local file for a change of th current system.
    Args:
        path: the name of the monitored file
        char_name: the players  name which is assigned to the pathname
        line: str
            the new line out of the intel text file to be parsed now

    Returns:
        Message Object which hold the information regarding the change of the system
            user: holds the name of the character
            status : if States.LOCATION a change of the system is required
            affectedSystems: a list holding the name of the system

    """
    message = Message(room="Local", message=line)

    if message.user in CTX.EVE_SYSTEM:
        if u':' in message.plainText:
            message.user = char_name
            message.affectedSystems = [message.plainText.split("*")[0].split(u':')[1].strip()]
            message.status = States.LOCATION
        elif u'：' in message.plainText:
            message.user = char_name
            message.affectedSystems = [message.plainText.split("*")[0].split(u'：')[1].strip()]
            message.status = States.LOCATION
        else:
            # We could not determine if the message was system-change related
            message.affectedSystems.clear()
            message.status = States.IGNORE
    else:
        message.status = States.IGNORE
    return message


def parseMessageForMap(systems_on_map: dict[str, System], message: Message) -> Message:
    """
        Parse the massage based on the current systems an text
    Args:
        systems_on_map:
        message:

    Returns:

    """
    original_text = message.plainText
    formatted_text = u"<rtext>{0}</rtext>".format(original_text)
    soup = BeautifulSoup(formatted_text, 'html.parser')
    rtext = soup.select("rtext")[0]
    message.affectedSystems = set()

    while parseUrls(rtext):
        continue

    parseSystems(systems_on_map, rtext, message.affectedSystems)

    for system in message.affectedSystems:
        if system.name in systems_on_map.keys():
            while parsePlayerNames(rtext):
                continue

    while parseShips(rtext):
        continue

    parsed_status = parseStatus(rtext)
    message.status = parsed_status if parsed_status is not None else States.ALARM

    message.guiText = str(rtext)
    message.original_text = original_text

    for system in message.affectedSystems:
        system.setStatus(message=message)

    return message

###########################################################################
#  Vintel - Visual Intel Chat Analyzer									  #
#  Copyright (C) 2014-15 Sebastian Meyer (sparrow.242.de+eve@gmail.com )  #
#  																		  #
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

import datetime
import os
import time
import logging

from bs4 import BeautifulSoup
from vi import states
from PySide6.QtWidgets import QMessageBox

from .parser_functions import parseStatus, CTX
from .parser_functions import parseUrls, parseShips, parseSystems

# Names the local chatlogs could start with (depends on l10n of the client)
LOCAL_NAMES = ("Local", "Lokal", str("\u041B\u043E\u043A\u0430\u043B\u044C\u043D\u044B\u0439"))


class ChatParser(object):
    """ ChatParser will analyze every new line that was found inside the Chatlogs.
    """

    def __init__(self, path=None, rooms=None, systems=None, inteltime=20):
        """ path = the path with the logs
            rooms = the rooms to parse"""
        self.path = path  # the path with the chatlog
        self.rooms = rooms  # the rooms to watch (excl. local)
        self.systems = systems  # the known systems as dict name: system
        self.intelTime = inteltime  # 20 min intel time as default
        self.fileData = {}  # information about the files in the directory
        self.knownMessages = []  # message we already analyzed
        self.locations = {}  # information about the location of a char
        self.ignoredPaths = []
        self.ignoredChars = []  # character names to be ignored
        if path is not None:
            self._collectInitFileData(path)

    def _collectInitFileData(self, path):
        current_time = time.time()
        max_diff = 60 * 60 * 24  # what is 1 day in seconds
        for filename in os.listdir(path):
            full_path = os.path.join(path, filename)
            file_time = os.path.getmtime(full_path)
            if current_time - file_time < max_diff:
                self.addFile(full_path)

    def roomNameFromFileName(self, filename):
        # Checking if we must do anything with the changed file.
        # We only need those which name is in the rooms-list
        # EvE names the file like room_20210210_223941_1350114619.txt, so we don't need
        # the last 31 chars
        no_id_str = filename[:filename.rindex("_")]
        no_time_str = no_id_str[:no_id_str.rindex("_")]
        return no_time_str[:no_time_str.rindex("_")]
          
    def addFile(self, path):
        filename = os.path.basename(path)
        roomname = self.roomNameFromFileName(filename)
        try:
            with open(path, "r", encoding='utf-16-le') as f:
                content = f.read()
            logging.debug("Add room " + roomname + " to list.")
        except Exception as e:
            self.ignoredPaths.append(path)
            logging.warning("Read a log file failed: File: {0} - problem: {1}".format(path, str(e)))
            return None

        lines = content.split("\n")
        if path not in self.fileData or (roomname in LOCAL_NAMES and "charname" not in self.fileData.get(path, [])):
            self.fileData[path] = {}
            if roomname in LOCAL_NAMES:
                charname = None
                sessionStart = None
                # for local-chats we need more infos
                for line in lines:
                    if "Listener:" in line:
                        charname = line[line.find(":") + 1:].strip()
                    elif "Session started:" in line:
                        sessionStr = line[line.find(":") + 1:].strip()
                        sessionStart = datetime.datetime.strptime(sessionStr, "%Y.%m.%d %H:%M:%S")

                    if charname and sessionStart:
                        self.fileData[path]["charname"] = charname
                        self.fileData[path]["sessionstart"] = sessionStart
                        break
        self.fileData[path]["lines"] = len(lines)
        return lines

    def _lineToMessage(self, line, roomname):

        if roomname not in self.rooms:
            return None

        # finding the timestamp
        timeStart = line.find("[") + 1
        timeEnds = line.find("]")
        timeStr = line[timeStart:timeEnds].strip()
        try:
            timestamp = datetime.datetime.strptime(timeStr, "%Y.%m.%d %H:%M:%S")
        except ValueError:
            return None

        if timestamp < datetime.datetime.utcnow()-datetime.timedelta(minutes=self.intelTime):
            logging.debug("Skip {} Room:{}".format(line, roomname))
            return None

        # finding the username of the poster
        userEnds = line.find(">")
        username = line[timeEnds + 1:userEnds].strip()
        # finding the pure message
        text = line[userEnds + 1:].strip()  # text will the text to work an
        originalText = text
        formatedText = u"<rtext>{0}</rtext>".format(text)
        soup = BeautifulSoup(formatedText, 'html.parser')
        rtext = soup.select("rtext")[0]
        systems = set()
        upperText = text.upper()

        message = Message(roomname, "", timestamp, username, systems, text, originalText)
        # May happen if someone plays > 1 account
        if message in self.knownMessages:
            message.status = states.IGNORE
            return message

        while parseShips(rtext):
            continue
        while parseUrls(rtext):
            continue
        while parseSystems(self.systems, rtext, systems):
            continue
        parsedStatus = parseStatus(rtext)
        status = parsedStatus if parsedStatus is not None else states.ALARM

        # If message says clear and no system? Maybe an answer to a request?
        if status == states.CLEAR and not systems:
            maxSearch = 2  # we search only max_search messages in the room
            for count, oldMessage in enumerate(
                    oldMessage for oldMessage in self.knownMessages[-1::-1] if oldMessage.room == roomname):
                if oldMessage.systems and (oldMessage.status == states.REQUEST or oldMessage.status == states.ALARM):
                    for system in oldMessage.systems:
                        systems.add(system)
                    break
                if count > maxSearch:
                    break
        message.message = str(rtext)
        message.status = status
        self.knownMessages.append(message)
        if systems:
            for system in systems:
                system.messages.append(message)
        return message

    def _parseLocal(self, path, line):
        message = []
        """ Parsing a line from the local chat. Can contain the system of the char
        """
        charname = self.fileData[path]["charname"]
        if charname not in self.locations:
            self.locations[charname] = {"system": "?", "timestamp": datetime.datetime(1970, 1, 1, 0, 0, 0, 0)}

        # Finding the timestamp
        timeStart = line.find("[") + 1
        timeEnds = line.find("]")
        timeStr = line[timeStart:timeEnds].strip()
        timestamp = datetime.datetime.strptime(timeStr, "%Y.%m.%d %H:%M:%S")

        # Finding the username of the poster
        userEnds = line.find(">")
        username = line[timeEnds + 1:userEnds].strip()

        # Finding the pure message
        text = line[userEnds + 1:].strip()  # text will the text to work an
        #todo: other lanuagas here
        if username in CTX.EVE_SYSTEM:
            if ":" in text:
                system = text.split(":")[1].strip().replace("*", "").upper()
                status = states.LOCATION
            else:
                # We could not determine if the message was system-change related
                system = "?"
                status = states.IGNORE
            if timestamp > self.locations[charname]["timestamp"]:
                self.locations[charname]["system"] = system
                self.locations[charname]["timestamp"] = timestamp
                message = Message("", "", timestamp, charname, [system, ], "", "", status)
        return message

    def fileModified(self, path, rescan=False):
        messages = []
        if path in self.ignoredPaths:
            return []
        filename = os.path.basename(path)
        roomname = self.roomNameFromFileName(filename)
        if path not in self.fileData or rescan:
            # seems eve created a new file. New Files have 12 lines header
            self.fileData[path] = {"lines": 13}

        old_length = self.fileData[path]["lines"]
        lines = self.addFile(path)
        if path in self.ignoredPaths:
            return []
        for line in lines[old_length - 1:]:
            line = line.strip()
            if len(line) > 2:
                if roomname in LOCAL_NAMES:
                    message = self._parseLocal(path, line)
                else:
                    message = self._lineToMessage(line, roomname )
                if message:
                    messages.append(message)
        return messages


class Message(object):
    def __init__(self, room, message, timestamp, user, systems, upperText, plainText="", status=states.ALARM):
        self.room = room  # chatroom the message was posted
        self.message = message  # the messages text
        self.timestamp = timestamp  # time stamp of the massage
        self.user = user  # user who posted the message
        self.systems = systems  # list of systems mentioned in the message
        self.status = status  # status related to the message
        self.upperText = upperText  # the text in UPPER CASE
        self.plainText = plainText  # plain text of the message, as posted
        # if you add the message to a widget, please add it to widgets
        self.widgets = []

    def canProcess(self) -> bool:
        return self.user not in CTX.EVE_SYSTEM and self.status != states.IGNORE

    def __key(self):
        return self.room, self.plainText, self.timestamp, self.user

    def __eq__(x, y):
        return x.__key() == y.__key()

    def __hash__(self):
        return hash(self.__key())        

    def __del__(self):
        logging.debug("delete message {}".format(self.message))

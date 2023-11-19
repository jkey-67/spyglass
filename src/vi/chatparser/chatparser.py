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
import logging

from vi import states
from .message import Message
from .parser_functions import parseMessageForMap
from .parser_functions import parseLocal

# Names the local chat logs could start with (depends on l10n of the client)

LOCAL_NAMES = ("Local", "Lokal", str("\u041B\u043E\u043A\u0430\u043B\u044C\u043D\u044B\u0439"), u'지역', u'ローカル')


class ChatParser(object):
    """ ChatParser will analyze every new line that was found inside the Chatlogs.
    """

    def __init__(self, path=None, rooms=None, inteltime=20):
        """ path = the path with the logs
            rooms = the rooms to parse"""
        self.path = path  # the path with the chatlog
        self.rooms = rooms  # the rooms to watch (excl. local)
        self.intelTime = inteltime  # 20 min intel time as default
        self.fileData = {}  # information about the files in the directory
        self.knownMessages = []  # message we already analyzed
        self.locations = {}  # information about the location of a char
        self.ignoredPaths = []
        self.ignoredChars = []  # character names to be ignored
        if path is not None:
            self._collectInitFileData(path)

    @staticmethod
    def lastDowntime():
        """ Return the timestamp from the last downtime
        """
        target = datetime.datetime.utcnow()
        if target.hour < 11:
            target = target - datetime.timedelta(1)
        target = datetime.datetime(target.year, target.month, target.day, 11, 5, 0, 0)
        return target.timestamp()

    def _collectInitFileData(self, path):
        last_downtime = self.lastDowntime()  # 60 * 60 * 24  # what is 1 day in seconds
        for filename in os.listdir(path):
            full_path = os.path.join(path, filename)
            file_time = os.path.getmtime(full_path)
            if file_time > last_downtime:
                self._fetchFileChanges(full_path)

    @staticmethod
    def roomNameFromFileName(filename):
        # Checking if we must do anything with the changed file.
        # We only need those which name is in the rooms-list
        # EvE names the file like room_20210210_223941_1350114619.txt, so we don't need
        # the last 31 chars
        no_id_str = filename[:filename.rindex("_")]
        no_time_str = no_id_str[:no_id_str.rindex("_")]
        return no_time_str[:no_time_str.rindex("_")]
          
    def _fetchFileChanges(self, path):
        """
            updates the data like number of lines and user and room name for a give path and return the content
            full content or the update section
        Args:
            path: name of the file to be fetched

        Returns:

        """
        filename = os.path.basename(path)
        roomname = self.roomNameFromFileName(filename)
        try:
            with open(path, "r", encoding='utf-16-le') as f:
                content = f.read()
            logging.debug("Add room " + roomname + " to list.")
        except Exception as e:
            self.ignoredPaths.append(path)
            logging.warning("Read a log file failed: File: {0} - problem: {1}".format(path, str(e)))
            return None, None

        lines = content.split("\n")
        if path not in self.fileData or (roomname in LOCAL_NAMES and "charname" not in self.fileData.get(path, [])):
            self.fileData[path] = {}
            if roomname in LOCAL_NAMES:
                charname = None
                session_start = None
                # for local-chats we need more infos
                for line in lines:
                    if "Listener:" in line:
                        charname = line[line.find(":") + 1:].strip()
                    elif "Session started:" in line:
                        session_str = line[line.find(":") + 1:].strip()
                        session_start = datetime.datetime.strptime(session_str, "%Y.%m.%d %H:%M:%S")

                    if charname and session_start:
                        self.fileData[path]["charname"] = charname
                        self.fileData[path]["sessionstart"] = session_start
                        self.fileData[path]["lines"] = 1
                        break
        if "lines" in self.fileData[path].keys():
            prev_lines = self.fileData[path]["lines"]
        else:
            prev_lines = 1
        self.fileData[path]["lines"] = len(lines)
        return lines, prev_lines

    def _lineToMessage(self, line, room_name, systems_on_map):
        if room_name not in self.rooms:
            return None

        timestamp = Message.lineToDatetime(line)
        if timestamp is None:
            return None

        message = Message(room=room_name,
                          message=line)
        valid_timestamp = datetime.datetime.utcnow()-datetime.timedelta(minutes=self.intelTime)
        if message.timestamp < valid_timestamp:
            logging.debug("Skip {} Room:{}".format(line, room_name))
            return None

        # May happen if someone plays > 1 account
        if message in self.knownMessages:
            message.status = states.IGNORE
            logging.debug("Ignore {} Room:{}".format(line, room_name))
            return message
        # Parse new message only  if needed
        parseMessageForMap(systems_on_map, message)
        self.knownMessages.append(message)
        return message

    def fileModified(self, path, systems_on_map, rescan=False):
        messages = []
        if path in self.ignoredPaths:
            return []

        if rescan:
            self.knownMessages.clear()

        file_name = os.path.basename(path)
        room_name = self.roomNameFromFileName(file_name)
        if path not in self.fileData or rescan:
            # seems eve created a new file. New Files have 12 lines header
            self.fileData[path] = {"lines": 13}

        if path in self.ignoredPaths:
            return []

        lines, old_length = self._fetchFileChanges(path)
        for line in lines[old_length-1:]:
            line = line.strip()
            if len(line) > 2:
                if room_name in LOCAL_NAMES:
                    monitored_character_name = self.fileData[path]["charname"]
                    if monitored_character_name not in self.locations:
                        self.locations[monitored_character_name] = {"system": "?",
                                                                    "timestamp": datetime.datetime(1970, 1, 1, 0, 0, 0,
                                                                                                   0)}
                    message = parseLocal(path, monitored_character_name, line)
                    if message.status is states.LOCATION:
                        if message.timestamp > self.locations[monitored_character_name]["timestamp"]:
                            self.locations[monitored_character_name]["system"] = message.affectedSystems[0]
                            self.locations[monitored_character_name]["timestamp"] = message.timestamp
                        else:
                            message.status = states.IGNORE

                        messages.append(message)
                else:
                    if room_name in self.rooms:
                        message = self._lineToMessage(line, room_name, systems_on_map)
                        if message:
                            messages.append(message)
        return messages

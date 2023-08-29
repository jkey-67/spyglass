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
import logging

from vi import states
from .ctx import CTX


class Message(object):
    def __init__(self,
                 room: str,
                 message: str,
                 systems=list()):
        self.roomName = room                                # chatroom the message was posted
        self.affectedSystems = systems                      # list of systems mentioned in the message
        self.timestamp = Message.lineToDatetime(message)    # time stamp of the massage
        self.user = Message.lineToUserName(message)         # user who posted the message
        self.plainText = Message.lineToMessageText(message) # plain text of the message, as posted
        self.status = states.UNKNOWN                        # status related to the message
        self.guiText = ""                                   # the messages text to be displayed on the GUI

        # if you add the message to a widget, please add it to widgets
        self.widgets = []

    def canProcess(self) -> bool:
        return self.user not in CTX.EVE_SYSTEM and self.status != states.IGNORE

    def __key(self):
        return self.roomName, self.timestamp, self.user

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __hash__(self):
        return hash(self.__key())        

    def __del__(self):
        logging.debug("delete message {}".format(self.guiText))

    @property
    def simpleText(self):
        return Message.lineToMessageText(self.plainText)
    @staticmethod
    def lineToDatetime(line):
        # finding the timestamp
        time_start = line.find("[") + 1
        time_ends = line.find("]")
        time_str = line[time_start:time_ends].strip()
        try:
            return datetime.datetime.strptime(time_str, "%Y.%m.%d %H:%M:%S")
        except ValueError:
            return None


    @staticmethod
    def lineToUserName(line):
        user_start = line.find("]") + 1
        user_ends = line.find(">")
        return line[user_start:user_ends].strip()

    @staticmethod
    def lineToMessageText(line):
        # finding the username of the poster
        user_ends = line.find(">")
        # finding the pure message
        return line[user_ends + 1:].strip()  # text will the text to work an

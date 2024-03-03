###########################################################################
#  Vintel - Visual Intel Chat Analyzer                                    #
#  Copyright (C) 2014-15 Sebastian Meyer (sparrow.242.de+eve@gmail.com )  #
#                                                                         #
#  This program is free software: you can redistribute it and/or modify	  #
#  it under the terms of the GNU General Public License as published by	  #
#  the Free Software Foundation, either version 3 of the License, or	  #
#  (at your option) any later version.                                    #
#                                                                         #
#  This program is distributed in the hope that it will be useful,        #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the          #
#  GNU General Public License for more details.                           #
#                                                                         #
#                                                                         #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.   If not, see <http://www.gnu.org/licenses/>. #
###########################################################################

import logging
from vi.states import States
from .ctx import CTX
from .line_parser import lineToDatetime, lineToMessageText, lineToUserName


class Message(object):
    """
    Class representing a single  message to be possibly logged to one of the chat widgets

    Attributes:
    ----------
    roomName:str
        The name of the room which causes the message

    timestamp:
        time stamp of the massage

    user: str
        The name of the user who posted the message

    plainText:str
        The plain text of the message, as posted

    guiText:str
        The messages text to be displayed on the GUI

    widgets: list[QWidget]
        If you add the message to a widget, please add it also to that widgets

    Args:
    ----
    roomName : str
        The name io the room.

    user : str
        Name of the user who posts the message.

    Method:
    ------
    __init__(room, message, systems):
        Construct the instance

    canProcess(): bool
        Prints the person's name and age.

    status():States:
        Gets the state io the message.

    affectedSystems() -> set:
        A set of system names or Systems which were affected by the message.
    """

    def __init__(self,
                 room: str,
                 message: str,
                 systems: set[str] = None):
        self.roomName = room                                    # chatroom the message was posted
        self._affectedSystems = systems if systems else set()   # list of systems mentioned in the message
        self._status = States.UNKNOWN                           # status related to the message
        self.timestamp = lineToDatetime(message)        # time stamp of the massage
        self.user = lineToUserName(message)             # user who posted the message
        self.plainText = lineToMessageText(message)     # plain text of the message, as posted
        self.guiText = ""                                       # the messages text to be displayed on the GUI

        # if you add the message to a widget, please add it to widgets
        self.widgets = []

    def canProcess(self) -> bool:
        """
            Check if the message is not from system and not flagged as IGNORE

        Returns: bool
            True if the message can be processed
        """
        return self.status != States.IGNORE and self.user not in CTX.EVE_SYSTEM

    def __key(self):
        return self.timestamp, self.roomName, self.user

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __hash__(self):
        return hash(self.__key())        

    def __del__(self):
        logging.debug("delete message {}".format(self.__key()))

    @property
    def status(self) -> States:
        """
        Gets the state io the message.

        Returns: State
            One of the States enum
        """
        return self._status

    @status.setter
    def status(self, status: States):
        """
        Sets the state of the message
        Args:
            status:

        Returns:

        """
        self._status = status

    @property
    def affectedSystems(self) -> set:
        """
        A set of system names which were affected by the message.

        Returns: str
            Set of system names
        """
        return self._affectedSystems

    @affectedSystems.setter
    def affectedSystems(self, systems: set = None):
        self._affectedSystems = systems if systems else set()

    @property
    def simpleText(self):
        return lineToMessageText(self.plainText)

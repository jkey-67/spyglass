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

###########################################################################
# Holding the states for messages here                                    #
###########################################################################

from enum import IntEnum


class States(IntEnum):
    """
    IGNORE:
        Do not process the message.

    NOT_CHANGE:
        Don't change anything.

    CLEAR:
        State is clear, system was tagged as clr or clear.

    ALARM:
        State is alarm, system was tagged as red +10 clr or a character name.

    REQUEST:
        A status update is required.

    LOCATION:
        A characters location was changed

    SOUND_TEST:
        Beep or say 'testing sound test'

    UNKNOWN:
        Initial value, not initialized jet.
    """
    UNKNOWN = 0
    CLEAR = 1
    ALARM = 2
    REQUEST = 3
    LOCATION = 4
    IGNORE = 5

    def __str__(self):
        if self.value == States.IGNORE:
            return 'ignore'
        elif self.value == States.UNKNOWN:
            return 'unknown'
        elif self.value == States.CLEAR:
            return 'clear'
        elif self.value == States.ALARM:
            return 'alarm'
        elif self.value == States.REQUEST:
            return 'request'
        elif self.value == States.LOCATION:
            return 'location'
        else:
            return ''


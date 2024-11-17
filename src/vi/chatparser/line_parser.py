###########################################################################
#  EVE-Spyglass - Visual Intel Chat Analyzer                              #
#  Copyright (C) 2022 Nele McCool (nele.mccool@gmx.net)                   #
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

import datetime
from typing import Optional


def lineToDatetime(line: str) -> Optional[datetime]:
    """
        Extracts the timestamp from a single line from an intel file.

    Args:
        line:
            The line from a text file that has to be parsed now.

    Returns:
        datetime or None
    """
    time_start = line.find("[") + 1
    time_ends = line.find("]")
    time_str = line[time_start:time_ends].strip()
    try:
        return datetime.datetime.strptime(time_str, "%Y.%m.%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        try:
            return datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            return None


def lineToUserName(line: str) -> str:
    """
        Fetch the users name from a single line from an intel file.

    Args:
        line: str
            The line from a text file that has to be parsed now.

    Returns: str
        The name of the user who post the message
    """
    user_start = line.find("]") + 1
    user_ends = line.find(">")
    return line[user_start:user_ends].strip()


def lineToMessageText(line):
    """
        Fetch the message from a single line from an intel file.

    Args:
        line: str
            The line from a text file that has to be parsed now.

    Returns: str
        The message text.
    """
    # finding the username of the poster
    user_ends = line.find(">")
    # finding the pure message
    return line[user_ends + 1:].strip()  # text will the text to work an

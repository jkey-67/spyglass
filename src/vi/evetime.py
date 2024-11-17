###########################################################################
#  EVE-Spyglass - Visual Intel Chat Analyzer                              #
#  Copyright (C) 2024 Nele McCool (nele.mccool @ gmx.net)                 #
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
import time
import zoneinfo

def currentEveTime() -> datetime.datetime:
    """ Gets the current eve time utc now

    Returns:
        datetime.datetime: The current eve-time as a datetime.datetime
    """
    return datetime.datetime.now(datetime.timezone.utc)


def secondsTillDowntime() -> int:
    """ Return the seconds till the next downtime"""
    now = currentEveTime()
    target = now
    if now.hour > 11:
        target = target + datetime.timedelta(1)
    target = datetime.datetime(target.year, target.month, target.day, 11, 5, 0, 0, tzinfo=datetime.timezone.utc)
    delta = target - now
    return delta.seconds


def lastDowntime() -> float:
    """ Return the timestamp from the last downtime as local time float
    """
    target = currentEveTime()
    if target.hour < 11:
        target = target - datetime.timedelta(days=1)
    target = datetime.datetime(target.year, target.month, target.day, 11, 5, 0, 0,
                               tzinfo=datetime.timezone.utc).astimezone(tz=None)
    return target.timestamp()


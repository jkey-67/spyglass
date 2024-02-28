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


class CTX:
    EVE_SYSTEM = (u"EVE-System", u"EVE System", u"Système EVE", u"Система EVE", u'EVE システム', u'EVE系统',
                  u'EVE星系', u'이브 시스템', u'Sistema EVE')
    CHARS_TO_IGNORE = ("*", "?", ",", "!", ".", "^")
    WORDS_TO_IGNORE = ("IN", "IS", "AS", "AT", "NV", "ESS", "GATE", "HOSTILE")
    FORMAT_URL = u"""<a style="color:#28a5ed;font-weight:medium" href="link/{0}">{0}</a>"""
    FORMAT_SHIP \
        = u"""<a  style="color:#d95911;font-weight:medium" href="link/https://wiki.eveuniversity.org/{0}">{0}</a>"""
    FORMAT_PLAYER_NAME \
        = u""" <a  style="color:#d0d0d0;font-weight:medium" href="link/https://zkillboard.com/character/{1}/">{0}</a>"""
    FORMAT_ALLIANCE_NAME \
        = u""" <a  style="color:#d0d0d0;font-weight:medium" href="link/https://zkillboard.com/alliance/{1}/">{0}</a>"""
    FORMAT_SYSTEM = u"""<a style="color:#888880;font-weight:medium" href="mark_system/{0}">{1}</a>"""
    FORMAT_SYSTEM_IN_REGION = u"""<a style="color:#DAA520;font-weight:medium" href="mark_system/{0}">{1}</a>"""
    STATUS_CLEAR = {"CLEAR", "CLR", "CRL", "CLR ATM"}
    STATUS_STATUS = {"STAT", "STATUS", "STATE"}
    STATUS_BLUE = {"BLUE", "BLUES ONLY", "ONLY BLUE" "STILL BLUE", "ALL BLUES"}

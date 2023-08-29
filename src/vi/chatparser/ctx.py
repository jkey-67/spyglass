class CTX:
    EVE_SYSTEM = ("EVE-System", "EVE System", "Système EVE", "Система EVE")
    CHARS_TO_IGNORE = ("*", "?", ",", "!", ".", "^")
    WORDS_TO_IGNORE = ("IN", "IS", "AS", "AT", "NV", "ESS", "GATE", "HOSTILE")
    FORMAT_URL = u"""<a style="color:#28a5ed;font-weight:bold" href="link/{0}">{0}</a>"""
    FORMAT_SHIP = u"""<a  style="color:#d95911;font-weight:bold" href="link/https://wiki.eveuniversity.org/{0}">{0}</a>"""
    FORMAT_PLAYER_NAME = u""" <a  style="color:#d9c11;font-weight:bold" href="link/https://zkillboard.com/character/{1}/">{0}</a> """
    FORMAT_SYSTEM = u"""<a style="color:#888880;font-weight:bold" href="mark_system/{0}">{1}</a>"""
    FORMAT_SYSTEM_IN_RERION = u"""<a style="color:#CC8800;font-weight:bold" href="mark_system/{0}">{1}</a>"""
    STATUS_CLEAR = {"CLEAR", "CLR", "CRL"}
    STATUS_STATUS = {"STAT", "STATUS", "STATE"}
    STATUS_BLUE = {"BLUE", "BLUES ONLY", "ONLY BLUE" "STILL BLUE", "ALL BLUES"}
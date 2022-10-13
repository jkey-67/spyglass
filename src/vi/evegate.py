###########################################################################
#  EVE-Spyglass - Visual Intel Chat Analyzer                              #
#  Copyright (C) 2022 Nele McCool (nele.mccool @ gmx.net)                 #
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
import locale
import json
import time
import parse
import threading
from vi.universe import Universe

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread, QUrl
from PySide6.QtCore import Signal as pyqtSignal
from PySide6.QtWebEngineWidgets import QWebEngineView

from packaging import version

import queue
import requests
import logging
import urllib.parse
import http.server
import webbrowser
import base64
import hashlib
import secrets
from typing import Optional

""" eve_api_key.py defines the secret api key CLIENTS_API_KEY = "1234...4321" 
"""

import eve_api_key
from vi.cache.cache import Cache, currentEveTime, secondsTillDowntime
from vi.version import VERSION


ERROR = -1
NOT_EXISTS = 0
EXISTS = 1

""" todo: split the cache from esi functionality
"""

def setEsiCharName(name):
    """
    Sets the name of the current active api char to sqlite cache.

    Args:
        name(str):name of the active esi character

    Returns:
        str: Name of the current char from cache as string, or None
    """
    if name and name != "":
        Cache().putIntoCache("api_char_name", name)


def esiCharName():
    """
    Gets the name of the current active api char from the sqlite cache.

    Args: None

    Returns:
        str: Name of the current char from cache as string, or None
    """
    res = Cache().getFromCache("api_char_name", True)
    if res == "":
        return None
    else:
        return res


def secondUntilExpire(response, default:int = 3600) -> int:
    """
    Returns the second until expire from the html response header
    Args:
        response:

    Returns:
        seconds that can be used for caching, or 3600 as default
    """
    if "Expires" in response.headers:
        expires = response.headers["Expires"]
        old_locale = locale.setlocale(locale.LC_TIME, 'en_US')
        return (datetime.datetime.strptime(expires, "%a, %d %b %Y %H:%M:%S GMT") - datetime.datetime.utcnow()).seconds
    else:
        return default


def esiStatus() -> dict:
    """
    Request EVE Server status
    Returns:
        dict: status of EVE-Online

    """
    req = "https://esi.evetech.net/latest/status/?datasource=tranquility"
    response = requests.get(req)
    if response.status_code != 200:
        logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
        response.raise_for_status()
    return response.json()


def esiCharNameToId(char_name: str, use_outdated=False):
    """ Uses the EVE API to convert a character name to his ID.

    Args:
        char_name(str):character name to convert
        use_outdated(bool):if True, the cache timestamp will be ignored

    Returns:
        int:id of the character name
    """
    cache_key = "_".join(("name", "id", char_name))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id:
        return cached_id
    else:
        content = esiUniverseIds({char_name})
        if "characters" in content.keys():
            for idFound in content["characters"]:
                url = "https://esi.evetech.net/latest/characters/{id}/?datasource=tranquility".format(id=idFound["id"])
                response = requests.get(url.format(char_name))
                if response.status_code == 200:
                    details = response.json()
                    if "name" in details.keys():
                        name_found = details["name"]
                        if name_found.lower() == char_name.lower():
                            cache.putIntoCache(cache_key, idFound["id"], 60 * 60 * 24 * 365)
                            return idFound["id"]
                else:
                    logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
                    response.raise_for_status()
    return None


def esiUniverseIds(names, use_outdated=False):
    """ Uses the EVE API to convert a list of names to ids_to_names

    Args:
        names(list(str)): names list of names
        use_outdated(bool): if True the cache timestamp will be ignored

    Returns:
             dict : key=name, value=id
    """
    if len(names) == 0:
        return {}
    data = {}
    api_check_names = set()
    cache = Cache()
    # do we have already something in the cache?
    for name in names:
        cache_key = "_".join(("ids", "dicts", name))
        id_from_cache = cache.getFromCache(cache_key, use_outdated)
        if id_from_cache:
            for key, items in json.loads(id_from_cache).items():
                for item in items:
                    if key in data.keys():
                        data[key].append(item)
                    else:
                        data[key] = [item]

        else:
            api_check_names.add(name)

    try:
        # not in cache? asking the EVE API
        if len(api_check_names) > 0:
            list_of_name = ""
            for name in api_check_names:
                if list_of_name != "":
                    list_of_name = list_of_name + ","
                list_of_name = list_of_name + "\"{}\"".format(name)
            url = "https://esi.evetech.net/latest/universe/ids/?datasource=tranquility"
            response = requests.post(url, data="[{}]".format(list_of_name))
            if response.status_code == 200:
                content = response.json()
                with Cache() as cache:
                    for key, items in content.items():
                        for item in items:
                            cache_data = dict()
                            cache_data[key] = [item]
                            cache_key = "_".join(("ids", "dicts", item["name"]))
                            cache.putIntoCacheNoLock(cache_key, json.dumps(cache_data))
                            if key in data.keys():
                                data[key].append(item)
                            else:
                                data[key] = [item]
                    cache.con.commit()
                return data
            else:
                logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
    except Exception as e:
        logging.error("Exception during namesToIds: %s", e)
    return data


def esiUniverseNames(ids, use_outdated=False):
    """ Returns the names for a list of ids

        Args:
            ids(list): list of ids to search
            use_outdated(bool): if True the cache timestamp will be ignored

        Returns:
              dict:dict  key = id, value = name
    """
    data = {}
    if len(ids) == 0:
        return data
    api_check_ids = list()
    cache = Cache()

    # something already in the cache?
    for checked_id in ids:
        cache_key = u"_".join(("name", "id", str(checked_id)))
        name = cache.getFromCache(cache_key, use_outdated)
        if name:
            data[checked_id] = name
        else:
            api_check_ids.append(checked_id)
    if len(api_check_ids) == 0:
        return data

    try:
        list_of_ids = ""
        for checked_id in list(set(api_check_ids[0:999])):
            if list_of_ids != "":
                list_of_ids = list_of_ids + ","
            list_of_ids = list_of_ids + str(checked_id)
        url = "https://esi.evetech.net/latest/universe/names/?datasource=tranquility"
        response = requests.post(url, data="[{}]".format(list_of_ids))
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()
        content = response.json()
        if len(content) > 0:
            for elem in content:
                data[elem["id"]] = elem["name"]
            # and writing into cache
            with Cache() as cache:
                for checked_id in api_check_ids:
                    cache_key = u"_".join(("name", "id", str(checked_id)))
                    if checked_id in data.keys():
                        cache.putIntoCacheNoLock(cache_key, data[int(checked_id)], 60 * 60 * 24 * 365)
                cache.con.commit()
        if len(api_check_ids) > 1000:
            return esiUniverseNames(ids, use_outdated)
    except Exception as e:
        logging.error("Exception during idsToNames: %s", e)
    return data


class evetech_image:
    alliances = ["alliances", "logo"]
    characters = ["characters", "portrait"]
    types_icon = ["types", "icon"]
    types_render = ["types", "render"]
    types_bpc = ["types", "bpc"]
    types_bp = ["types", "bp"]
    types_relict = ["types", "relict"]
    corporations = ["corporations", "logo"]


def esiImageEvetechNet(character_id: int, req_type: evetech_image, image_size=64):
    """Downloading the avatar for a player/character
       - https://docs.esi.evetech.net/docs/image_server.html
    Args:
        int id:ident to fined
        evetech_image type:type of image
        image_size: size of the image, 32, 64, 128, 256, 512, and 1024.

    Returns:
        bytearray: None if something gone wrong, else the png
    """

    avatar = None
    if character_id:
        image_url = "https://images.evetech.net/{type}/{id}/{info}?tenant=tranquility&size={size}"
        response = requests.get(image_url.format(id=character_id, size=image_size, type=req_type[0], info=req_type[1]))
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %60s", response.status_code, response.reason, response.url)
            avatar = None
        else:
            avatar = response.content
    return avatar


def getTypesIcon(type_id: int, size_image=64):
    """Get icon from a given type_id or character_id

    Args:
        type_id:  id of type
        size_image: size of the image 32, 64 or 128

    Returns:
        bytearray: png image as bytearray

    """
    used_cache = Cache()
    img = used_cache.getImageFromCache(str(type_id))
    if img is None:
        image_url = "https://images.evetech.net/types/{id}/icon"
        response = requests.get(image_url.format(id=type_id, size=size_image))
        if response.status_code == 200:
            used_cache.putImageToCache(str(type_id), response.content)
            img = response.content
        else:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
    if img:
        return bytearray(img)
    else:
        return None


def esiCharactersPortrait(char_name, image_size=64):
    """Downloading the avatar for a player/character

    Args:
        char_name: name of the character
        image_size: size of the image, 32, 64, 128, 256, 512, and 1024.

    Returns:
        bytearray: None if something gone wrong, else the png
    """

    avatar = None
    try:
        char_id = esiCharNameToId(char_name)
        if char_id:
            image_url = "https://images.evetech.net/characters/{id}/portrait?tenant=tranquility&size={size}"
            response = requests.get(image_url.format(id=char_id, size=image_size))
            if response.status_code != 200:
                logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
                response.raise_for_status()
            avatar = response.content

    except Exception as e:
        logging.error("Exception during esiCharactersPortrait: %s", e)
        avatar = None
    return avatar


def checkPlayerName(char_name):
    """ Checking on esi for an exiting exact player name

        Args:
            char_name(str): name of the character

        Returns:
             int: 1 if exists, 0 if not and -1 if an error occurred
    """
    if not char_name:
        return ERROR
    try:
        if esiCharNameToId(char_name):
            return EXISTS
        else:
            return NOT_EXISTS
    except Exception as e:
        logging.error("Exception on checkPlayerName: %s", e)
    return ERROR


def esiCharacters(char_id, use_outdated=False):
    cache_key = u"_".join(("playerinfo_id_", str(char_id)))
    used_cache = Cache()
    char_info = used_cache.getFromCache(cache_key, use_outdated)
    if char_info is not None:
        char_info = json.loads(char_info)
    else:
        try:
            url = "https://esi.evetech.net/latest/characters/{id}/?datasource=tranquility".format(id=int(char_id))
            response = requests.get(url)
            if response.status_code != 200:
                logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
                response.raise_for_status()
            char_info = response.json()
            # should be valid for up to three days
            used_cache.putIntoCache(cache_key, response.text, 86400)
        except requests.exceptions.RequestException as e:
            # We get a 400 when we pass non-pilot names for KOS check so fail silently for that one only
            if e.response.status_code != 400:
                logging.error("Exception during getCharInfoForCharId: %s", str(e))
    return char_info


def esiCheckCharacterToken(char_name: str) -> bool:
    return checkTokenTimeLine(getTokenOfChar(char_name)) is not None


def esiGetCharsOnlineStatus() -> list:
    result = list()
    for char in Cache().getAPICharNames():
        api_char = {
            "name": char,
            "online": esiCharactersOnline(char),
            "system": esiUniverseSystems(esiCharactersLocation(char))
        }
        result.append(api_char)
    return result


def esiCharactersOnline(char_name: str) -> bool:
    """ Returns the online state of the char with name char_name.

    Args:
        char_name(str): The in game name of the char.

    Returns:
        bool:true if char is online, false otherwise .

    Raises:
        HTTPError:
    """
    token = checkTokenTimeLine(getTokenOfChar(char_name))
    if token:
        url = "https://esi.evetech.net/latest/characters/{}/online/?datasource=tranquility&token={}".format(
            esiCharNameToId(char_name), token.access_token)
        response = requests.get(url)
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            return False
        char_online = response.json()
        if "online" in char_online.keys():
            return char_online["online"]
        else:
            return False
    return False


def esiCharactersLocation(char_name: str):
    """Gets the current solar system id of the char with id char_id, or None

    Args:
        char_name(str):The in game name of the character

    Returns:
        int: Current system_id or None

    Raises:
        HTTPError:
    """
    token = checkTokenTimeLine(getTokenOfChar(char_name))
    if token:
        url = "https://esi.evetech.net/latest/characters/{}/location/?datasource=tranquility&token={}".format(
            esiCharNameToId(char_name),
            token.access_token)
        response = requests.get(url)
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()
        char_online = response.json()
        if "solar_system_id" in char_online.keys():
            return char_online["solar_system_id"]
    return None


def esiCharactersCorporationHistory(char_id, use_outdated=True):
    """ Returns a list with the ids if the corporation history of a charId
        returns a list of only the corp structs
        @param char_id id the char
        @param use_outdated also return outdated results from cache
    """
    cache_key = u"_".join(("corp_history_id_", str(char_id)))
    cache = Cache()
    corp_ids = cache.getFromCache(cache_key, use_outdated)
    if corp_ids is not None:
        corp_ids = json.loads(corp_ids)
    else:
        try:
            char_id = int(char_id)
            url = "https://esi.evetech.net/latest/characters/{id}/corporationhistory/?datasource=tranquility".format(id=char_id)
            response = requests.get(url)
            if response.status_code != 200:
                logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
                response.raise_for_status()
            corp_ids = response.json()
            cache.putIntoCache(cache_key, response.text, 86400)
        except requests.exceptions.RequestException as e:
            # We get a 400 when we pass non-pilot names for KOS check so fail silently for that one only
            if e.response.status_code != 400:
                logging.error("Exception during getCharInfoForCharId: %s", str(e))
    # id_list = list()
    # for elem in corp_ids:
    #     id_list.append(elem["corporation_id"])
    return corp_ids


def getCurrentCorpForCharId(char_id, use_outdated=True):
    """ Returns the ID of the players current corporation.
    """
    info = esiCharacters(char_id, use_outdated)
    if info and "corporation_id" in info.keys():
        return info["corporation_id"]
    else:
        logging.error("Unable to get corporation_id of char id:{}".format(char_id))
        return None


def esiUniverseSystem_jumps(use_outdated=False):
    """ Reads the information for all solarsystem from the EVE API
        Reads a dict like:
            systemid: "jumps", "shipkills", "factionkills", "podkills"
    """
    data = {}
    system_data = {}
    cache = Cache()
    # first the data for the jumps
    cache_key = "jumpstatistic"
    jump_data = cache.getFromCache(cache_key, use_outdated)

    try:
        if jump_data is None:
            jump_data = {}
            url = "https://esi.evetech.net/latest/universe/system_jumps/?datasource=tranquility"
            response = requests.get(url)
            if response.status_code != 200:
                logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
                response.raise_for_status()
            resp = response.json()
            for row in resp:
                jump_data[int(row["system_id"])] = int(row["ship_jumps"])
            cache.putIntoCache(cache_key, json.dumps(jump_data), secondUntilExpire(response))
        else:
            jump_data = json.loads(jump_data)

        # now the further data
        cache_key = "systemstatistic"
        system_data = cache.getFromCache(cache_key, use_outdated)

        if system_data is None:
            system_data = {}
            url = "https://esi.evetech.net/latest/universe/system_kills/?datasource=tranquility"
            response = requests.get(url)
            if response.status_code != 200:
                logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
                response.raise_for_status()
            resp = response.json()
            for row in resp:
                system_data[int(row["system_id"])] = {"ship": int(row["ship_kills"]),
                                                      "faction": int(row["npc_kills"]),
                                                      "pod": int(row["pod_kills"])}

            cache.putIntoCache(cache_key, json.dumps(system_data), secondUntilExpire(response))
        else:
            system_data = json.loads(system_data)
    except Exception as e:
        logging.error("Exception during getSystemStatistics: : %s", e)

    # We collected all data (or loaded them from cache) - now zip it together
    for i, v in jump_data.items():
        i = int(i)
        if i not in data:
            data[i] = {"shipkills": 0, "factionkills": 0, "podkills": 0}
        data[i]["jumps"] = v
    for i, v in system_data.items():
        i = int(i)
        if i not in data:
            data[i] = {"jumps": 0}
        data[i]["shipkills"] = v["ship"] if "ship" in v else 0
        data[i]["factionkills"] = v["faction"] if "faction" in v else 0
        data[i]["podkills"] = v["pod"] if "pod" in v else 0

    return data


class MyApiServer(http.server.BaseHTTPRequestHandler):
    """http server to get the redirected login message
    """
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("<html><head><title>Spyglass API Registration</title></head>".encode("utf-8"))
        self.wfile.write("<body onload=\"closePage()\"><p>Close this page to complete registration.</p>".encode("utf-8"))
        self.wfile.write("<script>function closePage(){self.close();}</script>".encode("utf-8"))
        self.wfile.write("</body></html>".encode("utf-8"))
        self.wfile.close()
        try:
            code = self.requestline.split(" ")[1]
            pos_code = code.find("code=")
            pos_state = code.find("&state=")
            self.server.api_code = code[pos_code + 5:pos_state]
            self.server.api_state = code[pos_state+6:]
            self.server.server_close()
        except Exception as e:
            logging.error("Exception during MyApiServer: %s", e)
            self.server.api_code = None

    def handle_timeout(self):
        logging.error("Http request not read, api registration canceled.")


class APIServerThread(QThread):
    new_serve_aki_key = pyqtSignal(str)
    LIST_CHARS = list()
    WEB_SERVER_LOCK = threading.Lock()

    def __init__(self, params,browser=None):
        QThread.__init__(self)
        self.client_param = params
        self.queue = queue.Queue()
        self.active = True
        self.auth_code = None
        self.browser = browser
        self.webserver = None

    def run(self):
        while self.active:
            try:
                with APIServerThread.WEB_SERVER_LOCK:
                    self.webserver = http.server.HTTPServer(("localhost", 8182), MyApiServer)
                    self.webserver.timeout = 120
                    self.webserver.api_code = None
                    self.webserver.close_connection = True
                self.webserver.handle_request()
                self.auth_code = self.webserver.api_code
                with APIServerThread.WEB_SERVER_LOCK:
                    self.webserver = None
                if self.auth_code is not None:
                    esiOauthToken(self.client_param, self.auth_code)
            except Exception as e:
                logging.error("Error in APIServerThread.run: %s", e)
                #continue
            self.browser = None
            self.active = False

    def createBrowserWindow(self, string_params, parent=None):
        """
            create the browser widget to login
        Args:
            string_params: param string to pass to web
            parent:None for system browser or a QObject with api_thread

        Returns:

        """
        if self.browser and parent:
            self.browser.destroyed.connect(self.quit)
            self.browser.load(QUrl("https://login.eveonline.com/v2/oauth/authorize?{}".format(string_params)))
            self.browser.resize(600, 800)
            self.browser.show()
        else:
            webbrowser.open_new("https://login.eveonline.com/v2/oauth/authorize?{}".format(string_params))

        logging.info("Awaiting registration during the next 120 seconds to be completed.")
        while self.isRunning():
            QApplication.processEvents()

        if self.auth_code:
            logging.info("Registration completed.")
        else:
            logging.error("Registration not succeeded.")

    def quit(self):
        self.active = False
        if self.browser:
            self.browser.close()
        with APIServerThread.WEB_SERVER_LOCK:
            if self.webserver:
                response = requests.get("http://localhost:8182/oauth-callback")
        QThread.quit(self)


def oauthLoginEveOnline(client_param, parent=None):
    """ Queries the eve-online api key valid for one eve online account,
        using http://localhost:8182/oauth-callback as application defined
        callback from inside the webb browser
        params client_id, scope and state see esi-docs
    """
    used_hash = hashlib.sha256()
    used_hash.update(client_param["random"])
    digs = used_hash.digest()
    code_challenge = base64.urlsafe_b64encode(digs).decode().replace("=", "")
    params = {
        "response_type": "code",
        "redirect_uri": "http://localhost:8182/oauth-callback",
        "client_id": client_param["client_id"],
        "scope": client_param["scope"],
        "state": client_param["state"],
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    string_params = urllib.parse.urlencode(params)

    if parent:
        if hasattr(parent, 'apiThread') and parent.apiThread:
            parent.apiThread.quit()
    else:
        class Object(object):
            pass

        parent = Object()
        parent.apiThread = None

    parent.apiThread = APIServerThread(client_param, QWebEngineView(None))
    parent.apiThread.start()
    parent.apiThread.createBrowserWindow(string_params, parent)


def esiOauthToken(client_param, auth_code: str, add_headers: dict = None):
    """ gets the access token from the application logging
        fills the cache wit valid login data
    """
    form_values = {
        "grant_type": "authorization_code",
        "client_id": client_param["client_id"],
        "code": auth_code,
        "code_verifier":  client_param["random"]
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "login.eveonline.com",
    }
    if add_headers:
        headers.update(add_headers)
    response = requests.post(
        "https://login.eveonline.com/v2/oauth/token",
        data=form_values,
        headers=headers,
    )
    if response.status_code == 200:
        oauth_call = response.json()
        header = {
            "Authorization": "{} {}".format(oauth_call["token_type"], oauth_call["access_token"]),
        }
        oauth_result = requests.get("https://login.eveonline.com/oauth/verify", headers=header)
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()
        else:
            char_api_key_set = oauth_result.json()
            char_api_key_set.update(oauth_call)
            Cache().putAPIKey(char_api_key_set)
            return char_api_key_set["CharacterName"]
    else:
        logging.error("ESI-Error %i : '%s' url: %60s", response.status_code, response.reason, response.url)
        response.raise_for_status()
    return None


def openWithEveonline(parent=None):
    """perform an api key request and updates the cache on case of a positive response
        returns the selected user name from the login
    """
    client_param_set = {
        "client_id": eve_api_key.CLIENTS_API_KEY,
        "scope": "esi-ui.write_waypoint.v1 "
                 "esi-universe.read_structures.v1 "
                 "esi-search.search_structures.v1 "
                 "esi-location.read_online.v1 "
                 "esi-location.read_location.v1",
        "random": base64.urlsafe_b64encode(secrets.token_bytes(32)),
        "state": base64.urlsafe_b64encode(secrets.token_bytes(8))
    }
    oauthLoginEveOnline(client_param_set, parent)


class ApiKey(object):
    def __init__(self, dictionary):
        self.__dict__ = dictionary
        if not hasattr(self, 'valid_until'):
            self.access_token = None
        if not hasattr(self, 'valid_until'):
            self.valid_until = None
        if not hasattr(self, 'expires_in'):
            self.expires_in = None
        if not hasattr(self, 'refresh_token'):
            self.refresh_token = None
        if not hasattr(self, 'CharacterName'):
            self.CharacterName = None
        if not hasattr(self, 'CharacterID'):
            self.CharacterID = None

    def update(self, dictionary):
        for k, v in dictionary.items():
            setattr(self, k, v)


def getTokenOfChar(char_name) -> Optional[ApiKey]:
    """gets the api key for char_name, or id from the cache, Result is the last ApiKey, or None

    Args:
        char_name: name of the char
    """
    if char_name is None:
        return None
    char_data = Cache().getAPIKey(char_name)
    if char_data:
        return ApiKey(json.loads(char_data))
    else:
        if char_name not in APIServerThread.LIST_CHARS:
            logging.debug("The character '{}' is not registered with ESI.".format(char_name))
            APIServerThread.LIST_CHARS.append(char_name)
        return None


def refreshToken(params: Optional[ApiKey]) -> Optional[ApiKey]:
    """ refreshes the token using the previously acquired data structure from the cache
        if succeeded with result 200 the cache will be updated too
    """
    if params is None:
        return None
    if params.refresh_token is None:
        return None

    data = {
        "grant_type": "refresh_token",
        "refresh_token": params.refresh_token,
        "client_id": eve_api_key.CLIENTS_API_KEY,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "login.eveonline.com",
    }
    response = requests.post("https://login.eveonline.com/v2/oauth/token", data=data, headers=headers)
    if response.status_code == 200:
        ref_token = response.json()
        params.update(ref_token)

        cache = Cache()
        char_api_key_set = json.loads(cache.getAPIKey(params.CharacterName))
        char_api_key_set["ExpiresOn"] = \
            datetime.datetime.utcfromtimestamp(time.time() + params.expires_in).strftime('%Y-%m-%dT%H:%M:%S')
        char_api_key_set["valid_until"] = \
            time.time() + params.expires_in
        char_api_key_set.update(ref_token)
        cache.putAPIKey(char_api_key_set)
        return params
    else:
        return params


def checkTokenTimeLine(param: Optional[ApiKey]) -> Optional[ApiKey]:
    """
        double-check the api timestamp, if expired the parm set will be updated

    Args:
        param: ApiKey to check

    Returns:
        updated ApiKey or None
    """
    if param is None:
        return None
    if param.valid_until is not None and param.valid_until > time.time():
        return param
    else:
        return refreshToken(param)


def sendTokenRequest(form_values, add_headers=None):
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "login.eveonline.com",
    }
    if add_headers:
        headers.update(add_headers)

    response = requests.post(
        "https://login.eveonline.com/v2/oauth/token",
        data=form_values,
        headers=headers,
    )

    print("Request sent to URL {} with headers {} and form values: "
          "{}\n".format(response.url, headers, form_values))
    if response.status_code != 200:
        logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
        response.raise_for_status()
    return response


def esiAutopilotWaypoint(char_name: str, system_id: int, beginning=True, clear_all=True):
    token = checkTokenTimeLine(getTokenOfChar(char_name))
    if token:
        route = {
            "add_to_beginning": beginning,
            "clear_other_waypoints": clear_all,
            "datasource": "tranquility",
            "destination_id": system_id,
            "token": token.access_token,
        }
        req = "https://esi.evetech.net/latest/ui/autopilot/waypoint/?{}".format(urllib.parse.urlencode(route))
        response = requests.post(req)
        if response.status_code != 204:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()


def getRouteFromEveOnline(jumpgates, src, dst):
    """build rout respecting jump bridges
        returns the list of systems to travel to
    """
    route_elements = ""
    for elem in jumpgates:
        if route_elements != "":
            route_elements = route_elements + ","
        route_elements = route_elements + "{}|{}".format(elem[0], elem[1])

    req = "https://esi.evetech.net/v1/route/{}/{}/?connections={}".format(src, dst, route_elements)
    response = requests.get(req)
    if response.status_code != 200:
        logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
        response.raise_for_status()
    return response.json()


def esiIncursions(use_outdated=False):
    """builds a list of incursion dicts cached 300s
    """
    cache = Cache()
    cache_key = "incursions"
    response = cache.getFromCache(cache_key, use_outdated)
    if response:
        return json.loads(response)
    else:
        req = "https://esi.evetech.net/latest/incursions/?datasource=tranquility"
        response = requests.get(req)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
            return response.json()
        else:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)

    return []


def getIncursionSystemsIds(use_outdated=False):
    res = list()
    incursion_list = esiIncursions(use_outdated)
    for constellations in incursion_list:
        for sys in constellations["infested_solar_systems"]:
            res.append(sys)
    return res


def esiSovereigntyCampaigns(use_outdated=False):
    """builds a list of reinforced campaigns for IHUB  and TCU dicts cached 60s
    """
    cache = Cache()
    cache_key = "sovereignty_campaigns"
    response = cache.getFromCache(cache_key, use_outdated)
    if response:
        return json.loads(response)
    else:
        req = "https://esi.evetech.net/latest/sovereignty/campaigns/?datasource=tranquility"
        response = requests.get(req)
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()
        cache.putIntoCache(cache_key, response.text, 60)  # 5 seconds from esi
        return response.json()


def esiSovereigntyStructures(use_outdated=False):
    """
    Shows sovereignty data for structures.

    Args:
        use_outdated:

    Returns:

    """
    cache = Cache()
    cache_key = "sovereignty_structures"
    response = cache.getFromCache(cache_key, use_outdated)
    if response:
        return json.loads(response)
    else:
        req = "https://esi.evetech.net/latest/sovereignty/structures/?datasource=tranquility"
        response = requests.get(req)
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()
        cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
        return response.json()


def esiSovereigntyMap(use_outdated=False):
    """
    Shows sovereignty information for solar systems

    Args:
        use_outdated:

    Returns:

    """
    cache = Cache()
    cache_key = "sovereignty_map"
    response = cache.getFromCache(cache_key, use_outdated)
    if response:
        return json.loads(response)
    else:
        req = "https://esi.evetech.net/latest/sovereignty/map/?datasource=tranquility"
        response = requests.get(req)
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()
        cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
        return response.json()

def getCampaignsSystemsIds(use_outdated=False):
    """builds a list of system ids being part of campaigns for hubs and tcus dicts cached 60s
    """
    curr_campaigns = list()
    for system in esiSovereigntyCampaigns(use_outdated):
        curr_campaigns.append(system["solar_system_id"])
    return curr_campaigns


def getCampaignsStructureIds(use_outdated=False):
    """builds a list of system ids being part of campaigns for hubs and tcus dicts cached 60s
    """
    curr_campaigns = list()
    for system in esiSovereigntyCampaigns(use_outdated):
        curr_campaigns.append(system["structure_id"])
    return curr_campaigns


def getAllStructures(typeid=None):
    req = "https://esi.evetech.net/latest/universe/structures/?datasource=tranquility"
    response = requests.get(req)
    if response.status_code != 200:
        logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
        response.raise_for_status()
    structs_found = response.json()
    if typeid is None:
        return structs_found
    types = list()
    for structure in structs_found:
        if "structure_type_id" in structure.keys():
            if structure["structure_type_id"]==typeid:
                types.append(structure)
    return types


def esiUniverseStructure(esi_char_name: str, structure_id: int, use_outdated=False):
    """"Calls https://esi.evetech.net/ui/#/Universe/get_universe_structures
    """
    res_value = None
    if esi_char_name is None:
        logging.error("esiUniverseStructure needs the eve-online api account.")
        return res_value
    cache_key = "_".join(("structure", "id", str(structure_id)))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id:
        res_value = json.loads(cached_id)
        res_value["structure_id"] = structure_id
    else:
        token = checkTokenTimeLine(getTokenOfChar(esi_char_name))
        if token:
            req = "https://esi.evetech.net/latest/universe/structures/{}/?datasource=tranquility&token={}".format(
                structure_id, token.access_token)
            response = requests.get(req)
            if response.status_code == 200:
                cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
                res_value = response.json()
                res_value["structure_id"] = structure_id
            else:
                logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
    return res_value


def esiCorporationsStructures(esi_char_name: str, corporations_id: int, use_outdated=False):
    """"Calls https://esi.evetech.net/ui/#/Universe/get_universe_structures
    """
    res_value = None
    if esi_char_name is None:
        logging.error("esiUniverseStructure needs the eve-online api account.")
        return res_value
    cache_key = "_".join(("corporations", "structures", "id", str(corporations_id)))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id:
        res_value = json.loads(cached_id)
    else:
        token = checkTokenTimeLine(getTokenOfChar(esi_char_name))
        if token:
            req = "https://esi.evetech.net/latest/corporations/{}/structures/?datasource=tranquility&token={}"\
                .format(corporations_id, token.access_token)
            response = requests.get(req)
            if response.status_code == 200:
                cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
                res_value = response.json()
            else:
                logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
    return res_value


def esiLatestSovereigntyMap(use_outdated=False, fore_refresh=False):
    """builds a list of reinforced campaigns for hubs and tcus dicts cached 60s
       https://esi.evetech.net/ui/?version=latest#/Sovereignty/get_sovereignty_map
    """
    cache = Cache()
    cache_key = "sovereignty"
    response = cache.getFromCache(cache_key, use_outdated)
    if response and not fore_refresh:
        campaigns_list = json.loads(response)
    else:
        req = "https://esi.evetech.net/latest/sovereignty/map/?datasource=tranquility"
        response = requests.get(req)
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()
        cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
        campaigns_list = response.json()
    return campaigns_list


def getPlayerSovereignty(use_outdated=False, fore_refresh=True, show_npc=True, callback=None):
    seq = ""

    def update_callback(seq_in):
        if callback:
            seq_in = seq_in + "."
            callback("updating alliance and system database {}".format(seq_in))
            if len(seq_in) > 40:
                seq_in = ""
        return seq_in

    cache_key = "player_sovereignty"
    cache = Cache()
    cached_result = cache.getFromCache(cache_key, use_outdated)
    if cached_result and not fore_refresh:
        return json.loads(cached_result)
    else:
        player_sov = dict()
        npc_sov = dict()
        list_of_all_factions = set()
        for sov in esiLatestSovereigntyMap(use_outdated, fore_refresh):
            if len(sov) > 2:
                player_sov[str(sov["system_id"])] = sov
            elif show_npc and len(sov) > 1:
                list_of_all_factions.add(sov["faction_id"])
                npc_sov[str(sov["system_id"])] = sov
        for sov in player_sov.values():
            if "alliance_id" in sov.keys():
                alli_id = sov["alliance_id"]
                sov["ticker"] = esiAlliances(alli_id)["ticker"]
            seq = update_callback(seq)

        if show_npc:
            npc_list = esiUniverseNames(list_of_all_factions)
            for sov in npc_sov.values():
                if "faction_id" in sov.keys():
                    sov["ticker"] = Universe.npcFactionNames(sov["faction_id"], npc_list)
                seq = update_callback(seq)
            player_sov.update(npc_sov)
        cache.putIntoCache(cache_key, json.dumps(player_sov), 3600)
        return player_sov


class JumpBridge(object):
    def __init__(self, name: str, structure_id: int, system_id: int, owner_id: int):
        tok = name.split(" ")
        self.src_system_name = tok[0]
        self.dst_system_name = tok[2]
        self.name = name
        self.structureId = structure_id
        self.systemId = system_id
        self.ownerId = owner_id
        self.paired = False
        self.links = 0


def sanityCheckGates(gates):
    """ grant that all item of gates builds valid pairs of jump bridges src<->dst and also dst<->src
        all other items will be removed
    """
    for gate in gates:
        for elem in gates:
            if (gate.src_system_name == elem.dst_system_name) and (gate.dst_system_name == elem.src_system_name):
                gate.paired = True
                elem.paired = True

    for gate in gates:
        if not gate.paired:
            gates.remove(gate)
    return gates


def countCheckGates( gates ):
    for gate in gates:
        for elem in gates:
            if (gate.src_system_name == elem.src_system_name) or (gate.src_system_name == elem.dst_system_name):
                gate.links = gate.links+1

class category:
    agent = "agent"
    alliance = "alliance"
    character = "character"
    constellation = "constellation"
    corporation = "corporation"
    faction = "faction"
    inventory_type = "inventory_type"
    region = "region"
    solar_system = "solar_system"
    station = "station"
    structure = "structure"


def esiSearch(esi_char_name: str, search_text, search_category: str, search_strict=False):
    """ updates all jump bridge data via api searching for names which have a substring  %20%C2%BB%20 means " >> "
    """
    if esi_char_name is None:
        logging.error("esiSearch needs the eve-online api account.")
        return {}
    token = checkTokenTimeLine(getTokenOfChar(esi_char_name))
    if token is None:
        logging.error("esiSearch needs the eve-online api account.")
        return {}
    search_strict = "true" if search_strict else "false"
    req = "https://esi.evetech.net/v3/characters/{character_id}/search/?datasource=tranquility"\
          "&categories={cat}&strict={sstr}&search={sys}&token={tok}".format(
            character_id=token.CharacterID, tok=token.access_token,
            sys=search_text, cat=search_category, sstr=search_strict)
    res = requests.get(req)
    if res.status_code == 200:
        return res.json()
    else:
        return {}


def getAllJumpGates(nameChar: str,systemName="",systemNameDst="", callback=None, use_outdated=False):
    """ updates all jump bridge data via api searching for names which have a substring  %20%C2%BB%20 means " >> "
    """
    if nameChar is None:
        logging.error("getAllJumpGates needs the eve-online api account.")
        return None
    token = checkTokenTimeLine(getTokenOfChar(nameChar))
    if token is None:
        logging.error("getAllJumpGates needs the eve-online api account.")
        return None

    req = "https://esi.evetech.net/v3/characters/{id}/search/?"\
          "datasource=tranquility&categories=structure&search={src}%20%C2%BB%20{dst}&token={tok}".format(
                id=token.CharacterID,
                tok=token.access_token,
                src=systemName,
                dst=systemNameDst)
    response = requests.get(req)
    if response.status_code != 200:
        logging.error(response.reason)
        return None
    structs = response.json()
    gates = list()
    processed = list()
    if token and len(structs):
        process = 0
        if callback and not callback(len(structs["structure"]), process):
            return gates
        for id_structure in structs["structure"]:
            if id_structure in processed:
                continue
            json_src = esiUniverseStructure(esi_char_name=nameChar, structure_id=id_structure, use_outdated=use_outdated)
            jump_bridge_text = parse.parse("{src} » {dst} - {info}", json_src["name"])
            structure = esiSearch(
                esi_char_name=nameChar,
                search_text="{} » {}".format(jump_bridge_text["src"], jump_bridge_text["dst"]),
                search_category=category.structure)

            if "structure" not in structure.keys():
                Cache().clearJumpGate(jump_bridge_text["src"])
                Cache().clearJumpGate(jump_bridge_text["dst"])
                continue
            cnt_structures = len(structure["structure"])
            if cnt_structures < 2:
                Cache().clearJumpGate(jump_bridge_text["src"])
                Cache().clearJumpGate(jump_bridge_text["dst"])
                continue

            for id in structure["structure"]:
                processed.append(id)

            json_src = esiUniverseStructure(
                esi_char_name=nameChar,
                structure_id=structure["structure"][0])
            json_dst = esiUniverseStructure(
                esi_char_name=nameChar,
                structure_id=structure["structure"][cnt_structures-1])

            Cache().putJumpGate(
                src=jump_bridge_text.named["src"],
                dst=jump_bridge_text.named["dst"],
                src_id=structure["structure"][0],
                dst_id=structure["structure"][cnt_structures-1],
                json_src=json_src,
                json_dst=json_dst,
                used=cnt_structures
            )

            gates.append(
                JumpBridge(name=json_src["name"], system_id=json_src["solar_system_id"],
                           structure_id=structure["structure"][0],
                           owner_id=json_src["owner_id"]))
            gates.append(
                JumpBridge(name=json_dst["name"], system_id=json_dst["solar_system_id"],
                           structure_id=structure["structure"][cnt_structures - 1],
                           owner_id=json_dst["owner_id"]))

            process = process + 1
            if callback and not callback(len(structs["structure"]), process):
                break

    #gates=sanityCheckGates(gates)
    elif token and (systemName != "" and systemNameDst != ""):
        Cache().clearJumpGate(systemName)
        Cache().clearJumpGate(systemNameDst)

    countCheckGates(gates)
    return gates


def writeGatesToFile(gates, filename="jb.txt"):
    gates_list = list()
    with open(filename, "w")as gf:
        for gate in gates:
            s_t_d = "{} » {}".format(gate.src_system_name, gate.dst_system_name)
            d_t_s = "{} » {}".format(gate.dst_system_name, gate.src_system_name)
            if s_t_d not in gates_list and d_t_s not in gates_list:
                gf.write("{} {} {} {} ({} {})\n".format(s_t_d, gate.systemId, gate.structureId, gate.ownerId, gate.links,gate.paired))
                gates_list.append(s_t_d)
        gf.close()


def esiUniverseStargates(stargate_id, use_outdated=False):
    """gets the solar system info from system id
    """
    cache_key = "_".join(("universe", "systems", str(stargate_id)))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id:
        return json.loads(cached_id)
    else:
        req = "https://esi.evetech.net/latest/universe/stargates/{}/?datasource=tranquility&language=en".format(stargate_id)
        response = requests.get(req)
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()
        cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
        return response.json()


def esiUniverseStations(station_id, use_outdated=False):
    """gets the solar system info from system id
    """
    cache_key = "_".join(("universe", "stations", str(station_id)))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id:
        return json.loads(cached_id)
    else:
        req = "https://esi.evetech.net/latest/universe/stations/{}/?datasource=tranquility&language=en".format(station_id)
        response = requests.get(req)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
            return response.json()
        else:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            return None


def esiUniverseSystems(system_id, use_outdated=False):
    """gets the solar system info from system id
    """
    cache_key = "_".join(("universe", "systems", str(system_id)))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id:
        return json.loads(cached_id)
    else:
        req = "https://esi.evetech.net/latest/universe/systems/{}/?datasource=tranquility&language=en".format(system_id)
        response = requests.get(req)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, response.text,secondUntilExpire(response))
            return response.json()
        else:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            return None


def esiUniverseAllSystems( use_outdated=False):
    """gets the solar system info from system id
    """
    cache_key = "_".join(("universe", "all", "systems"))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id:
        return json.loads(cached_id)
    else:
        req = "https://esi.evetech.net/latest/universe/systems/?datasource=tranquility&language=en"
        response = requests.get(req)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
            return response.json()
        else:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            return None


def esiAlliances(alliance_id, use_outdated=True):
    """gets the alliance from allicance id
    """
    cache_key = "_".join(("alliance", str(alliance_id)))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id:
        return json.loads(cached_id)
    else:
        req = "https://esi.evetech.net/latest/alliances/{}/?datasource=tranquility".format(alliance_id)
        response = requests.get(req)
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()
        cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
        return response.json()


def esiUniverseRegions(region_id: int, use_outdated=False):
    cache_key = "_".join(("universe", "regions", str(region_id)))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id:
        return json.loads(cached_id)
    else:
        req = "https://esi.evetech.net/latest/universe/regions/{}/?datasource=tranquility&language=en".format(region_id)
        response = requests.get(req)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
            return response.json()
        else:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            return None


def esiUniverseGetAllRegions(use_outdated=False) -> Optional[list]:
    """ Uses the EVE API to get the list of all region ids

    Returns:
             list : list of the ids of all regions
    """
    cache = Cache()
    all_systems = cache.getFromCache("universe_all_regions", use_outdated)
    if all_systems is not None:
        return json.loads(all_systems)
    else:
        url = "https://esi.evetech.net/latest/universe/regions/?datasource=tranquility"
        response = requests.get(url)
        if response.status_code == 200:
            cache.putIntoCache("universe_all_regions", response.text, secondUntilExpire(response))
            return response.json()
        else:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            return None


def esiUniverseConstellations(constellation_id: int, use_outdated=False):
    cache_key = "_".join(("universe", "constellations", str(constellation_id)))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id:
        return json.loads(cached_id)
    else:
        req = "https://esi.evetech.net/latest/universe/constellations/{}/?datasource=tranquility&language=en".format(constellation_id)
        response = requests.get(req)
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()
        cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
        return response.json()


def esiUniverseAllConstellations(use_outdated=False):
    cache_key = "universe_all_constellations"
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id:
        return json.loads(cached_id)
    else:
        req = "https://esi.evetech.net/latest/universe/constellations/?datasource=tranquility&language=en"
        response = requests.get(req)
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()
        cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
        return response.json()


def esiUniverseAllCategories(use_outdated=False):
    """
    Get information of an item category


    Args:
        use_outdated:

    Returns:

    """
    cache_key = "universe_all_categories"
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id is not None:
        return json.loads(cached_id)
    else:
        req = "https://esi.evetech.net/latest/universe/categories/?datasource=tranquility&language=en"
        response = requests.get(req)
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()
        cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
        return response.json()


def esiUniverseCategories(categorie_id: int, use_outdated=False):
    """
    Get information of an item category


    Args:
        categorie_id:

        use_outdated:

    Returns:

    """
    cache_key = "universe_categories_{}".format(categorie_id)
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id is not None:
        return json.loads(cached_id)
    else:
        req = "https://esi.evetech.net/latest/universe/categories/{}/?datasource=tranquility&language=en".format(categorie_id)
        response = requests.get(req)
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()
        cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
        return response.json()

def esiUniverseAllGroups(categorie_id: int, use_outdated=False):
    """
    Get information of an item category


    Args:
        use_outdated:

    Returns:

    """
    cache_key = "universe_groups"
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id is not None:
        return json.loads(cached_id)
    else:
        req = "https://esi.evetech.net/latest/universe/groups/?datasource=tranquility&language=en"
        response = requests.get(req)
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()
        cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
        return response.json()


def esiUniverseGroups(group_id: int, use_outdated=False):
    """
    Get information of an item category


    Args:
        use_outdated:

    Returns:

    """
    cache_key = "universe_group_{}".format(group_id)
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id is not None:
        return json.loads(cached_id)
    else:
        req = "https://esi.evetech.net/latest/universe/groups/{}/?datasource=tranquility&language=en".format(group_id)
        response = requests.get(req)
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()
        cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
        return response.json()


def esiUniverseAllTypes(types_id: int, use_outdated=False):
    """
    Get information of an item category


    Args:
        use_outdated:

    Returns:

    """
    cache_key = "universe_types"
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id is not None:
        return json.loads(cached_id)
    else:
        req = "https://esi.evetech.net/latest/universe/types/?datasource=tranquility&language=en"
        response = requests.get(req)
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()
        cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
        return response.json()


def esiUniverseTypes(types_id: int, use_outdated=False):
    """
    Get information of an item category


    Args:
        use_outdated:

    Returns:

    """
    cache_key = "universe_types_{}".format(types_id)
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id is not None:
        return json.loads(cached_id)
    else:
        req = "https://esi.evetech.net/latest/universe/types/{}/?datasource=tranquility&language=en".format(types_id)
        response = requests.get(req)
        if response.status_code != 200:
            logging.error("ESI-Error %i : '%s' url: %s", response.status_code, response.reason, response.url)
            response.raise_for_status()
        cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
        return response.json()



def hasAnsiblex( sys ) -> bool:
    return False


def applyRouteToEveOnline(name_char, jump_list):
    if name_char is None:
        logging.error("applyRouteToEveOnline needs the eve-online api account.")
        return None
    for id_system in jump_list:
        if hasAnsiblex(id_system):
            pass
        else:
            esiAutopilotWaypoint(name_char, id_system, beginning=False, clear_all=False)


SHIPIDS = [24692, 22448, 2836, 23919, 32872, 642, 11936,17726,37604,29266,11969,628,23757,11202,28850,643,11938,32305,
           17922,22466,33468,608,625,29337,11567,648,582,33820,11985,630,1944,17920,37480,632,34328,598,12013,16229,
           33151,599,12731,11192,42246,45647,17619,672,32788,621,17634,16240,633,11993,33675,20185,11182,42243,23915,
           33397,48648,11196,22468,16236,583,34317,32876,16238,34496,17476,12729,11176,2161,37453,17926,11184,20125,16231,17720,42242,47269,22474,17928,37457,12023,12017,645,32307,32874,24698,33153,17932,52254,49711,12011,3532,617,37135,44995,12044,22442,655,671,22460,32790,589,634,29344,11957,17841,20189,16227,35781,22464,32207,11129,33816,17715,3756,11940,28710,21097,584,37455,11987,11011,21628,24696,33155,11381,11379,35683,22852,11172,33079,22452,605,651,12034,11961,22544,24702,33157,48636,11387,24690,601,52252,607,615,35779,596,12753,17703,594,590,30842,12042,12005,657,34828,11400,11174,602,49710,37458,11194,45649,28661,654,11971,29986,33513,47271,3764,37606,45645,29990,17738,22548,24694,29248,37483,11186,3516,624,652,12032,44996,12747,609,37456,641,13202,17728,603,656,32811,4363,4388,32209,11132,37605,623,42241,45534,33395,19724,12015,24700,4306,19722,592,11377,650,52250,33472,24483,22470,17736,37607,2998,28846,23913,20187,12745,2006,17709,11989,11995,635,4302,28606,33818,620,29340,44993,28659,22440,17718,12021,19726,11965,33677,37481,42244,47466,2863,586,17480,16233,12733,33697,29988,20183,12735,597,12038,42245,23773,11963,11178,17918,638,17636,26840,588,22428,17812,11393,17478,19720,3514,28844,587,49712,24688,11959,28352,629,22456,12019,37460,11978,640,4005,32309,631,29336,11190,19744,11942,22430,22546,54731,585,22444,622,17713,11198,37482,54732,33470,17924,42685,34562,33081,4308,32878,11200,649,639,17732,26842,29984,52267,37459,23911,627,16242,54733,48635,591,4310,593,644,32311,2834,11999,3518,42132,42126,28665,47270,42124,606,42125,42133,11365,32880,626,17843,12743,45531,34590,3766,37454,17722,17740,33083,45530,22446,33673,22436,11371,17930,653,23917,49713,12003,2078,52907]

SHIPNAMES = (u'ABADDON',u'ABSOLUTION',u'ADRESTIA',u'AEON',u'ALGOS',u'APOCALYPSE',
            u'APOCALYPSE IMPERIAL ISSUE',u'APOCALYPSE NAVY ISSUE',u'APOSTLE',u'APOTHEOSIS',u'ARAZU',u'ARBITRATOR',
            u'ARCHON',u'ARES',u'ARK',u'ARMAGEDDON',u'ARMAGEDDON IMPERIAL ISSUE',
            u'ARMAGEDDON NAVY ISSUE',u'ASHIMMU',u'ASTARTE',u'ASTERO',u'ATRON',u'AUGOROR',u'AUGOROR NAVY ISSUE',
            u'AVATAR',u'BADGER',u'BANTAM',u'BARGHEST',u'BASILISK',u'BELLICOSE',u'BESTOWER',u'BHAALGORN',
            u'BIFROST',u'BLACKBIRD',u'BOWHEAD',u'BREACHER',u'BROADSWORD',u'BRUTIX',
            u'BRUTIX NAVY ISSUE',u'BURST',u'BUSTARD',u'BUZZARD',u'CAEDES',u'CAIMAN',u'CALDARI NAVY HOOKBILL',
            u'CALDARI SHUTTLE',u'CAMBION',u'CARACAL',u'CARACAL NAVY ISSUE',u'CATALYST',u'CELESTIS',u'CERBERUS',
            u'CHAMELEON',u'CHARON',u'CHEETAH',u'CHEMOSH',u'CHIMERA',u'CHREMOAS',u'CITIZEN VENTURE',u'CLAW',
            u'CLAYMORE',u'COERCER',u'CONDOR',u'CONFESSOR',u'CORAX',u'CORMORANT',
            u'COUNCIL DIPLOMATIC SHUTTLE',u'COVETOR',u'CRANE',u'CROW',u'CRUCIFIER',u'CRUCIFIER NAVY ISSUE',u'CRUOR',
            u'CRUSADER',u'CURSE',u'CYCLONE',u'CYNABAL',u'DAGON',u'DAMAVIK',u'DAMNATION',u'DAREDEVIL',
            u'DEACON',u'DEIMOS',u'DEVOTER',u'DOMINIX',u'DOMINIX NAVY ISSUE',u'DRAGOON',u'DRAKE',
            u'DRAKE NAVY ISSUE',u'DRAMIEL',u'DRAUGUR',u'DREKAVAC',u'EAGLE',u'ECHELON',u'ECHO',u'ENDURANCE',
            u'ENFORCER',u'ENYO',u'EOS',u'EPITHAL',u'EREBUS',u'ERIS',u'ETANA',u'EXECUTIONER',u'EXEQUROR',
            u'EXEQUROR NAVY ISSUE',u'FALCON',u'FEDERATION NAVY COMET',u'FENRIR',u'FEROX',u'FIEND',u'FLYCATCHER',
            u'FREKI',u'GALLENTE SHUTTLE',u'GARMUR',u'GILA',u'GNOSIS',u'GOLD MAGNATE',u'GOLEM',
            u'GORU\'S SHUTTLE',u'GRIFFIN',u'GRIFFIN NAVY ISSUE',u'GUARDIAN',u'GUARDIAN-VEXOR',
            u'GURISTAS SHUTTLE',u'HARBINGER',u'HARBINGER NAVY ISSUE',u'HARPY',u'HAWK',u'HECATE',u'HEL',u'HELIOS',
            u'HEMATOS',u'HERETIC',u'HERON',u'HOARDER',u'HOUND',u'HUGINN',u'HULK',u'HURRICANE',
            u'HURRICANE FLEET ISSUE',u'HYDRA',u'HYENA',u'HYPERION',u'IBIS',u'IKITURSA',u'IMICUS',u'IMMOLATOR',u'IMP',
            u'IMPAIROR',u'IMPEL',u'IMPERIAL NAVY SLICER',u'INCURSUS',u'INQUISITOR',
            u'INTERBUS SHUTTLE',u'ISHKUR',u'ISHTAR',u'ITERON MARK V',u'JACKDAW',u'JAGUAR',u'KERES',u'KESTREL',
            u'KIKIMORA',u'KIRIN',u'KITSUNE',u'KOMODO',u'KRONOS',u'KRYOS',u'LACHESIS',u'LEGION',u'LEOPARD',
            u'LESHAK',u'LEVIATHAN',u'LIF',u'LOGGERHEAD',u'LOKI',u'MACHARIEL',u'MACKINAW',u'MAELSTROM',
            u'MAGNATE',u'MAGUS',u'MALEDICTION',u'MALICE',u'MALLER',u'MAMMOTH',u'MANTICORE',u'MARSHAL',
            u'MASTODON',u'MAULUS',u'MAULUS NAVY ISSUE',u'MEGATHRON',u'MEGATHRON FEDERATE ISSUE',
            u'MEGATHRON NAVY ISSUE',u'MERLIN',u'MIASMOS',u'MIASMOS AMASTRIS EDITION',
            u'MIASMOS QUAFE ULTRA EDITION',u'MIASMOS QUAFE ULTRAMARINE EDITION',u'MIMIR',u'MINMATAR SHUTTLE',
            u'MINOKAWA',u'MOA',u'MOLOK',u'MONITOR',u'MORACHA',u'MOROS',u'MUNINN',u'MYRMIDON',u'NAGA',
            u'NAGLFAR',u'NAVITAS',u'NEMESIS',u'NEREUS',u'NERGAL',u'NESTOR',u'NIDHOGGUR',u'NIGHTHAWK',
            u'NIGHTMARE',u'NINAZU',u'NOCTIS',u'NOMAD',u'NYX',u'OBELISK',u'OCCATOR',u'OMEN',
            u'OMEN NAVY ISSUE',u'ONEIROS',u'ONYX',u'OPUX LUXURY YACHT',u'ORACLE',u'ORCA',u'ORTHRUS',u'OSPREY',
            u'OSPREY NAVY ISSUE',u'PACIFIER',u'PALADIN',u'PANTHER',u'PHANTASM',u'PHOBOS',u'PHOENIX',u'PILGRIM',
            u'POLICE PURSUIT COMET',u'PONTIFEX',u'PORPOISE',u'PRAXIS',u'PRIMAE',u'PROBE',u'PROCURER',u'PROPHECY',
            u'PRORATOR',u'PROSPECT',u'PROTEUS',u'PROVIDENCE',u'PROWLER',u'PUNISHER',u'PURIFIER',u'RABISU',
            u'RAGNAROK',u'RAPIER',u'RAPTOR',u'RATTLESNAKE',u'RAVEN',u'RAVEN NAVY ISSUE',
            u'RAVEN STATE ISSUE',u'REAPER',u'REDEEMER',u'REPUBLIC FLEET FIRETAIL',u'RETRIBUTION',u'RETRIEVER',
            u'REVELATION',u'REVENANT',u'RHEA',u'RIFTER',u'RODIVA',u'ROKH',u'ROOK',u'RORQUAL',u'RUPTURE',
            u'SABRE',u'SACRILEGE',u'SCALPEL',u'SCIMITAR',u'SCORPION',u'SCORPION ISHUKONE WATCH',
            u'SCORPION NAVY ISSUE',u'SCYTHE',u'SCYTHE FLEET ISSUE',u'SENTINEL',u'SIGIL',u'SILVER MAGNATE',u'SIN',
            u'SKIFF',u'SKYBREAKER',u'SLASHER',u'SLEIPNIR',u'STABBER',u'STABBER FLEET ISSUE',
            u'STILETTO',u'STORK',u'STORMBRINGER',u'STRATIOS',u'SUCCUBUS',u'SUNESIS',u'SVIPUL',u'TAIPAN',
            u'TALOS',u'TALWAR',u'TARANIS',u'TAYRA',u'TEMPEST',u'TEMPEST FLEET ISSUE',
            u'TEMPEST TRIBAL ISSUE',u'TENGU',u'TEST SITE MALLER',u'THALIA',u'THANATOS',u'THORAX',u'THRASHER',
            u'THUNDERCHILD',u'TIAMAT',u'TORMENTOR',u'TORNADO',u'TRISTAN',u'TYPHOON',u'TYPHOON FLEET ISSUE',
            u'UTU',u'VAGABOND',u'VANGEL',u'VANGUARD',u'VANQUISHER',u'VARGUR',u'VEDMAK',u'VEHEMENT',
            u'VELATOR',u'VENDETTA',u'VENERABLE',u'VENGEANCE',u'VENTURE',u'VEXOR',u'VEXOR NAVY ISSUE',
            u'VIATOR',u'VICTOR',u'VICTORIEUX LUXURY YACHT',u'VIGIL',u'VIGIL FLEET ISSUE',
            u'VIGILANT',u'VINDICATOR',u'VIOLATOR',u'VIRTUOSO',u'VULTURE',u'WHIPTAIL',u'WIDOW',u'WOLF',
            u'WORM',u'WREATHE',u'WYVERN',u'ZARMAZD',u'ZEALOT',u'ZEPHYR',u'ZIRNITRA')

SHIPNAMES = sorted(SHIPNAMES, key=lambda x: len(x), reverse=True)

PC_CORPS_IDS = [ 1000032, 1000164, 1000033, 1000165, 1000297, 1000034, 1000166, 1000298, 1000035, 1000167, 1000299, 1000036, 1000168, 1000300, 1000037, 1000169, 1000301, 1000038,  1000170, 1000039, 1000171, 1000040, 1000172, 1000041, 1000173, 1000042, 1000174, 1000043, 1000175, 1000044, 1000176, 1000045, 1000177, 1000046, 1000178, 1000047, 1000179, 1000048, 1000180, 1000049, 1000181, 1000050, 1000182, 1000051, 1000052, 1000053,  1000054, 1000055, 1000056, 1000057, 1000058, 1000059, 1000060, 1000061,  1000193, 1000062, 1000063, 1000064, 1000065, 1000197, 1000066, 1000198, 1000067, 1000068,  1000069, 1000070, 1000071, 1000072, 1000073, 1000205, 1000074, 1000206,  1000075, 1000207, 1000076, 1000208, 1000077, 1000078, 1000079, 1000080, 1000081, 1000213, 1000082, 1000214, 1000083, 1000215, 1000084, 1000216, 1000085, 1000217,  1000086, 1000218, 1000087, 1000219, 1000088, 1000220, 1000089, 1000090, 1000222, 1000091, 1000223, 1000092, 1000224, 1000093, 1000225, 1000094, 1000226, 1000095,  1000227, 1000096, 1000228, 1000097, 1000229, 1000098, 1000230, 1000099, 1000231, 1000100, 1000232, 1000101, 1000233, 1000102, 1000234, 1000103, 1000235, 1000104,  1000236, 1000105, 1000237, 1000106, 1000238, 1000107, 1000239, 1000108, 1000240, 1000109, 1000110, 1000111, 1000243, 1000112, 1000244, 1000113, 1000245, 1000114,  1000246, 1000115, 1000247, 1000116, 1000248, 1000117, 1000249, 1000118, 1000250, 1000119, 1000251, 1000120, 1000252, 1000121, 1000253, 1000122, 1000254, 1000123,  1000255, 1000124, 1000256, 1000125, 1000257, 1000126, 1000258, 1000127, 1000259, 1000128, 1000129, 1000261, 1000130, 1000262, 1000131, 1000263, 1000132, 1000001,  1000133, 1000002, 1000134, 1000003, 1000135, 1000004, 1000136, 1000005, 1000137, 1000006, 1000138, 1000270, 1000007, 1000139, 1000271, 1000008, 1000140, 1000009,  1000141, 1000010, 1000142, 1000274, 1000011, 1000143, 1000012, 1000144, 1000276, 1000013, 1000145, 1000277, 1000409, 1000014, 1000146, 1000015, 1000147, 1000279,  1000016, 1000148, 1000280, 1000017, 1000149, 1000281, 1000018, 1000150, 1000282, 1000019, 1000151, 1000283, 1000020, 1000152, 1000284, 1000021, 1000153, 1000285,  1000022, 1000154, 1000286, 1000023, 1000155, 1000287, 1000024, 1000156, 1000288, 1000025, 1000157, 1000289, 1000026, 1000158, 1000290, 1000027, 1000159, 1000291,  1000028, 1000160, 1000292, 1000029, 1000161, 1000293, 1000030, 1000162, 1000294, 1000031, 1000163]

NPC_CORPS = (u'Republic Justice Department', u'House of Records', u'24th Imperial Crusade', u'Template:NPC corporation',
             u'Khanid Works', u'Caldari Steel', u'School of Applied Knowledge', u'NOH Recruitment Center',
             u'Sarum Family', u'Impro', u'Guristas', u'Carthum Conglomerate', u'Secure Commerce Commission',
             u'Amarr Trade Registry', u'Anonymous', u'Federal Defence Union', u'Federal Freight', u'Ardishapur Family',
             u'Thukker Mix', u'Sebiestor tribe', u'Core Complexion Inc.', u'Federal Navy Academy', u'Dominations',
             u'Ishukone Watch', u'Kaalakiota Corporation', u'Nurtura', u'Center for Advanced Studies', u'CONCORD',
             u'Ammatar Consulate', u'HZO Refinery', u'Joint Harvesting', u'Caldari Funds Unlimited', u'Propel Dynamics',
             u'Caldari Navy', u'Amarr Navy', u'Amarr Certified News', u'Serpentis Corporation', u'CreoDron',
             u'Society of Conscious Thought', u'Shapeset', u'Kor-Azor Family', u'Khanid Transport',
             u'Imperial Chancellor', u'Rapid Assembly', u'Khanid Innovation', u'Combined Harvest',
             u'Peace and Order Unit', u'The Leisure Group', u'CBD Sell Division', u'DED', u'Six Kin Development',
             u'Zero-G Research Firm', u'Defiants', u'Noble Appliances', u'Guristas Production', u'Intaki Space Police',
             u'Spacelane Patrol', u'User talk:ISD Crystal Carbonide', u'Caldari Provisions', u'Brutor tribe',
             u'True Power', u'Nefantar Miner Association', u'Garoun Investment Bank', u'FedMart', u'Prosper',
             u'Inherent Implants', u'Chief Executive Panel', u'Top Down', u'Federation Customs',
             u'Lai Dai Protection Service', u'Roden Shipyards', u'Wiyrkomi Peace Corps', u'Allotek Industries',
             u'Minedrill', u'Court Chamberlain', u'Intaki Syndicate', u'Caldari Constructions',
             u'State and Region Bank', u'Amarr Civil Service', u'Pend Insurance', u'Zainou', u'Material Institute',
             u'Republic Fleet', u'Intaki Bank', u'Hyasyoda Corporation', u'Nugoeihuvi Corporation', u'Modern Finances',
             u'Bank of Luminaire', u'Ministry of War', u'Genolution', u'Pator Tech School', u'Hedion University',
             u'Kador Family', u'Ducia Foundry', u'Prompt Delivery', u'Trust Partners', u'Material Acquisition',
             u'Jovian Directorate', u'DUST 514 NPC Corporations', u'Ministry of Assessment', u'Expert Distribution',
             u'Ishukone Corporation', u'Caldari Business Tribunal', u'The Scope', u'Eifyr and Co.',
             u'Jovian directorate', u'Lai Dai Corporation', u'Chemal Tech', u'CBD Corporation', u'Internal Security',
             u'Salvation Angels', u'TransStellar Shipping', u'InterBus', u'Outer Ring Excavations',
             u'Tribal Liberation Force', u'Impetus', u'Intaki Commerce', u'University of Caille', u'Home Guard',
             u'The Draconis Family', u'The Sanctuary', u'Republic University', u'Federal Intelligence Office',
             u'Egonics Inc.', u'Native Freshfood', u'Republic Security Services', u'Wiyrkomi Corporation',
             u'Sukuuvestaa Corporation', u'Vherokior tribe', u'Republic Parliament', u'Ytiri', u'Mercantile Club',
             u'Civic Court', u'Imperial Academy', u'Tash-Murkon Family', u'Viziam', u'Ammatar Fleet',
             u'Urban Management', u'Royal Amarr Institute', u'Echelon Entertainment', u'Archangels',
             u'Poteque Pharmaceuticals', u'Imperial Armaments', u'Academy of Aggressive Behaviour',
             u'Duvolle Laboratories', u'Ministry of Internal Order', u'Quafe Company', u'Serpentis Inquest',
             u'True Creations', u'Science and Trade Institute', u'Further Foodstuffs', u'Poksu Mineral Group',
             u'Astral Mining Inc.', u'Krusual tribe', u'Blood Raiders', u'Amarr Constructions', u'Federation Navy',
             u'Inner Circle', u'State War Academy', u'Zoar and Sons', u'Boundless Creation', u'Guardian Angels',
             u'Food Relief', u'Royal Khanid Navy', u'Imperial Shipment', u'Perkone', u'Federal Administration',
             u'Emperor Family', u'Inner Zone Shipping', u'Theology Council', u'Aliastra', u'Republic Military School',
             u'Freedom Extension', u'Sisters of EVE', u'President', u'Expert Housing', u'Deep Core Mining Inc.',
             u'Senate', u"Mordu's Legion", u'State Protectorate', u'Jove Navy', u'X-Sense', u'Corporate Police Force',
             u'Minmatar Mining Corporation', u'Supreme Court')


def checkSpyglassVersionUpdate(current_version=VERSION, force_check=False):
    """check github for a new latest release
    """
    checked = Cache().getFromCache("version_check")
    if force_check or checked is None:
        new_version = None
        req = "https://api.github.com/repos/jkey-67/spyglass/releases"
        response = requests.get(req)
        if response.status_code != 200:
            return [False, "Error %i : '%s' url: %s", response.status_code, response.reason, response.url]
        page_json_found = response.json()
        if len(page_json_found) > 0 and "tag_name" in page_json_found[0].keys():
            new_version = page_json_found[0]["tag_name"][1:]
        else:
            return [False, "Unable to read version from github."]
        Cache().putIntoCache("version_check", new_version, 60 * 60)
        if version.parse(new_version) > version.parse(current_version):
            return [True,
                "An newer Spyglass Version {} is available, you are currently running Version {}.".format(
                    new_version, current_version)]
        else:
            return [False,
                    "You are running the actual Spyglass Version {}.".format(current_version)]
    else:
        return [False,
                "Pending version check, current version is {}.".format(checked)]


def checkTheraConnections(system_name="1-7HVI"):
    req = "https://www.eve-scout.com/api/wormholes?systemSearch={}".format(system_name)
    response = requests.get(req)
    if response.status_code == 200:
        res = response.json()
        return res

    else:
        return None


def getSpyglassUpdateLink(ver=VERSION):
    req = "https://api.github.com/repos/jkey-67/spyglass/releases"
    response = requests.get(req)
    if response.status_code != 200:
        return [False, "Error %i : '%s' url: %s", response.status_code, response.reason, response.url]
    page_json_found = response.json()
    if len(page_json_found) > 0 and "assets" in page_json_found[0].keys():
        return page_json_found[0]["assets"][0]["browser_download_url"]
    else:
        return None


# The main application for testing
if __name__ == "__main__":
    Cache.PATH_TO_CACHE = "/home/jkeymer/Documents/EVE/spyglass/cache-2.sqlite3"
    res = checkTheraConnections()
    res = getPlayerSovereignty(use_outdated=False, fore_refresh=True, show_npc=True, callback=None)
    res = esiSovereigntyStructures()
    with Cache() as cache:
        for item in res:
            key = "{}_{}_{}".format("system", "tmp", str(item["solar_system_id"]))
            cache.putIntoCacheNoLock(key, str(item))
        cache.con.commit()

    res = esiSovereigntyMap()
    res = esiSovereigntyCampaigns()
    res = esiGetCharsOnlineStatus()

    res = esiGetCharsOnlineStatus()
    res = checkSpyglassVersionUpdate()



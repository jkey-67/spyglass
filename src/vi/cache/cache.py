###########################################################################
#  Vintel - Visual Intel Chat Analyzer									  #
#  Copyright (C) 2014-15 Sebastian Meyer (sparrow.242.de+eve@gmail.com )  #
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

import sqlite3
import threading
import time
import logging
import vi.version
import json

from typing import Optional
from .dbstructure import updateDatabase
from vi.evetime import currentEveTime, secondsTillDowntime


def to_blob(x):
    return x


def from_blob(x):
    return x


class Cache(object):
    # Cache checks PATH_TO_CACHE when init, so you can set this on a
    # central place for all Cache instances.
    PATH_TO_CACHE = None

    # Ok, this is dirty. To make sure we check the database only
    # one time/runtime we will change this class variable after the
    # check. Following inits of Cache will now, that we already checked.
    VERSION_CHECKED = False

    # Cache-Instances in various threads: must handle concurrent writings
    SQLITE_WRITE_LOCK = threading.Lock()

    def __enter__(self):
        self.SQLITE_WRITE_LOCK.acquire()
        return self

    def __exit__(self, typeof, value, traceback):
        if typeof is not None:
            self.con.rollback()
        self.SQLITE_WRITE_LOCK.release()

    def __init__(self, path_to_sql_file="cache.sqlite3"):
        """
        Args:
            path_to_sql_file(str): Path to sqlite-file to save the cache. will be ignored if you set Cache.PATH_TO_CACHE
            before init
        """
        if Cache.PATH_TO_CACHE:
            path_to_sql_file = Cache.PATH_TO_CACHE
        self.con = sqlite3.connect(path_to_sql_file)
        if not Cache.VERSION_CHECKED:
            with Cache.SQLITE_WRITE_LOCK:
                self.checkVersion()
        Cache.VERSION_CHECKED = True

    def checkVersion(self):
        query = "SELECT version FROM version;"
        version = 0
        try:
            version = self.con.execute(query).fetchall()[0][0]
        except Exception as e:
            if isinstance(e, sqlite3.OperationalError) and "no such table: version" in str(e):
                pass
            elif isinstance(e, IndexError):
                pass
            else:
                raise e
        updateDatabase(version, self.con)

    def removeFromCache(self, key):
        """ Remove an item from the table cache

        Args:
            key: the key to be removed
        """
        with Cache.SQLITE_WRITE_LOCK:
            query = "DELETE FROM cache WHERE key = ?"
            self.con.execute(query, (key,))
            self.con.commit()

    def putIntoCache(self, key, value, max_age=60*60*24*3):
        """
            Putting something in the cache maxAge is maximum age in seconds
        Args:
                key(str):
                value(str):
                max_age(int):
        """
        with Cache.SQLITE_WRITE_LOCK:
            query = "DELETE FROM cache WHERE key = ?"
            self.con.execute(query, (key,))
            query = "INSERT INTO cache (key, data, modified, maxage) VALUES (?, ?, ?, ?)"
            self.con.execute(query, (key, value, time.time(), max_age))
            self.con.commit()

    def putIntoCacheNoLock(self, key, value, max_age=60*60*24*3):
        """ Putting key value to th database with external lock

        Args:
            key: the key
            value: the value
            max_age: max age in seconds

        Returns:
            None
        Raises:
            Exception: if SQLITE_WRITE_LOCK is not locked

        Example:
           >>>
           try:
                with cache:
                    cache.putIntoCacheNoLock("Key1","value1")
                    cache.putIntoCacheNoLock("Key2","value2")
                    cache.putIntoCacheNoLock("Key3","value3")
           except:
                cache.con.rollback()

        """
        if not self.SQLITE_WRITE_LOCK.locked():
            raise Exception("SQLITE_WRITE_LOCK not locked")
        query = "DELETE FROM cache WHERE key = ?;"
        self.con.execute(query, (key,))
        query = "INSERT INTO cache (key, data, modified, maxage) VALUES (?, ?, ?, ?);"
        self.con.execute(query, (key, value, time.time(), max_age))

    def getFromCache(self, key, outdated=False) -> Optional[any]:
        """ Getting something from cache
        Args:
            key : the key for the value

        Args:
            outdated: if true, the function returns the value even if it is outdated

        Returns:
            str:The resulting string from the cache table , or None
        """
        query = "SELECT key, data, modified, maxage FROM cache WHERE key = ?"
        founds = self.con.execute(query, (key,)).fetchall()
        if len(founds) == 0:
            return None
        elif founds[0][2] + founds[0][3] < time.time() and not outdated:
            return None
        else:
            return founds[0][1]

    def clearDataBase(self):
        with Cache.SQLITE_WRITE_LOCK:
            self.con.execute("DELETE FROM cache WHERE datetime(modified+maxage,'unixepoch') < datetime();")
            self.con.execute("DELETE FROM cache WHERE key LIKE 'alliance%_';")
            self.con.execute("DELETE FROM cache WHERE key LIKE 'ids_dicts_%' OR key LIKE 'system_tmp%';")
            self.con.execute("DELETE FROM cache WHERE key LIKE 'public_info%';")
            self.con.execute("DELETE FROM cache WHERE key LIKE 'universe_systems_%';")
            self.con.execute("DELETE FROM cache WHERE key LIKE 'mapdata%';")
            self.con.execute("DELETE FROM avatars;")
            self.con.commit()

    def clearOutdatedCache(self):
        """ Delete all outdated jumpbridges from database
        """
        with Cache.SQLITE_WRITE_LOCK:
            query = "DELETE FROM cache WHERE datetime(modified+maxage,'unixepoch') < datetime()"
            self.con.execute(query)
            self.con.commit()

    def clearAllAvatar(self):
        """
            Removes all avatar images
        Returns:

        """
        query = "DELETE FROM avatars"
        self.con.execute(query, ()).fetchall()

    def putImageToAvatar(self, name, data, max_age=47*24*60*60):
        """ Put the picture of a player or other item into the avatars table

        Args:
            name(str):Key of interests
            data:
            max_age:
        Args:
              data:Picture data to be inserted as blob
        """
        with Cache.SQLITE_WRITE_LOCK:
            select_query = "SELECT charname FROM avatars WHERE charname = ?"
            founds = self.con.execute(select_query, (name,)).fetchall()
            if len(founds):
                # data is a blob, so we have to change it to buffer
                data = to_blob(data)
                query = "UPDATE avatars SET data = ?, modified = ?  WHERE charname = ?"
                self.con.execute(query, (data, time.time(), name))
            else:
                data = to_blob(data)
                query = "INSERT INTO avatars (charname, data, modified, maxage) VALUES (?, ?, ?,?)"
                self.con.execute(query, (name, data, time.time(), max_age))
            self.con.commit()

    def getImageFromAvatar(self, name) -> Optional[bytes]:
        """ Getting the avatars_pictures data from the Cache. Returns None if there is no entry in the cache

        Args:
            name(str):Key of interests

        Returns:
            bytes:blob of data or None
        """
        select_query = "SELECT data FROM avatars WHERE charname = ?"
        founds = self.con.execute(select_query, (name,)).fetchall()
        if len(founds) == 0:
            return None
        else:
            # dats is buffer, we convert it back to str
            data = from_blob(founds[0][0])
            return data

    def putImageToIconCache(self, icon_id: int, data, expire: int = 365*24*60*60) -> None:
        """ Put the icon of an item into the iconcache table

        Args:
            icon_id(int):Key of interests
            expire(int):expire in seconds from now
        Args:
              data:Picture data to be inserted as blob
        """
        with Cache.SQLITE_WRITE_LOCK:
            select_query = "SELECT id FROM iconcache WHERE id = ?"
            icon_founds = self.con.execute(select_query, (icon_id,)).fetchall()
            if len(icon_founds):
                # data is a blob, so we have to change it to buffer
                data = to_blob(data)
                query = "UPDATE iconcache SET icon = ?, modified = ?  WHERE id = ?"
                self.con.execute(query, (data, time.time(), icon_id))
            else:
                data = to_blob(data)
                query = "INSERT INTO iconcache (id, icon, modified, maxage) VALUES (?, ?, ?,?)"
                self.con.execute(query, (icon_id, data, time.time(), expire))
            self.con.commit()

    def getImageFromIconCache(self, icon_id: int) -> Optional[bytes]:
        """ Getting the image data from the Cache. Returns None if there is no entry in the cache

        Args:
            icon_id(int):Key of interests

        Returns:
            bytes:blob of data or None
        """
        select_query = "SELECT icon FROM iconcache WHERE id = ?"
        founds = self.con.execute(select_query, (icon_id,)).fetchall()
        if len(founds) == 0:
            return None
        else:
            # dats is buffer, we convert it back to str
            data = from_blob(founds[0][0])
            return data

    def putJsonToAvatar(self, player_name: str, json_txt: str, player_id=None, alliance_id=None, max_age=60*60*24*14):
        """ Put the picture of a player or other item into the avatars table

        Args:
            player_name(str):Key of interests
            json_txt: text of json description
            player_id: id of player
            alliance_id: alliance id of player

        """
        with Cache.SQLITE_WRITE_LOCK:
            select_query = "SELECT charname FROM avatars WHERE charname = ?"
            founds = self.con.execute(select_query, (player_name,)).fetchall()
            if len(founds):
                # data is a blob, so we have to change it to buffer
                query = "UPDATE avatars SET json = ?, modified = ? ,player_id = ?, alliance_id = ?  WHERE charname = ?"
                self.con.execute(query, (json_txt, time.time(), player_name, player_id, alliance_id))
            else:
                query = "INSERT INTO avatars (charname, json, modified, player_id, alliance_id, maxage) "\
                        "VALUES (?, ?, ?, ?, ?, ?)"
                self.con.execute(query, (player_name, json_txt, time.time(), player_id, alliance_id, max_age))
            self.con.commit()

    def getJsonFromAvatar(self, name) -> Optional[bytes]:
        """ Getting the avatars_pictures data from the Cache. Returns None if there is no entry in the cache

        Args:
            name(str):Key of interests

        Returns:
            bytes:blob of data or None
        """
        select_query = "SELECT json FROM avatars WHERE charname = ?"
        res = self.con.execute(select_query, (name,)).fetchall()
        if len(res):
            return res[0][0]
        else:
            return None

    def clearOutdatedAvatar(self, months: int = 12):
        """
        Clears all images older than 6 months

        Returns:
            None

        """

        with Cache.SQLITE_WRITE_LOCK:
            query = "DELETE FROM avatars WHERE datetime(modified+{},'unixepoch') < datetime()".\
                format(60*60*24*30*months)
            self.con.execute(query)
            self.con.commit()

    def removeAvatar(self, name):
        """ Removing an avatar from the cache

        Args:
            name(str):Key of interests
        """
        with Cache.SQLITE_WRITE_LOCK:
            query = "DELETE FROM avatars WHERE charname = ?"
            self.con.execute(query, (name,))
            self.con.commit()

    def _applyAttributeList(self, respond, attr):
        if len(attr) == 1:
            return getattr(respond, attr[0])
        else:
            for items in attr:
                if isinstance(items, str):
                    respond = getattr(respond, items)
            return respond

    def recallAndApplySettings(self, responder, settings_identifier):
        db_version = self.getFromCache("version")
        restore_gui = db_version == vi.version.VERSION
        settings = self.getFromCache(settings_identifier)
        if settings:
            settings = eval(settings)
            for setting in settings:
                obj = responder if not setting[0] else _applyAttributeList(responder, setting[0].split('.'))
                # logging.debug("{0} | {1} | {2}".format(str(obj), setting[1], setting[2]))
                try:
                    if restore_gui and setting[1] == "restoreGeometry":
                        if not obj.restoreGeometry(eval(setting[2])):
                            logging.error("Fail to call {0} | {1} | {2}".format(str(obj), setting[1], setting[2]))
                    elif restore_gui and setting[1] == "restoreState":
                        if not getattr(obj, setting[1])(eval(setting[2])):
                            logging.error("Fail to call {0} | {1} | {2}".format(str(obj), setting[1], setting[2]))
                    elif len(setting) > 3 and setting[3]:
                        if restore_gui:
                            getattr(obj, setting[1])(eval(setting[2]))
                    else:
                        getattr(obj, setting[1])(setting[2])

                except (Exception,) as e:
                    logging.error("Recall application setting failed to set attribute {0} | {1} | {2} | error {3}"
                                  .format(str(obj), setting[1], setting[2], e))

    def putJumpGate(self, src, dst, src_id=None, dst_id=None,
                    json_src=None, json_dst=None, used=None, max_age=60*60*24*14) -> bool:
        """
        Updates an Ansiblex jump bride struct inside the database
        Args:
            src: Source system
            dst: Destination system
            src_id: Source system id
            dst_id: Destination system id
            json_src: Source system esi response
            json_dst: Destination system esi response
            used: not used yet, system should recognize a jump automatically
            max_age: purge time

        Returns:
            bool; true if added false,  if a duplicate
        """
        with Cache.SQLITE_WRITE_LOCK:
            query = "UPDATE jumpbridge SET modified = ? WHERE (src IS ? AND dst IS ?) OR (dst IS ? and src IS ?)"
            if self.con.execute(query, (time.time(), src, dst, src, dst)).rowcount == 1:
                self.con.commit()
                return False
            query = "DELETE FROM jumpbridge WHERE src LIKE ? or dst LIKE ? or src LIKE ? or dst LIKE ?"
            self.con.execute(query, (src, src, dst, dst))
            query = "INSERT INTO jumpbridge (src, dst, used, id_src, id_dst, json_src, json_dst, modified, maxage) "\
                    "VALUES (?, ?, ?, ?, ?, ?, ? , ?, ?)"
            self.con.execute(query, (src, dst, used, src_id, dst_id,
                                     json.dumps(json_src), json.dumps(json_dst), time.time(), max_age))
            self.con.commit()
            return True

    def clearJumpGate(self, src: Optional[str]) -> None:
        """ Removes all items from the jumpbridge table where FROM or TO match str

        Args:
            src(str):Name of the system which can be FROM or TO

        """
        with Cache.SQLITE_WRITE_LOCK:
            if src is None:
                query = "DELETE FROM jumpbridge;"
                self.con.execute(query, ())
            else:
                query = "DELETE FROM jumpbridge WHERE src LIKE ? or dst LIKE ?"
                self.con.execute(query, (src, src))
            self.con.commit()

    def getOutdatedJumpGates(self):
        """ Delete all outdated jumpbridges from database
        """
        with Cache.SQLITE_WRITE_LOCK:
            query = "SELECT * FROM jumpbridge WHERE datetime(modified+maxage,'unixepoch') < datetime()"
            return self.con.execute(query).fetchall()

    def clearOutdatedJumpGates(self):
        """ Delete all outdated jumpbridges from database
        """
        with Cache.SQLITE_WRITE_LOCK:
            query = "DELETE FROM jumpbridge WHERE datetime(modified+maxage,'unixepoch') < datetime()"
            self.con.execute(query)
            self.con.commit()

    def hasJumpGate(self, src) -> bool:
        """Check the database  for an existing jumpbpridge

        Args:
            src(str):Name of the system which match FROM

        Returns:
            bool:True if a jumpgridge is anchored in the system

        """
        with Cache.SQLITE_WRITE_LOCK:
            # data is a blob, so we have to change it to buffer
            query = "SELECT SRC FROM jumpbridge WHERE src LIKE ? or dst LIKE ?"
            res = self.con.execute(query, (src, src)).fetchall()
        return len(res) > 0

    def getPlayerSovereignty(self) -> dict:
        sovereignty = self.getFromCache("player_sovereignty", True)
        if sovereignty:
            return json.loads(sovereignty)
        else:
            return dict()

    def getJumpGates(self):
        """Get a list of all jumpbridges

        Returns:
            list(tuple(str,str,str): List of tuple of strings
        """
        query = "SELECT src, ' ', dst FROM jumpbridge"
        founds = self.con.execute(query, ()).fetchall()
        if len(founds) == 0:
            return list()
        else:
            return founds

    def getJumpGatesAtIndex(self, inx: int):
        """
        """
        with Cache.SQLITE_WRITE_LOCK:
            query = "select src, dst, id_src, json_src  from jumpbridge  LIMIT 1 OFFSET ?"
            founds = self.con.execute(query, (inx,)).fetchall()
            if len(founds) == 0:
                return dict()
            else:
                return {
                    "src": founds[0][0],
                    "dst": founds[0][1],
                    "id_src": founds[0][2],
                    "json_src": json.loads(founds[0][3])if founds[0][3] != "null" else None
                }

    def putPOI(self, data) -> bool:
        """ data can be structure or station dict

        Returns:
            bool:True if item added
        """
        if data is None:
            return False
        with Cache.SQLITE_WRITE_LOCK:
            query = "SELECT name FROM pointofinterest WHERE id = ?"
            if "station_id" in data:
                founds = self.con.execute(query, (data["station_id"],)).fetchall()
            elif "structure_id" in data:
                founds = self.con.execute(query, (data["structure_id"],)).fetchall()
            else:
                return False

            if len(founds) != 0:
                return False

            # data is a blob, so we have to change it to buffer
            if "station_id" in data.keys():
                query = "DELETE FROM pointofinterest WHERE id IS ?"
                self.con.execute(query, (data["station_id"],))
                query = "INSERT INTO pointofinterest (id,type,name,json) VALUES (?, ?, ?, ?)"
                self.con.execute(query, (data["station_id"], data["type_id"], data["name"], json.dumps(data)))
            if "structure_id" in data.keys():
                query = "DELETE FROM pointofinterest WHERE id IS ?"
                self.con.execute(query, (data["structure_id"],))
                query = "INSERT INTO pointofinterest (id,type,name,json) VALUES (?, ?, ?, ?)"
                self.con.execute(query, (data["structure_id"], data["type_id"], data["name"], json.dumps(data)))
            self.con.commit()
            return True

    def setPOIItemInfoText(self, id_poi, info_poi):
        with Cache.SQLITE_WRITE_LOCK:
            query = "UPDATE pointofinterest SET name = ? WHERE id is ?"
            self.con.execute(query, (info_poi, id_poi))
            self.con.commit()

    def getPOIAtIndex(self, inx: int) -> Optional[dict]:
        """
        gets the POI at index position inx
        Args:
            inx: model index

        Returns:
            dict of the POI or None
        """
        with Cache.SQLITE_WRITE_LOCK:
            query = "select json, name ,sid from pointofinterest ORDER BY sid LIMIT 1 OFFSET ?"
            founds = self.con.execute(query, (inx,)).fetchall()
            if len(founds) == 0:
                return None
            else:
                ret_val = json.loads(founds[0][0])
                ret_val["gui_name"] = founds[0][1]
                ret_val["sid"] = founds[0][2]
                if "station_id" in ret_val.keys():
                    ret_val["destination_id"] = ret_val["station_id"]
                if "structure_id" in ret_val.keys():
                    ret_val["destination_id"] = ret_val["structure_id"]
                return ret_val

    def getPOIs(self) -> Optional[list]:
        """
        gets the POI at index position inx
        Args:

        Returns:
            dict of the POI or None
        """
        with Cache.SQLITE_WRITE_LOCK:
            query = "select json from pointofinterest"
            founds = self.con.execute(query).fetchall()
            if len(founds) == 0:
                return None
            else:
                return [json.loads(itm[0]) for itm in founds]

    def clearPOI(self, destination_id: int) -> None:
        with Cache.SQLITE_WRITE_LOCK:
            query = "DELETE FROM pointofinterest  WHERE id IS ?"
            self.con.execute(query, (destination_id,)).fetchall()
            self.con.commit()

    def swapPOIs(self, src, dst):
        if src == dst:
            return
        with Cache.SQLITE_WRITE_LOCK:
            queries = [
                "UPDATE pointofinterest SET sid = {a}  WHERE sid = {b};".format(a=dst-0.1, b=src),
                "DROP TABLE IF EXISTS temp.tmp;",
                "CREATE TEMPORARY TABLE tmp AS SELECT id, row_number() OVER (ORDER BY sid) AS rn FROM pointofinterest;",
                "UPDATE POINTOFINTEREST SET sid = (SELECT rn FROM temp.tmp WHERE temp.tmp.id = pointofinterest.id);",
                "Drop TABLE temp.tmp;"]

            for query in queries:
                self.con.execute(query)
                self.con.commit()

    def clearAPIKey(self, param) -> None:
        with Cache.SQLITE_WRITE_LOCK:
            if isinstance(param, str):
                query = "DELETE FROM players WHERE id IS ? or name IS ?"
                self.con.execute(query, (param, param))
            else:
                query = "DELETE FROM players WHERE id IN (?) OR name IN (?)"
                param_str = ', '.join([str(v) for v in param])
                self.con.execute(query, (param_str, param_str))
            # data is a blob, so we have to change it to buffer

            self.con.commit()

    def hasAPIKey(self, char) -> bool:
        with Cache.SQLITE_WRITE_LOCK:
            query = "SELECT key FROM players WHERE id IS ? or name IS ?"
            res = self.con.execute(query, (char, char)).fetchall()
            return len(res) > 0 and res[0] is None

    def getAPIKey(self, char) -> Optional[dict]:
        with Cache.SQLITE_WRITE_LOCK:
            query = "SELECT key FROM players WHERE id IS ? or name IS ?;"
            res = self.con.execute(query, (char, char)).fetchall()
            if len(res) > 0:
                return res[0][0]
            else:
                return None

    def putAPIKey(self, key, max_age=60 * 60 * 24 * 90):
        self.clearAPIKey(key["CharacterName"])
        with Cache.SQLITE_WRITE_LOCK:
            query = "INSERT INTO players (id, name, key, active, modified, maxage) VALUES (?, ?, ?, ?, ?, ?)"
            self.con.execute(query,
                             (key["CharacterID"], key["CharacterName"], json.dumps(key), 1, time.time(), max_age))
            self.con.commit()

    def removeAPIKey(self, char_name):
        self.clearAPIKey(char_name)

    def getAPICharNames(self) -> list:
        with Cache.SQLITE_WRITE_LOCK:
            query = "SELECT name FROM players WHERE key NOT NULL"
            res = self.con.execute(query).fetchall()
        lst = list()
        for i in res:
            lst.append(i[0])
        return lst

    def getKnownPlayerNames(self) -> set:
        with Cache.SQLITE_WRITE_LOCK:
            query = "SELECT name FROM players"
            res = {elem[0] for elem in self.con.execute(query).fetchall()}
        return res

    def setKnownPlayerNames(self, values: set):
        current_players = self.getKnownPlayerNames()
        with self as cache:
            for player_name in values:
                if player_name not in current_players:
                    query = "INSERT INTO players (name, modified, active,maxage) VALUES (?, ?, 1, ?)"
                    cache.con.execute(query, (player_name, time.time(), secondsTillDowntime()))
            cache.con.commit()

    def getActivePlayerNames(self) -> set:
        with Cache.SQLITE_WRITE_LOCK:
            query = "SELECT name FROM players WHERE active=1"
            res = {elem[0] for elem in self.con.execute(query).fetchall()}
        return res

    def setActivePlayerNames(self, values: set):
        current_players = self.getKnownPlayerNames()
        with self as cache:
            for player_name in current_players | values:
                if player_name not in current_players:
                    query = "INSERT INTO players (active,name,maxage) VALUES (?, ?, {});".format(secondsTillDowntime())
                else:
                    query = "UPDATE  players SET active = ?  WHERE name = ?;"
                cache.con.execute(query, (player_name in values, player_name))
            query = "UPDATE  players set modified = ?  WHERE active=1;"
            cache.con.execute(query, (time.time(),))
            cache.con.commit()

    def setPlayerOnline(self, online_player_names: set):
        current_players = self.getKnownPlayerNames()
        with self as cache:
            for player_name in current_players | online_player_names:
                if player_name not in current_players:
                    query = "INSERT INTO players (active,online,name,maxage) VALUES (?,1, ?, {});".format(
                        secondsTillDowntime())
                    cache.con.execute(query, (player_name in online_player_names, player_name))
                query = "UPDATE  players set modified = ?  online=1 WHERE name= ? ;"
                cache.con.execute(query, (time.time(), player_name))
            cache.con.commit()

    def clearOutdatedPlayerNames(self):
        """
        Clears all Outdated player names

        Returns:
            None

        """
        with Cache.SQLITE_WRITE_LOCK:
            query = "DELETE FROM players WHERE datetime(modified+maxage,'unixepoch') < datetime() and key is null"
            self.con.execute(query)
            self.con.commit()

    def setThreaConnections(self, data):
        self.putIntoCache("Eve_Scout_Public_Signatures", data, 60)

    def getThreaConnections(self):
        data = self.getFromCache("Eve_Scout_Public_Signatures", outdated=True)
        if data is not None:
            return json.loads(data)
        else:
            return list()

    def insertAlliance(self, alliance_id, alliance_name, alliance_standing=None):
        with Cache.SQLITE_WRITE_LOCK:
            query = "INSERT INTO alliances (id,name,standing,maxage) VALUES (?,?, ?);"
            self.con.execute(query, (alliance_id, alliance_name, alliance_standing))
            self.con.commit()

    def getAllianceRed(self) -> list:
        """
            get all red alliances from database
        Returns:

        """
        with Cache.SQLITE_WRITE_LOCK:
            query = "SELECT id FROM alliances WHERE standing <= 0 "
            res = self.con.execute(query).fetchall()
        lst = list()
        for i in res:
            lst.append(i[0])
        return lst

    def getAllianceBlue(self) -> list:
        """
            get all blue alliances from database
        Returns:

        """
        with Cache.SQLITE_WRITE_LOCK:
            query = "SELECT alliance_id FROM avatars WHERE alliance_id is not NULL"
            res = self.con.execute(query).fetchall()
        lst = list()
        for i in res:
            lst.append(i[0])
        res = list(dict.fromkeys(lst))
        return res

    def clearOutdatedKillmails(self):
        """
        Clears all expired kill mails

        Returns:
            None

        """
        with Cache.SQLITE_WRITE_LOCK:
            self.con.execute("DELETE FROM killmails WHERE datetime(modified+maxage,'unixepoch') < datetime()")
            self.con.commit()

    def putKillmailtoCache(self, killmail_id, system_id, region_id,
                           json_txt, modified=time.time(), maxage=48*60*60) -> None:
        """
            Puts a zKillboard notification into the database
        Args:
            killmail_id:
            system_id: id of system
            region_id: id of the reagion
            json_txt:
            modified:
            maxage: two days 48h

        Returns:
            None
        """
        with Cache.SQLITE_WRITE_LOCK:
            self.con.execute("DELETE FROM killmails WHERE datetime(modified+maxage,'unixepoch') < datetime()")
            query = "INSERT OR IGNORE INTO killmails (id, system_id, region_id, json, modified, maxage) " \
                    "VALUES (?,?,?,?,?,?);"
            self.con.execute(query, (killmail_id, system_id, region_id, json_txt, modified, maxage)).fetchall()
            self.con.commit()

    def getKillmails(self, intel_time=20*60):
        query = "select json from killmails WHERE datetime(modified + {},'unixepoch') < datetime()".format(intel_time)
        res = self.con.execute(query).fetchall()
        lst = list()
        for i in res:
            lst.append(i[0])
        return lst

    def putDotlanMap(self, region_id, xml_map=None, native_map=None):
        with Cache.SQLITE_WRITE_LOCK:
            query = "INSERT OR REPLACE INTO map (id, dotlan, native, modified, maxage) VALUES (?,?,?,?);"
            self.con.execute(query, (region_id, xml_map, native_map, currentEveTime(), 24*60+60)).fetchall()
            self.con.commit()

    def getDotlanMap(self, region_id):
        with Cache.SQLITE_WRITE_LOCK:
            query = "SELECT dotlan FROM map WHERE id = ?;"
            self.con.execute(query, (region_id, ))

    def clearOutdated(self) -> None:
        """
            Deletes  all outdated items when modified + maxage  < datetime()
        Returns:
            None
        """
        with Cache.SQLITE_WRITE_LOCK:
            self.con.execute("DELETE FROM cache WHERE datetime(modified+maxage,'unixepoch') < datetime()")
            self.con.execute("DELETE FROM players WHERE datetime(modified+maxage,'unixepoch') < datetime()")
            self.con.execute("DELETE FROM avatars WHERE datetime(modified+maxage,'unixepoch') < datetime()")
            self.con.execute("DELETE FROM killmails WHERE datetime(modified+maxage,'unixepoch') < datetime()")
            self.con.commit()

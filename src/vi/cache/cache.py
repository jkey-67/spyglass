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
from .dbstructure import updateDatabase


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
        """ Putting something in the cache maxAge is maximum age in seconds
        """
        with Cache.SQLITE_WRITE_LOCK:
            query = "DELETE FROM cache WHERE key = ?"
            self.con.execute(query, (key,))
            query = "INSERT INTO cache (key, data, modified, maxAge) VALUES (?, ?, ?, ?)"
            self.con.execute(query, (key, value, time.time(), max_age))
            self.con.commit()

    def getFromCache(self, key, outdated=False):
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

    def clearOutdatedCache(self):
        """ Delete all outdated jumpbridges from database
        """
        with Cache.SQLITE_WRITE_LOCK:
            query = "DELETE FROM cache WHERE datetime(modified+maxage,'unixepoch') < datetime()"
            self.con.execute(query)
            self.con.commit()

    def putImageToCache(self, name, data):
        """ Put the picture of a player or other item into the avatars table

        Args:
            name(str):Key of interests

        Args:
              data:Picture data to be inserted as blob
        """
        with Cache.SQLITE_WRITE_LOCK:
            # data is a blob, so we have to change it to buffer
            data = to_blob(data)
            query = "DELETE FROM avatars WHERE charname = ?"
            self.con.execute(query, (name,))
            query = "INSERT INTO avatars (charname, data, modified) VALUES (?, ?, ?)"
            self.con.execute(query, (name, data, time.time()))
            self.con.commit()

    def getImageFromCache(self, name):
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

    def clearOutdatedImages(self, months: int = 12):
        """
        Clears all images older than 6 months

        Returns:
            None

        """

        with Cache.SQLITE_WRITE_LOCK:
            query = "DELETE FROM avatars WHERE datetime(modified+60*60*24*30*{},'unixepoch') < datetime()".\
                format(months)
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

    def recallAndApplySettings(self, responder, settings_identifier):

        def getattrlist(responder, attr):
            if len(attr) == 1:
                return getattr(responder, attr[0])
            else:
                for itms in attr:
                    if isinstance(itms, str) :
                        responder= getattr(responder, itms)
                return responder


        version = self.getFromCache("version")
        restore_gui = version == vi.version.VERSION
        settings = self.getFromCache(settings_identifier)
        if settings:
            settings = eval(settings)
            for setting in settings:
                obj = responder if not setting[0] else getattrlist(responder, setting[0].split('.'))
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

                except Exception as e:
                    logging.error("Recall application setting failed to set attribute {0} | {1} | {2} | error {3}"
                                  .format(str(obj), setting[1], setting[2], e))

    def putJumpGate(self, src, dst, src_id=None, dst_id=None,
                    json_src=None, json_dst=None, used=None, max_age=60 * 60 * 24 * 14):
        """
        """
        with Cache.SQLITE_WRITE_LOCK:
            # data is a blob, so we have to change it to buffer
            query = "DELETE FROM jumpbridge WHERE src LIKE ? or dst LIKE ? or src LIKE ? or dst LIKE ?"
            self.con.execute(query, (src, src, dst, dst))
            query = "INSERT INTO jumpbridge (src, dst, used, id_src, id_dst, json_src, json_dst, modified, maxage) "\
                    "VALUES (?, ?, ?, ?, ?, ?, ? , ?, ?)"
            self.con.execute(query, (src, dst, used, src_id, dst_id,
                                     json.dumps(json_src), json.dumps(json_dst), time.time(), max_age))
            self.con.commit()

    def clearJumpGate(self, src) -> None:
        """ Removes all items from the jumpbridge table where FROM  or TO match str

        Args:
            src(str):Name of the system which can be FROM or TO

        """
        with Cache.SQLITE_WRITE_LOCK:
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
            return eval(sovereignty)
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
            return None
        else:
            return founds

    def getJumpGatesAtIndex(self, inx: int):
        """
        """
        with Cache.SQLITE_WRITE_LOCK:
            query = "select src, dst, id_src, json_src  from jumpbridge  LIMIT 1 OFFSET ?"
            founds = self.con.execute(query, (inx,)).fetchall()
            if len(founds) == 0:
                return None
            else:
                return {
                    "src": founds[0][0],
                    "dst": founds[0][1],
                    "id_src": founds[0][2],
                    "json_src": eval(founds[0][3])if founds[0][3] != "null" else None
                }

    def putPOI(self, data):
        """ data can be structure or station dict
        """
        if data is None:
            return
        with Cache.SQLITE_WRITE_LOCK:
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

    def getPOIAtIndex(self, inx: int):
        """
        """
        with Cache.SQLITE_WRITE_LOCK:
            query = "select json from pointofinterest  LIMIT 1 OFFSET ?"
            founds = self.con.execute(query, (inx,)).fetchall()
            if len(founds) == 0:
                return None
            else:
                ret_val = eval(founds[0][0])
                if "station_id" in ret_val.keys():
                    ret_val["destination_id"] = ret_val["station_id"]
                if "structure_id" in ret_val.keys():
                    ret_val["destination_id"] = ret_val["structure_id"]
                return ret_val

    def clearPOI(self, destination_id: int) -> None:
        with Cache.SQLITE_WRITE_LOCK:
            query = "DELETE FROM pointofinterest  WHERE id IS ?"
            founds = self.con.execute(query, (destination_id,)).fetchall()
            self.con.commit()

    def clearAPIKey(self, char) -> None:
        with Cache.SQLITE_WRITE_LOCK:
            # data is a blob, so we have to change it to buffer
            query = "DELETE FROM players WHERE id IS ? or name IS ?"
            self.con.execute(query, (char, char))
            self.con.commit()

    def hasAPIKey(self, char) -> bool:
        with Cache.SQLITE_WRITE_LOCK:
            query = "SELECT key FROM players WHERE id IS ? or name IS ?"
            res = self.con.execute(query, (char, char)).fetchall()
            return len(res) > 0 and res[0] is None

    def getAPIKey(self, char):
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
            query = "INSERT INTO players (id, name, key, active, max_age) VALUES (?, ?, ?, ?, ?)"
            self.con.execute(query, (key["CharacterID"], key["CharacterName"], json.dumps(key), 1, max_age))
            self.con.commit()

    def removeAPIKey(self, char_name):
        self.clearAPIKey(char_name)

    def getAPICharNames(self):
        query = "SELECT name FROM players;"
        res = self.con.execute(query).fetchall()
        lst = list()
        for i in res:
            lst.append(i[0])
        return lst

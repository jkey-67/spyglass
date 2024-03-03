###########################################################################
#  Vintel - Visual Intel Chat Analyzer									  #
#  Copyright (C) 2014-15 Sebastian Meyer (sparrow.242.de+eve@gmail.com )  #
#   																	  #
#  This program is free software: you can redistribute it and/or modify	  #
#  it under the terms of the GNU General Public License as published by	  #
#  the Free Software Foundation, either version 3 of the License, or	  #
#  (at your option) any later version.									  #
#   																	  #
#  This program is distributed in the hope that it will be useful,		  #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of		  #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the		  #
#  GNU General Public License for more details.							  #
#   																	  #
#   																	  #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.	 If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

import time

"""
you can add external databaseupdates to database updates.
they should be a tuple like (query, condition)
query	  = the query to run on the database connection
condition = if TRUE the query qull be executed
"""
databaseUpdates = []


def updateDatabase(old_version, con):
    """ Changes for the database-structure should be added here,
        or added to added_database_updates
        con = the database connection
    """
    queries = []
    if old_version < 1:
        queries += ["CREATE TABLE IF NOT EXISTS version (version INT);", "INSERT INTO version (version) VALUES (1)"]
    if old_version < 2:
        queries += ["CREATE TABLE playernames (charname VARCHAR PRIMARY KEY, status INT, modified INT)",
                    "CREATE TABLE avatars (charname VARCHAR PRIMARY KEY, data  BLOB, modified INT)",
                    "UPDATE version SET version = 2"]
    if old_version < 3:
        queries += ["CREATE TABLE cache (key VARCHAR PRIMARY KEY, data BLOB, modified INT, maxage INT)",
                    "UPDATE version SET version = 3"]

    if old_version < 4:
        queries += ["CREATE TABLE jumpbridge (src VARCHAR PRIMARY KEY, dst VARCHAR, id_src INT, id_dst INT, used INT,"
                    "modified INT, maxage INT)",
                    "UPDATE version SET version = 4"]

    if old_version < 5:
        queries += ["CREATE TABLE players (id INT PRIMARY KEY, name VARCHAR, key VARCHAR, active INT, max_age INT)",
                    "UPDATE version SET version = 5"]

    if old_version < 6:
        queries += ["CREATE TABLE pointofinterest  (id INT PRIMARY KEY, type INT, name VARCHAR, json VARCHAR )",
                    "UPDATE version SET version = 6"]

    if old_version < 7:
        queries += ["ALTER TABLE jumpbridge add COLUMN json_src",
                    "ALTER TABLE jumpbridge add COLUMN json_dst",
                    "UPDATE version SET version = 7"]

    if old_version < 8:
        queries += ["ALTER TABLE players add COLUMN modified INT;",
                    "ALTER TABLE players add COLUMN system_id INT;",
                    "ALTER TABLE players add COLUMN intel_range INT;",
                    "DROP TABLE IF EXISTS playernames;",
                    "UPDATE players SET modified = {};".format(time.time()),
                    "UPDATE version SET version = 8"]
    if old_version < 9:
        queries += ["ALTER TABLE players add COLUMN online INT;",
                    "UPDATE version SET version = 9"]

    if old_version < 10:
        queries += ["ALTER TABLE avatars add COLUMN player_id INT;",
                    "ALTER TABLE avatars add COLUMN alliance_id INT;",
                    "ALTER TABLE avatars add COLUMN json VARCHAR;",
                    "ALTER TABLE avatars add COLUMN maxage INT;",
                    "CREATE TABLE alliances (id INT PRIMARY KEY, name VARCHAR, standing INT, maxage INT  );",
                    "CREATE TABLE iconcache (id INT PRIMARY KEY, icon BLOB , modified INT, maxage INT);",
                    "CREATE TABLE killmails (id INT PRIMARY KEY, system_id INT, region_id, json VARCHAR," 
                    "modified INT, maxage INT);",
                    "DELETE FROM cache WHERE key LIKE 'ids_dicts_%' OR key LIKE 'system_tmp%';",
                    "ALTER TABLE players RENAME COLUMN max_age TO maxage;",
                    "UPDATE version SET version = 10"]
    if old_version < 11:
        queries += ["DELETE FROM cache WHERE key LIKE 'map_%';",
                    "CREATE TABLE map (id INT PRIMARY KEY, dotlan VARCHAR, native VARCHAR, modified INT, maxage INT);",
                    "UPDATE version SET version = 11"]

    for query in queries:
        con.execute(query)
    for update in databaseUpdates:
        if update[1]:
            con.execute(update[0])
    con.commit()

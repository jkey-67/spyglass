<p align="center">
  <img align="middle" src="./src/vi/ui/res/logo_splash.png">
</p>

# Welcome To EVE Spyglass 1.7

EVE Spyglass is an intel visualisation and alarm system for [EVE Online](http://www.eveonline.com). This too gathers information from in game 
chat channels and presents the data on a [dotlan](http://evemaps.dotlan.net/map/Catch#npc24) generated map. The map is highlighted in real time as players 
report intel in monitored chat channels.

Spyglass is written with Python 3.10, using PySide6 for the graphical interface and audio playback, BeautifulSoup4 
for SVG parsing.

## Screenshot

<p align="center">
  <img align="middle" src="./img/2024-11-17_15-42-15.png">
</p>

## Features
### 1.6.0
 - Platforms supported: Executable for Windows, Linux and Mac runs directly with python 3 from source.
 - Monitored intel chat channels are merged to one chat stream. You can add or remove channels via a menu option.
 - These chat channels can be rescanned on startup to allow for existing intel to be displayed
 - An interactive map of Providence / Catch is provided. Systems on the map display real-time intel data as reported through intel channels.
 - Systems on the map display different color backgrounds as their alarms age, with text indicating how long ago the specific system was reported. Background color becomes red when a system is reported and lightens (red->orange->yellow->white) in the following intervals: 4min, 10min, 15min, and 25min.
 - Systems reported clear display on the map with a green background for 20 minutes.
 - For all Systems, a right button context menu allows you to open [dotlan](https://www.dotlan.net/) or [zkillboard](https://zkillboard.com/) for the selected system directly.
 - Manual follow a Region, a right button context menu allows to select a different Region directly from inside the map.
 - Clicking on a specific system will display all messages bound on that system in the past 20 minutes. From there one can set a system alarm, set the systems clear or set it as the current system for one or more of your characters.
 - Clicking on a system in the intel channel (the right side column) causes it to be highlighted on the map with a blue background for 10 seconds.
 - The system where your character is currently located is highlighted on the map with a violet background automatically whenever a character changes systems.
 - Automatic region change for the pilot with api registration is possible.
 - Alarms can be set so that task-bar notifications are displayed when an intel report calls out a system within a specified number of jumps from your character(s). This can be configured from the task-bar icon.
 - For each alarm distance you can select a different sound file.
 - The sound volume for the notification is now adapt to the distance, closer it is louder, further away it gets quieter.
 - The main window can be set up to remain "always on top", can be displayed with a specified level of transparency and also frameless works.
 - Ship names in the intel chat are highlighted.
 - Incursion system and systems with reinforced TCU Territorial Claim Unit or I-HUB Infrastructure Hub are marked with orange and red borders.

### 1.6.1
 - You can see the alliance ticker for all systems under sovereignty of a player alliance.
 - During startup, the software automatically double check for a new version ready to download. If there is an update available four your version, you will get a button start the download on screen. You can check for new version manually, try [double check latest release](https://github.com/jkey-67/spyglass/releases/latest)

 - If you copy the name of the jump bridge in game, the connection is automatically added into the database, the software will remove all pairs with the same source or destination system.

### 1.6.2
 - list of POI added, you can use the list items to set the destination
 - now you can refresh and delete the Ansiblex jump gates from inside Spyglass
 - the registered chars can be switched from Spyglass
 - fixing ESI search changes

### 1.6.3
 - using QT6 with PySide6 now (QtTextToSpeech is still missing)
 - preset of statistic and jump connections now work
 - using pyside6-uic for ui files
 - copy structure names in game now works also with the new Photon UI enabled
 - Ansiblex jump connections out of the current region are now also displayed
 - automatically flush the solar system for unregistered chars after two days
 - use online state and position for registered characters on startup and intel rescan 
 - The text in the POI List can be edited now

### 1.6.4
 - filewatcher now use only files changed after downtime
 - reload of intel now use the lift of files from the filewatcher
 - processing of chat entries now run separated from the map
 - using clipboard with Photon UI improved

### 1.6.5
 - The navigation context menus now allow to select the api char
 - Adding some icons, update of Thera connection on button
 - Now QDesktopServices is used to show web pages
 - Added json files to access the Universe
 - fix high sec system now found, new ships added
 - using shorter npc faction names on map

### 1.6.6
 - icons added on gui
 - bug fixes to improve stability 

### 1.6.7
 - stargates added
 - now Jumpbridges can be used without esi validation   
 - bug fixes for chat parsing  
 - bug fixes to improve stability

### 1.6.8
 - alliances with access to the intel channels will be marked as friendly
 - now using the [zKillboard websockets](https://github.com/zKillboard/zKillboard/wiki/Websocket) as source for intel if victim or attacker is part of an alliance which is marked as friendly
 - calculation of the path length now includes jump bridges
 - the intel status is displayed in transparent tool window on hover
 - bug fixes for the sqlite database
 - bug fixes inaccessible chars after removing of API users

### 1.6.9
 - bug fixes corrupt maps names in cache
 - spoken notification for zKillbord are now much shorter
 - now region can be changed from POI and Thera context menu

### 1.7.0
 - fixing corrupted maps when dotlan returns 503 error during the map update
 - region Yasna Zakh added to maps
 - new ships from 14 November 2013 update added to database
 - now the software now sorts the intel chat by datetime
 - Regions can now be selected by system names
 - regions can now be change easy by combobox
 - the public part of the EvE-Scout Backend API v2 2.1.0 is now used to handle Thera and Turnur system. [ESAPI](https://api.eve-scout.com/ui/#overview)
 - fix detection local change for local zh, es, ko and jp 

## 1.7.1
- using native Qt paint functions instead of the QSVGPainter
- fixed a regression which caused a deadlock during file parsing
- the monitored areas within the alarm distance is now marked with a white background
- zKillboard entries will get a orange background
- known Wormhole Thera and Turnur connections will be marked yellow on the current map, the info window show the identifier, the estimated lifetime and the maximum allowed ship types
- the mouse forward and backward buttons can now be used to navigate in between the last maps and positions 

## 1.7.2
- fixing an endless loop while parsing intel lines with multiple space in between tokens
- showing vulnerability occupancy level (ADM) and vulnerable start time on top
- the VR regions are removed from selection
- a honeycomb-shape background with a defined color can be placed around a system in the background listed in EVE/spyglass/backgrounds.txt
- show location button added
- display systems with ice belts listed in EVE/spyglass/icesystems.txt
- enables the viewing of small medium and large structures listed in EVE/spyglass/structures.txt
- fixing crash when jumping into *Unknown* systems 
- now using Qt dock widgets instead of tab widgets
- oauth2 registration change to 127.0.0.1
- POIs can now be sorted via drag and drop

## Features with API registration
EVE Spyglass is using the v2/oauth/authorize and v2/oauth/token for authentication.[SSO](https://developers.eveonline.com/blog/article/sso-endpoint-deprecations-2)

The following access rights will be use
 - esi-location.read_location.v1  since in 1.7.2 
 - esi-search.search_structures.v1 
 - esi-universe.read_structures.v1
 - esi-ui.write_waypoint.v1 
 - esi-characters.read_standings.v1 
 - esi-location.read_online.v1
 

### API access enables
 - the right button context menu to set waypoints and destinations in game directly form inside EVE Syglass.
 - filling the jump bridge data from online structures
 - using the POI Table to set destination in game
 - monitoring login state and current solar system for registered characters

### API access monitoring and removal
Please remember to manage your access to all [third-party-applications](https://community.eveonline.com/support/third-party-applications)

## Intel Rescan

 - Spyglass can look over all of your previous logs to check for intel. This is useful in two main cases. Firstly when you start up Spyglass but have already had eve running and want to see the intel you have already collected. Secondly, when changing theme the intel in Spyglass is all reset. You can rescan to get it back.
 - By default, automatically rescanning is disabled, this is so people don't complain of speed issues.
 - THIS IS VERY SLOW! looking over existing logs can be incredibly time-consuming so if you use it, please be patient. This is especially the case for more characters/chat channels you have.
 - If you want to use the feature, but find it to be too slow, clear out your chat logs regularly.

## POIs
- If you are docked on station, copy the name of the structure to the clipboard to fill the POI list.

## JBs
- If you are docked on station, copy the name of the structure from inside the Solar System: Information Structure Tab
- In space, use the right mouse button to click on the structure inside the overview and copy then

## Background marking
You can mark systems with a honeycomb colored background by adding the file background.txt to the spyglass folder 
%user%/Documents/EVE/Spyglass.

Each line represent one marking, the first element is a name of a Region, Constellation or System.
The second element, the color and the option third element defines a scale factor defining the bounding box for the 
drawing in between 1.0 to 2.0. 

Valid colors will be for example ,gree,#AARRGGBB  and #RRGGBB. If alpha is defined as 1.0(255) the alpha is replaced 
with 0.3f.

You can comment out lines by with a leading #. 

```
 # Region Lonetrek has RGB color R=0xC0, G=0xC0, B=0xC0 alpha is defaulted to 1.0
 Lonetrek,#c0c0c0
 
 # Connstellation VT-LHB will be red  R=0xFF, G=0x00, B=0x00 alpha is defaulted to 1.0
 VT-LHB,red
 
 # System Jitas bounding box will be scaled by factor 1.5 
 Jita,#FFB8860B,2.0 
 
 #System MJ-5F9 is yellow with alpha 1.0 
 MJ-5F9,#ffffff00
 
 #System TDP-T3 is blue with alpha defaulted
 TDP-T3,blue
 
 #System Z-ENUD is white with alpha defaulted
 Z-ENUD,white
 ```

## Mark Systems with Ice with a blue border
Add a test file **%user%/Documents/EVE/Spyglass/icesystems.txt** with names of systems which should be marked by the 
software. 
 ```
#System name
00TY-J
01B-88
02V-BK
04-LQM
 ```

## Mark Structures and Stations in Systems
Add a test file **%user%/Documents/EVE/Spyglass/structures.txt** with type_id,structure_id,system_name,name 
of the structure which should be displayed by the software. 

To generate the list of structures, copy in game from structure browser to the in-game utility notepad, 
Then use 'copy selected with formatting' to copy all with xml information to clipboard and pate all here 
and reformat.

 ```
#type_id,structure_id,system_name,name
#
# Copy in game from stucture brower to the in-game utility notepad, 
# Then use 'copy selected with formating' to copy all with xml information to cipboard and pate all here and reformat.
#
35832,1039589414201,KOI0-H,Structure 1
35833,1032611391522,P-1O18,Structure 2
35833,1031894841319,L-4FU9,Structure 3
 ```

## Running EVE Spyglass from Source

To run or build from the source you need the following packages installed on your machine. Most, if not all, can be 
installed from the command line using package management software such as "pip". Mac and Linux both come with pip installed, Windows users may need to install [cygwin](https://www.cygwin.com) or use the powershell to use pip. Of course all the requirements also have download links.

The packages required are:
- Python 3.10
https://www.python.org/downloads/
- PySide6
https://pypi.org/project/PySide6/
- BeautifulSoup 4
https://pypi.org/project/beautifulsoup4/
- Requests
https://pypi.org/project/requests/
- parse
https://pypi.org/project/parse/
- espeakng (awaiting QtTextToSpeech)
https://pypi.org/project/espeakng/
- networkx
https://networkx.org/

Optional use the Windows installer https://github.com/espeak-ng/espeak-ng/releases

Please look to the file requirements.txt for the list off dependencies.

You need an installed and configured python with pip and git installed.

To start EVE Spyglass, open a console checkout sources and dependencies and start it.

`win> git clone https://github.com/jkey-67/spyglass.git`

`win> cd spyglass\src`

`win> git checkout qt5`

`win> pip install -r requirements.txt`

`win> python spyglass.py`

Register as developer and create a own application key on the [EVE-Developer](https://developers.eveonline.com/applications) webpage.

## The background of Spyglass

EVE-Spyglass is forked out from qt5 branch of [Crypta-Eve/spyglass](https://github.com/Crypta-Eve/spyglass) 

Spyglass is a project aimed at the continuation to the work done on the Vintel tool by [Xanthos](https://github.com/Xanthos-Eve) which can be 
found [Xanthos-Eve/vintel](https://github.com/Xanthos-Eve/vintel).

## FAQ

**License?**

Spyglass is licensed under the [GPLv3](https://www.gnu.org/licenses/gpl-3.0.html).

**A little too big for such a little tool.**

The .exe ships with the complete python environment and needed libs. You could save some space using the source code instead.

**What platforms are supported?**

Spyglass runs on Windows, Linux and Mac. A Windows standalone packages are provided with each release. Linux and Mac 
users are advised to use run spyglass from source.

**What file system permissions does Spyglass need?**

- It reads your PCs EVE chatlogs stored on the local hard drive 
- It creates and writes to **path-to-your-chatlogs**/../../spyglass/.
- It needs to connect the internet [dotlan](https://dotlan.evemaps.net), and [EVE Swagger Interface](https://esi.evetech.net/).
- If activated, the software use the [EVE Swagger Interface](https://esi.evetech.net/ui/?version=latest#/Swagger/get_v6_swagger). 

**Spyglass calls home?**

Yes it does. If you don't want to this, use a firewall to forbid it.
Spyglass use the esi interface to update player images, routes and structure data from eve online.

NO DATA IS SENT FROM YOU TO ME!

**Spyglass does not find my chatlogs or is not showing changes to chat when it should. What can I do?**

Spyglass looks for your chat logs in ~\EVE\logs\chatlogs and ~\DOCUMENTS\EVE\logs\chatlogs. Logging must be enabled in 
the EVE client options. You can set this path on your own by giving it to Spyglass at startup. For this you have to 
start it on the command line and call the program with the path to the logs.

Examples:

`win> spyglass-1.x.x.exe "d:\strange\path\EVE\logs\chatlogs"`

    – or –

`linux> python spyglass.py "/home/user/myverypecialpath/EVE/logs/chatlogs"`

**Spyglass does not start! What can I do?**

Please try to delete Spyglass's Cache. It is located in the EVE-directory where the chat logs are in. If your chat logs 
are in **\Documents\EVE\logs\chatlogs** Spyglass writes the cache to **\Documents\EVE\spyglass**

**Spyglass takes many seconds to start up; what are some causes and what can I do about it?**

Spyglass asks the operating system to notify when a change has been made to the ChatLogs directory - this will happen 
when a new log is created or an existing one is updated. In response to this notification, Spyglass examines all files 
in the directory to analyze the changes. If you have a lot of chat logs this can make Spyglass slow to scan for file 
changes. Try periodically moving all the chatlogs out of the ChatLogs directory (zip them up and save them somewhere 
else if you think you may need them some day).

**Spyglass is misbehaving, and I don't know why - how can I easily help diagnose problems with Spyglass**

Spyglass writes its own set of logs to the \Documents\EVE\spyglass\logs directory. A new log is created as the old one 
fills up to its maximum size setting. Each entry inside the log file is time-stamped. These logs are emitted in 
real-time, so you can watch the changes to the file as you use the app.

**I'm not a coder, how can I help?**

Your feedback is needed! Use the program for a while, then come back [here and create issues](https://github.com/jkey-67/spyglass/tree/qt5). Record anything you 
think about Spyglass - bugs, frustrations, and ideas to make it better.

**After the last update, I can't start Spyglass anymore.**

Maybe you need to remove the database, close Spyglass then rename the current database and start again. You find the 
database file in \Documents\EVE\spyglass\cache-2.sqlite3 rename the file.

**Trouble using Wayland on linux**
Currently transparent windows, clipboard and hotkeys did not work proper on linux system. 

**All EVE related materials are property of [CCP Games](https://www.ccpgames.com/)**

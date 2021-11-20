<p align="center">
  <img align="middle" src="https://raw.githubusercontent.com/jkey-67/spyglass/master/src/vi/ui/res/logo_splash.png">
</p>


# Welcome To Spyglass 1.6

Spyglass is an intel visualisation and alarm system for [EVE Online](http://www.eveonline.com). This too gathers information from in game chat channels and presents the data on a [dotlan](http://evemaps.dotlan.net/map/Catch#npc24) generated map. The map is highlighted in real time as players report intel in monitored chat channels.

Spyglass 1.6 is written with Python 3.9, using PyQt5 for the graphical interface and audio playback, BeautifulSoup4 for SVG parsing.

## Screenshot

![](https://raw.githubusercontent.com/jkey-67/spyglass/qt5/src/docs/Screenshot%201.6-abyss.png)

## Features

 - Platforms supported: Executable for Windows, Linux and Mac runs directly from python source.
 - Monitored intel chat channels are merged to one chat stream. You can add or remove channels via a menu option.
 - These chat channels can be rescanned on startup to allow for existing intel to be displayed
 - An interactive map of Providence / Catch is provided. Systems on the map display real-time intel data as reported through intel channels.
 - Systems on the map display different color backgrounds as their alarms age, with text indicating how long ago the specific system was reported. Background color becomes red when a system is reported and lightens (red->orange->yellow->white) in the following intervals: 4min, 10min, 15min, and 25min.
 - Systems reported clear display on the map with a green background for 10 minutes.
 - For all Systems a right button context menu allows you to open [dotlan](https://www.dotlan.net/) or [zkillboard](https://zkillboard.com/) for the selected system directly.
 - Clicking on a specific system will display all messages bound on that system in the past 20 minutes. From there one can can set a system alarm, set the systems clear or set it as the current system for one or more of your characters.
 - Clicking on a system in the intel channel (the right side column) causes it to be highlighted on the map with a blue background for 10 seconds.
 - The system where your character is currently located is highlighted on the map with an violet background automatically whenever a character changes systems.
 - Automatic region change for the pilot with api registration is possible.
 - Alarms can be set so that task-bar notifications are displayed when an intel report calls out a system within a specified number of jumps from your character(s). This can be configured from the task-bar icon.
 - For each alarm distance you can select a different sound file.
 - The sound volume for the notification is now adapt to the distance, near is louder, far quitter.
 - The main window can be set up to remain "always on top", can be displayed with a specified level of transparency and also frameless works.
 - Ship names in the intel chat are highlighted.


## Features with API registration

Spyglass  use the following access rights 
 - esi-ui.write_waypoint.v1 
 - esi-universe.read_structures.v1 
 - esi-search.search_structures.v1


### API access enables 

 - the right button context menu to set waypoints and destinations in game directly form inside spyglass.
 - filling the jump bridge data from online structures  

### API access monitoring and removal
Please remember to manage your access to all [third-party-applications](https://community.eveonline.com/support/third-party-applications)  


## Intel Rescan

 - Spyglass can look over all of your previous logs to check for intel. This is useful in two main cases. Firstly when you start up Spyglass but have already had eve running and want to see the intel you have already collected. Secondly, when changing theme the intel in Spyglass is all reset. You can rescan to get it back.
 - By default, automatically rescanning is disabled, this is so people don't complain of speed issues.
 - THIS IS VERY SLOW! looking over existing logs can be incredibly time-consuming so if you use it, please be patient. This is especially the case for more characters/chat channels you have.
 - If you want to use thi feature, but find it to be too slow, clear out your chatlogs regularly.


## Running Spyglass from Source

To run or build from the source you need the following packages installed on your machine. Most, if not all, can be installed from the command line using package management software such as "pip". Mac and Linux both come with pip installed, Windows users may need to install [cygwin](https://www.cygwin.com) or use the powershell to use pip. Of course all the requirements also have download links.

The packages required are:
- Python 3.9
https://www.python.org/downloads/release/python-390/
- PyQt5
https://pypi.org/project/PyQt5/
- BeautifulSoup 4
https://pypi.org/project/beautifulsoup4/
- PyQtWebEngine
https://pypi.org/project/PyQtWebEngine/
- Requests
https://pypi.org/project/requests/
Please look to the file requirements.txt for the list off dependencies.

You need an installed and configured python with pip and git installed.  
To start spyglass, open a console checkout sources and dependencies and start it.    
`win> git clone https://github.com/jkey-67/spyglass.git`

`win> cd spyglass\src`

`win> git checkout qt5`

`win> pip install -r requirements.txt`

`win> python spyglass.py`

Currently, users with Windows may choose Qt 5.15.2  inside requirements.txt

## The background of Spyglass

DENCI-Spyglass is forked out from qt5 branche of [Crypta-Eve/spyglass](https://github.com/Crypta-Eve/spyglass) 

Spyglass is a project aimed at the continuation to the work done on the Vintel tool by [Xanthos](https://github.com/Xanthos-Eve) which can be found [Xanthos-Eve/vintel](https://github.com/Xanthos-Eve/vintel).

## FAQ

**License?**

Spyglass is licensed under the [GPLv3](http://www.gnu.org/licenses/gpl-3.0.html).

**A little bit to big for such a little tool.**

The .exe ships with the complete python environment and needed libs. You could save some space using the source code instead.

**What platforms are supported?**

Spyglass runs on Windows, Linux and Mac. A Windows standalone packages are provided with each release. Linux and Mac users are advised to use run spyglass from source.

**What file system permissions does Spyglass need?**

- It reads your EVE chatlogs
- It creates and writes to **path-to-your-chatlogs**/../../spyglass/.
- It needs to connect the internet [dotlan](https://dotlan.evemaps.net), and [EVE Swagger Interface](https://esi.evetech.net/).

**Spyglass calls home?**

Yes it does. If you don't want to this, use a firewall to forbid it.
Spyglass use the esi interface to update player images, routes and structure data from eve online.

NO DATA IS SENT FROM YOU TO ME!

**Spyglass does not find my chatlogs or is not showing changes to chat when it should. What can I do?**

Spyglass looks for your chat logs in ~\EVE\logs\chatlogs and ~\DOCUMENTS\EVE\logs\chatlogs. Logging must be enabled in the EVE client options. You can set this path on your own by giving it to Spyglass at startup. For this you have to start it on the command line and call the program with the path to the logs.

Examples:

`win> spyglass-1.x.x.exe "d:\strange\path\EVE\logs\chatlogs"`

    – or –

`linux> python spyglass.py "/home/user/myverypecialpath/EVE/logs/chatlogs"`

**Spyglass does not start! What can I do?**

Please try to delete Spyglass's Cache. It is located in the EVE-directory where the chatlogs are in. If your chatlogs are in \Documents\EVE\logs\chatlogs Spyglass writes the cache to \Documents\EVE\spyglass

**Spyglass takes many seconds to start up; what are some causes and what can I do about it?**

Spyglass asks the operating system to notify when a change has been made to the ChatLogs directory - this will happen when a new log is created or an existing one is updated. In response to this notification, Spyglass examines all files in the directory to analyze the changes. If you have a lot of chat logs this can make Spyglass slow to scan for file changes. Try periodically moving all the chatlogs out of the ChatLogs directory (zip them up and save them somewhere else if you think you may need them some day).

**Spyglass is misbehaving, and I don't know why - how can I easily help diagnose problems with Spyglass**

Spyglass writes its own set of logs to the \Documents\EVE\spyglass\logs directory. A new log is created as the old one fills up to its maximum size setting. Each entry inside the log file is time-stamped. These logs are emitted in real-time, so you can watch the changes to the file as you use the app.

**I'm not a coder, how can I help?**

Your feedback is needed! Use the program for a while, then come back [here and create issues](https://github.com/jkey-67/spyglass/tree/qt5). Record anything you think about Spyglass - bugs, frustrations, and ideas to make it better.



**All EVE related materials are property of [CCP Games](https://www.ccpgames.com/)**

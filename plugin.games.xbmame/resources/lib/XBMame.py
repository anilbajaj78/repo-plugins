# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
#
# The Original Code is plugin.games.xbmame.
#
# The Initial Developer of the Original Code is Olivier LODY aka Akira76.
# Portions created by the XBMC team are Copyright (C) 2003-2010 XBMC.
# All Rights Reserved.

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

import os
import re
import sys
import urllib
import shutil

from XMLHelper import XMLHelper
from GameItem import GameItem
from DIPSwitch import DIPSwitch
from DBHelper import DBHelper
from BiosSet import BiosSet

FILTERS = {}

PLUGIN_ID = "plugin.games.xbmame"
PLUGIN_PATH = xbmc.translatePath("special://home/addons/%s" % PLUGIN_ID)
PLUGIN_DATA_PATH = xbmc.translatePath("special://profile/addon_data/%s" % PLUGIN_ID)

MEDIA_PATH = os.path.join(PLUGIN_PATH, "resources", "media")

SETTINGS_PLUGIN_ID = "%s%s" % (PLUGIN_ID, ".settings")
SETTINGS_PLUGIN_PATH = xbmc.translatePath("special://home/addons/%s" % SETTINGS_PLUGIN_ID)
SETTINGS_PLUGIN_DATA_PATH = xbmc.translatePath("special://profile/addon_data/%s" % SETTINGS_PLUGIN_ID)
SETTINGS_PLUGIN_XML_TEMPLATE = xbmc.translatePath(os.path.join(SETTINGS_PLUGIN_PATH, "resources", "settings.xml"))
SETTINGS_PLUGIN_XML_DOCUMENT = xbmc.translatePath(os.path.join(SETTINGS_PLUGIN_DATA_PATH, "settings.xml"))

__settings__ =  xbmcaddon.Addon(id=PLUGIN_ID)
__language__ =  __settings__.getLocalizedString

progress = xbmcgui.DialogProgress()
dialog = xbmcgui.Dialog()

class XBMame:

    _ICON_YEAR=os.path.join(MEDIA_PATH, "year.png")
    _ICON_BIOS=os.path.join(MEDIA_PATH, "bios.png")
    _ICON_MANUFACTURER=os.path.join(MEDIA_PATH, "manu.png")
    _ICON_NAME=os.path.join(MEDIA_PATH, "text.png")
    _ICON_HDD=os.path.join(MEDIA_PATH, "hdd.png")
    _ICON_ALL=os.path.join(MEDIA_PATH, "all.png")
    _ICON_SEARCH=os.path.join(MEDIA_PATH, "zoom-original.png")
    _FILTERS = ""

    HOME = 0
    REBUILD_DB = 1
    REBUILD_HAVEMISS = 2
    REBUILD_THUMBS = 3
    BROWSE_TYPE_YEAR = 4
    BROWSE_TYPE_BIOS = 5
    BROWSE_TYPE_MANUFACTURER = 6
    BROWSE_TYPE_NAME = 7
    BROWSE_TYPE_HDD = 8
    BROWSE_TYPE_ALL = 9
    BROWSE_SEARCH = 10
    GAME_SETTINGS = 11
    ACTION_EXECUTE = 12


    def __init__( self ):
        print "Arguments: %s" % sys.argv
        self._path = sys.argv[0]
        self._handle = sys.argv[1]
        try:
            self._params = dict([part.split('=') for part in sys.argv[ 2 ].replace("?", "").split('&')])
        except ValueError:
            self._params = {}
        if not os.path.exists(SETTINGS_PLUGIN_PATH):
            os.makedirs(os.path.join(SETTINGS_PLUGIN_PATH, "resources"))
            plugin = open(os.path.join(SETTINGS_PLUGIN_PATH, "addon.xml"), "w")
            plugin.write("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><addon id=\"plugin.games.xbmame.settings\" name=\"DIP Switches\"><extension point=\"xbmc.python.library\" library=\"default.py\" />  <extension point=\"xbmc.addon.metadata\"><platform>all</platform><summary></summary><description></description></extension></addon>")
            plugin.close()
            dialog.ok(__language__(30000), __language__(30704), __language__(30705))
            xbmc.executebuiltin("RestartApp")
        else:
            self._MAME_CONFIG_PATH = xbmc.translatePath(os.path.join(PLUGIN_DATA_PATH, "cfg"))
            if not os.path.exists(self._MAME_CONFIG_PATH): os.makedirs(self._MAME_CONFIG_PATH)
            self._MAME_CACHE_PATH = xbmc.translatePath(os.path.join(PLUGIN_DATA_PATH, "titles"))
            if not os.path.exists(self._MAME_CACHE_PATH): os.makedirs(self._MAME_CACHE_PATH)
            self._MAME_DATABASE_PATH = xbmc.translatePath(os.path.join(PLUGIN_DATA_PATH, "XBMame.db"))
            self._MAME_EXE_PATH = __settings__.getSetting("mame_exe_path").replace("\\", "/")
            self._MAME_ROM_PATH = __settings__.getSetting("mame_rom_path").replace("\\", "/")
            self._MAME_SAMPLES_PATH = __settings__.getSetting("mame_samples_path").replace("\\", "/")
            self._MAME_TITLES_PATH = __settings__.getSetting("mame_titles_path").replace("\\", "/")
            self._CACHE_TITLES = __settings__.getSetting("cache_titles")=="true"
            self._ONLINE_TITLES = __settings__.getSetting("online_titles")=="true"
            self._HIRES_TITLES = __settings__.getSetting("hires_titles")=="true"
            self._ROMSET_TITLES = __settings__.getSetting("romset_titles")=="true"
            if __settings__.getSetting("hide_clones")=="true":self._FILTERS +=" AND cloneof=''"
            if __settings__.getSetting("hide_nothave")=="true":self._FILTERS += " AND have"
            if __settings__.getSetting("hide_notworking")=="true":self._FILTERS += " AND isworking"
            if __settings__.getSetting("hide_impemul")=="true":self._FILTERS += " AND emul"
            if __settings__.getSetting("hide_impcolor")=="true":self._FILTERS += " AND color"
            if __settings__.getSetting("hide_graphics")=="true":self._FILTERS += " AND graphic"
            if __settings__.getSetting("hide_impsound")=="true":self._FILTERS += " AND sound"
            self._db = DBHelper(self._MAME_DATABASE_PATH)
            if self._db.isEmpty():
                self._gameDatabase()
            self._main()

    def _main(self):

        action = int("0%s" % self._getParam("action"))
        item = urllib.unquote(self._getParam("item"))

        if   action==self.REBUILD_DB:                self._gameDatabase()
        elif action==self.REBUILD_HAVEMISS:          self._haveList()
        elif action==self.REBUILD_THUMBS:            self._thumbNails()
        elif action==self.BROWSE_TYPE_YEAR:          self._browseYear(item)
        elif action==self.BROWSE_TYPE_BIOS:          self._browseBios(item)
        elif action==self.BROWSE_TYPE_MANUFACTURER:  self._browseManufacturer(item)
        elif action==self.BROWSE_TYPE_NAME:          self._browseName(item)
        elif action==self.BROWSE_TYPE_HDD:           self._gameCollection(hasdisk=1)
        elif action==self.BROWSE_TYPE_ALL:           self._gameCollection()
        elif action==self.BROWSE_SEARCH:             self._browseSearch(item)
        elif action==self.GAME_SETTINGS:             self._gameSettings(item)
        elif action==self.ACTION_EXECUTE:            self._runGame(item)
        else: self._browseHome()
                
    def _browseHome(self):
        listitem = xbmcgui.ListItem(__language__(30100), thumbnailImage=self._ICON_YEAR)
        xbmcplugin.addDirectoryItem(handle=int(self._handle), url="%s?action=%s"  % (self._path, self.BROWSE_TYPE_YEAR), listitem=listitem, isFolder=True)
        listitem = xbmcgui.ListItem(__language__(30101), thumbnailImage=self._ICON_BIOS)
        xbmcplugin.addDirectoryItem(handle=int(self._handle), url="%s?action=%s"  % (self._path, self.BROWSE_TYPE_BIOS), listitem=listitem, isFolder=True)
        listitem = xbmcgui.ListItem(__language__(30102), thumbnailImage=self._ICON_MANUFACTURER)
        xbmcplugin.addDirectoryItem(handle=int(self._handle), url="%s?action=%s"  % (self._path, self.BROWSE_TYPE_MANUFACTURER), listitem=listitem, isFolder=True)
        listitem = xbmcgui.ListItem(__language__(30103), thumbnailImage=self._ICON_NAME)
        xbmcplugin.addDirectoryItem(handle=int(self._handle), url="%s?action=%s"  % (self._path, self.BROWSE_TYPE_NAME), listitem=listitem, isFolder=True)
        listitem = xbmcgui.ListItem(__language__(30104), thumbnailImage=self._ICON_HDD)
        xbmcplugin.addDirectoryItem(handle=int(self._handle), url="%s?action=%s"  % (self._path, self.BROWSE_TYPE_HDD), listitem=listitem, isFolder=True),
        listitem = xbmcgui.ListItem(__language__(30105), thumbnailImage=self._ICON_ALL)
        xbmcplugin.addDirectoryItem(handle=int(self._handle), url="%s?action=%s"  % (self._path, self.BROWSE_TYPE_ALL), listitem=listitem, isFolder=True),
        listitem = xbmcgui.ListItem(__language__(30106), thumbnailImage=self._ICON_SEARCH)
        xbmcplugin.addDirectoryItem(handle=int(self._handle), url="%s?action=%s"  % (self._path, self.BROWSE_SEARCH), listitem=listitem, isFolder=True),
        xbmcplugin.endOfDirectory( handle=int( self._handle ), succeeded=True , cacheToDisc=False)
        xbmc.executebuiltin("Container.SetViewMode(500)")

    def _browseYear(self, year):
        if year:
            self._gameCollection(year=year)
        else:
            sql = "SELECT year FROM Games WHERE id>0 %s GROUP BY year ORDER BY year" % self._FILTERS
            years = self._db.getGames(sql, ())
            for year in years:
                listitem = xbmcgui.ListItem(year[0], thumbnailImage=self._ICON_YEAR)
                xbmcplugin.addDirectoryItem(handle=int(self._handle), url="%s?action=%s&item=%s"  % (self._path, self.BROWSE_TYPE_YEAR, urllib.quote(year[0])), listitem=listitem, isFolder=True)
            xbmcplugin.endOfDirectory( handle=int( self._handle ), succeeded=True , cacheToDisc=False)
            xbmc.executebuiltin("Container.SetViewMode(500)")

    def _browseBios(self, bios):
        if (bios):
            self._gameCollection(bios=bios)
        else:
            sql = "select gamename, romset from games where isbios and romset in (select romof from games where romof<>'' %s group by romof) ORDER BY gamename" % self._FILTERS
            bioses = self._db.getGames(sql, ())
            for bios in bioses:
                listitem = xbmcgui.ListItem(bios[0], thumbnailImage=self._ICON_BIOS)
                xbmcplugin.addDirectoryItem(handle=int(self._handle), url="%s?action=%s&item=%s"  % (self._path, self.BROWSE_TYPE_BIOS, urllib.quote(bios[1])), listitem=listitem, isFolder=True)
            xbmcplugin.endOfDirectory( handle=int( self._handle ), succeeded=True , cacheToDisc=False)
            xbmc.executebuiltin("Container.SetViewMode(500)")

    def _browseManufacturer(self, manufacturer):
        if (manufacturer):
            self._gameCollection(manufacturer=manufacturer)
        else:
            sql = "SELECT manufacturer FROM Games WHERE id>0 %s GROUP BY manufacturer ORDER BY manufacturer" % self._FILTERS
            manufacturers = self._db.getGames(sql, ())
            for manufacturer in manufacturers:
                listitem = xbmcgui.ListItem(manufacturer[0], thumbnailImage=self._ICON_MANUFACTURER)
                xbmcplugin.addDirectoryItem(handle=int(self._handle), url="%s?action=%s&item=%s"  % (self._path, self.BROWSE_TYPE_MANUFACTURER, urllib.quote(manufacturer[0])), listitem=listitem, isFolder=True)
            xbmcplugin.endOfDirectory( handle=int( self._handle ), succeeded=True , cacheToDisc=False)
            xbmc.executebuiltin("Container.SetViewMode(500)")

    def _browseName(self, letter):
        if (letter):
            if letter=="#":
                criteria = "("
                for i in range(10):
                    criteria += "gamename LIKE '" + str(i) + "%'"
                    if i < 9:
                        criteria += " OR " 
                criteria += ")"
            else:
                criteria = "gamename LIKE '" + letter + "%'"
            self._gameCollection(letter=criteria)
        else:
            folders = ['#', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
            for folder in folders:
                listitem = xbmcgui.ListItem(__language__( 30107 ) % folder.upper(), thumbnailImage=self._ICON_NAME)
                xbmcplugin.addDirectoryItem(handle=int(self._handle), url="%s?action=%s&item=%s"  % (self._path, self.BROWSE_TYPE_NAME, urllib.quote(folder)), listitem=listitem, isFolder=True)
            xbmcplugin.endOfDirectory( handle=int( self._handle ), succeeded=True , cacheToDisc=False)
            xbmc.executebuiltin("Container.SetViewMode(500)")

    def _browseSearch(self, item):
        if item:
            self._gameCollection(search=item)
        else:
            kb = xbmc.Keyboard("", "Type in the name of the game you're looking for", False)
            kb.doModal()
            if (kb.isConfirmed()):
                item = kb.getText()
                self._gameCollection(search=item)
            else:
                xbmcplugin.endOfDirectory( handle=int( self._handle ), succeeded=False , cacheToDisc=False)
                
    def _gameSettings(self, romset_id):
        game = GameItem(self._db, id=romset_id)

        rotate_by_name = {__language__(30916):0,__language__(30917):90,__language__(30918):180,__language__(30919):270}
        rotate_by_value = {0:__language__(30916),90:__language__(30917),180:__language__(30918),720:__language__(30919)}
        view_by_name = {__language__(30921):0,__language__(30922):1,__language__(30923):2,__language__(30924):3}
        view_by_value = {0:__language__(30921),1:__language__(30922),2:__language__(30923),2:__language__(30924)}
        bool_by_name = {"false":0, "true":1}
        bool_by_value = {0:"false", 1:"true"}

        settings_xml ="<settings>"

        settings_xml +="<category label=\"%s\">" % __language__(30914)
        settings_xml +="<setting label=\"%s\" type=\"labelenum\" id=\"display_rotate\" values=\"%s|%s|%s|%s\" default=\"%s\"/>" % \
            (__language__(30915), __language__(30916), __language__(30917), __language__(30918), __language__(30919), view_by_value[game.view])
        settings_xml +="<setting label=\"%s\" type=\"labelenum\" id=\"display_view\" values=\"%s|%s|%s|%s\" default=\"%s\"/>" % \
            (__language__(30920), __language__(30921), __language__(30922), __language__(30923), __language__(30924), rotate_by_value[game.rotate])
        settings_xml +="<setting label=\"%s\" type=\"bool\" id=\"display_backdrops\" default=\"%s\"/>" % (__language__(30925), bool_by_value[game.backdrops])
        settings_xml +="<setting label=\"%s\" type=\"bool\" id=\"display_overlays\" default=\"%s\"/>" % (__language__(30926), bool_by_value[game.overlays])
        settings_xml +="<setting label=\"%s\" type=\"bool\" id=\"display_bezels\" default=\"%s\"/>" % (__language__(30927), bool_by_value[game.bezels])
        settings_xml +="<setting label=\"%s\" type=\"bool\" id=\"display_zoom\" default=\"%s\"/>" % (__language__(30928), bool_by_value[game.zoom])
        settings_xml +="</category>"
        switches = self._db.getList("Dipswitches", ["id"], {"romset_id=":romset_id})

        if len(game.biossets):
            values = ""
            for biosset in game.biossets:
                if game.biosset==biosset.name:default = biosset.description
                values+="|%s" % biosset.description
            settings_xml +="<category label=\"%s\">" % __language__(30937)
            settings_xml +="<setting label=\"%s\" type=\"labelenum\" id=\"biosset\" values=\"%s\" default=\"%s\"/>" % \
                (__language__(30938), values[1:], default)
            settings_xml +="</category>"

        settings_xml +="<category label=\"%s\">" % __language__(30801)
        for switch in switches:
            switch = DIPSwitch(self._db, id=switch["id"])
            values = ""
            for value in switch.values_by_value:
                values+="|%s" % value
            if values=="|On|Off" or values=="|Yes|No":
                if switch.values_by_name[str(switch.value)]=="On" or switch.values_by_name[str(switch.value)]=="Yes":
                    default="true"
                else:
                    default="false"
                settings_xml += "<setting label=\"%s\" type=\"bool\" id=\"S%s\" default=\"%s\"/>" % (switch.name, switch.id, default)
            else:
                settings_xml += "<setting label=\"%s\" type=\"labelenum\" id=\"S%s\" default=\"%s\"  values=\"%s\"/>" % (switch.name, switch.id, switch.values_by_name[str(switch.value)], values[1:])
        settings_xml+="</category>"
        settings_xml+="</settings>"
        settings_xml_file = open(SETTINGS_PLUGIN_XML_TEMPLATE, "w")
        settings_xml_file.write(settings_xml.encode('utf8'))
        settings_xml_file.close()
        __fakesettings__ = xbmcaddon.Addon(id=SETTINGS_PLUGIN_ID)
        __fakesettings__.openSettings()
        if os.path.exists(SETTINGS_PLUGIN_XML_DOCUMENT):
            src = open(SETTINGS_PLUGIN_XML_DOCUMENT, "r")
            xml = src.read()
            src.close()
            xml = re.sub("\r|\t|\n", "", xml)
            settings = XMLHelper().getNodes(xml, "setting")
            for setting in settings:
                if XMLHelper().getAttribute(setting, "setting", "id")=="display_view":
                    game.view = view_by_name[XMLHelper().getAttribute(setting, "setting", "value")]
                elif XMLHelper().getAttribute(setting, "setting", "id")=="display_rotate":
                    game.rotate = rotate_by_name[XMLHelper().getAttribute(setting, "setting", "value")]
                elif XMLHelper().getAttribute(setting, "setting", "id")=="display_backdrops":
                    game.backdrops = bool_by_name[XMLHelper().getAttribute(setting, "setting", "value")]
                elif XMLHelper().getAttribute(setting, "setting", "id")=="display_overlays":
                    game.overlays = bool_by_name[XMLHelper().getAttribute(setting, "setting", "value")]
                elif XMLHelper().getAttribute(setting, "setting", "id")=="display_bezels":
                    game.bezels = bool_by_name[XMLHelper().getAttribute(setting, "setting", "value")]
                elif XMLHelper().getAttribute(setting, "setting", "id")=="display_zoom":
                    game.zoom = bool_by_name[XMLHelper().getAttribute(setting, "setting", "value")]
                elif XMLHelper().getAttribute(setting, "setting", "id")=="biosset":
                    game.biosset = BiosSet(self._db).getByDescription(XMLHelper().getAttribute(setting, "setting", "value")).name
                else:
                    switch = DIPSwitch(self._db, id=XMLHelper().getAttribute(setting, "setting", "id")[1:])
                    value = XMLHelper().getAttribute(setting, "setting", "value")
                    if value=="true":
                        try:
                            switch.value = switch.values_by_value["On"]
                        except KeyError:
                         switch.value = switch.values_by_value["Yes"]
                    elif value=="false":
                        try:
                            switch.value = switch.values_by_value["Off"]
                        except KeyError:
                            switch.value = switch.values_by_value["No"]
                    else:
                        switch.value=switch.values_by_value[XMLHelper().getAttribute(setting, "setting", "value")]
                    switch.writeDB()
                game.writeDB()
                self._db.commit()
            os.remove(SETTINGS_PLUGIN_XML_DOCUMENT)
        os.remove(SETTINGS_PLUGIN_XML_TEMPLATE)
         
    def xpPath(self, path):
        return "\"%s\"" % path.replace("\\", "/")

    def _runGame(self, romset):
        game = GameItem(self._db, id=romset)
        if game.have:
            config_path = self.xpPath(self._MAME_CONFIG_PATH)
            media_path = self.xpPath(MEDIA_PATH)
            rom_path = self.xpPath(self._MAME_ROM_PATH)
            sample_path = self.xpPath(self._MAME_SAMPLES_PATH)
            params = {}
            params ["-cfg_directory"] = config_path
            params ["-rompath"] = rom_path
            params ["-artpath"] = media_path
            params ["-samplepath"] = sample_path
            params ["-cheat"] = ""
            params ["-switchres"] = ""
            params ["-video"] = "d3d"
            params ["-d3dversion"] = "9"
            params ["-filter"] = ""
            params ["-multithreading"] = ""
            params ["-waitvsync"] = ""
            params ["-skip_gameinfo"] = ""
#            params ["-resolution"] = "1280x800@60"
            params ["-effect"] = "Scanlines75Dx4_j4"
            if self._MAME_SAMPLES_PATH:
                params ["-samplepath"] = sample_path
            if game.biosset:
                params ["-bios"] = game.biosset
            cfgxml = "<?xml version=\"1.0\"?><mameconfig version=\"10\"><system name=\"%s\"><input>" % game.romset
            for switch in game.dipswitches:
                switch = DIPSwitch(self._db, switch[0])
                cfgxml+= "<port tag=\"%s\" type=\"DIPSWITCH\" mask=\"%s\" defvalue=\"%s\" value=\"%s\" />" % (switch.tag,switch.mask,switch.defvalue,switch.value)
            cfgxml+="</input><video>"
            cfgxml+="<target index=\"0\" view=\"%s\" rotate=\"%s\" backdrops=\"%s\" overlays=\"%s\" bezels=\"%s\" zoom=\"%s\" />" % (game.view, game.rotate, game.backdrops, game.overlays, game.bezels, game.zoom)
            cfgxml+="</video></system></mameconfig>"
            cfg = open(os.path.join(self._MAME_CONFIG_PATH, "%s.cfg" % game.romset), "w")
            cfg.write(cfgxml)
            cfg.close()
            command = self._MAME_EXE_PATH
            for key in params.keys():
                command += " %s %s " % (key, params[key])
            command+=game.romset
            command = "System.Exec(\"%s\")" % command.replace("\"", "\\\"")
            xbmc.executebuiltin(command)
        else:
            if dialog.yesno(__language__(30701), __language__(30702), __language__(30703)):
                xbmc.executebuiltin("XBMC.RunPlugin(%s)" % "plugin://%s?action=%s" % (PLUGIN_ID, self.REBUILD_DB))
        
    def _getParam(self, param):
        try:
            return self._params[param]
        except KeyError:
            return ""

    def _gameCollection(self, year="", bios="", manufacturer="", letter="", search="", hasdisk=0):
        progress.create(__language__(30600))

        sql = "SELECT id, gamename, gamecomment, thumb, romset, hasdips FROM Games WHERE NOT isbios %s %s ORDER BY gamename"
        
        criteria=""
        values=""
        if year:
            criteria="AND year=?"
            values = (year,)
        if bios:
            criteria="AND romof=?"
            values = (bios,)
        if hasdisk:
            criteria="AND hasdisk"
            values = ""
        if manufacturer:
            criteria="AND manufacturer=?"
            values = (manufacturer,)
        if letter:
            criteria="AND %s" % letter
            values = ()
        if search:
            criteria="AND gamename LIKE '%" + search + "%'"
            values = ()

        sql =  "SELECT id, gamename, gamecomment, thumb, romset, hasdips FROM Games WHERE NOT isbios %s %s ORDER BY gamename" % (criteria, self._FILTERS)
        games = self._db.getGames(sql, values)
        count = len(games)
        index = 0
        for game in games:
            if game[3]:
                if self._CACHE_TITLES or self._ONLINE_TITLES:thumb=os.path.join(self._MAME_CACHE_PATH, "%s.png" % game[4])
                else:thumb=os.path.join(self._MAME_TITLES_PATH, "%s.png" % game[4])
            else:thumb=""
            if game[2]!="":
                label="%s (%s)" % (game[1], game[2])
            else:
                label=game[1]
            progress.update(int((float(index)/float(count)) * 100), __language__(30601), __language__(30602) % label, __language__(30603) % (index, count))
            if progress.iscanceled(): break
            index += 1
            listitem = xbmcgui.ListItem(label=label, thumbnailImage=os.path.join(self._MAME_TITLES_PATH, thumb))
            listitem.addContextMenuItems([(__language__( 30800 ), "XBMC.RunPlugin(%s?action=%s&item=%s)" % (self._path, self.GAME_SETTINGS, game[0]),)])
            xbmcplugin.addDirectoryItem(handle=0, url="%s?action=%s&item=%s"  % (self._path, self.ACTION_EXECUTE, game[0]), listitem=listitem, isFolder=False)
        progress.close()
        xbmcplugin.endOfDirectory( handle=int( self._handle ), succeeded=True , cacheToDisc=False)
        xbmc.executebuiltin("Container.SetViewMode(500)")

    def _gameDatabase(self):
        if len(self._db.runQuery("SELECT * FROM sqlite_master WHERE name=?", ("Games",))):
            self._db.execute("DROP TABLE Games")
        if len(self._db.runQuery("SELECT * FROM sqlite_master WHERE name=?", ("BiosSets",))):
            self._db.execute("DROP TABLE BiosSets")
        if len(self._db.runQuery("SELECT * FROM sqlite_master WHERE name=?", ("Dipswitches",))):
            self._db.execute("DROP TABLE Dipswitches")
        if len(self._db.runQuery("SELECT * FROM sqlite_master WHERE name=?", ("DipswitchesValues",))):
            self._db.execute("DROP TABLE DipswitchesValues")
        self._db.execute("CREATE TABLE Games (id INTEGER PRIMARY KEY, romset TEXT, cloneof TEXT, romof TEXT, biosset TEXT, driver TEXT, gamename TEXT, gamecomment TEXT, manufacturer TEXT, year TEXT, isbios BOOLEAN, hasdisk BOOLEAN, isworking BOOLEAN, emul BOOLEAN, color BOOLEAN, graphic BOOLEAN, sound BOOLEAN, hasdips BOOLEAN, view INTEGER, rotate INTEGER, backdrops BOOLEAN, overlays BOOLEAN, bezels BOOLEAN, zoom BOOLEAN, have BOOLEAN, thumb BOOLEAN)")
        self._db.execute("CREATE TABLE BiosSets (id INTEGER PRIMARY KEY, romset_id INTEGER, name TEXT, description TEXT)")
        self._db.execute("CREATE TABLE Dipswitches (id INTEGER PRIMARY KEY, romset_id integer, name TEXT, tag TEXT, mask INTEGER, defvalue INTEGER, value INTEGER)")
        self._db.execute("CREATE TABLE DipswitchesValues (id INTEGER PRIMARY KEY, dipswitch_id INTEGER, name TEXT, value TEXT)")
        self._db.commit()
        progress.create(__language__(30000))
        progress.update(0, __language__(30604))
        xml = os.popen("\"%s\" -listxml" % self._MAME_EXE_PATH).read()
        progress.update(50, __language__(30604), __language__(30605))
        if not progress.iscanceled():
            xml = re.sub("\r|\t|\n|<rom.*?/>", "", xml)
            progress.update(75, __language__(30604), __language__(30605), __language__(30606))
        if not progress.iscanceled():
            files = {}
            tmpfiles = os.listdir(self._MAME_ROM_PATH)
            for file in tmpfiles:files[file.replace(".zip", "").replace(".rar", "").replace(".7z","")] = 1
            items = re.findall("(<game.*?>.*?</game>)", xml, re.M)
            progress.close()
            progress.create(__language__(30607))
            count = len(items)
            index = 0
            for item in items:
                if progress.iscanceled(): break
                index += 1
                game = GameItem(self._db, xml=item)
                try:
                    if files[str(game.romset)]:game.have = 1
                except KeyError:
                    game.have = 0
                game.writeDB()
                progress.update(int((float(index)/float(count)) * 100), __language__(30608), __language__(30609) % game.gamename, __language__(30610) % (index, count))
            self._db.commit()
        progress.close()
#        self._haveList()
        self._thumbNails()

    def _haveList(self):
        progress.create(__language__(30611))
        files = os.listdir(self._MAME_ROM_PATH)
        count = len(files)
        index = 0
        for file in files:
            if progress.iscanceled(): break
            index += 1
            romset = file.replace(".zip", "").replace(".rar", "").replace(".7z","")
            progress.update(int((float(index)/float(count)) * 100), __language__(30612), __language__(30613) % romset, __language__(30614) % (index, count))
            self._db.execute("UPDATE Games SET have=1 WHERE romset=?", (romset,))
        self._db.commit()
        progress.close()

    def _thumbNails(self):
        if self._MAME_TITLES_PATH or self._ONLINE_TITLES:
            progress.create(__language__(30615))
            if self._ROMSET_TITLES:
                files = self._db.runQuery("SELECT romset FROM Games WHERE have")
            else:
                files = self._db.runQuery("SELECT romset FROM Games")
            count = len(files)
            index = 0
            for file in files:
                romset = file["romset"]
                progress.update(int((float(index)/float(count)) * 100), __language__(30616), __language__(30617) % romset, __language__(30618) % (index, count))
                if progress.iscanceled(): break
                index += 1
                if self._MAME_TITLES_PATH:
                    filename = os.path.join(self._MAME_TITLES_PATH, "%s.png" % romset)
                if self._CACHE_TITLES:
                    cachefile = os.path.join(self._MAME_CACHE_PATH, "%s.png" % romset)
                    if not os.path.exists(cachefile):
                        if os.path.exists(filename):
                            shutil.copyfile(filename, cachefile)
                            filename = cachefile
                if self._ONLINE_TITLES:
                    filename = os.path.join(self._MAME_CACHE_PATH, "%s.png" % romset)
                    if self._HIRES_TITLES:res="hi"
                    else:res="lo"
                    if not os.path.exists(filename):
                        urllib.urlcleanup()
                        urllib.urlretrieve("https://www.otaku-realm.net/xbmame/%s/%s.png" % (res, romset), filename)
                if os.path.exists(filename): self._db.execute("UPDATE Games SET thumb=1 WHERE romset=?", (romset,))
            self._db.commit()
            progress.close()

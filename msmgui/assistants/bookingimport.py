#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    This file is part of MSM.

    MSM is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    MSM is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with MSM.  If not, see <http://www.gnu.org/licenses/>.
"""
import logging
logger = logging.getLogger( __name__ )
import threading
from gi.repository import Gtk, GLib
from core.pluginmanager import PluginManagerSingleton as pluginmanager, plugintypes
from core.database import Magazine, Issue
from core.bookingimport import BookingImporter
from msmgui.assistants.genericimport import GenericImportAssistant, GenericImportSettings


class GuiLogHandler(logging.Handler):
    def __init__(self, gui_label, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gui_label = gui_label

    def emit(self, record):
        self.format(record)
        GLib.idle_add(self._gui_label.set_text, record.message)


class GuiImporter(threading.Thread):
    def __init__(self, importer, gui_objects):
        threading.Thread.__init__(self)
        self._importer = importer
        self._gui_spinner, self._gui_label, \
            self._gui_assistant, self._gui_page = gui_objects

    def run(self):
        handler = GuiLogHandler(self._gui_label, level=logging.INFO)
        guilogger = self._importer.logger
        guilogger.addHandler(handler)
        GLib.idle_add(self._gui_spinner.start)
        self._importer.start()
        self._importer.join()
        GLib.idle_add(self._gui_spinner.stop)
        GLib.idle_add(self._gui_assistant.set_page_complete, self._gui_page,
                      True)
        guilogger.removeHandler(handler)


class FileFormatPluginWrapper(Gtk.FileFilter):
    def __init__(self, plugin_info):
        super().__init__()
        self.plugin_info = plugin_info
        pattern = "*.{}".format(plugin_info.plugin_object.FILE_EXT)
        self.set_name("{name} ({pattern})".format(name=plugin_info.description,
                                                  pattern=pattern))
        self.add_pattern(pattern)


class BookingImportAssistant(GenericImportAssistant):
    def __init__(self):
        plugins = pluginmanager.getPluginsOfCategory(
            plugintypes.BookingImporter.CATEGORY)
        filefilters = [FileFormatPluginWrapper(plugin) for plugin in plugins]

        super().__init__(filefilters=filefilters)
        widget = BookingImportSettings( session=self.session )
        self.set_settingswidget( widget )
        # Customize labels
        self.begin_label = "Willkommen beim Import-Assistenten für Bankumsätze."
        self.confirm_label = "Der Importvorgang kann nun gestartet werden."
        self.summary_label = "Die Datensätze wurden erfolgreich importiert."
        page = self._assistant.get_nth_page(GenericImportAssistant.Page.Settings)
        self._assistant.set_page_complete(page, True)

    def confirm( self, settingswidget, input_file ):
        self.confirm_label = ""

    def start_import( self, settingswidget, gui_objects, input_file ):
        """
        Starts the import thread.
        Arguments:
            settingswidget:
                the widget that stores export settings
            gui_objects:
                a tuple containing spinner, label, assistant, page (in that order)
            input_file:
                a string pointing to the output file
        """
        # Start the Thread
        importformat = self.input_filter.plugin_info.plugin_object
        importer = BookingImporter(input_file, importformat)
        watcher = GuiImporter(importer, gui_objects)
        watcher.start()


class BookingImportSettings(GenericImportSettings):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add(Gtk.Label("Hier gibt es nichts zu tun."))
        self.emit("changed", True)

    def get_settings(self):
        return None

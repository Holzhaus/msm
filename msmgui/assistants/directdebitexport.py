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
from core.directdebitexport import DirectDebitExporter
from msmgui.assistants.genericexport import GenericExportAssistant, GenericExportSettings


class GuiLogHandler(logging.Handler):
    def __init__(self, gui_label, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gui_label = gui_label

    def emit(self, record):
        self.format(record)
        GLib.idle_add(self._gui_label.set_text, record.message)


class GuiExporter(threading.Thread):
    def __init__(self, exporter, gui_objects):
        threading.Thread.__init__(self)
        self._exporter = exporter
        self._gui_spinner, self._gui_label, \
            self._gui_assistant, self._gui_page = gui_objects

    def run(self):
        handler = GuiLogHandler(self._gui_label, level=logging.INFO)
        guilogger = self._exporter.logger
        guilogger.addHandler(handler)
        GLib.idle_add(self._gui_spinner.start)
        self._exporter.start()
        self._exporter.join()
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


class DirectDebitExportAssistant(GenericExportAssistant):
    def __init__(self):
        plugins = pluginmanager.getPluginsOfCategory(
            plugintypes.DirectDebitExportFormatter.CATEGORY)
        filefilters = [FileFormatPluginWrapper(plugin) for plugin in plugins]

        super().__init__(filefilters=filefilters)
        widget = DirectDebitExportSettings( session=self.session )
        self.set_settingswidget( widget )
        # Customize labels
        self.begin_label = "Willkommen beim Export-Assistenten für Lastschriften."
        self.confirm_label = "Der Exportvorgang kann nun gestartet werden."
        self.summary_label = "Die Datensätze wurden erfolgreich exportiert."
        page = self._assistant.get_nth_page(GenericExportAssistant.Page.Settings)
        self._assistant.set_page_complete(page, True)

    def confirm( self, settingswidget, output_file ):
        self.confirm_label = "Es werden die Lastschriftdaten von allen unbezahlten Rechnungen mit der Zahlungsart <b>Lastschrift</b> exportiert"

    def export( self, settingswidget, gui_objects, output_file ):
        """
        Starts the export thread.
        Arguments:
            settingswidget:
                the widget that stores export settings
            gui_objects:
                a tuple containing spinner, label, assistant, page (in that order)
            output_file:
                a string pointing to the output file
        """
        # Remove stuff from the session so that it can be re-added in the thread
        self._session.close()
        # Start the Thread
        formatter = self.output_filter.plugin_info.plugin_object
        exporter = DirectDebitExporter(output_file, formatter)
        watcher = GuiExporter(exporter, gui_objects)
        watcher.start()

class DirectDebitExportSettings( GenericExportSettings ):
    def __init__( self, session=None ):
        super().__init__( session=session )
        self.add(Gtk.Label("Hier gibt es nichts zu tun."))
        self.emit("changed", True)

    def get_settings(self):
        return None
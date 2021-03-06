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
import datetime
import dateutil.parser
from gi.repository import Gtk, GLib
from core import paths
from core.pluginmanager import PluginManagerSingleton as pluginmanager, plugintypes
from core.database import Magazine, Issue
from core.contractexport import ContractExporter
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


class ContractExportAssistant(GenericExportAssistant):
    def __init__(self):
        plugins = pluginmanager.getPluginsOfCategory(
            plugintypes.ContractExportFormatter.CATEGORY)
        filefilters = [FileFormatPluginWrapper(plugin) for plugin in plugins]

        super().__init__(filefilters=filefilters)
        widget = ContractExportSettings( session=self.session )
        self.set_settingswidget( widget )
        # Customize labels
        self.begin_label = "Willkommen beim vertragsbasierten Export-Assistenten."
        self.confirm_label = "Der Exportvorgang kann nun gestartet werden."
        self.summary_label = "Die Datensätze wurden erfolgreich exportiert."

    def confirm( self, settingswidget, output_file ):
        magazine, issue, date = settingswidget.get_settings()
        self.confirm_label = ""
        if issue is not None:
            self.confirm_label = "Es werden Vertragsdaten der Kunden, die <b>Ausgabe {}-{}</b> (vom {}) der Zeitschrift <b>{}</b> erhalten haben exportiert.".format( issue.year, issue.number, issue.date.strftime("%x"), issue.magazine.name )
        elif magazine is not None:
            self.confirm_label = "Es werden Vertragsdaten der Kunden, die am <b>{}</b> die Zeitschrift <b>{}</b> abonniert haben oder hatten, exportiert.".format( date.strftime("%x"), magazine.name )
        else:
            if date is not None:
                self.confirm_label = "Es werden Vertragsdaten der Kunden, die am <b>{}</b> eine Zeitschrift abonniert haben oder hatten, exportiert.".format( date.strftime("%x") )
            else:
                self.confirm_label = "Es werden Vertragsdaten aller Kunden exportiert."
        if not self.confirm_label:
            raise RuntimeError( "These settings look strange." )

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
        unmerged_magazine, unmerged_issue, date = settingswidget.get_settings()
        magazine = self._session.merge( unmerged_magazine ) if unmerged_magazine is not None else None
        issue = self._session.merge( unmerged_issue ) if unmerged_issue is not None else None
        # Remove stuff from the session so that it can be re-added in the thread
        self._session.close()
        # Start the Thread
        formatter = self.output_filter.plugin_info.plugin_object
        exporter = ContractExporter(output_file, formatter, magazine, issue, date)
        watcher = GuiExporter(exporter, gui_objects)
        watcher.start()
class ContractExportSettings( GenericExportSettings ):
    def __init__( self, session=None ):
        super().__init__( session=session )
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( paths.data("ui","widgets","contractexportsettings.glade" ))
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        self.builder.connect_signals( self )
    def refresh( self ):
        selected_magazine = self.get_magazine()
        model = self.builder.get_object( "magazine_liststore" )
        model.clear()
        for magazine in Magazine.get_all( session=self.session ):
            treeiter = model.append( [magazine, magazine.name] )
            if selected_magazine is not None and magazine.id == selected_magazine.id:
                self.builder.get_object( "mag_combobox" ).set_active_iter( treeiter )
        if not self.get_magazine() and len( model ) > 0:
            self.builder.get_object( "mag_combobox" ).set_active( 0 )
        alldate_entry = self.builder.get_object( "alldate_entry" )
        if not alldate_entry.get_text().strip():
            alldate_entry.set_text( datetime.date.today().strftime("%x"))
        magdate_entry = self.builder.get_object( "magdate_entry" )
        if not magdate_entry.get_text().strip():
            magdate_entry.set_text( datetime.date.today().strftime("%x"))
    def get_magazine( self ):
        combo = self.builder.get_object( "mag_combobox" )
        model = combo.get_model()
        treeiter = combo.get_active_iter()
        if model is not None and treeiter is not None:
            magazine = model[treeiter][0]
            if isinstance( magazine, Magazine ):
                return magazine
        return None
    def get_issue( self ):
        combo = self.builder.get_object( "magissue_combobox" )
        model = combo.get_model()
        treeiter = combo.get_active_iter()
        if model is not None and treeiter is not None:
            issue = model[treeiter][0]
            if isinstance( issue, Issue ):
                return issue
        return None
    def get_settings( self ):
        """
        Gets settings from widget.
        Returns:
            A tuple containing values for magazine, issue, date (in that order) or None if settings are not complete

        """
        if self.builder.get_object( "all_radiobutton" ).get_active():
            return ( None, None, None )
        elif self.builder.get_object( "allcurrent_radiobutton" ).get_active():
            return ( None, None, datetime.date.today() )
        elif self.builder.get_object( "alldate_radiobutton" ).get_active():
            text = self.builder.get_object( "alldate_entry" ).get_text().strip()
            if text:
                try:
                    date = dateutil.parser.parse( text, dayfirst=True )
                except Exception as error:
                    logger.warning( 'Invalid date entered: %s (%r)', text, error )
                else:
                    date = date.date()
                    return ( None, None, date )
        else:
            magazine = self.get_magazine()
            if magazine is not None:
                if self.builder.get_object( "magcurrent_radiobutton" ).get_active():
                    return ( magazine, None, datetime.date.today() )
                elif self.builder.get_object( "magdate_radiobutton" ).get_active():
                    text = self.builder.get_object( "magdate_entry" ).get_text().strip()
                    if text:
                        try:
                            date = dateutil.parser.parse( text, dayfirst=True )
                        except Exception as error:
                            logger.warning( 'Invalid date entered: %s (%r)', text, error )
                        else:
                            date = date.date()
                            return ( magazine, None, date )
                elif self.builder.get_object( "magissue_radiobutton" ).get_active():
                    issue = self.get_issue()
                    return ( magazine, issue, None )
        return None
    def radiobutton_toggled_cb( self, radiobutton ):
        self.emit( "changed", False if self.get_settings() is None else True )
    def alldate_entry_changed_cb( self, entry ):
        self.emit( "changed", False if self.get_settings() is None else True )
    def magdate_entry_changed_cb( self, entry ):
        self.emit( "changed", False if self.get_settings() is None else True )
    def mag_combobox_changed_cb( self, combo ):
        selected_issue = self.get_issue()
        model = self.builder.get_object( "issue_liststore" )
        model.clear()
        magazine = self.get_magazine()
        if magazine is not None:
            for issue in magazine.issues:
                treeiter = model.append( [issue, "{}/{}".format( issue.year, issue.number )] )
                if selected_issue is not None and issue.id == selected_issue.id:
                    self.builder.get_object( "magissue_combobox" ).set_active_iter( treeiter )
        if not self.get_issue() and len( model ) > 0:
            self.builder.get_object( "magissue_combobox" ).set_active( 0 )
        self.emit( "changed", False if self.get_settings() is None else True )
    def magissue_combobox_changed_cb( self, combo ):
        self.emit( "changed", False if self.get_settings() is None else True )

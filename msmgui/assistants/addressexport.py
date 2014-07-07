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
import locale
import datetime
import dateutil.parser
from gi.repository import Gtk, GLib
from core.database import Magazine, Issue
from core.lib.addressexport import AddressExporterCSV
from msmgui.assistants.genericexport import GenericExportAssistant, GenericExportSettings
class AddressExporter( AddressExporterCSV ):
    def __init__( self, output_file, magazine, issue, date, gui_objects, update_step=25 ):
        super().__init__( output_file, magazine, issue, date )
        self._gui_spinner, self._gui_label, self._gui_assistant, self._gui_page = gui_objects
        self._update_step = update_step
    def on_init_start( self ):
        text = "Hole Adressen aus Datenbank..."
        GLib.idle_add( self._gui_start )
        GLib.idle_add( self._gui_update, text )
    def on_init_finished( self, num_addresses ):
        text = "1 Adresse geholt!" if num_addresses == 1 else "{} Adressen geholt!".format( num_addresses )
        GLib.idle_add( self._gui_update, text )
    def on_export_start( self, num_addresses ):
        text = "Exportiere 1 Adresse..." if num_addresses == 1 else "Exportiere {} Adressen...".format( num_addresses )
        GLib.idle_add( self._gui_update, text )
    def on_export_output( self, work_done, work_started ):
        if self._update_step is not None:
            if not ( work_done % self._update_step == 0 or work_done == 1 ):
                return
        text = "Exportiere Adressen... ({}/{})".format( work_done, work_started )
        GLib.idle_add( self._gui_update, text )
    def on_export_finished( self, work_done ):
        text = "Fertig! 1 Adresse exportiert.".format( work_done ) if work_done == 1 else "Fertig! {} Adressen exportiert.".format( work_done )
        GLib.idle_add( self._gui_update, text )
        GLib.idle_add( self._gui_stop )
    def _gui_start( self ):
        self._gui_spinner.start()
    def _gui_update( self, text ):
        self._gui_label.set_text( text )
    def _gui_stop( self ):
        self._gui_spinner.stop()
        self._gui_assistant.set_page_complete( self._gui_page, True )
class AddressExportAssistant( GenericExportAssistant ):
    def __init__( self ):
        filter_csv = Gtk.FileFilter()
        filter_csv.set_name( "CSV-Dateien" )
        filter_csv.add_pattern( "*.csv" )
        super().__init__( filefilters=[filter_csv] )
        widget = AddressExportSettings( session=self.session )
        self.set_settingswidget( widget )
        # Customize labels
        self.begin_label = "Willkommen beim Adressexport-Assistenten."
        self.confirm_label = "Der Exportvorgang kann nun gestartet werden."
        self.summary_label = "Die Adressen wurden erfolgreich exportiert."
    def confirm( self, settingswidget, output_file ):
        magazine, issue, date = settingswidget.get_settings()
        self.confirm_label = ""
        if issue is not None:
            self.confirm_label = "Es werden die <b>Versandadressen</b> der Empfänger der <b>Ausgabe {}-{}</b> (vom {}) der Zeitschrift <b>{}</b> exportiert.".format( issue.year, issue.number, issue.date.strftime( locale.nl_langinfo( locale.D_FMT ) ), issue.magazine.name )
        elif magazine is not None:
            self.confirm_label = "Es werden die <b>Versandadressen</b> der Kunden, die am <b>{}</b> die Zeitschrift <b>{}</b> abonniert haben oder hatten, exportiert.".format( date.strftime( locale.nl_langinfo( locale.D_FMT ) ), magazine.name )
        else:
            if date is not None:
                self.confirm_label = "Es werden die <b>Versandadressen</b> der Kunden, die am <b>{}</b> eine Zeitschrift abonniert haben oder hatten, exportiert.".format( date.strftime( locale.nl_langinfo( locale.D_FMT ) ) )
            else:
                self.confirm_label = "Es werden die <b>Versandadressen aller Kunden</b> exportiert."
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
        watcher = AddressExporter( output_file, magazine, issue, date, gui_objects )
        watcher.start()
class AddressExportSettings( GenericExportSettings ):
    def __init__( self, session=None ):
        super().__init__( session=session )
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/widgets/addressexportsettings.glade" )
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
            alldate_entry.set_text( datetime.date.today().strftime( locale.nl_langinfo( locale.D_FMT ) ) )
        magdate_entry = self.builder.get_object( "magdate_entry" )
        if not magdate_entry.get_text().strip():
            magdate_entry.set_text( datetime.date.today().strftime( locale.nl_langinfo( locale.D_FMT ) ) )
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

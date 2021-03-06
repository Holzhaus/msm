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
from gi.repository import Gtk, GObject
from msmgui.widgets.base import ScopedDatabaseObject
from core import paths
class GenericExportAssistant( GObject.GObject, ScopedDatabaseObject ):
    class Page:
        """
        Enumeration of LetterExportAssistants pages.
        """
        Intro, Settings, Confirm, Progress, Summary = range( 5 )
    @property
    def begin_label( self ):
        return self.builder.get_object( 'begin_label' ).get_label()
    @begin_label.setter
    def begin_label( self, value ):
        self.builder.get_object( 'begin_label' ).set_markup( value )
    @property
    def confirm_label( self ):
        return self.builder.get_object( 'confirm_label' ).get_label()
    @confirm_label.setter
    def confirm_label( self, value ):
        self.builder.get_object( 'confirm_label' ).set_markup( value )
    @property
    def summary_label( self ):
        return self.builder.get_object( 'summary_label' ).get_label()
    @summary_label.setter
    def summary_label( self, value ):
        self.builder.get_object( 'summary_label' ).set_markup( value )
    @property
    def output_file( self ):
        return self.builder.get_object( 'outputfile_entry' ).get_text()
    @output_file.setter
    def output_file( self, value ):
        self.builder.get_object( 'outputfile_entry' ).set_text( value )
    def __init__( self, exportsettingswidget=None, filefilters=[] ):
        ScopedDatabaseObject.__init__( self )
        GObject.GObject.__init__( self )
        self.filefilters = filefilters.copy()
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( paths.data("ui","assistants","genericexport.glade" ))
        self._assistant = self.builder.get_object( "content" )
        # self._assistant.set_modal( True )
        self._assistant.set_forward_page_func( self.page_forward_func )
        if exportsettingswidget is not None:
            self.set_settingswidget( exportsettingswidget )
        # Connect Signals
        self.builder.connect_signals( self )
    def set_settingswidget( self, widget ):
        settingsbox = self.builder.get_object( "exportsettingsbox" )
        for widget in settingsbox.get_children():
            settingsbox.remove( widget )
        self._exportsettings = widget
        settingsbox.pack_start( self._exportsettings, True, True, 0 )
        self._exportsettings.connect( "changed", self.exportsettings_changed_cb )
    def set_parent( self, parent ):
        """
        Sets the assistants parent window. Internally calls Gtk.Assistant.set_transient_for(parent).
        Arguments:
            parent:
                the assistant's parent window
        """
        self._assistant.set_transient_for( parent )
    def show( self ):
        """
        Shows the LetterExportAssistant.
        """
        self.builder.get_object( "content" ).show_all()
    def confirm( self, settingswidget, output_file ):
        """
        If overridden, this method can customize the confirmation screen.
        Arguments:
            settingswidget:
                the widget that stores export settings
            output_file:
                a string pointing to the output file
        """
        pass
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
        raise NotImplementedError
    def page_forward_func( self, page ):
        """
        Function called when the forward button is pressed.
        Arguments:
            page:
                integer index of the current page
        returns:
            integer index of the next page to display
        """
        return page + 1
    # Page prepare funcs
    def page_confirm_prepare_func( self, assistant, page ):
        """
        Calls the confirm function.
        Arguments:
            assistant:
                the calling Gtk.Assistant
            page:
                current page of the assistant
        """
        # Collect GUI objects to be using during rendering
        self.confirm( self._exportsettings, self.output_file )
    def page_export_prepare_func( self, assistant, page ):
        """
        Starts the letter rendering thread.
        Arguments:
            assistant:
                the calling Gtk.Assistant
            page:
                current page of the assistant
        """
        # Collect GUI objects to be using during rendering
        assistant.set_page_complete( page, False )
        spinner = self.builder.get_object( "render_spinner" )
        label = self.builder.get_object( "render_label" )
        gui_objects = ( spinner, label, assistant, page )
        self.export( self._exportsettings, gui_objects, self.output_file )
    # Callbacks
    def exportsettings_changed_cb( self, exportsettings, is_ready ):
        """
        Callback function for the LetterCompositor "changed" signal.
        Arguments:
            exportsettings:
                the ExportSettings widget that emitted the signal
            is_ready:
                True if we are ready to export
        """
        page = self._assistant.get_nth_page( GenericExportAssistant.Page.Settings )
        self._assistant.set_page_complete( page, is_ready )
    def outputfile_togglebutton_toggled_cb( self, button ):
        """
        Callback function for the "toggled" signal of the "Save as..."-Gtk.ToggleButton.
        Arguments:
            button:
                the Gtk.ToggleButton that emitted the signal.
            entry:
                the Gtk.Entry which displays the file path.
        """
        if button.get_active():
            dialog = Gtk.FileChooserDialog( "Bitte Speicherort festlegen", self._assistant, Gtk.FileChooserAction.SAVE, ( Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK ) )
            for filefilter in self.filefilters:
                dialog.add_filter(filefilter)
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                self.output_file = dialog.get_filename()
                self.output_filter = dialog.get_filter()
                page = self._assistant.get_nth_page( GenericExportAssistant.Page.Intro )
                self._assistant.set_page_complete( page, True )
            dialog.destroy()
        button.set_active( False )
    def hide_cb( self, assistant ):
        """
        Callback for the "hide"-signal of the Gtk.Assistant.
        Rolls back and closes the database session.
        Arguments:
            assistant:
                the Gtk.Assistant that emitted the signal
        """
        self._session.rollback()
        self._session.close()
    def close_cb( self, assistant ):
        """
        Callback for the "close"-signal of the Gtk.Assistant.
        Hides the assistant.
        Arguments:
            assistant:
                the Gtk.Assistant that emitted the signal
        """
        assistant.hide()
    def cancel_cb( self, assistant ):
        """
        Callback for the "cancel"-signal of the Gtk.Assistant.
        Hides the assistant.coputer black white
        Arguments:
            assistant:
                the Gtk.Assistant that emitted the signal
        """
        assistant.hide()
    def apply_cb( self, assistant ):
        # FIXME: What to do here?
        pass
    def prepare_cb( self, assistant, page ):
        """
        Callback for the "prepare"-signal of the Gtk.Assistant.
        Calls the prepare_func for the respective page, if neccessary.
        Arguments:
            assistant:
                the Gtk.Assistant that emitted the signal
            page:
                the assistant's page to be prepared
        """
        if page == assistant.get_nth_page( GenericExportAssistant.Page.Settings ):
            self._exportsettings.refresh()
        elif page == assistant.get_nth_page( GenericExportAssistant.Page.Confirm ):
            self.page_confirm_prepare_func( assistant, page )
        elif page == assistant.get_nth_page( GenericExportAssistant.Page.Progress ):
            self.page_export_prepare_func( assistant, page )
class GenericExportSettings( Gtk.Box, ScopedDatabaseObject ):
    __gsignals__ = {
        'changed': ( GObject.SIGNAL_RUN_FIRST, None, ( bool, ) )
    }
    def __init__( self, session=None ):
        Gtk.Box.__init__( self )
        ScopedDatabaseObject.__init__( self, session=session )
    def refresh( self ):
        pass

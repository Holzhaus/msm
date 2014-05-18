#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from gi.repository import Gtk
import core.database
import core.config
from msmgui.widgets.magazinemanager import MagazineManager
class PreferencesDialog( object ):
    def _scopefunc( self ):
        """ Needed as scopefunc argument for the scoped_session"""
        return self
    def __init__( self, parent ):
        """
        __init__ function.
        Arguments:
            parent:
                the parent window of this dialog.
        """
        self._parent = parent
        self._session = core.database.Database.get_scoped_session( self._scopefunc )
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/dialogs/preferences.glade" )
        self.builder.get_object( "content" ).set_transient_for( self._parent )
        self.builder.get_object( "content" ).set_modal( True )
        # Connect Signals
        self.builder.connect_signals( self )
        # Add child widgets
        self._magazinemanager = MagazineManager( session=self._session )
        self.builder.get_object( "magazineeditorbox" ).add( self._magazinemanager )
    def show( self ):
        """
        Shows the dialog.
        """
        # DB info
        name, driver, version = core.database.Database.get_engine_info()
        version = '.'.join( [str( x ) for x in version] )
        data = "%i Magazine\n%i Vertragstypen\n%i Ausgaben\n%i Kunden\n%i Adressen\n%i Bankkonten\n%i Verträge" % ( core.database.Magazine.count(), core.database.Subscription.count(), core.database.Issue.count(), core.database.Customer.count(), core.database.Address.count(), core.database.Bankaccount.count(), core.database.Contract.count() )
        self.builder.get_object( 'general_database_name_label' ).set_text( name )
        self.builder.get_object( 'general_database_driver_label' ).set_text( driver )
        self.builder.get_object( 'general_database_version_label' ).set_text( version )
        self.builder.get_object( 'general_database_data_label' ).set_text( data )

        self.builder.get_object( 'general_bic_open_entry' ).set_text( core.config.Configuration().get( "Autocompletion", "bic_file" ) )
        self.builder.get_object( 'general_zipcode_open_entry' ).set_text( core.config.Configuration().get( "Autocompletion", "zipcode_file" ) )

        self._magazinemanager.start_edit()

        self.builder.get_object( "content" ).show_all()
    def hide( self ):
        """
        Hides the dialog.
        """
        self.builder.get_object( "content" ).hide()
    # Callbacks
    def general_bic_open_togglebutton_toggled_cb( self, button, entry=None ):
        """
        Callback function for the "toggled" signal of the "Open BIC-file"-Gtk.ToggleButton.
        Arguments:
            button:
                the Gtk.ToggleButton that emitted the signal.
            entry:
                the Gtk.Entry which displays the file path.
        """
        if button.get_active():
            dialog = Gtk.FileChooserDialog( "Bitte Datei auswählen", self.builder.get_object( 'window' ), Gtk.FileChooserAction.OPEN, ( Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK ) )
            filter_bic = Gtk.FileFilter()
            filter_bic.set_name( "Bankleitzahl-Dateien" )
            filter_bic.add_pattern( "blz_[0-9][0-9][0-9][0-9]_[0-9][0-9]_[0-9][0-9]_txt.txt" )
            dialog.add_filter( filter_bic )
            filter_any = Gtk.FileFilter()
            filter_any.set_name( "Alle Dateien" )
            filter_any.add_pattern( "*" )
            dialog.add_filter( filter_any )
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                if not entry:
                    entry = self.builder.get_object( 'general_bic_open_entry' )
                entry.set_text( dialog.get_filename() )
            dialog.destroy()
        button.set_active( False )
    def general_zipcode_open_togglebutton_toggled_cb( self, button, entry=None ):
        """
        Callback function for the "toggled" signal of the "Open zipcode-file"-Gtk.ToggleButton.
        Arguments:
            button:
                the Gtk.ToggleButton that emitted the signal.
            entry:
                the Gtk.Entry which displays the file path.
        """
        if button.get_active():
            dialog = Gtk.FileChooserDialog( "Bitte Datei auswählen", self.builder.get_object( 'window' ), Gtk.FileChooserAction.OPEN, ( Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK ) )
            filter_bankcode = Gtk.FileFilter()
            filter_bankcode.set_name( "PLZ-Dateien" )
            filter_bankcode.add_pattern( "PLZ.tab" )
            dialog.add_filter( filter_bankcode )
            filter_any = Gtk.FileFilter()
            filter_any.set_name( "Alle Dateien" )
            filter_any.add_pattern( "*" )
            dialog.add_filter( filter_any )
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                if not entry:
                    entry = self.builder.get_object( 'general_zipcode_open_entry' )
                entry.set_text( dialog.get_filename() )
            dialog.destroy()
        button.set_active( False )
    def response_cb( self, dialog, response ):
        """Response Callback of the Gtk.Dialog"""
        if response == 1: # Save new config values
            core.config.Configuration().set( "Autocompletion", "bic_file", self.builder.get_object( 'general_bic_open_entry' ).get_text() )
            core.config.Configuration().set( "Autocompletion", "zipcode_file", self.builder.get_object( 'general_zipcode_open_entry' ).get_text() )
            self._session.commit()
        else: # Discard new config values
            self._session.rollback()
        self.hide()

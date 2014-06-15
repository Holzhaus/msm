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
from gi.repository import GObject, Gtk
from core.config import Config
import msmgui.widgets.customereditor
import msmgui.widgets.customertable
import msmgui.widgets.base
class CustomerWindow( msmgui.widgets.base.RefreshableWindow ):
    __gsignals__ = {
        'status-changed': ( GObject.SIGNAL_RUN_FIRST, None, ( str, ) )
    }
    def __init__( self ):
        self._customertable = msmgui.widgets.customertable.CustomerTable()
        msmgui.widgets.base.RefreshableWindow.__init__( self, [self._customertable] )
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/widgets/customerwindow/customerwindow.glade" )
        self.builder.get_object( "content" ).reparent( self )
        self.builder.connect_signals( self )

        self._customereditor = msmgui.widgets.customereditor.CustomerEditor()
        self.builder.get_object( "editorbox" ).add( self._customereditor )
        self._customereditor.connect( "edit-started", self.customereditor_edit_started_cb )
        self._customereditor.connect( "edit-ended", self.customereditor_edit_ended_cb )
        self._customereditor.connect( "changed", self.customereditor_changed_cb )
        self._customereditor.connect( "save", self.customereditor_saved_cb )
        self._customereditor.connect( "expanded-changed", self.customereditor_expanded_changed_cb )

        self.builder.get_object( "tablebox" ).add( self._customertable )
        self._customertable.connect( "selection-changed", self.customertable_selection_changed_cb )
        active_only = Config.getboolean( "Interface", "active_only" )
        if not active_only:
            self.builder.get_object( "customers_showall_switch" ).set_active( not active_only )
    # Callbacks
    def customereditor_saved_cb( self, editor, customer_id, is_new ):
        if is_new:
            row = self._customertable.add_customer_by_id( customer_id )
            self.builder.get_object( "customers_add_togglebutton" ).set_active( False ) # Needs to be called explicitly to avoid double call caused by the toggle signal
            self._customertable.selection = row
            self.builder.get_object( "customers_edit_togglebutton" ).set_active( True ) # Needs to be called explicitly to avoid double call caused by the toggle signal
        else:
            self._customertable.update_customer_by_id( customer_id )
        self.emit( "status-changed", "Kundendaten gespeichert." )
    def customereditor_edit_ended_cb( self, editor ):
        if self._customertable.selection_blocked:
            self._customertable.selection_blocked = False
        self.emit( "status-changed", "Bearbeitung eines Kunden beendet." )
    def customereditor_edit_started_cb( self, editor, customer_id ):
        if customer_id == 0:
            self.builder.get_object( "customers_add_togglebutton" ).set_active( True )
        else:
            self.builder.get_object( "customers_edit_togglebutton" ).set_active( True )
        self.emit( "status-changed", "Bearbeitung eines Kunden begonnen." )
    def customereditor_changed_cb( self, editor ):
        if editor.data_is_valid():
            self._customertable.selection_blocked = False
            self.builder.get_object( "customers_add_togglebutton" ).set_sensitive( True )
            self.builder.get_object( "customers_edit_togglebutton" ).set_sensitive( True )
            self.emit( "status-changed", "Die eingegebenen Kundendaten sind valide." )
        else:
            self._customertable.selection_blocked = True
            self.builder.get_object( "customers_add_togglebutton" ).set_sensitive( False )
            self.builder.get_object( "customers_edit_togglebutton" ).set_sensitive( False )
            self.emit( "status-changed", "Die eingegebenen Kundendaten sind fehlerhaft oder unvollständig." )
    def customereditor_expanded_changed_cb( self, editor ):
        edit_togglebutton = self.builder.get_object( "customers_edit_togglebutton" )
        if self._customereditor.expanded:
            if self._customertable.selection:
                customer = self._customertable.selection.get_customer()
                if customer is not None and edit_togglebutton.get_active() is False:
                    edit_togglebutton.set_active( True )
        else:
            if edit_togglebutton.get_active() is True:
                self.builder.get_object( "customers_edit_togglebutton" ).set_active( False )
    def customertable_selection_changed_cb( self, table ):
        if table.selection is None:
            self._customereditor.expanded = False
            self._customereditor.expandable = False
            self.builder.get_object( "customers_delete_button" ).set_sensitive( False )
        else:
            self._customereditor.expandable = True
            if self._customereditor.expanded:
                self._customereditor.start_edit( table.selection.get_customer().id )
                self.builder.get_object( "customers_delete_button" ).set_sensitive( False )
            else:
                self.builder.get_object( "customers_delete_button" ).set_sensitive( True )
                self.builder.get_object( "customers_edit_togglebutton" ).set_sensitive( True )
    def customers_add_togglebutton_toggled_cb( self, toggle ):
        if toggle.get_active():
            edit_togglebutton = self.builder.get_object( "customers_edit_togglebutton" )
            if edit_togglebutton.get_active():
                edit_togglebutton.set_active( False )
            edit_togglebutton.set_sensitive( False )
            self._customertable.selection = None
            self._customereditor.start_edit()
            self._customertable.selection_blocked = True
        else:
            self._customertable.selection_blocked = False
            self._customereditor.end_edit()
            self._customereditor.expanded = False
    def customers_edit_togglebutton_toggled_cb( self, toggle ):
        if toggle.get_active():
            if toggle.get_sensitive() is False:
                toggle.set_sensitive( True )
            if self._customertable.selection:
                customer = self._customertable.selection.get_customer()
                if not customer or not customer.id:
                    raise RuntimeError( "EditTogglebutton should not be active if no customer is selected" )
                self._customereditor.start_edit( customer.id )
                if not self._customereditor.expanded:
                    self._customereditor.expanded = True
                self.builder.get_object( "customers_delete_button" ).set_sensitive( False )
        else:
            self._customereditor.end_edit()
            if self._customertable.selection:
                self.builder.get_object( "customers_delete_button" ).set_sensitive( True )
            if self._customereditor.expanded:
                self._customereditor.expanded = False
    def customers_delete_button_clicked_cb( self, button ):
        selection = self._customertable.selection
        if selection is None:
            raise RuntimeError( "Nothing selected" )
        customer = selection.get_customer()
        # Create ConfirmationDialog and ask if the user is sure
        message = "Willst du den Benutzer „%s“ (ID: %d) und alle verknüpften Daten (Addressen, Bankkonten, Verträge, Forderungen, Geldeingänge) wirklich löschen?" % ( customer.name, customer.id )
        dialog = msmgui.widgets.base.ConfirmationDialog( self.get_toplevel(), message )
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            self._customertable.remove( selection )
        dialog.destroy()
    def customers_search_entry_changed_cb( self, entry ):
        self._customertable.filter = entry.get_text().strip()
    def customers_showall_switch_notify_active_cb( self, switch, param_spec ):
        self._customertable.active_only = not switch.get_active()

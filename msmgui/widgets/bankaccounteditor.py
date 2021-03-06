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
from core import paths
import core.database
import core.autocompletion
import msmgui.rowreference
from msmgui.widgets.base import ScopedDatabaseObject, ConfirmationDialog
class BankaccountRowReference( msmgui.rowreference.GenericRowReference ):
    def get_bankaccount( self ):
        """Returns the core.database.Bankaccount that is associated with the Gtk.TreeRow that this instance references."""
        row = self.get_row()
        bankaccount = row[0]
        if not isinstance( bankaccount, core.database.Bankaccount ):
            raise RuntimeError( "tried to get a bankaccount that does not exist" )
        return bankaccount

class BankaccountEditor( Gtk.Box, ScopedDatabaseObject ):
    """Bankaccount editor inside the Customer editor"""
    __gsignals__ = {
        'changed': ( GObject.SIGNAL_RUN_FIRST, None, () ),
    }
    def __init__( self, session ):
        ScopedDatabaseObject.__init__( self, session )
        Gtk.Box.__init__( self )
        self._customer = None
        self.signals_blocked = True
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( paths.data("ui","widgets","customerwindow", "customereditor", "bankaccounteditor.glade" ))
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        # Connect Signals
        self.builder.connect_signals( self )
        self.builder.get_object( "bankaccounts_iban_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "bankaccounts_iban_cellrenderertext" ), self.iban_cell_data_func )
        self.builder.get_object( "bankaccounts_bic_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "bankaccounts_bic_cellrenderertext" ), self.bic_cell_data_func )
        self.builder.get_object( "bankaccounts_bank_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "bankaccounts_bank_cellrenderertext" ), self.bank_cell_data_func )
        self.builder.get_object( "bankaccounts_owner_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "bankaccounts_owner_cellrenderertext" ), self.owner_cell_data_func )
    def add_bankaccount( self, bankaccount ):
        """Add a bankaccount to the Gtk.Treemodel"""
        model = self.builder.get_object( "bankaccounts_liststore" )
        treeiter = model.append( [bankaccount] )
        path = model.get_path( treeiter )
        rowref = BankaccountRowReference( model, path )
        return rowref
    def remove( self, rowref ):
        if not isinstance( rowref, BankaccountRowReference ):
            raise TypeError( "Expected BankaccountRowReference, not {}".format( type( rowref ).__name__ ) )
        bankaccount = rowref.get_bankaccount()
        for contract in self._customer.contracts:
            # check if bankaccount is in use and replace it
            if bankaccount is contract.bankaccount:
                contract.bankaccount = None
        if bankaccount not in self._session.new:
            self._session.delete( bankaccount )
        if bankaccount in self._customer.bankaccounts:
            self._customer.bankaccounts.remove( bankaccount )
        model = rowref.get_model()
        treeiter = rowref.get_iter()
        model.remove( treeiter ) # Remove row from table
        self.emit( 'changed' )
    def _gui_clear( self ):
        self.builder.get_object( "bankaccounts_liststore" ).clear()
        self.builder.get_object( 'bankaccounts_remove_button' ).set_sensitive( False )
    def _gui_fill( self ):
        self._gui_clear()
        for bankaccount in self._customer.bankaccounts:
            self.add_bankaccount( bankaccount )
    def start_edit( self, customer ):
        self._customer = customer
        self._gui_fill()
    # Cell data funcs (control how Gtk.TreeModel contents are displayed)
    def iban_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = BankaccountRowReference( model, model.get_path( treeiter ) )
        bankaccount = rowref.get_bankaccount()
        if bankaccount.iban:
            new_text = bankaccount.iban_f
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def bic_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = BankaccountRowReference( model, model.get_path( treeiter ) )
        bankaccount = rowref.get_bankaccount()
        if bankaccount.bic:
            new_text = bankaccount.bic
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def bank_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = BankaccountRowReference( model, model.get_path( treeiter ) )
        bankaccount = rowref.get_bankaccount()
        if bankaccount.bank:
            new_text = bankaccount.bank
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def owner_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = BankaccountRowReference( model, model.get_path( treeiter ) )
        bankaccount = rowref.get_bankaccount()
        if bankaccount.owner:
            new_text = bankaccount.owner
        else:
            new_text = ""
            # TODO: default ownername in italics
        cellrenderer.set_property( 'text', new_text )
    # Callbacks
    def bankaccounts_add_button_clicked_cb( self, button ):
        if self.signals_blocked: return
        bankaccount = self._customer.add_bankaccount( "" )
        self.add_bankaccount( bankaccount )
        self.emit( "changed" )
    def bankaccounts_remove_button_clicked_cb( self, button ):
        if self.signals_blocked: return
        selection = self.builder.get_object( 'bankaccounts_treeview_selection' )
        model, treeiter = selection.get_selected()
        if treeiter is None:
            raise RuntimeError( "tried to remove an address, but none is currently selected" )
        rowref = BankaccountRowReference( model, model.get_path( treeiter ) )
        bankaccount = rowref.get_bankaccount()
        # If it is in use, create a ConfirmationDialog and ask if the user is sure
        bankaccount_in_use = False
        for contract in self._customer.contracts:
            if bankaccount is contract.bankaccount:
                bankaccount_in_use = True
                break
        if bankaccount_in_use:
            message = "Die Bankverbindung „%s“ wird zur Zeit einem oder mehreren Verträgen zur Abbuchung von Lastschriften verwendet. Dennoch löschen?" % bankaccount.iban_f
            dialog = ConfirmationDialog( self.get_toplevel(), message )
            response = dialog.run()
            if response == Gtk.ResponseType.YES:
                self.remove( rowref )
            dialog.destroy()
        else:
            self.remove( rowref )
    def bankaccounts_treeview_selection_changed_cb( self, selection ):
        if self.signals_blocked: return
        removebutton = self.builder.get_object( 'bankaccounts_remove_button' )
        model, treeiter = selection.get_selected()
        if treeiter is None:
            removebutton.set_sensitive( False )
        else:
            removebutton.set_sensitive( True )
    def bankaccounts_iban_cellrenderertext_edited_cb( self, cellrenderer, path_string, new_text ):
        if self.signals_blocked: return
        model = self.builder.get_object( 'bankaccounts_liststore' )
        rowref = BankaccountRowReference( model, Gtk.TreePath( path_string ) )
        bankaccount = rowref.get_bankaccount()
        bankaccount.iban_f = new_text
        bank = core.autocompletion.Banks.get_by_iban( bankaccount.iban )
        if bank:
            bankaccount.bank = bank.name
            bankaccount.bic = bank.bic
        self.emit( "changed" )
    def bankaccounts_bic_cellrenderertext_edited_cb( self, cellrenderer, path_string, new_text ):
        if self.signals_blocked: return
        model = self.builder.get_object( 'bankaccounts_liststore' )
        rowref = BankaccountRowReference( model, Gtk.TreePath( path_string ) )
        bankaccount = rowref.get_bankaccount()
        bankaccount.bic = new_text.strip()
        bank = core.autocompletion.Banks.get_by_bic( bankaccount.bic )
        if bank:
            bankaccount.bank = bank.name
        self.emit( "changed" )
    def bankaccounts_bank_cellrenderertext_edited_cb( self, cellrenderer, path_string, new_text ):
        if self.signals_blocked: return
        model = self.builder.get_object( 'bankaccounts_liststore' )
        rowref = BankaccountRowReference( model, Gtk.TreePath( path_string ) )
        bankaccount = rowref.get_bankaccount()
        bankaccount.bank = new_text.strip()
        self.emit( "changed" )
    def bankaccounts_owner_cellrenderertext_edited_cb( self, cellrenderer, path_string, new_text ):
        if self.signals_blocked: return
        model = self.builder.get_object( 'bankaccounts_liststore' )
        rowref = BankaccountRowReference( model, Gtk.TreePath( path_string ) )
        bankaccount = rowref.get_bankaccount()
        bankaccount.owner = new_text.strip()
        self.emit( "changed" )

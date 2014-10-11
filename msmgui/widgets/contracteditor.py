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
import dateutil.parser
from gi.repository import Gtk, GObject
from core import paths
import core.database
import msmgui.rowreference
from msmgui.widgets.base import ScopedDatabaseObject, ConfirmationDialog
class ContractRowReference( msmgui.rowreference.GenericRowReference ):
    def get_contract( self ):
        """Returns the core.database.Contract that is associated with the Gtk.TreeRow that this instance references."""
        row = self.get_row()
        contract = row[0]
        if not isinstance( contract, core.database.Contract ):
            raise RuntimeError( "tried to get a contract that does not exist" )
        return contract

class ContractEditor( Gtk.Box, ScopedDatabaseObject ):
    """Contract editor inside the Customer editor"""
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
        self.builder.add_from_file( paths.data("ui","widgets","customerwindow", "customereditor", "contracteditor.glade" ))
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        # Connect Signals
        self.builder.connect_signals( self )
        self.builder.get_object( "contracts_subscription_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "contracts_subscription_cellrenderercombo" ), self.subscription_cell_data_func )
        self.builder.get_object( "contracts_startdate_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "contracts_startdate_cellrenderertext" ), self.startdate_cell_data_func )
        self.builder.get_object( "contracts_enddate_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "contracts_enddate_cellrenderertext" ), self.enddate_cell_data_func )
        self.builder.get_object( "contracts_value_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "contracts_value_cellrendererspin" ), self.value_cell_data_func )
        self.builder.get_object( "contracts_shippingaddress_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "contracts_shippingaddress_cellrenderercombo" ), self.shippingaddress_cell_data_func )
        self.builder.get_object( "contracts_billingaddress_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "contracts_billingaddress_cellrenderercombo" ), self.billingaddress_cell_data_func )
        self.builder.get_object( "contracts_bankaccount_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "contracts_directwithdrawal_cellrenderertoggle" ), self.directwithdrawal_cell_data_func )
        self.builder.get_object( "contracts_bankaccount_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "contracts_bankaccount_cellrenderercombo" ), self.bankaccount_cell_data_func )
    def add_contract( self, contract ):
        """Add a contract to the Gtk.Treemodel"""
        model = self.builder.get_object( "contracts_liststore" )
        treeiter = model.append( [ contract ] )
        path = model.get_path( treeiter )
        rowref = ContractRowReference( model, path )
        return rowref
    def remove( self, rowref ):
        if not isinstance( rowref, ContractRowReference ):
            raise TypeError( "Expected ContractRowReference, not {}".format( type( rowref ).__name__ ) )
        contract = rowref.get_contract()
        if contract not in self._session.new:
            self._session.delete( contract )
        if contract in self._customer.contracts:
            self._customer.contracts.remove( contract )
        model = rowref.get_model()
        treeiter = rowref.get_iter()
        model.remove( treeiter ) # Remove row from table
        self.emit( 'changed' )
    def _gui_clear( self ):
        self.builder.get_object( "contracts_liststore" ).clear()
        self.builder.get_object( 'contracts_remove_button' ).set_sensitive( False )
    def _gui_fill( self ):
        self._gui_clear()
        for contract in self._customer.contracts:
            self.add_contract( contract )
    def start_edit( self, customer ):
        self._customer = customer
        self._gui_fill()
    # Cell data funcs (control how Gtk.TreeModel contents are displayed)
    def startdate_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = ContractRowReference( model, model.get_path( treeiter ) )
        contract = rowref.get_contract()
        if contract.startdate:
            new_text = contract.startdate.strftime("%x")
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def enddate_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = ContractRowReference( model, model.get_path( treeiter ) )
        contract = rowref.get_contract()
        if contract.enddate:
            new_text = contract.enddate.strftime("%x")
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def subscription_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = ContractRowReference( model, model.get_path( treeiter ) )
        contract = rowref.get_contract()
        if contract.subscription:
            new_text = contract.subscription.name
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def value_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = ContractRowReference( model, model.get_path( treeiter ) )
        contract = rowref.get_contract()
        cellrenderer.set_property( 'text', locale.currency( contract.value ) )
        if contract.subscription:
            cellrenderer.set_property( 'editable', contract.subscription.value_changeable )
        else:
            cellrenderer.set_property( 'editable', False )
    def shippingaddress_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = ContractRowReference( model, model.get_path( treeiter ) )
        contract = rowref.get_contract()
        address = contract.shippingaddress
        if address:
            new_text = address.string_f
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def billingaddress_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = ContractRowReference( model, model.get_path( treeiter ) )
        contract = rowref.get_contract()
        address = contract.billingaddress
        if address:
            new_text = address.string_f
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def directwithdrawal_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = ContractRowReference( model, model.get_path( treeiter ) )
        contract = rowref.get_contract()
        if contract.paymenttype == core.database.PaymentType.DirectWithdrawal:
            cellrenderer.set_active( True )
        else:
            cellrenderer.set_active( False )
    def bankaccount_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = ContractRowReference( model, model.get_path( treeiter ) )
        contract = rowref.get_contract()
        directwithdrawal = ( contract.paymenttype == core.database.PaymentType.DirectWithdrawal )
        if directwithdrawal != cellrenderer.get_sensitive():
            cellrenderer.set_sensitive( directwithdrawal )
        bankaccount = contract.bankaccount
        if bankaccount:
            new_text = bankaccount.iban_f
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def subscription_combo_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        combomodel = self.builder.get_object( "subscriptions_treestore" )
        obj = combomodel[treeiter][0]
        if isinstance( obj, core.database.Magazine ):
            cellrenderer.set_sensitive( False )
            cellrenderer.set_property( "text", obj.name )
        elif isinstance( obj, core.database.Subscription ):
            cellrenderer.set_sensitive( True )
            cellrenderer.set_property( "text", obj.name )
        else:
            raise TypeError( "Expected core.database.Magazine or core.database.Subscription, not {}".format( type( obj ).__name__ ) )
    def address_combo_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        combomodel = self.builder.get_object( "addresses_liststore" )
        address = combomodel[treeiter][0]
        if address:
            new_text = address.string_f
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def bankaccount_combo_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        combomodel = self.builder.get_object( "bankaccounts_liststore" )
        bankaccount = combomodel[treeiter][0]
        if bankaccount:
            new_text = bankaccount.iban_f
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    # Callbacks
    def contracts_add_button_clicked_cb( self, button ):
        if self.signals_blocked: return
        contract = self._customer.add_contract( None )
        self.add_contract( contract )
        self.emit( "changed" )
    def contracts_remove_button_clicked_cb( self, removebutton ):
        if self.signals_blocked: return
        selection = self.builder.get_object( 'contracts_treeview_selection' )
        model, treeiter = selection.get_selected()
        if treeiter is None:
            raise RuntimeError( "tried to remove a contract, but none is currently selected" )
        rowref = ContractRowReference( model, model.get_path( treeiter ) )
        contract = rowref.get_contract()
        # Create a ConfirmationDialog and ask if the user is sure
        message = "Willst du den Vertrag „%s“ wirklich löschen? Wenn der Vertrag gekündigt wurde, kannst du stattdessen besser ein Datum beim Feld „Vertragsende“ angeben. Dennoch löschen?" % contract.refid
        dialog = ConfirmationDialog( self.get_toplevel(), message )
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            self.remove( rowref )
        dialog.destroy()
    def contracts_treeview_selection_changed_cb( self, selection ):
        if self.signals_blocked: return
        removebutton = self.builder.get_object( 'contracts_remove_button' )
        model, treeiter = selection.get_selected()
        if treeiter is None:
            removebutton.set_sensitive( False )
        else:
            removebutton.set_sensitive( True )
    def contracts_subscription_cellrenderercombo_editing_started_cb( self, combo, editable, path_string ):
        """We reload the possible subscriptions before the edit"""
        cellview = editable.get_child()
        renderer_text = cellview.get_cells()[0]
        cellview.set_cell_data_func( renderer_text, self.subscription_combo_cell_data_func, None )
        if self.signals_blocked: return
        model = self.builder.get_object( "subscriptions_treestore" )
        model.clear()
        for magazine in core.database.Magazine.get_all( session=self._session ):
            treeiter = model.append( None, [magazine, ""] )
            for subscription in magazine.subscriptions:
                model.append( treeiter, [subscription, ""] )
    def contracts_bankaccount_cellrenderercombo_editing_started_cb( self, combo, editable, path_string ):
        """We reload the possible subscriptions before the edit"""
        cellview = editable.get_child()
        renderer_text = cellview.get_cells()[0]
        cellview.set_cell_data_func( renderer_text, self.bankaccount_combo_cell_data_func, None )
        if self.signals_blocked: return
        model = self.builder.get_object( "bankaccounts_liststore" )
        model.clear()
        for bankaccount in self._customer.bankaccounts:
            model.append( [bankaccount, ""] )
    def contracts_billingaddress_cellrenderercombo_editing_started_cb( self, combo, editable, path_string ):
        """We reload the possible subscriptions before the edit"""
        cellview = editable.get_child()
        renderer_text = cellview.get_cells()[0]
        cellview.set_cell_data_func( renderer_text, self.address_combo_cell_data_func, None )
        if self.signals_blocked: return
        model = self.builder.get_object( "addresses_liststore" )
        model.clear()
        for address in self._customer.addresses:
            model.append( [address, ""] )
    def contracts_shippingaddress_cellrenderercombo_editing_started_cb( self, combo, editable, path_string ):
        """We reload the possible subscriptions before the edit"""
        cellview = editable.get_child()
        renderer_text = cellview.get_cells()[0]
        cellview.set_cell_data_func( renderer_text, self.address_combo_cell_data_func, None )
        if self.signals_blocked: return
        model = self.builder.get_object( "addresses_liststore" )
        model.clear()
        for address in self._customer.addresses:
            model.append( [address, ""] )
    def contracts_startdate_cellrenderertext_edited_cb( self, cellrenderer, path_string, new_text ):
        if self.signals_blocked: return
        model = self.builder.get_object( 'contracts_liststore' )
        rowref = ContractRowReference( model, Gtk.TreePath( path_string ) )
        contract = rowref.get_contract()
        new_date = None
        text = new_text.strip()
        if text:
            try:
                new_date = dateutil.parser.parse( text, dayfirst=True )
            except Exception as error:
                logger.warning( 'Invalid date entered: %s (%r)', text, error )
            else:
                new_date = new_date.date()
        contract.startdate = new_date
        self.emit( "changed" )
    def contracts_enddate_cellrenderertext_edited_cb( self, cellrenderer, path_string, new_text ):
        if self.signals_blocked: return
        model = self.builder.get_object( 'contracts_liststore' )
        rowref = ContractRowReference( model, Gtk.TreePath( path_string ) )
        contract = rowref.get_contract()
        new_date = None
        text = new_text.strip()
        if text:
            try:
                new_date = dateutil.parser.parse( text, dayfirst=True )
            except Exception as error:
                logger.warning( 'Invalid date entered: %s (%r)', text, error )
            else:
                new_date = new_date.date()
        contract.enddate = new_date
        self.emit( "changed" )
    def contracts_subscription_cellrenderercombo_changed_cb( self, combo, path_string, new_iter ):
        if self.signals_blocked: return
        subscription = None
        if isinstance( new_iter, Gtk.TreeIter ):
            combomodel = self.builder.get_object( "subscriptions_treestore" )
            subscription = combomodel[new_iter][0]
        model = self.builder.get_object( 'contracts_liststore' )
        rowref = ContractRowReference( model, Gtk.TreePath( path_string ) )
        contract = rowref.get_contract()
        contract.subscription = subscription
        contract.value = subscription.value
        self.emit( "changed" )
    def contracts_billingaddress_cellrenderercombo_changed_cb( self, combo, path_string, new_iter ):
        if self.signals_blocked: return
        billingaddress = None
        if isinstance( new_iter, Gtk.TreeIter ):
            combomodel = self.builder.get_object( "addresses_liststore" )
            billingaddress = combomodel[new_iter][0]
        model = self.builder.get_object( 'contracts_liststore' )
        rowref = ContractRowReference( model, Gtk.TreePath( path_string ) )
        contract = rowref.get_contract()
        contract.billingaddress = billingaddress
        self.emit( "changed" )
    def contracts_shippingaddress_cellrenderercombo_changed_cb( self, combo, path_string, new_iter ):
        if self.signals_blocked: return
        shippingaddress = None
        if isinstance( new_iter, Gtk.TreeIter ):
            combomodel = self.builder.get_object( "addresses_liststore" )
            shippingaddress = combomodel[new_iter][0]
        model = self.builder.get_object( 'contracts_liststore' )
        rowref = ContractRowReference( model, Gtk.TreePath( path_string ) )
        contract = rowref.get_contract()
        contract.shippingaddress = shippingaddress
        self.emit( "changed" )
    def contracts_bankaccount_cellrenderercombo_changed_cb( self, combo, path_string, new_iter ):
        if self.signals_blocked: return
        bankaccount = None
        if isinstance( new_iter, Gtk.TreeIter ):
            combomodel = self.builder.get_object( "bankaccounts_liststore" )
            bankaccount = combomodel[new_iter][0]
        model = self.builder.get_object( 'contracts_liststore' )
        rowref = ContractRowReference( model, Gtk.TreePath( path_string ) )
        contract = rowref.get_contract()
        contract.bankaccount = bankaccount
        self.emit( "changed" )
    def contracts_directwithdrawal_cellrenderertoggle_toggled_cb( self, cellrenderer, path_string ):
        if self.signals_blocked: return
        model = self.builder.get_object( 'contracts_liststore' )
        rowref = ContractRowReference( model, Gtk.TreePath( path_string ) )
        contract = rowref.get_contract()
        if contract.paymenttype == core.database.PaymentType.DirectWithdrawal:
            contract.paymenttype = core.database.PaymentType.Invoice
        else:
            contract.paymenttype = core.database.PaymentType.DirectWithdrawal
        self.emit( "changed" )
    def contracts_value_cellrendererspin_edited_cb( self, spin, path_string, new_value ):
        if self.signals_blocked: return
        model = self.builder.get_object( 'contracts_liststore' )
        rowref = ContractRowReference( model, Gtk.TreePath( path_string ) )
        contract = rowref.get_contract()
        if new_value == "":
            contract.value = 0
        else:
            contract.value = locale.atof( new_value )
        self.emit( "changed" )

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
import pytz
from core import paths
import core.database
import core.autocompletion
import msmgui.rowreference
from msmgui.widgets.base import ScopedDatabaseObject, ConfirmationDialog
class AddressRowReference( msmgui.rowreference.GenericRowReference ):
    def get_address( self ):
        """Returns the core.database.Address that is associated with the Gtk.TreeRow that this instance references."""
        row = self.get_row()
        address = row[0]
        if not isinstance( address, core.database.Address ):
            raise RuntimeError( "tried to get an address that does not exist" )
        return address

class AddressEditor( Gtk.Box, ScopedDatabaseObject ):
    """Address editor inside the Customer editor"""
    __gsignals__ = {
        'changed': ( GObject.SIGNAL_RUN_FIRST, None, () ),
    }
    def __init__( self, session ):
        ScopedDatabaseObject.__init__( self, session )
        Gtk.Box.__init__( self )
        self.signals_blocked = True
        self._customer = None
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( paths.data("ui","widgets","customerwindow", "customereditor", "addresseditor.glade" ))
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        # Connect Signals
        self.builder.connect_signals( self )
        self.builder.get_object( "addresses_street_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "addresses_street_cellrenderertext" ), self.street_cell_data_func )
        self.builder.get_object( "addresses_zipcode_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "addresses_zipcode_cellrenderertext" ), self.zipcode_cell_data_func )
        self.builder.get_object( "addresses_city_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "addresses_city_cellrenderertext" ), self.city_cell_data_func )
        self.builder.get_object( "addresses_co_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "addresses_co_cellrenderertext" ), self.co_cell_data_func )
        self.builder.get_object( "addresses_recipient_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "addresses_recipient_cellrenderertext" ), self.recipient_cell_data_func )
        self.builder.get_object( "addresses_country_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "addresses_country_cellrenderercombo" ), self.country_cell_data_func )
        # Add Country List
        countries_liststore = self.builder.get_object( 'countries_liststore' )
        for country_code, country_name in sorted( pytz.country_names.items() ): # FIXME: Use babel.Locale instead
            countries_liststore.append( [country_code.upper(), country_name] )
    def add_address( self, address ):
        """Add an address to the Gtk.Treemodel"""
        model = self.builder.get_object( "addresses_liststore" )
        treeiter = model.append( [ address ] )
        path = model.get_path( treeiter )
        rowref = AddressRowReference( model, path )
        self.emit( "changed" )
        return rowref
    def remove( self, rowref ):
        if not isinstance( rowref, AddressRowReference ):
            raise TypeError( "Expected AddressRowReference, not {}".format( type( rowref ).__name__ ) )
        address = rowref.get_address()
        for contract in self._customer.contracts:
            # check if address is in use and replace it
            if address is contract.billingaddress:
                contract.billingaddress = None
            if address is contract.shippingaddress:
                contract.shippingaddress = None
        if address not in self._session.new:
            self._session.delete( address )
        if address in self._customer.addresses:
            self._customer.addresses.remove( address )
        model = rowref.get_model()
        treeiter = rowref.get_iter()
        model.remove( treeiter ) # Remove row from table
        self.emit( "changed" )
    def _gui_clear( self ):
        self.builder.get_object( "addresses_liststore" ).clear()
        self.builder.get_object( 'addresses_remove_button' ).set_sensitive( False )
    def _gui_fill( self ):
        self._gui_clear()
        for address in self._customer.addresses:
            self.add_address( address )
    def start_edit( self, customer ):
        self._customer = customer
        self._gui_fill()
    # Cell data funcs (control how Gtk.TreeModel contents are displayed)
    def street_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = AddressRowReference( model, model.get_path( treeiter ) )
        address = rowref.get_address()
        if address.street:
            new_text = address.street
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def zipcode_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = AddressRowReference( model, model.get_path( treeiter ) )
        address = rowref.get_address()
        if address.zipcode:
            new_text = address.zipcode
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def city_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = AddressRowReference( model, model.get_path( treeiter ) )
        address = rowref.get_address()
        if address.city:
            new_text = address.city
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def country_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = AddressRowReference( model, model.get_path( treeiter ) )
        address = rowref.get_address()
        if address.countrycode:
            new_text = address.countrycode # FIXME: Use countryname instead of countrycode
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def co_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = AddressRowReference( model, model.get_path( treeiter ) )
        address = rowref.get_address()
        if address.co:
            new_text = address.co
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def recipient_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = AddressRowReference( model, model.get_path( treeiter ) )
        address = rowref.get_address()
        if address.recipient:
            new_text = address.recipient
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    # Callbacks
    def addresses_add_button_clicked_cb( self, button ):
        if self.signals_blocked: return
        address = self._customer.add_address( "", "" )
        self.add_address( address )
    def addresses_remove_button_clicked_cb( self, removebutton ):
        if self.signals_blocked: return
        selection = self.builder.get_object( 'addresses_treeview_selection' )
        model, treeiter = selection.get_selected()
        if treeiter is None:
            raise RuntimeError( "tried to remove an address, but none is currently selected" )
        rowref = AddressRowReference( model, model.get_path( treeiter ) )
        address = rowref.get_address()
        # If it is in use, create a ConfirmationDialog and ask if the user is sure
        address_in_use = False
        for contract in self._customer.contracts:
            if address is contract.billingaddress or address is contract.shippingaddress:
                address_in_use = True
                break
        if address_in_use:
            message = "Die Adresse „%s“ ist in einem oder mehreren Verträgen als Rechnungs- oder Lieferadresse angegeben. Willst du die Adresse dennoch entfernen?" % address.string_f
            dialog = ConfirmationDialog( self.get_toplevel(), message )
            response = dialog.run()
            if response == Gtk.ResponseType.YES:
                self.remove( rowref )
            dialog.destroy()
        else:
            self.remove( rowref )
    def addresses_treeview_selection_changed_cb( self, selection ):
        if self.signals_blocked: return
        removebutton = self.builder.get_object( 'addresses_remove_button' )
        model, treeiter = selection.get_selected()
        if treeiter is None:
            removebutton.set_sensitive( False )
        else:
            removebutton.set_sensitive( True )
    def addresses_street_cellrenderertext_edited_cb( self, cellrenderer, path_string, new_text ):
        if self.signals_blocked: return
        model = self.builder.get_object( 'addresses_liststore' )
        rowref = AddressRowReference( model, Gtk.TreePath( path_string ) )
        address = rowref.get_address()
        address.street = new_text.strip()
        self.emit( "changed" )
    def addresses_zipcode_cellrenderertext_edited_cb( self, cellrenderer, path_string, new_text ):
        if self.signals_blocked: return
        model = self.builder.get_object( 'addresses_liststore' )
        rowref = AddressRowReference( model, Gtk.TreePath( path_string ) )
        address = rowref.get_address()
        zipcode = new_text.strip()
        city = core.autocompletion.Cities.get_by_iso_zipcode( zipcode )
        if city is None:
            country = 'DE' # FIXME: Enable completion for other countries too
            city = core.autocompletion.Cities.get( country, "zipcode", zipcode )
        if city is not None:
            address.city = city.name
            address.zipcode = city.zipcode
            address.countrycode = city.country
        else:
            address.zipcode = zipcode
        self.emit( "changed" )
    def addresses_city_cellrenderertext_edited_cb( self, cellrenderer, path_string, new_text ):
        if self.signals_blocked: return
        model = self.builder.get_object( 'addresses_liststore' )
        rowref = AddressRowReference( model, Gtk.TreePath( path_string ) )
        address = rowref.get_address()
        address.city = new_text.strip()
        self.emit( "changed" )
    def addresses_co_cellrenderertext_edited_cb( self, cellrenderer, path_string, new_text ):
        if self.signals_blocked: return
        model = self.builder.get_object( 'addresses_liststore' )
        rowref = AddressRowReference( model, Gtk.TreePath( path_string ) )
        address = rowref.get_address()
        address.co = new_text.strip()
        self.emit( "changed" )
    def addresses_recipient_cellrenderertext_edited_cb( self, cellrenderer, path_string, new_text ):
        if self.signals_blocked: return
        model = self.builder.get_object( 'addresses_liststore' )
        rowref = AddressRowReference( model, Gtk.TreePath( path_string ) )
        address = rowref.get_address()
        address.recipient = new_text.strip()
        self.emit( "changed" )
    def addresses_country_cellrenderercombo_changed_cb( self, combo, path_string, new_iter ):
        if self.signals_blocked: return
        model = self.builder.get_object( 'addresses_liststore' )
        rowref = AddressRowReference( model, Gtk.TreePath( path_string ) )
        address = rowref.get_address()
        countrycode = 'DE' # FIXME: Default country value
        if isinstance( new_iter, Gtk.TreeIter ):
            combomodel = self.builder.get_object( "countries_liststore" )
            countrycode = combomodel[new_iter][0]
        address.countrycode = countrycode
        city = core.autocompletion.Cities.get( address.countrycode, "zipcode", address.zipcode )
        if city is not None:
            address.city = city.name
            address.zipcode = city.zipcode
        self.emit( "changed" )

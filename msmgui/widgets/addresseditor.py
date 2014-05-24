#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from gi.repository import Gtk, GObject
import core.database
import core.autocompletion
import msmgui.rowreference
from msmgui.widgets.base import ScopedDatabaseObject
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
        self.builder.add_from_file( "data/ui/widgets/customerwindow/customereditor/addresseditor.glade" )
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        # Connect Signals
        self.builder.connect_signals( self )
        self.builder.get_object( "addresses_street_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "addresses_street_cellrenderertext" ), self.street_cell_data_func )
        self.builder.get_object( "addresses_zipcode_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "addresses_zipcode_cellrenderertext" ), self.zipcode_cell_data_func )
        self.builder.get_object( "addresses_city_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "addresses_city_cellrenderertext" ), self.city_cell_data_func )
        self.builder.get_object( "addresses_co_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "addresses_co_cellrenderertext" ), self.co_cell_data_func )

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
        # TODO: Check if address is currently in use
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
    def _gui_fill( self ):
        self._gui_clear()
        for address in self._customer.addresses:
            self.add_address( address )
    def start_edit( self, customer ):
        self._customer = customer
        self._gui_fill()
    """Cell data funcs (control how Gtk.TreeModel contents are displayed)"""
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
    def co_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = AddressRowReference( model, model.get_path( treeiter ) )
        address = rowref.get_address()
        if address.co:
            new_text = address.co
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
        """Callbacks"""
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
            address.country = city.country
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
"""self.emit( "changed" )
        model, treeiter = self.builder.get_object( 'customers_edit_addresses_treeview_selection' ).get_selected()
        if treeiter:
            if model.iter_is_valid( treeiter ):
                contracts_model = self.builder.get_object( 'customers_edit_contracts_liststore' )
                crefid = model[treeiter][6]
                desc = model[treeiter][7]
                crefid_used = False
                for row in contracts_model:
                    if row[7] == crefid or row[9] == crefid:
                        crefid_used = True
                        break
                if crefid_used:
                    dialog = Gtk.MessageDialog( self.builder.get_object( 'window' ), Gtk.DialogFlags.MODAL, Gtk.MessageType.WARNING, Gtk.ButtonsType.YES_NO, "Diese Adresse wird von einem Vertrag verwendet." )
                    dialog.format_secondary_text( "Die Adresse „%s“ ist in einem oder mehreren Verträgen als Rechnungs- oder Lieferadresse angegeben. Willst du die Adresse dennoch entfernen?" % desc )
                    response = dialog.run()
                    if response == Gtk.ResponseType.YES:
                        model.remove( treeiter )
                        if len( model ) == 0:
                            new_crefid = 0
                            new_desc = ""
                        elif len( model ) == 1:
                            firstiter = model.get_iter_first()
                            new_crefid = model[firstiter][6]
                            new_desc = model[firstiter][7]
                            self.parent.addStatusMessage( "Die Adresse „%s“ wurde in Verträgen automatisch durch „%s“ ersetzt." % ( desc, new_desc ) )
                        else:
                            # implement replacement address selection window
                            new_crefid = 0
                            new_desc = ""
                        for row in contracts_model:  # change crefid in contracts to new_crefid
                            if row[7] == crefid:
                                row[7] = new_crefid
                                row[8] = new_desc
                            if row[9] == crefid:
                                row[9] = new_crefid
                                row[10] = new_desc
                    dialog.destroy()
                else:
                    model.remove( treeiter )"""

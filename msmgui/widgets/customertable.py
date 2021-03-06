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
from gi.repository import Gtk, GObject, GLib
from core import paths
import core.database
from core.config import Config
import msmgui.rowreference
from msmgui.widgets.base import ScopedDatabaseObject
class CustomerRowReference( msmgui.rowreference.GenericRowReference ):
    @staticmethod
    def new_by_iter( model, treeiter ):
        """Convenience method that creates an instance by Gtk.TreeIter, not by Gtk.TreePath"""
        path = model.get_path( treeiter )
        rowref = CustomerRowReference( model, path )
        return rowref
    def __init__( self, model, path ):
        """Constructor. Internally, the reference always points to the row in the base Gtk.TreeModel."""
        treeiter = model.get_iter( path )
        while hasattr( model, "get_model" ) and callable( getattr( model, "get_model" ) ) and model.get_model():
            treeiter = model.convert_iter_to_child_iter( treeiter )
            model = model.get_model()
        path = model.get_path( treeiter )
        if not isinstance( model, ( Gtk.ListStore, Gtk.TreeStore ) ):
            raise TypeError( "Specified base TreeModel is invalid" )
        self._rowref = Gtk.TreeRowReference.new( model, path )
    def get_selection_iter( self, model ):
        """Return the Gtk.TreeIter for the selection Gtk.TreeModel."""
        models = [ model ]
        while hasattr( model, "get_model" ) and callable( getattr( model, "get_model" ) ) and model.get_model():
            model = model.get_model()
            models.append( model )
        models.reverse()
        if models[0] is not self.get_model():
            raise RuntimeError( "TreeModel mismatch" )
        models.pop( 0 )
        treeiter = self.get_iter()
        for model in models:
            success, treeiter = model.convert_child_iter_to_iter( treeiter )
            if not success:
                logger.warning( "TreeIter invalid for model: %r", model )
                return None
        return treeiter
    def get_selection_path( self, model ):
        """Return the Gtk.TreePath for the selection Gtk.TreeModel."""
        treeiter = self.get_selection_iter( model )
        if not treeiter:
            return None
        path = model.get_path( treeiter )
        return path
    def get_customer( self ):
        """Returns the core.database.Customer that is associated with the Gtk.TreeRow that this instance references."""
        row = self.get_row()
        customer_id = row[0]
        return core.database.Customer.get_by_id( customer_id )
    def update_row( self ):
        customer = self.get_customer()
        self.set_row( CustomerTable.convert_customer_to_rowdata( customer ) )

class CustomerTable( Gtk.Box, ScopedDatabaseObject ):
    MIN_FILTER_LEN = 3 # what is the minimum length for the filter string
    FILTER_COLUMNS = ( 1, 2, 7, 11, 12 ) # which columns should be used for filtering
    __gsignals__ = {
        'selection_changed': ( GObject.SIGNAL_RUN_FIRST, None, () ),
        'refresh-started': ( GObject.SIGNAL_RUN_FIRST, None, () ),
        'refresh-ended': ( GObject.SIGNAL_RUN_FIRST, None, () )
    }
    def __init__( self ):
        ScopedDatabaseObject.__init__( self )
        Gtk.Box.__init__( self )
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( paths.data("ui","widgets","customerwindow", "customertable.glade"))
        CustomerRowReference.builder = self.builder
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        # Connect Signals
        self.builder.connect_signals( self )
        # Use the selection function
        self.builder.get_object( 'customers_treeview_selection' ).set_select_function( self._is_row_selection_changeable, None )

        model = self.builder.get_object( "customers_liststore" )
        self._customers_treemodelfilter = model.filter_new()
        self._customers_treemodelfilter.set_visible_func( self._is_row_visible )
        self._customers_treemodelsort = Gtk.TreeModelSort( self._customers_treemodelfilter )

        # Add properties
        self.needs_refresh = True
        self.currently_refreshing = False
        self._active_only = True
        self._filter = ""
        self._selection_blocked = False
        self._current_selection = None
    # Data interaction
    def clear( self ):
        self.builder.get_object( "customers_liststore" ).clear()
    def _do_refresh( self, step=25 ):
        if not self.needs_refresh:
            return False
        self.currently_refreshing = True
        self.needs_refresh = False
        self.emit( 'refresh-started' )
        treeview = self.builder.get_object( "customers_treeview" )
        model = self.builder.get_object( "customers_liststore" )
        treeview.freeze_child_notify()
        self.set_sensitive( False )
        treeview.set_model( None )
        del self._customers_treemodelsort
        del self._customers_treemodelfilter
        for i, customer in enumerate( core.database.Customer.get_all( session=self.session ) ):
            rowref = self.add_customer( customer )
            del rowref
            # change something
            if i % step == 0:
                # freeze/thaw not really  necessary here as sorting is wrong because of the
                # default sort function
                logger.debug("Refreshed %d rows", i)
        self._customers_treemodelfilter = model.filter_new()
        self._customers_treemodelfilter.set_visible_func( self._is_row_visible )
        GLib.idle_add( self.refilter )
        self._customers_treemodelsort = Gtk.TreeModelSort( self._customers_treemodelfilter )
        treeview.set_model( self._customers_treemodelsort )
        treeview.thaw_child_notify()
        self.set_sensitive( True )
        self.currently_refreshing = False
        self.emit( 'refresh-ended' )
        return False
    def refresh( self ):
        GLib.idle_add(self._do_refresh)
    @staticmethod
    def convert_customer_to_rowdata( customer ):
        if not isinstance( customer, core.database.Customer ):
            raise TypeError( "Expected core.database.Customer, not {}".format( type( customer ).__name__ ) )
        birthday = customer.birthday.strftime("%x") if customer.birthday else ""
        has_running_contracts = customer.has_running_contracts()
        color = 'black' if has_running_contracts else 'gray'
        if len( customer.addresses ):
            address = customer.addresses[0]
            return [customer.id, customer.familyname, customer.prename, customer.honourific, customer.title, customer.gender, birthday, customer.company1, customer.company2, customer.department, address.co, address.street, address.zipcode, address.city, has_running_contracts, color]
        else:
            return [customer.id, customer.familyname, customer.prename, customer.honourific, customer.title, customer.gender, birthday, customer.company1, customer.company2, customer.department, "", "", "", "", has_running_contracts, color]
    def add_customer( self, customer ):
        model = self.builder.get_object( "customers_liststore" )
        treeiter = model.append( CustomerTable.convert_customer_to_rowdata( customer ) )
        return CustomerRowReference.new_by_iter( model, treeiter )
    def add_customer_by_id( self, customer_id ):
        customer = core.database.Customer.get_by_id( customer_id )
        if not isinstance( customer, core.database.Customer ):
            raise TypeError( "Expected core.database.Customer, not {}".format( type( customer ).__name__ ) )
        return self.add_customer( customer )
    def remove( self, rowref ):
        if not isinstance( rowref, CustomerRowReference ):
            raise TypeError( "Expected msmgui.customertable.CustomerRowReference, not {}".format( type( rowref ).__name__ ) )
        customer = rowref.get_customer()
        self.session.delete( self.session.merge( customer ) )
        self.session.commit()
        self.session.remove()
        model = rowref.get_model()
        treeiter = rowref.get_iter()
        model.remove( treeiter ) # Remove row from table
    # Getting and setting rows
    def _get_rowref_by_customer_id( self, customer_id ):
        if not isinstance( customer_id, int ):
            raise TypeError( "Expected int, not {}".format( type( customer_id ).__name__ ) )
        model = self.builder.get_object( "customers_liststore" )
        treeiter = model.get_iter_first()
        while treeiter != None:
            if model[treeiter][0] == customer_id:
                return CustomerRowReference.new_by_iter( model, treeiter )
            treeiter = model.iter_next( treeiter )
        return None
    def update_customer_by_id( self, customer_id ):
        rowref = self._get_rowref_by_customer_id( customer_id )
        if rowref is None:
            raise ValueError( "No row for given customer_id" )
        rowref.update_row()
    # Filtering stuff
    @property
    def filter( self ):
        """The string used to filter the table"""
        return self._filter
    @filter.setter
    def filter( self, q ):
        if not isinstance( q, str ):
            raise TypeError( "Expected str, not {}".format( type( q ).__name__ ) )
        if self._filter != q:
            old_q = self._filter
            self._filter = q
            if not ( len( old_q ) < self.MIN_FILTER_LEN and len( q ) < self.MIN_FILTER_LEN ):
                # No need to refilter if the filter string is discarded anyway because it's too short
                GLib.idle_add( self.refilter )
    def refilter( self ):
        if hasattr( self, '_customers_treemodelfilter' ):
            self._customers_treemodelfilter.refilter()
        return False
    @property
    def active_only( self ):
        '''Show only active customers (i.e. customers with running contracts)'''
        return self._active_only
    @active_only.setter
    def active_only( self, value ):
        if not isinstance( value, bool ):
            raise TypeError( "Expected bool, not {}".format( type( value ).__name__ ) )
        if self._active_only != value:
            self._active_only = value
            Config.set( "Interface", "active_only", self._active_only )
            GLib.idle_add( self.refilter )
    def _is_row_visible( self, model, treeiter, data=None ):
        rowref = CustomerRowReference.new_by_iter( model, treeiter )
        if rowref == self.selection:
            # if self.selection and self.selection.get_row() is row:
            return True # Prevent currently selected row from being hidden
        row = rowref.get_row()
        if self.active_only and not row[14]:
            return False # if active_only is True, then customers without contracts are hidden
        if len( self.filter ) < CustomerTable.MIN_FILTER_LEN:
            return True
        else:
            for column in CustomerTable.FILTER_COLUMNS:
                if self.filter.lower() in row[column].lower():
                    return True
        return False
    # Selection of a row
    @property
    def selection( self ):
        """The string used to filter the table"""
        return self._current_selection
    @selection.setter
    def selection( self, new_selection ):
        treeselection = self.builder.get_object( "customers_treeview_selection" )
        if new_selection is None:
            treeselection.unselect_all()
            self._current_selection = None
        elif isinstance( new_selection, int ) or isinstance( new_selection, CustomerRowReference ):
            if isinstance( new_selection, int ):
                rowref = self._get_rowref_by_customer_id( new_selection )
            else:
                rowref = new_selection
            if self.selection is None or self.selection != rowref:
                new_selection_iter = rowref.get_selection_iter( treeselection.get_tree_view().get_model() )
                if new_selection_iter is not None:
                    treeselection.select_iter( new_selection_iter )
                    self._current_selection = rowref
            else:
                raise ValueError
        else:
            raise TypeError( "Expected int, CustomerRowReference or None, not {}".format( type( new_selection ).__name__ ) )
    @property
    def selection_blocked( self ):
        """Can the selection be changed?"""
        return self._selection_blocked
    @selection_blocked.setter
    def selection_blocked( self, value ):
        if not isinstance( value, bool ):
            raise TypeError( "Expected bool, not {}".format( type( value ).__name__ ) )
        self._selection_blocked = value
    def _is_row_selection_changeable( self, selection, model, treepath, path_currently_selected, data=None ):
        if self.selection_blocked:
            return False
        return True
    # Callbacks
    def customers_treeview_selection_changed_cb( self, selection ):
        if self.selection_blocked:
            self.selection = self.selection # Restore current selection
            return
        model, treeiter = selection.get_selected()
        if treeiter:
            rowref = CustomerRowReference.new_by_iter( model, treeiter )
        else:
            rowref = None
        if self.selection != rowref:
            self.selection = rowref
            GLib.idle_add( self.refilter )
            self.emit( "selection-changed" )

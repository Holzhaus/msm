#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from gi.repository import Gtk, GObject
from core.database import *
from core.config import Configuration
import locale
import msmgui.rowreference
class CustomerRowReference( msmgui.rowreference.GenericRowReference ):
        builder = None
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
            if model is not CustomerRowReference.builder.get_object( "customers_liststore" ) or not isinstance( model, Gtk.ListStore ):
                raise TypeError( "Specified base TreeModel is invalid" )
            self._rowref = Gtk.TreeRowReference.new( model, path )
        def get_selection_iter( self ):
            """Return the Gtk.TreeIter for the selection Gtk.TreeModel."""
            treeiter = self.get_iter()
            success, treeiter = CustomerRowReference.builder.get_object( "customers_treemodelfilter" ).convert_child_iter_to_iter( treeiter )
            if not success:
                raise ValueError( "TreeIter invalid" )
            success, treeiter = self.get_selection_model().convert_child_iter_to_iter( treeiter )
            if not success:
                raise ValueError( "TreeIter invalid" )
            return treeiter
        def get_selection_path( self ):
            """Return the Gtk.TreePath for the selection Gtk.TreeModel."""
            model = self.get_selection_model()
            treeiter = self.get_selection_iter()
            path = model.get_path( treeiter )
            return path
        def get_selection_model( self ):
            """Return the selection Gtk.TreeModel."""
            model = CustomerRowReference.builder.get_object( "customers_treemodelsort" )
            if not isinstance( model, Gtk.TreeModelSort ):
                raise TypeError( "Specified selection TreeModel is invalid" )
            return model
        def get_customer( self ):
            """Returns the core.database.Customer that is associated with the Gtk.TreeRow that this instance references."""
            row = self.get_row()
            customer_id = row[0]
            return core.database.Customer.get_by_id( customer_id )
        def update_row( self ):
            customer = self.get_customer()
            self.set_row( CustomerTable.convert_customer_to_rowdata( customer ) )

class CustomerTable( Gtk.Box ):
    MIN_FILTER_LEN = 3  # what is the minimum length for the filter string
    FILTER_COLUMNS = ( 1, 2, 11, 12 )  # which columns should be used for filtering
    __gsignals__ = {
        'selection_changed': ( GObject.SIGNAL_RUN_FIRST, None, () )
    }
    def _scopefunc( self ):
        """ Needed as scopefunc argument for the scoped_session"""
        return self
    def __init__( self ):
        Gtk.Box.__init__( self )
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/widgets/customerwindow/customertable.glade" )
        CustomerRowReference.builder = self.builder
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        # Connect Signals
        self.builder.connect_signals( self )

        # Use the filter function
        self.builder.get_object( 'customers_treemodelfilter' ).set_visible_func( self._is_row_visible )
        # Use the selection function
        self.builder.get_object( 'customers_treeview_selection' ).set_select_function( self._is_row_selection_changeable, None )

        # Add properties
        self._active_only = True
        self._filter = ""
        self._selection_blocked = False
        self._current_selection = None

        self.session = core.database.Database.get_scoped_session( self._scopefunc )

    """Data interaction"""
    def clear( self ):
        self.builder.get_object( "customers_liststore" ).clear()
    def fill( self ):
        self.clear()
        for customer in core.database.Customer.get_all():
            self.add_customer( customer )
    @staticmethod
    def convert_customer_to_rowdata( customer ):
        if not isinstance( customer, core.database.Customer ):
            raise TypeError( "Expected core.database.Customer, not {}".format( type( customer ).__name__ ) )
        birthday = customer.birthday.strftime( locale.nl_langinfo( locale.D_FMT ) ) if customer.birthday else ""
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
        self.session().delete( self.session().merge( customer ) )
        self.session().commit()
        self.session.remove()
        model = rowref.get_model()
        treeiter = rowref.get_iter()
        model.remove( treeiter )  # Remove row from table
    """Getting and setting rows"""
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
    """Filtering stuff"""
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
                self.builder.get_object( 'customers_treemodelfilter' ).refilter()
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
            Configuration().set( "Interface", "active_only", self._active_only )
            self.builder.get_object( 'customers_treemodelfilter' ).refilter()
    def _is_row_visible( self, model, treeiter, data=None ):
        rowref = CustomerRowReference.new_by_iter( model, treeiter )
        if rowref == self.selection:
            # if self.selection and self.selection.get_row() is row:
            return True  # Prevent currently selected row from being hidden
        row = rowref.get_row()
        if self.active_only and not row[14]:
            return False  # if active_only is True, then customers without contracts are hidden
        if len( self.filter ) < CustomerTable.MIN_FILTER_LEN:
            return True
        else:
            for column in CustomerTable.FILTER_COLUMNS:
                if self.filter.lower() in row[column].lower():
                    return True
        return False
    """ Selection of a row """
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
            if self.selection is None or self._current_selection.get_row() is not rowref.get_row():
                if treeselection.get_tree_view().get_model() is not rowref.get_selection_model():
                    raise AttributeError( "CustomerRowReference selection model mismatch" )
                treeselection.select_iter( rowref.get_selection_iter() )
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
    """Callbacks"""
    def customers_treeview_selection_changed_cb( self, selection ):
        if self.selection_blocked:
            self.selection = self.selection  # Restore current selection
            return
        model, treeiter = selection.get_selected()
        if treeiter:
            self._current_selection = CustomerRowReference.new_by_iter( model, treeiter )
        else:
             self._current_selection = None
        self.builder.get_object( 'customers_treemodelfilter' ).refilter()
        self.emit( "selection-changed" )

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
import core.database
from core import paths
from core.config import Config
import locale
import msmgui.rowreference
from core.letterrenderer import LetterPreviewRenderer
from msmgui.widgets.base import ScopedDatabaseObject

class InvoiceRowReference( msmgui.rowreference.GenericRowReference ):
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
    def get_invoice( self ):
        """Returns the core.database.Invoice that is associated with the Gtk.TreeRow that this instance references."""
        row = self.get_row()
        invoice = row[0]
        return invoice

class InvoiceTable( Gtk.Box, ScopedDatabaseObject ):
    MIN_FILTER_LEN = 3 # what is the minimum length for the filter string
    FILTER_COLUMNS = ( 1, 2, 11, 12 ) # which columns should be used for filtering
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
        self.builder.add_from_file( paths.data("ui","widgets","invoicewindow", "invoicetable.glade"))
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        # Connect Signals
        self.builder.connect_signals( self )

        # Use the selection function
        self.builder.get_object( 'invoices_treeview_selection' ).set_select_function( self._is_row_selection_changeable, None )

        model = self.builder.get_object( "invoices_liststore" )
        self._invoices_treemodelfilter = model.filter_new()
        self._invoices_treemodelfilter.set_visible_func( self._is_row_visible )
        self._invoices_treemodelsort = Gtk.TreeModelSort( self._invoices_treemodelfilter )

        self.builder.get_object( "invoices_id_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "invoices_id_cellrenderertext" ), self.id_cell_data_func )
        self.builder.get_object( "invoices_customer_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "invoices_customer_cellrenderertext" ), self.customer_cell_data_func )
        self.builder.get_object( "invoices_contractrefid_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "invoices_contractrefid_cellrenderertext" ), self.contractrefid_cell_data_func )
        self.builder.get_object( "invoices_number_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "invoices_number_cellrenderertext" ), self.number_cell_data_func )
        self.builder.get_object( "invoices_date_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "invoices_date_cellrenderertext" ), self.date_cell_data_func )
        self.builder.get_object( "invoices_value_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "invoices_value_cellrenderertext" ), self.value_cell_data_func )
        self.builder.get_object( "invoices_valueleft_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "invoices_valueleft_cellrenderertext" ), self.valueleft_cell_data_func )

        # Add properties
        self.needs_refresh = True
        self.currently_refreshing = False
        self._active_only = True
        self._filter = ""
        self._selection_blocked = False
        self._current_selection = None

    # Data interaction
    def clear( self ):
        self.builder.get_object( "invoices_liststore" ).clear()
    def get_contents( self ):
        return [row[0] for row in self.builder.get_object( "invoices_liststore" )]
    def _do_refresh( self, step=25 ):
        self.currently_refreshing = True
        self.needs_refresh = False
        self.emit( 'refresh-started' )
        treeview = self.builder.get_object( "invoices_treeview" )
        model = self.builder.get_object( "invoices_liststore" )
        treeview.freeze_child_notify()
        self.set_sensitive( False )
        treeview.set_model( None )
        del self._invoices_treemodelsort
        del self._invoices_treemodelfilter
        for i, invoice in enumerate( core.database.Invoice.get_all( session=self.session ) ):
            rowref = self.add_invoice( invoice )
            del rowref
            # change something
            if i % step == 0:
                # freeze/thaw not really  necessary here as sorting is wrong because of the
                # default sort function
                logger.debug("Refreshed %d rows", i)
        self._invoices_treemodelfilter = model.filter_new()
        self._invoices_treemodelfilter.set_visible_func( self._is_row_visible )
        GLib.idle_add( self.refilter )
        self._invoices_treemodelsort = Gtk.TreeModelSort( self._invoices_treemodelfilter )
        treeview.set_model( self._invoices_treemodelsort )
        treeview.thaw_child_notify()
        self.set_sensitive( True )
        self.currently_refreshing = False
        self.emit( 'refresh-ended' )
        return False
    def refresh( self ):
        GLib.idle_add(self._do_refresh)
    def add_invoice( self, invoice ):
        model = self.builder.get_object( "invoices_liststore" )
        treeiter = model.append( [ invoice ] )
        return InvoiceRowReference( model, model.get_path( treeiter ) )
    def remove( self, rowref ):
        if not isinstance( rowref, InvoiceRowReference ):
            raise TypeError( "Expected msmgui.invoicetable.InvoiceRowReference, not {}".format( type( rowref ).__name__ ) )
        invoice = rowref.get_invoice()
        self.session.delete( self.session.merge( invoice ) )
        self.session.commit()
        self.session.remove()
        model = rowref.get_model()
        treeiter = rowref.get_iter()
        model.remove( treeiter ) # Remove row from table
    # Getting and setting rows
    def _get_rowref_by_invoice_id( self, invoice_id ):
        if not isinstance( invoice_id, int ):
            raise TypeError( "Expected int, not {}".format( type( invoice_id ).__name__ ) )
        model = self.builder.get_object( "invoices_liststore" )
        treeiter = model.get_iter_first()
        while treeiter != None:
            invoice = model[treeiter][0]
            if invoice.id == invoice_id:
                return InvoiceRowReference( model, model.get_path( treeiter ) )
            treeiter = model.iter_next( treeiter )
        return None
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
        if hasattr( self, '_invoices_treemodelfilter' ):
            self._invoices_treemodelfilter.refilter()
        return False
    @property
    def active_only( self ):
        '''Show only active invoices (i.e. invoices with running contracts)'''
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
        rowref = InvoiceRowReference( model, model.get_path( treeiter ) )
        if rowref == self.selection:
            # if self.selection and self.selection.get_row() is row:
            return True # Prevent currently selected row from being hidden
        invoice = rowref.get_invoice()
        if self.active_only and not invoice.value_left:
            return False # if active_only is True, then invoices without contracts are hidden
        if len( self.filter ) < InvoiceTable.MIN_FILTER_LEN:
            return True
        else:
            return True
            """for column in InvoiceTable.FILTER_COLUMNS:
                if self.filter.lower() in row[column].lower():
                    return True"""
        return False
    # Selection of a row
    @property
    def selection( self ):
        """The string used to filter the table"""
        return self._current_selection
    @selection.setter
    def selection( self, new_selection ):
        treeselection = self.builder.get_object( "invoices_treeview_selection" )
        if new_selection is None:
            treeselection.unselect_all()
            self._current_selection = None
        elif isinstance( new_selection, int ) or isinstance( new_selection, InvoiceRowReference ):
            if isinstance( new_selection, int ):
                rowref = self._get_rowref_by_invoice_id( new_selection )
            else:
                rowref = new_selection
            if self.selection is None or self._current_selection.get_row() is not rowref.get_row():
                new_selection_iter = rowref.get_selection_iter( treeselection.get_tree_view().get_model() )
                if new_selection_iter is not None:
                    treeselection.select_iter( new_selection_iter )
                    self._current_selection = rowref
            else:
                raise ValueError
        else:
            raise TypeError( "Expected int, InvoiceRowReference or None, not {}".format( type( new_selection ).__name__ ) )
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
    # Cell data funcs (control how Gtk.TreeModel contents are displayed)
    def id_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = InvoiceRowReference( model, model.get_path( treeiter ) )
        invoice = rowref.get_invoice()
        new_text = invoice.id if invoice.id else ""
        cellrenderer.set_property( 'text', str( new_text ) )
    def customer_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = InvoiceRowReference( model, model.get_path( treeiter ) )
        invoice = rowref.get_invoice()
        contract = invoice.contract
        if not contract or not contract.refid:
            raise RuntimeError
        customer = contract.customer
        new_text = customer.name
        cellrenderer.set_property( 'text', new_text )
    def contractrefid_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = InvoiceRowReference( model, model.get_path( treeiter ) )
        invoice = rowref.get_invoice()
        contract = invoice.contract
        if not contract or not contract.refid:
            raise RuntimeError
        new_text = contract.refid
        cellrenderer.set_property( 'text', new_text )
    def number_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = InvoiceRowReference( model, model.get_path( treeiter ) )
        invoice = rowref.get_invoice()
        new_text = invoice.number if invoice.number else ""
        cellrenderer.set_property( 'text', str( new_text ) )
    def date_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = InvoiceRowReference( model, model.get_path( treeiter ) )
        invoice = rowref.get_invoice()
        if invoice.date:
            new_text = invoice.date.strftime("%x")
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def value_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = InvoiceRowReference( model, model.get_path( treeiter ) )
        invoice = rowref.get_invoice()
        if invoice.value:
            new_text = locale.currency( invoice.value )
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def valueleft_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = InvoiceRowReference( model, model.get_path( treeiter ) )
        invoice = rowref.get_invoice()
        value_left = invoice.value_left
        if value_left:
            new_text = locale.currency( value_left )
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    # Callbacks
    def invoices_treeview_button_press_event_cb( self, treeview, event ):
        info = treeview.get_path_at_pos( int( event.x ), int( event.y ) )
        if not info:
            return
        path, column, x, y = info
        if column is not self.builder.get_object( "invoice_previewpdf_treeviewcolumn" ):
            return
        model = treeview.get_model()
        rowref = InvoiceRowReference( model, path )
        invoice = rowref.get_invoice()
        letter = core.database.Letter( invoice.contract, contents=[ invoice, ] )
        watcher = LetterPreviewRenderer( letter )
        watcher.start()
    def invoices_treeview_selection_changed_cb( self, selection ):
        if self.selection_blocked:
            self.selection = self.selection # Restore current selection
            return
        model, treeiter = selection.get_selected()
        if treeiter:
            rowref = InvoiceRowReference( model, model.get_path( treeiter ) )
        else:
            rowref = None
        if self.selection != rowref:
            self.selection = rowref
            GLib.idle_add( self.refilter )
            self.emit( "selection-changed" )

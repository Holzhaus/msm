#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from gi.repository import Gtk, GObject
import core.database
import msmgui.rowreference
import locale
class BalanceRowReference( msmgui.rowreference.GenericRowReference ):
    def get_entry( self ):
        """Returns the core.database.Contract that is associated with the Gtk.TreeRow that this instance references."""
        row = self.get_row()
        entry = row[0]
        if not isinstance( entry, core.database.Debit ) and not isinstance( entry, core.database.Credit ):
            raise RuntimeError( "tried to get an entry that does not exist" )
        return entry
class BalanceEditor( Gtk.Box ):
    """Balance editor inside the Customer editor"""
    __gsignals__ = {
        'changed': ( GObject.SIGNAL_RUN_FIRST, None, () ),
    }
    def __init__( self ):
        Gtk.Box.__init__( self )
        self._customer = None
        self.signals_blocked = True
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/widgets/customerwindow/customereditor/balanceeditor.glade" )
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        # Connect Signals
        self.builder.connect_signals( self )
        self.builder.get_object( "balance_date_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "balance_date_cellrenderertext" ), self.date_cell_data_func )
    """Cell data funcs (control how Gtk.TreeModel contents are displayed)"""
    def date_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = BalanceRowReference( model, model.get_path( treeiter ) )
        entry = rowref.get_entry()
        if entry.date:
            new_text = entry.date.strftime( locale.nl_langinfo( locale.D_FMT ) )
        else:
            new_text = "Unbekannt"
        cellrenderer.set_property( 'text', new_text )
    def debit_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = BalanceRowReference( model, model.get_path( treeiter ) )
        entry = rowref.get_entry()
        if isinstance( entry, core.database.Debit ):
            new_text = locale.currency( entry.value )
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def credit_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = BalanceRowReference( model, model.get_path( treeiter ) )
        entry = rowref.get_entry()
        if isinstance( entry, core.database.Credit ):
            new_text = locale.currency( entry.value )
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def description_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = BalanceRowReference( model, model.get_path( treeiter ) )
        entry = rowref.get_entry()
        if entry.description:
            new_text = locale.currency( entry.description )
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    """Callbacks"""
    def add_entry( self, entry ):
        """Add an entry to the Gtk.Treemodel"""
        model = self.builder.get_object( "balance_liststore" )
        treeiter = model.append( [ entry ] )
        path = model.get_path( treeiter )
        rowref = BalanceRowReference( model, path )
        return rowref
    def _gui_clear( self ):
        self.builder.get_object( "balance_liststore" ).clear()
    def _gui_fill( self ):
        self._gui_clear()
        for entry in self._customer.debits_and_credits:
            self.add_entry( entry )
    def start_edit( self, customer ):
        self._customer = customer
        self._gui_fill()
    def balance_treeview_selection_changed_cb( self, selection ):
        pass

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
from gi.repository import Gtk, GObject
import core.database
from core.letterrenderer import LetterPreviewRenderer
import msmgui.rowreference
from msmgui.widgets.base import ScopedDatabaseObject
class CorrespondeceRowReference( msmgui.rowreference.GenericRowReference ):
    def get_letter( self ):
        """Returns the core.database.Letter that is associated with the Gtk.TreeRow that this instance references."""
        row = self.get_row()
        letter = row[0]
        if not isinstance( letter, core.database.Letter ):
            raise RuntimeError( "tried to get a letter that does not exist" )
        return letter

class CorrespondenceEditor( Gtk.Box, ScopedDatabaseObject ):
    """
    Correspondence editor inside the Customer editor
    """
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
        self.builder.add_from_file( "data/ui/widgets/customerwindow/customereditor/correspondenceeditor.glade" )
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        # Connect Signals
        self.builder.connect_signals( self )
        self.builder.get_object( "letters_id_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "letters_id_cellrenderertext" ), self.id_cell_data_func )
        self.builder.get_object( "letters_date_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "letters_date_cellrenderertext" ), self.date_cell_data_func )
        self.builder.get_object( "letters_contract_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "letters_contract_cellrenderertext" ), self.contract_cell_data_func )
        self.builder.get_object( "letters_contents_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "letters_contents_cellrenderertext" ), self.contents_cell_data_func )
    def add_letter( self, letter ):
        """
        Add a letter to the Gtk.Treemodel
        """
        model = self.builder.get_object( "letters_liststore" )
        treeiter = model.append( [ letter ] )
        path = model.get_path( treeiter )
        rowref = CorrespondeceRowReference( model, path )
        self.emit( "changed" )
        return rowref
    def _gui_clear( self ):
        self.builder.get_object( "letters_liststore" ).clear()
    def _gui_fill( self ):
        self._gui_clear()
        for contract in self._customer.contracts:
            for letter in contract.letters:
                self.add_letter( letter )
    def start_edit( self, customer ):
        self._customer = customer
        self._gui_fill()
    # Cell data funcs (control how Gtk.TreeModel contents are displayed)
    def id_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = CorrespondeceRowReference( model, model.get_path( treeiter ) )
        letter = rowref.get_letter()
        if letter.id:
            new_text = str( letter.id )
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def date_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = CorrespondeceRowReference( model, model.get_path( treeiter ) )
        letter = rowref.get_letter()
        if letter.date:
            new_text = letter.date.strftime( locale.nl_langinfo( locale.D_FMT ) )
        else:
            raise ValueError( "Letter must have a date" )
        cellrenderer.set_property( 'text', new_text )
    def contract_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = CorrespondeceRowReference( model, model.get_path( treeiter ) )
        letter = rowref.get_letter()
        if letter.contract:
            new_text = letter.contract.refid
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    def contents_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = CorrespondeceRowReference( model, model.get_path( treeiter ) )
        letter = rowref.get_letter()
        if letter.contents:
            new_text = ""
            for content in letter.contents:
                if type( content ) is core.database.Invoice:
                    new_text += "Rechnung, "
                elif type( content ) is core.database.Note:
                    new_text += content.name
                else:
                    raise TypeError( 'Unknown LetterPart' )
            new_text = new_text.rstrip().rstrip( ',' )
        else:
            new_text = ""
        cellrenderer.set_property( 'text', new_text )
    # Callbacks
    def letters_treeview_button_press_event_cb( self, treeview, event ):
        info = treeview.get_path_at_pos( int( event.x ), int( event.y ) )
        if not info:
            return
        path, column, x, y = info
        if column is not self.builder.get_object( "letters_previewpdf_treeviewcolumn" ):
            return
        model = treeview.get_model()
        rowref = CorrespondeceRowReference( model, path )
        letter = rowref.get_letter()
        watcher = LetterPreviewRenderer( letter )
        watcher.start()

#!/usr/bin/env python
from gi.repository import Gtk, Gdk, GObject, GdkPixbuf
from core.database import Note
from core.lettercomposition import InvoicePlaceholder, Criterion
import msmgui.rowreference
TARGET_ENTRY_PYOBJECT = 0
COLUMN_PYOBJECT, COLUMN_TEXT, COLUMN_PIXBUF = range( 3 )
DRAG_ACTION = Gdk.DragAction.COPY

class LetterPartRowReference( msmgui.rowreference.GenericRowReference ):
        def get_object( self ):
            """Returns the core.database.Invoice that is associated with the Gtk.TreeRow that this instance references."""
            row = self.get_row()
            obj = row[0]
            return obj
class LetterCompositor( Gtk.Box ):
    __gsignals__ = {
        'changed': ( GObject.SIGNAL_RUN_FIRST, None, ( bool, ) )
    }
    def __init__( self ):
        Gtk.Box.__init__( self )
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/widgets/lettercompositor.glade" )
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        self.builder.connect_signals( self )
        self._dragarea = DragArea()
        self._droparea = DropArea( self._dragarea.get_model() )
        self.builder.get_object( "dragareabox" ).pack_start( self._dragarea, True, True, 0 )
        self.builder.get_object( "dropareabox" ).pack_start( self._droparea, True, True, 0 )
        self._droparea.connect( "changed", self.droparea_changed_cb )
        """
        Set up DnD targets
        """
        targets = Gtk.TargetList.new( [] )
        targets.add( Gdk.Atom.intern( "MSMLetterPart", False ), Gtk.TargetFlags.SAME_APP, TARGET_ENTRY_PYOBJECT )
        self._droparea.drag_dest_set_target_list( targets )
        self._dragarea.drag_source_set_target_list( targets )
    @staticmethod
    def get_letterpart_info( obj ):
        if isinstance( obj, InvoicePlaceholder ):
            name = "Rechnungen"
            icon_name = "image-missing"
        elif isinstance( obj, Note ):
            name = "Anschreiben: {}".format( obj.name )
            icon_name = "text-x-generic"
        else:
            raise TypeError( 'Unhandled type: {}'.format( obj.__class__.__name__ ) )
        return name, icon_name
    def get_composition( self ):
        return self._droparea.get_composition()
    def droparea_changed_cb( self, droparea, not_empty ):
        self.emit( "changed", not_empty )

class DragArea( Gtk.IconView ):
    def __init__( self ):
        Gtk.IconView.__init__( self )
        self.set_text_column( COLUMN_TEXT )
        self.set_pixbuf_column( COLUMN_PIXBUF )
        model = Gtk.ListStore( GObject.TYPE_PYOBJECT, str, GdkPixbuf.Pixbuf )
        self.set_model( model )
        self.add_item( InvoicePlaceholder() )
        for note in Note.get_all():
            print( note )
            self.add_item( note )
            obj_session = note.session
            if obj_session:
                obj_session.expunge( note )
        self.enable_model_drag_source( Gdk.ModifierType.BUTTON1_MASK, [], DRAG_ACTION )
        self.connect( "drag-data-get", self.drag_data_get_cb )
    def drag_data_get_cb( self, widget, drag_context, data, info, time ):
        path = self.get_selected_items()[0]
        data.set( Gdk.Atom.intern( "MSMLetterPart", False ), 32, str( path ).encode( "utf-8" ) )
    def add_item( self, obj ):
        name, icon = LetterCompositor.get_letterpart_info( obj )
        pixbuf = Gtk.IconTheme.get_default().load_icon( icon, 16, 0 )
        self.get_model().append( [obj, name, pixbuf] )

class DropArea( Gtk.Box ):
    __gsignals__ = {
        'changed': ( GObject.SIGNAL_RUN_FIRST, None, ( bool, ) )
    }
    def __init__( self, model ):
        Gtk.Box.__init__( self )
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/widgets/lettercompositordroparea.glade" )
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        self.builder.connect_signals( self )
        self.drag_dest_set( Gtk.DestDefaults.ALL, [], DRAG_ACTION )
        self.connect( "drag-data-received", self.on_drag_data_received, model )
        self.builder.get_object( "name_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "name_cellrenderertext" ), self.name_cell_data_func )
        self.builder.get_object( "criterion_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "criterion_cellrenderercombo" ), self.criterion_cell_data_func )
        self.builder.get_object( "lettercomposition_treeview" ).set_reorderable( True )
        criterions = [Criterion.Always, Criterion.OnlyOnInvoice, Criterion.OnlyOnDirectWithdrawal]
        for criterion in criterions:
            self.builder.get_object( "criterion_liststore" ).append( [ "", criterion ] )
    def get_composition( self ):
        composition = []
        for row in self.builder.get_object( "lettercomposition_liststore" ):
            composition.append( ( row[0], row[1] ) )
        return composition
    def lettercomposition_treeview_key_press_event_cb( self, treeview, event ):
        keyname = Gdk.keyval_name( event.keyval )
        if keyname == "Delete":
            selection = treeview.get_selection()
            model, treeiter = selection.get_selected()
            model.remove( treeiter )
            self.emit( "changed", len( model ) != 0 )
    def on_drag_data_received( self, widget, drag_context, x, y, data, info, time, model ):
        path = Gtk.TreePath( data.get_data().decode( "utf-8" ) )
        rowref = LetterPartRowReference( model, path )
        obj = rowref.get_object()
        dropmodel = self.builder.get_object( "lettercomposition_treeview" ).get_model()
        for row in dropmodel:
            if obj in row:
                return # Already in model, do not add again
        dropmodel.append( [obj, None] )
        self.emit( "changed", len( dropmodel ) != 0 )
    def name_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        obj = model[treeiter][0]
        name, icon = LetterCompositor.get_letterpart_info( obj )
        cellrenderer.set_property( 'text', name )
    def criterion_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        criterion = model[treeiter][1]
        text = Criterion.get_text( criterion )
        cellrenderer.set_property( 'text', text )
    def criterion_cellrenderercombo_editing_started_cb( self, combo, editable, path_string ):
        cellview = editable.get_child()
        renderer_text = cellview.get_cells()[0]
        cellview.set_cell_data_func( renderer_text, self.criterion_cell_data_func, None )
    def criterion_cellrenderercombo_changed_cb( self, combo, path_string, new_iter ):
        criterion = Criterion.Always
        if isinstance( new_iter, Gtk.TreeIter ):
            combomodel = self.builder.get_object( "criterion_liststore" )
            criterion = combomodel[new_iter][1]
        model = self.builder.get_object( 'lettercomposition_liststore' )
        model[Gtk.TreePath( path_string )][1] = criterion
        self.emit( "changed", len( self.builder.get_object( 'lettercomposition_liststore' ) ) )

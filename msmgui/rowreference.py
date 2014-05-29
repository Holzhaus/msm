#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
logger = logging.getLogger( __name__ )
from gi.repository import Gtk
class GenericRowReference( object ):
    """For some strange reason (probably because of the weird constructor) I cannot
       subclass Gtk.TreeRowReference, which sucks hard. Therefore I need to create a
       whole new object that stores a Gtk.TreeRowReference internally.

       PyGObject, I hate you. You're a badly documented son-of-a-bitch."""
    def __eq__( self, rowref ):
        if type( rowref ) != type( self ):
            return False
        if self.get_model() == rowref.get_model() and  self.get_path() == rowref.get_path():
            return True
        return False
    def __neq__( self, rowref ):
        return not self.__eq__( rowref )
    def __init__( self, model, path ):
        """Constructor. Internally, the reference always points to the row in the base Gtk.TreeModel."""
        self._rowref = Gtk.TreeRowReference.new( model, path )
    def get_path( self ):
        """Returns the Gtk.TreePath to the Gtk.TreeRow that this instance points to.

        Notice: This is simply a wrapper to the get_path() method of the internally
        stored Gtk.TreeRowReference."""
        return self._rowref.get_path()
    def get_model( self ):
        """Returns the base Gtk.TreeModel.

        Notice: This is simply a wrapper to the get_model() method of the internally
        stored Gtk.TreeRowReference."""
        return self._rowref.get_model()
    def get_iter( self ):
        """Returns the Gtk.TreeIter for the base Gtk.TreeModel."""
        model = self.get_model()
        treeiter = model.get_iter( self.get_path() )
        return treeiter
    def get_row( self ):
        """Returns the Gtk.TreeRow that this instance references."""
        model = self.get_model()
        path = self.get_path()
        return model[path]
    def set_row( self, rowdata ):
        """Sets new row data for the Gtk.TreeRow that this instance references."""
        model = self.get_model()
        path = self.get_path()
        # TODO: Maybe do some rowdata typechecking in subclasses
        model[path] = rowdata

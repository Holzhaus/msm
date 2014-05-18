#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from gi.repository import Gtk
class AboutDialog( object ):
    def __init__( self, parent ):
        self._parent = parent
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/dialogs/about.glade" )
        self.builder.get_object( "content" ).set_transient_for( self._parent )
        self.builder.get_object( "content" ).set_modal( True )
        # Connect Signals
        self.builder.connect_signals( self )
        self.hide()
    def show( self ):
        self.builder.get_object( "content" ).run()
    def hide( self ):
        self.builder.get_object( "content" ).hide()
    """Callbacks"""
    def aboutdialog_close_cb( self, aboutdialog ):
        self.hide()
    def aboutdialog_response_cb( self, aboutdialog, response ):
        self.hide()

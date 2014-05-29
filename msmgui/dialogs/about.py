#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
logger = logging.getLogger( __name__ )
from gi.repository import Gtk
class AboutDialog( object ):
    def __init__( self, parent ):
        """
        __init__ function.
        Arguments:
            parent:
                the parent window of this dialog.
        """
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
        """
        Shows the dialog.
        """
        self.builder.get_object( "content" ).run()
    def hide( self ):
        """
        Hides the dialog.
        """
        self.builder.get_object( "content" ).hide()
    # Callbacks
    def aboutdialog_close_cb( self, aboutdialog ):
        """
        Callback function for the "close" signal of the dialog.
        Hides the dialog.
        Arguments:
            aboutdialog:
                the AboutDialog that emitted the signal.
        """
        self.hide()
    def aboutdialog_response_cb( self, aboutdialog, response ):
        """
        Callback function for the "response" signal of the dialog.
        Hides the dialog.
        Arguments:
            aboutdialog:
                the AboutDialog that emitted the signal.
            response:
                the response of the dialog.
        """
        self.hide()

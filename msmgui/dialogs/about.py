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

#!/usr/bin/env python3
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
import logging.config
import os.path
def logging_init():
    logfile = os.path.join( os.path.dirname( __file__ ), 'data', 'logging.cfg' )
    logging.config.fileConfig( logfile )
logging_init()
logger = logging.getLogger()
import sys
from gi.repository import Gtk, Gio, GObject
from gi.repository.GLib import GError
import msmgui.main
from core.config import Config
from core.database import Database
import msmgui.lib.exceptionhook
from msmgui.dialogs.preferences import PreferencesDialog

class MagazineSubscriptionManager( Gtk.Application ):
    def __init__( self ):
        """
        __init__ function.
        """
        Gtk.Application.__init__( self,
                                  application_id="apps.holzhaus.magazinesubscriptionmanager",
                                  flags=Gio.ApplicationFlags.FLAGS_NONE )
        self.set_property( "register-session" , True )
        self.connect( "activate", self.on_activate )
        self.connect( "startup", self.on_startup )
    def on_activate( self, data=None ):
        """
        Callback for the "activate"-signal of the Gtk.Application.
        Presents the MainWindow if the application is already running.
        Arguments:
            data:
                additional data passed to this function
        """
        if len( self.get_windows() ):
            self.get_windows()[0].present()
    def on_startup( self, data=None ):
        """
        Callback for the "startup"-signal of the Gtk.Application.
        Initializes the GUI of the application.
        Arguments:
            data:
                additional data passed to this function
        """
        logger.debug( 'Starting up...' )
        self.config = Config
        db_uri = self.config.get( "Database", "db_uri" )
        self.database = Database( db_uri )
        # Start building the GUI
        builder = Gtk.Builder()
        builder.add_from_file( "data/ui/menu.ui" )
        # We use the method Gtk.Application.set_menubar(menubar) to
        # add the menubar to the application (Note: NOT the window!)
        self.set_menubar( builder.get_object( "menubar" ) )
        self.set_app_menu( builder.get_object( "appmenu" ) )
        self._mainwindow = msmgui.main.MainWindow( self )
        self._preferencesdialog = PreferencesDialog( self._mainwindow )
        self.add_window( self._mainwindow )
        # AppMenu Actions
        settings_action = Gio.SimpleAction.new( "settings", None )
        settings_action.connect( "activate", self.settings_cb )
        self.add_action( settings_action )
        quit_action = Gio.SimpleAction.new( "quit", None )
        quit_action.connect( "activate", self.quit_cb )
        self.add_action( quit_action )
        self._mainwindow.show_all()
        self._mainwindow.present()
        logger.debug( 'Startup finished, presenting MainWindow...' )
    # Callbacks for AppMenu Actions
    def settings_cb( self, action, parameter ):
        """
        Callback for the "settings"-action of the AppMenu.
        Shows the preferences dialog.
        Arguments:
            action:
                the Gio.SimpleAction that emitted the "activate" signal
            parameter:
                the parameter to the activation
        """
        self._preferencesdialog.show()
    def quit_cb( self, action, parameter ):
        """
        Callback for the "quit"-action of the AppMenu.
        Tries to close the CustomerEditor and quits.
        Arguments:
            action:
                the Gio.SimpleAction that emitted the "activate" signal
            parameter:
                the parameter to the activation
        """
        if self.mainwindow.customereditor.end_edit():
            Gtk.main_quit()
            sys.exit()

if __name__ == "__main__":
    logger.debug( 'Initializing' )
    msmgui.lib.exceptionhook.install()
    GObject.threads_init() # Yup, we use threading in this application ;-)
    msmapp = MagazineSubscriptionManager()
    logger.debug( 'Running app...' )
    msmapp.run( None )

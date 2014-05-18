#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from gi.repository import Gtk, Gio, GObject
import msmgui.main
import core.database
import msmgui.dialogs.preferences

class MagazineSubscriptionManager( Gtk.Application ):
    def __init__( self ):
        Gtk.Application.__init__( self, application_id="apps.holzhaus.magazinesubscriptionmanager",
                                 flags=Gio.ApplicationFlags.FLAGS_NONE )
        self.set_property( "register-session" , True )
        self.connect( "activate", self.on_activate )
        self.connect( "startup", self.on_startup )
    def on_activate( self, data=None ):
        if len( app.get_windows() ):
            app.get_windows()[0].present()
    def on_startup( self, data=None ):
        self.config = core.config.Configuration()
        self.database = core.database.Database( self.config.get( "Database", "db_uri" ) )

        # a builder to add the UI designed with Glade to the grid:
        builder = Gtk.Builder()
        # get the file (if it is there)
        try:
            builder.add_from_file( "data/ui/menu.ui" )
        except:
            print( "file not found" )
            sys.exit()
        # we use the method Gtk.Application.set_menubar(menubar) to add the menubar
        # to the application (Note: NOT the window!)
        self.set_menubar( builder.get_object( "menubar" ) )
        self.set_app_menu( builder.get_object( "appmenu" ) )
        self._mainwindow = msmgui.main.MainWindow( self, self.database )
        self._preferencesdialog = msmgui.dialogs.preferences.PreferencesDialog( self._mainwindow )
        self.add_window( self._mainwindow )

        """AppMenu Actions"""
        settings_action = Gio.SimpleAction.new( "settings", None )
        settings_action.connect( "activate", self.settings_cb )
        self.add_action( settings_action )

        quit_action = Gio.SimpleAction.new( "quit", None )
        quit_action.connect( "activate", self.quit_cb )
        self.add_action( quit_action )
        self._mainwindow.show_all()

    """Callbacks for AppMenu Actions"""
    def settings_cb( self, action, parameter ):
        self._preferencesdialog.show()
    def quit_cb( self, action, parameter ):
        if self.mainwindow.customereditor.endEdit():
            Gtk.main_quit()
            sys.exit()
if __name__ == "__main__":
    GObject.threads_init()
    app = MagazineSubscriptionManager()
    app.run( None )

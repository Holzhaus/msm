#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This is derived from a PyGTK-script by Jonas Wagner <jonas@29a.ch>
URL: http://29a.ch/2009/1/8/pygtk-exception-hook
It was modified to work with Python 3.x and PyGObject Introspection.
"""
from gi.repository import Gtk, GLib
import sys
import cgitb

def scrolled( widget, shadow=Gtk.ShadowType.NONE ):
    window = Gtk.ScrolledWindow()
    window.set_shadow_type( shadow )
    window.set_policy( Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC )
    window.add_with_viewport( widget )
    return window

_ = lambda s: s

class ExceptionDialog( Gtk.MessageDialog ):
    def __init__( self, etype, evalue, etb ):
        Gtk.MessageDialog.__init__( self, buttons=Gtk.ButtonsType.CLOSE, type=Gtk.MessageType.ERROR )
        self.set_resizable( True )
        self.set_markup( _( "An error has occured:\n%r\nYou should save "
                "your work and restart the application. If the error "
                "occurs again please report it to the developer." % evalue ) )
        text = cgitb.text( ( etype, evalue, etb ), 5 )
        expander = Gtk.Expander()
        expander.set_label( _( "Exception Details" ) )
        self.vbox.pack_start( expander, True, True, 0 )
        textview = Gtk.TextView()
        textview.get_buffer().set_text( text )
        expander.add( scrolled( textview ) )
        self.show_all()

def install_exception_hook( dialog=ExceptionDialog ):
    old_hook = sys.excepthook
    def new_hook( etype, evalue, etb ):
        if etype not in ( KeyboardInterrupt, SystemExit ):
            d = dialog( etype, evalue, etb )
            d.run()
            d.destroy()
        old_hook( etype, evalue, etb )
    new_hook.old_hook = old_hook
    sys.excepthook = new_hook


if __name__ == "__main__":
    install_exception_hook()
    GLib.idle_add( lambda: 1 / 0 )
    GLib.idle_add( Gtk.main_quit )
    Gtk.main()

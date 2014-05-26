#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This is derived from a PyGTK-script by Jonas Wagner <jonas@29a.ch>
URL: http://29a.ch/2009/1/8/pygtk-exception-hook
It was modified to work with Python 3.x and PyGObject Introspection.
"""
from gi.repository import Gtk, GLib, Pango
import sys
import cgitb

_ = lambda s: s

class ExceptionDialog( Gtk.Dialog ):
    def __init__( self, etype, evalue, etb ):
        Gtk.Dialog.__init__( self ) # , buttons=Gtk.ButtonsType.CLOSE, type=Gtk.MessageType.ERROR )
        text = cgitb.text( ( etype, evalue, etb ), 5 )
        self.set_resizable( True )
        # Build GUI
        self.add_button( _( "Close" ), 0 )
        self.add_button( _( "Close and Quit (recommended)" ), 1 )
        box = Gtk.Box()
        box.set_orientation( Gtk.Orientation.VERTICAL )
        box.set_border_width( 5 )
        self.get_content_area().pack_start( box, True, True, 0 )

        label = Gtk.Label()
        label.set_markup( _( "An error has occured:\n    %r\nYou should save "
                             "your work and restart the application.\nIf the error "
                             "occurs again please report it to the developer." % evalue ) )
        box.pack_start( label, False, True, 0 )

        expander = Gtk.Expander()
        expander.set_label( _( "Exception Details" ) )
        expander.connect( "notify::expanded", self._autoshrink )
        box.pack_start( expander, True, True, 0 )

        textview = Gtk.TextView()
        textview.modify_font( Pango.FontDescription ( "Fixed" ) )
        scrolledwindow = Gtk.ScrolledWindow()
        scrolledwindow.add_with_viewport( textview )
        scrolledwindow.set_vexpand( True )
        expander.set_vexpand( False )
        expander.add( scrolledwindow )

        textview.get_buffer().set_text( text )
        self._autoshrink()
        self.show_all()
    def _autoshrink( self, expander=None, user_data=None ):
        box = self.get_content_area()
        size = box.get_preferred_size()[1]
        self.resize( size.width, size.height );

def install( dialog=ExceptionDialog ):
    old_hook = sys.excepthook
    def new_hook( etype, evalue, etb ):
        if etype not in ( KeyboardInterrupt, SystemExit ):
            d = dialog( etype, evalue, etb )
            response = d.run()
            if response == 1:
                GLib.idle_add( Gtk.main_quit )
            d.destroy()
        old_hook( etype, evalue, etb )
    new_hook.old_hook = old_hook
    sys.excepthook = new_hook


if __name__ == "__main__":
    install()
    GLib.idle_add( lambda: 1 / 0 )
    Gtk.main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This is derived from a PyGTK-script by Jonas Wagner <jonas@29a.ch>
URL: http://29a.ch/2009/1/8/pygtk-exception-hook
It was modified to work with Python 3.x and PyGObject Introspection.
"""
from gi.repository import Gtk, GLib, Pango
import sys
import os
import tempfile
import cgitb
import traceback
import threading

# If gettext is not used
try: _
except NameError:
    def _( s ): return s

class ExceptionDialog( Gtk.Dialog ):
    def __init__( self, doc, etype, evalue, etb ):
        Gtk.Dialog.__init__( self ) # , buttons=Gtk.ButtonsType.CLOSE, type=Gtk.MessageType.ERROR )
        self.set_size_request( 600, 200 )
        self.set_resizable( True )
        self.set_title( _( "Error occured!" ) )
        # Build GUI
        self.add_button( _( "Close and Quit" ), 0 )
        box = Gtk.Box()
        box.set_orientation( Gtk.Orientation.VERTICAL )
        box.set_border_width( 5 )
        self.get_content_area().pack_start( box, True, True, 0 )

        label = Gtk.Label()
        box.pack_start( label, False, False, 0 )

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

        textview.get_buffer().set_text( doc )
        self._autoshrink()
        self.show_all()
        label.set_markup( _( "An error has occured:\n<tt>  %r</tt>\nYou should save "
                             "your work and restart the application. If the error "
                             "occurs again please report it to the developer." ) % evalue )
        label.set_line_wrap( True )
    def _autoshrink( self, expander=None, user_data=None ):
        box = self.get_content_area()
        size = box.get_preferred_size()[0]
        cur_width = self.get_size()[0]
        self.resize( cur_width, size.height );

class Hook:
    """
    A hook to replace sys.excepthook that shows tracebacks in in a Gtk.Dialog.
    """
    def __init__( self, logdir=None, context=5, file=None, dialog=ExceptionDialog ):
        self.logdir = logdir # log tracebacks to files if not None
        self.context = context # number of source code lines per frame
        self.file = file or sys.stdout # place to send the output
        self.dialog = dialog
        self.done = False

    def __call__( self, etype, evalue, etb ):
        if etype not in ( KeyboardInterrupt, SystemExit ) and not self.done:
            self.done = True
            GLib.idle_add( self.handle, ( etype, evalue, etb ) )

    def handle( self, info=None ):
        info = info or sys.exc_info()

        try:
            doc = cgitb.text( info, self.context )
        except: # just in case something goes wrong
            doc = ''.join( traceback.format_exception( *info ) )

        if self.logdir is not None:
            suffix = '.txt'
            ( fd, path ) = tempfile.mkstemp( suffix=suffix, dir=self.logdir )
            try:
                file = os.fdopen( fd, 'w' )
                file.write( doc )
                file.close()
                msg = '%s contains the description of this error.' % path
            except:
                msg = 'Tried to save traceback to %s, but failed.' % path
            self.file.write( msg + '\n' )
        try:
            self.file.flush()
        except: pass

        d = self.dialog( doc, *info )
        d.run()
        sys.exit( 1 )

def install_threads():
    """
    Workaround for sys.excepthook thread bug
    From
    http://spyced.blogspot.com/2007/06/workaround-for-sysexcepthook-bug.html
    (https://sourceforge.net/tracker/?func=detail&atid=105470&aid=1230540&group_id=5470).
    Call once from __main__ before creating any threads.
    If using psyco, call psyco.cannotcompile(threading.Thread.run)
    since this replaces a new-style class method.
    """
    init_old = threading.Thread.__init__
    def init( self, *args, **kwargs ):
        init_old( self, *args, **kwargs )
        run_old = self.run
        def run_with_except_hook( *args, **kw ):
            try:
                run_old( *args, **kw )
            except ( KeyboardInterrupt, SystemExit ):
                raise
            except:
                sys.excepthook( *sys.exc_info() )
        self.run = run_with_except_hook
    threading.Thread.__init__ = init

def install( logdir=None, context=5, file=None, dialog=ExceptionDialog ):
    sys.excepthook = Hook( logdir=logdir, context=context, file=file, dialog=dialog )
    install_threads()

if __name__ == "__main__":
    install()
    GLib.idle_add( lambda: 1 / 0 ) # This raises a ZeroDivisionError for testing
    Gtk.main()

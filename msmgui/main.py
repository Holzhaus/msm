#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from gi.repository import Gtk, Gio
import msmgui.widgets.customerwindow
import msmgui.widgets.invoicewindow
import msmgui.dialogs.about
class MainWindow( Gtk.ApplicationWindow ):
    def __init__( self, application ):
        Gtk.ApplicationWindow.__init__( self, application=application )
        self.set_property( "window_position", Gtk.WindowPosition.CENTER )
        self.set_property( "default_width", 900 )
        self.set_property( "default_height", 650 )
        """FIXME: Setting an icon from stock is quite hackish.
           Read this if you want more details:
           https://mail.gnome.org/archives/gtk-app-devel-list/2007-September/msg00163.html"""
        image = Gtk.Image();
        pixbuf = image.render_icon( "gtk-find-and-replace", Gtk.IconSize.DIALOG, None );
        self.set_default_icon( pixbuf )
        # Set the window title
        self.set_title( "POSITIONs-Manager" )
        self.set_wmclass( "POSITIONs-Manager", "POSITIONs-Manager" )
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/main.glade" )
        self.builder.get_object( "content" ).reparent( self )
        self.builder.connect_signals( self )

        self._customerwindow = msmgui.widgets.customerwindow.CustomerWindow()
        self.builder.get_object( "customerwindow" ).add( self._customerwindow )
        self._customerwindow.connect( "status-changed", self.statusbar_cb )

        self._invoicewindow = msmgui.widgets.invoicewindow.InvoiceWindow()
        self.builder.get_object( "invoicewindow" ).add( self._invoicewindow )
        self._invoicewindow.connect( "status-changed", self.statusbar_cb )

        self._aboutdialog = msmgui.dialogs.about.AboutDialog( self )

        """MenuBar Actions"""
        about_action = Gio.SimpleAction.new( "about", None )
        about_action.connect( "activate", self.about_cb )
        self.add_action( about_action )

        notebook = self.builder.get_object( "notebook" )
        page = self.builder.get_object( "customerwindow" )
        self.notebook_switch_page_cb( notebook, page, notebook.get_current_page() ) # Call the loading routine manually for first time
    def add_status_message( self, message ):
        statusbar = self.builder.get_object( "statusbar" )
        context_id = statusbar.get_context_id( message )
        statusbar.push( context_id, message )
        return context_id
    """Callbacks for MenuBar Actions"""
    def about_cb( self, action, parameter ):
        self._aboutdialog.show()
    """Callbacks"""
    def statusbar_cb( self, sender, message ):
        self.add_status_message( message )
    def notebook_switch_page_cb( self, notebook, page, page_num, user_data=None ):
        if page_num == notebook.page_num( self.builder.get_object( "customerwindow" ) ):
            self._customerwindow.refresh()
        elif page_num == notebook.page_num( self.builder.get_object( "invoicewindow" ) ):
            self._invoicewindow.refresh()
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
logger = logging.getLogger( __name__ )
from gi.repository import Gtk, Gio, GLib
import msmgui.widgets.customerwindow
import msmgui.widgets.invoicewindow
import msmgui.dialogs.about
import msmgui.assistants.contractexport
import msmgui.assistants.directdebitexport
import msmgui.assistants.bookingimport
class MainWindow( Gtk.ApplicationWindow ):
    def __init__( self, application ):
        """
        __init__ function.
        Arguments:
            application:
                the Gtk.Application that this window belongs to
        """

        logger.debug( 'Initializing MainWindow' )

        Gtk.ApplicationWindow.__init__( self, application=application )
        self.set_property( "window_position", Gtk.WindowPosition.CENTER )
        self.set_property( "default_width", 900 )
        self.set_property( "default_height", 650 )
        # FIXME: Setting an icon from stock is quite hackish.
        # Read this if you want more details:
        # https://mail.gnome.org/archives/gtk-app-devel-list/2007-September/msg00163.html
        image = Gtk.Image()
        pixbuf = image.render_icon( "gtk-find-and-replace",
                                    Gtk.IconSize.DIALOG, None )
        self.set_default_icon( pixbuf )
        # Set the window title
        self.set_title( "MSM" )
        self.set_wmclass( "MSM", "MSM" )
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
        self._contractexportassistant = msmgui.assistants.contractexport.ContractExportAssistant()
        self._directdebitexportassistant = msmgui.assistants.directdebitexport.DirectDebitExportAssistant()
        self._bookingimportassistant = msmgui.assistants.bookingimport.BookingImportAssistant()

        # MenuBar Actions
        contractexport_action = Gio.SimpleAction.new("contractexport", None)
        contractexport_action.connect("activate", self.contractexport_cb)
        self.add_action(contractexport_action)

        directdebitexport_action = Gio.SimpleAction.new("directdebitexport", None)
        directdebitexport_action.connect("activate", self.directdebitexport_cb)
        self.add_action(directdebitexport_action)

        bookingimport_action = Gio.SimpleAction.new("bookingimport", None)
        bookingimport_action.connect("activate", self.bookingimport_cb)
        self.add_action(bookingimport_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.about_cb)
        self.add_action(about_action)

        notebook = self.builder.get_object( "notebook" )
        page = self.builder.get_object( "customerwindow" )
        # Call the loading routine manually for first time
        GLib.idle_add( self.notebook_switch_page_cb, notebook, page, notebook.get_current_page() )
    def add_status_message( self, message ):
        """
        Adds a status message to the statusbar of the MainWindow.
        Arguments:
            message:
                the status message string to add.
        """
        statusbar = self.builder.get_object( "statusbar" )
        context_id = statusbar.get_context_id( message )
        statusbar.push( context_id, message )
        return context_id

    # Callbacks for MenuBar Actions
    def contractexport_cb(self, action, parameter):
        """
        Callback for the "contractexport"-action of the MenuBar. Shows the ContractExport dialog.
        Arguments:
            action:
                the Gio.SimpleAction that emitted the "activate" signal
            parameter:
                the parameter to the activation
        """
        self._contractexportassistant.set_parent( self.get_toplevel() )
        self._contractexportassistant.show()

    def directdebitexport_cb(self, action, parameter):
        """
        Callback for the "contractexport"-action of the MenuBar. Shows the DirectDebitExport dialog.
        Arguments:
            action:
                the Gio.SimpleAction that emitted the "activate" signal
            parameter:
                the parameter to the activation
        """
        self._directdebitexportassistant.set_parent( self.get_toplevel() )
        self._directdebitexportassistant.show()

    def bookingimport_cb(self, action, parameter):
        """
        Callback for the "contractexport"-action of the MenuBar. Shows the BookingImport dialog.
        Arguments:
            action:
                the Gio.SimpleAction that emitted the "activate" signal
            parameter:
                the parameter to the activation
        """
        self._bookingimportassistant.set_parent( self.get_toplevel() )
        self._bookingimportassistant.show()

    def about_cb( self, action, parameter ):
        """
        Callback for the "about"-action of the MenuBar. Shows the about dialog.
        Arguments:
            action:
                the Gio.SimpleAction that emitted the "activate" signal
            parameter:
                the parameter to the activation
        """
        self._aboutdialog.show()
    # Callbacks
    def statusbar_cb( self, sender, message ):
        """
        Callback for child widgets that emit the "status-changed" signal.
        The emitted messages will be passed to the add_status_message
        method of the MainWindow.
        Arguments:
            sender:
                the child widget that emitted the "status_changed" signal
            message:
                the status message string to add.
        """
        self.add_status_message( message )
    def notebook_switch_page_cb( self, notebook, page, page_num, user_data=None ):
        """
        Callback for the "switch-page" signal of the MainWindow's Gtk.Notebook.
        Refreshes the child windows if needed.
        Arguments:
            notebook:
                MainWindow's Gtk.Notebook
            page:
                the child widget the notebook switched to
            page_num:
                the page number the notebook switched to
            user_data:
                additional data passed to the callback function
        """
        if page_num == notebook.page_num( self.builder.get_object( "customerwindow" ) ):
            self._customerwindow.refresh()
        elif page_num == notebook.page_num( self.builder.get_object( "invoicewindow" ) ):
            self._invoicewindow.refresh()

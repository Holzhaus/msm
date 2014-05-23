#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from gi.repository import GObject, Gtk, Gdk, Gio, Poppler, GdkPixbuf
from core.config import Configuration
import msmgui.widgets.invoicetable
import datetime
import core.database
import msmgui.assistants.invoicing
import msmgui.assistants.letterexport
import msmgui.widgets.base
class InvoiceWindow( msmgui.widgets.base.RefreshableWindow ):
    __gsignals__ = {
        'status-changed': ( GObject.SIGNAL_RUN_FIRST, None, ( str, ) )
    }
    def __init__( self ):
        self._invoicetable = msmgui.widgets.invoicetable.InvoiceTable()
        msmgui.widgets.base.RefreshableWindow.__init__( self, [self._invoicetable] )
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/widgets/invoicewindow/invoicewindow.glade" )
        self.builder.get_object( "content" ).reparent( self )
        self.builder.connect_signals( self )

        self.builder.get_object( "tablebox" ).add( self._invoicetable )
        self._invoicetable.connect( "selection-changed", self.invoicetable_selection_changed_cb )

        self._invoicingassistant = msmgui.assistants.invoicing.InvoicingAssistant()
        self._invoicingassistant.connect( "saved", self.invoicingassistant_saved_cb )

        self._letterexportassistant = msmgui.assistants.letterexport.LetterExportAssistant()

        active_only = Configuration().getboolean( "Interface", "active_only" )
        if not active_only:
            self.builder.get_object( "invoices_showall_switch" ).set_active( not active_only )
    def invoicetable_selection_changed_cb( self, table ):
        pass
    def invoices_search_entry_changed_cb( self, entry ):
        self._invoicetable.filter = entry.get_text().strip()
    def invoices_showall_switch_notify_active_cb( self, switch, param_spec ):
        self._invoicetable.active_only = not switch.get_active()
    def invoices_create_button_clicked_cb( self, button ):
        self._invoicingassistant.set_parent( self.get_toplevel() )
        self._invoicingassistant.show()
    def invoices_export_button_clicked_cb( self, button ):
        self._letterexportassistant.set_parent( self.get_toplevel() )
        self._letterexportassistant.show()

        """pdfs = []
        invoices = [] # FIXME
        for invoice in invoices:
            pdfs.append( core.pdfgenerator.LetterGenerator.render_invoice( invoice ) )
        self.add_status_message( ( "Eine Rechnung als PDF generiert." if len( pdfs ) == 1 else "%d Rechnungen als PDF generiert." % len( pdfs ) ) )"""
        """document = Poppler.Document.new_from_file( "file://" + filename, None )
        def edraw( widget, surface ):
            page.render( surface )
        page = document.get_page( 0 )
        window = Gtk.Window( title="Hello World" )
        window.connect( "delete-event", Gtk.main_quit )
        window.connect( "draw", edraw )
        window.set_app_paintable( True )
        window.show_all()"""
    def invoicingassistant_saved_cb( self, assistant, num_invoices ):
        if num_invoices > 0:
            self.emit( "status-changed", ( "Eine Rechnung erstellt." if num_invoices == 1 else "%d Rechnungen erstellt." % num_invoices ) )
            self._invoicetable.needs_refresh = True
            self.refresh()
        else:
            self.emit( "status-changed", "Keine Rechnungen erstellt." )

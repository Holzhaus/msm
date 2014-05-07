#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from gi.repository import Gtk, GObject, GLib
import core.database
import msmgui.widgets.invoicetable
import locale
import datetime
import threading
class InvoicingAssistant( GObject.GObject ):
    __gsignals__ = { 'saved': ( GObject.SIGNAL_RUN_FIRST, None, ( int, ) ) }
    session = None
    def _scopefunc( self ):
        """ Needed as scopefunc argument for the scoped_session"""
        return self
    def __init__( self ):
        GObject.GObject.__init__( self )
        InvoicingAssistant.session = core.database.Database.get_scoped_session( self._scopefunc )
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/assistants/invoicing.glade" )
        self._assistant = self.builder.get_object( "content" )
        self._assistant.set_modal( True )

        self._invoicetable = msmgui.widgets.invoicetable.InvoiceTable()
        self._invoicetable.active_only = False
        self.builder.get_object( "invoicetablebox" ).add( self._invoicetable )

        self._assistant.set_forward_page_func( self.page_forward_func )
        # Connect Signals
        self.builder.connect_signals( self )
    def set_parent( self, parent ):
        self._assistant.set_transient_for( parent )
    def show( self ):
        invoice_date = datetime.date.today()
        maturity_date = invoice_date + datetime.timedelta( days=14 )
        self.builder.get_object( "invoice_date_entry" ).set_text( invoice_date.strftime( locale.nl_langinfo( locale.D_FMT ) ) )
        self.builder.get_object( "invoice_maturitydate_entry" ).set_text( maturity_date.strftime( locale.nl_langinfo( locale.D_FMT ) ) )
        self.builder.get_object( "invoice_accountingenddate_entry" ).set_text( invoice_date.strftime( locale.nl_langinfo( locale.D_FMT ) ) )
        self.builder.get_object( "content" ).show_all()
    class Page:
        """ Page Enum """
        Intro, Select, Details, Generate, Confirm, Save, Summary = range( 7 )
    def page_forward_func( self, page ):
        """
        Function called when the forward button is pressed,
        Arguments:
            page:
                integer index of the current page
        returns:
            integer index of the next page to display
        """
        if page == InvoicingAssistant.Page.Intro and self.builder.get_object( "contracts_all_radiobutton" ).get_active():
            return InvoicingAssistant.Page.Details
        elif page == InvoicingAssistant.Page.Generate and len( self._invoicetable.get_contents() ) == 0:
            return InvoicingAssistant.Page.Summary
        else:
            return page + 1
    """
    Page prepare funcs
    """
    def page_generate_prepare_func( self, assistant, page ):
        class ThreadObject( GObject.GObject, threading.Thread ):
            __gsignals__ = {
                        'start': ( GObject.SIGNAL_RUN_FIRST, None, () ),
                        'stop': ( GObject.SIGNAL_RUN_FIRST, None, ( int, int ) )
            }
            def __init__( self, contracts, invoice_options, gui_objects ):
                GObject.GObject.__init__( self )
                threading.Thread.__init__( self )
                self.contracts = contracts
                self.invoice_options = invoice_options
                self.gui_objects = gui_objects
                self.invoices = []
            def run( self ):
                GLib.idle_add( lambda: self._gui_start() )
                local_session = core.database.Database.get_scoped_session()
                i = 1
                num_contracts = len( self.contracts )
                for unmerged_contract in self.contracts:
                    contract = local_session.merge( unmerged_contract ) # add them to the local session
                    try:
                        invoice = contract.add_invoice( **self.invoice_options )
                    except ( ValueError, TypeError ):
                        invoice = None
                    if invoice is not None:
                        self.invoices.append( invoice )
                    i += 1
                    GLib.idle_add( lambda: self._gui_update( i, num_contracts ) )
                local_session.expunge_all() # expunge everything afterwards
                local_session.remove()
                GLib.idle_add( lambda: self._gui_stop( len( self.invoices ), num_contracts ) )
            def _gui_start( self ):
                spinner, label, assistant, page, invoicetable = self.gui_objects
                label.set_text( "Generiere Rechnungen..." )
                spinner.start()
            def _gui_update( self, contract_current, contract_total ):
                spinner, label, assistant, page, invoicetable = self.gui_objects
                label.set_text( "Generiere Rechnungen... (Vertrag {}/{})".format( contract_current, contract_total ) )
            def _gui_stop( self, num_invoices, num_contracts ):
                merged_contracts = []
                for unmerged_contract in self.contracts:
                    contract = InvoicingAssistant.session().merge( unmerged_contract ) # Readd the object to the main thread session
                    merged_contracts.append( contract )
                self.contracts = merged_contracts
                spinner, label, assistant, page, invoicetable = self.gui_objects
                invoicetable.clear()
                for unmerged_invoice in self.invoices:
                    invoice = InvoicingAssistant.session().merge( unmerged_invoice )
                    invoicetable.add_invoice( invoice )
                label.set_text( "Fertig! {} Rechnungen aus {} Verträgen generiert.".format( num_invoices, num_contracts ) )
                spinner.stop()
                assistant.set_page_complete( page, True )
        assistant.set_page_complete( page, False )
        spinner = self.builder.get_object( "generate_spinner" )
        label = self.builder.get_object( "generate_label" )
        gui_objects = ( spinner, label, assistant, page, self._invoicetable )
        InvoicingAssistant.session.close()
        contracts = core.database.Contract.get_all( session=InvoicingAssistant.session ) # We expunge everything, use it inside the thread and readd it later
        InvoicingAssistant.session.expunge_all()
        date = datetime.date.today()
        maturity = datetime.timedelta( days=14 )
        threadobj = ThreadObject( contracts, {"date":date, "maturity":maturity}, gui_objects )
        threadobj.start()
    def page_save_prepare_func( self, assistant, page ):
        class ThreadObject( GObject.GObject, threading.Thread ):
            __gsignals__ = {
                        'start': ( GObject.SIGNAL_RUN_FIRST, None, () ),
                        'stop': ( GObject.SIGNAL_RUN_FIRST, None, ( int, int ) )
            }
            def __init__( self, invoices, gui_objects ):
                GObject.GObject.__init__( self )
                threading.Thread.__init__( self )
                self.gui_objects = gui_objects
                self.invoices = invoices
            def run( self ):
                GLib.idle_add( lambda: self._gui_start() )
                local_session = core.database.Database.get_scoped_session()
                for invoice in self.invoices:
                    local_session.add( invoice ) # add them to the local session
                local_session.commit()
                local_session.remove() # expunge everything afterwards
                GLib.idle_add( lambda: self._gui_stop( len( self.invoices ) ) )
            def _gui_start( self ):
                spinner, label, assistant, page, window = self.gui_objects
                label.set_text( "Speichere Rechnungen..." )
                spinner.start()
            def _gui_stop( self, num_invoices ):
                spinner, label, assistant, page, window = self.gui_objects
                assistant.commit()
                label.set_text( "Fertig! {} Rechnungen gespeichert.".format( num_invoices ) )
                spinner.stop()
                assistant.set_page_complete( page, True )
                window.emit( "saved", num_invoices )
        assistant.set_page_complete( page, False )
        spinner = self.builder.get_object( "save_spinner" )
        label = self.builder.get_object( "save_label" )
        gui_objects = ( spinner, label, assistant, page, self )
        invoices = self._invoicetable.get_contents()
        InvoicingAssistant.session.expunge_all()
        InvoicingAssistant.session.close()
        threadobj = ThreadObject( invoices, gui_objects )
        threadobj.start()
    """
    Callbacks
    """
    def hide_cb( self, assistant ):
        InvoicingAssistant.session.rollback()
        InvoicingAssistant.session.close()
    def close_cb( self, assistant ):
        assistant.hide()
    def cancel_cb( self, assistant ):
        assistant.hide()
    def apply_cb( self, assistant ):
        pass
    def prepare_cb( self, assistant, page ):
        if page == assistant.get_nth_page( InvoicingAssistant.Page.Intro ):
            assistant.set_page_complete( page, True )
        elif page == assistant.get_nth_page( InvoicingAssistant.Page.Details ):
            assistant.set_page_complete( page, True )
        elif page == assistant.get_nth_page( InvoicingAssistant.Page.Generate ):
            self.page_generate_prepare_func( assistant, page )
        elif page == assistant.get_nth_page( InvoicingAssistant.Page.Save ):
            self.page_save_prepare_func( assistant, page )
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
import locale
import datetime
import threading
import dateutil.parser
from gi.repository import Gtk, GObject, GLib
from core import paths
import core.database
from core.errors import InvoiceError
import msmgui.widgets.invoicetable
from msmgui.widgets.base import ScopedDatabaseObject
class InvoicingAssistant( GObject.GObject, ScopedDatabaseObject ):
    __gsignals__ = { 'saved': ( GObject.SIGNAL_RUN_FIRST, None, ( int, ) ) }
    def __init__( self ):
        ScopedDatabaseObject.__init__( self )
        GObject.GObject.__init__( self )
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( paths.data("ui","assistants","invoicing.glade" ))
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
                GLib.idle_add( self._gui_start )
                local_session = core.database.Database.get_scoped_session()
                i = 1
                num_contracts = len( self.contracts )
                for unmerged_contract in self.contracts:
                    contract = local_session.merge( unmerged_contract ) # add them to the local session
                    try:
                        invoice = contract.add_invoice( **self.invoice_options )
                    except InvoiceError as err:
                        logger.critical( "Error adding invoice: %r", err )
                        invoice = None
                    if invoice is not None:
                        self.invoices.append( invoice )
                    i += 1
                    GLib.idle_add( self._gui_update, i, num_contracts )
                local_session.expunge_all() # expunge everything afterwards
                local_session.remove()
                GLib.idle_add( self._gui_stop, len( self.invoices ), num_contracts )
            def _gui_start( self ):
                invoicingassistant, spinner, label, assistant, page, invoicetable = self.gui_objects
                label.set_text( "Generiere Rechnungen..." )
                spinner.start()
            def _gui_update( self, contract_current, contract_total ):
                invoicingassistant, spinner, label, assistant, page, invoicetable = self.gui_objects
                label.set_text( "Generiere Rechnungen... (Vertrag {}/{})".format( contract_current, contract_total ) )
            def _gui_stop( self, num_invoices, num_contracts ):
                invoicingassistant, spinner, label, assistant, page, invoicetable = self.gui_objects
                merged_contracts = []
                for unmerged_contract in self.contracts:
                    contract = invoicingassistant.session.merge( unmerged_contract ) # Readd the object to the main thread session
                    merged_contracts.append( contract )
                self.contracts = merged_contracts
                invoicetable.clear()
                def gen( invoicetable, invoices, session, step=10 ):
                    treeview = invoicetable.builder.get_object( "invoices_treeview" )
                    model = invoicetable.builder.get_object( "invoices_liststore" )
                    treeview.freeze_child_notify()
                    sort_settings = model.get_sort_column_id()
                    model.set_default_sort_func( lambda *unused: 0 )
                    model.set_sort_column_id( -1, Gtk.SortType.ASCENDING )
                    i = 0
                    for unmerged_invoice in invoices:
                        invoice = session.merge( unmerged_invoice )
                        invoicetable.add_invoice( invoice )
                        i += 1
                        # change something
                        if i % step == 0:
                            # freeze/thaw not really  necessary here as sorting is wrong because of the
                            # default sort function
                            yield True
                    if sort_settings != ( None, None ):
                        model.set_sort_column_id( *sort_settings )
                    treeview.thaw_child_notify()
                    yield False
                g = gen( invoicetable, self.invoices, invoicingassistant.session )
                if next( g ): # run once now, remaining iterations when idle
                    GLib.idle_add( next, g )
                label.set_text( "Fertig! {} Rechnungen aus {} Verträgen generiert.".format( num_invoices, num_contracts ) )
                spinner.stop()
                assistant.set_page_complete( page, True )
        def parse_date( text ):
            new_date = None
            if text:
                try:
                    new_date = dateutil.parser.parse( text, dayfirst=True )
                except Exception as error:
                    logger.warning( 'Invalid date entered: %s (%r)', text, error )
                else:
                    return new_date.date()
        assistant.set_page_complete( page, False )
        spinner = self.builder.get_object( "generate_spinner" )
        label = self.builder.get_object( "generate_label" )
        gui_objects = ( self, spinner, label, assistant, page, self._invoicetable )
        self._session.close()
        contracts = core.database.Contract.get_all( session=self.session ) # We expunge everything, use it inside the thread and readd it later
        self._session.expunge_all()
        invoice_date = parse_date( self.builder.get_object( "invoice_date_entry" ).get_text().strip() )
        if not invoice_date:
            invoice_date = datetime.date.today()
        maturity_date = parse_date( self.builder.get_object( "invoice_maturitydate_entry" ).get_text().strip() )
        if not maturity_date:
            maturity_date = invoice_date + datetime.timedelta( days=14 )
        accounting_enddate = parse_date( self.builder.get_object( "invoice_accountingenddate_entry" ).get_text().strip() )
        if not accounting_enddate:
            accounting_enddate = invoice_date
        self.invoice_generator_threadobj = ThreadObject( contracts, {"date":invoice_date, "maturity_date":maturity_date, "accounting_enddate": accounting_enddate}, gui_objects )
        self.invoice_generator_threadobj.start()
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
        invoices = self.invoice_generator_threadobj.invoices
        self._session.expunge_all()
        self._session.close()
        threadobj = ThreadObject( invoices, gui_objects )
        threadobj.start()
    """
    Callbacks
    """
    def hide_cb( self, assistant ):
        self._session.rollback()
        self._session.close()
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

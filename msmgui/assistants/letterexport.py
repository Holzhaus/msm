#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from gi.repository import Gtk, GObject, GLib
import core.database
import msmgui.widgets.lettercompositor
import datetime
import threading
from msmgui.widgets.lettercompositor import LetterCompositor
import sqlalchemy.orm.session
class LetterExportAssistant( GObject.GObject ):
    class Page:
        """
        Enumeration of LetterExportAssistants pages.
        """
        Intro, Compose, Confirm, Render, Summary = range( 5 )
    __gsignals__ = { 'saved': ( GObject.SIGNAL_RUN_FIRST, None, ( int, ) ) }
    session = None
    def _scopefunc( self ):
        """
        Needed as scopefunc argument for the scoped_session
        """
        return self
    def __init__( self ):
        GObject.GObject.__init__( self )
        LetterExportAssistant.session = core.database.Database.get_scoped_session( self._scopefunc )
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/assistants/letterexport.glade" )
        self._assistant = self.builder.get_object( "content" )
        self._assistant.set_modal( True )

        self._lettercompositor = msmgui.widgets.lettercompositor.LetterCompositor()
        self.builder.get_object( "lettercompositorbox" ).pack_start( self._lettercompositor, True, True, 0 )
        self._lettercompositor.connect( "changed", self.lettercompositor_changed_cb )
        self._assistant.set_forward_page_func( self.page_forward_func )
        # Connect Signals
        self.builder.connect_signals( self )
    def set_parent( self, parent ):
        """
        Sets the assistants parent window. Internally calls Gtk.Assistant.set_transient_for(parent).
        Arguments:
            parent:
                the assistant's parent window
        """
        self._assistant.set_transient_for( parent )
    def show( self ):
        """
        Shows the LetterExportAssistant.
        """
        self.builder.get_object( "content" ).show_all()
    def page_forward_func( self, page ):
        """
        Function called when the forward button is pressed.
        Arguments:
            page:
                integer index of the current page
        returns:
            integer index of the next page to display
        """
        return page + 1
    # Page prepare funcs
    def page_render_prepare_func( self, assistant, page ):
        """
        Starts the letter rendering thread.
        Arguments:
            assistant:
                the calling Gtk.Assistant
            page:
                current page of the assistant
        """
        class ThreadObject( GObject.GObject, threading.Thread ):
            __gsignals__ = {
                        'start': ( GObject.SIGNAL_RUN_FIRST, None, () ),
                        'stop': ( GObject.SIGNAL_RUN_FIRST, None, ( int, int ) )
            }
            def __init__( self, lettercomposition, contracts, gui_objects ):
                GObject.GObject.__init__( self )
                threading.Thread.__init__( self )
                self.contracts = contracts
                self.lettercomposition = lettercomposition
                self.gui_objects = gui_objects
                self.letters = []
            def contract_to_letter( self, contract ):
                letter = core.pdfgenerator.Letter( contract, date=datetime.date.today() )
                for letterpart, criterion in self.lettercomposition:
                    if criterion is None or criterion == LetterCompositor.Criterion.Always or \
                    ( criterion == LetterCompositor.Criterion.OnlyOnInvoice and contract.paymenttype == core.database.PaymentType.Invoice ) or \
                    ( criterion == LetterCompositor.Criterion.OnlyOnDirectWithdrawal and contract.paymenttype == core.database.PaymentType.DirectWithdrawal ):
                        if type( letterpart ) is LetterCompositor.InvoicePlaceholder:
                            for invoice in contract.invoices:
                                letter.add_content( invoice )
                        elif isinstance( letterpart, core.database.Note ):
                            letter.add_content( letterpart )
                    else:
                        raise RuntimeError( "unknown type: %s", letterpart )
                return letter
            def run( self ):
                GLib.idle_add( lambda: self._gui_start() )
                local_session = core.database.Database.get_scoped_session()
                num_contracts = len( self.contracts )
                letters = []
                for i, unmerged_contract in enumerate( self.contracts ):
                    contract = local_session.merge( unmerged_contract ) # add them to the local session
                    letter = self.contract_to_letter( contract )
                    if letter.has_contents():
                        letters.append( letter )
                    if i % 100 == 0:
                        text = "Stelle zusammen ({}/{})".format( i, num_contracts )
                        GLib.idle_add( self._gui_update, text )
                num_letters = len( letters )
                prerendered_letters = []
                for i, prerendered_letter in enumerate( core.pdfgenerator.LetterRenderer.prerender( letters ) ):
                    prerendered_letters.append( prerendered_letter )
                    if i % 100 == 0:
                        text = "Prerendering ({}/{})".format( i, num_letters )
                        GLib.idle_add( self._gui_update, text )
                output_file = "/tmp/exporttest.pdf"
                GLib.idle_add( self._gui_update, "Finales Rendering..." )
                core.pdfgenerator.LetterRenderer.render_prerendered_letters( prerendered_letters, output_file )
                local_session.expunge_all() # expunge everything afterwards
                local_session.remove()
                GLib.idle_add( lambda: self._gui_stop( num_letters, num_contracts ) )
            def _gui_start( self ):
                spinner, label, assistant, page = self.gui_objects
                label.set_text( "Starte Rendering..." )
                spinner.start()
            def _gui_update( self, text ):
                spinner, label, assistant, page = self.gui_objects
                label.set_text( text )
            def _gui_stop( self, num_letters, num_contracts ):
                spinner, label, assistant, page = self.gui_objects
                label.set_text( "Fertig! {} Briefe aus {} Verträgen generiert.".format( num_letters, num_contracts ) )
                spinner.stop()
                assistant.set_page_complete( page, True )
        assistant.set_page_complete( page, False )
        spinner = self.builder.get_object( "render_spinner" )
        label = self.builder.get_object( "render_label" )
        gui_objects = ( spinner, label, assistant, page )
        LetterExportAssistant.session.close()
        contracts = core.database.Contract.get_all( session=LetterExportAssistant.session ) # We expunge everything, use it inside the thread and readd it later
        LetterExportAssistant.session.expunge_all()
        lettercomposition = []
        for letterpart, criterion in self._lettercompositor.get_composition():
            if isinstance( letterpart, core.database.Note ):
                object_session = sqlalchemy.orm.session.object_session( letterpart )
                if object_session:
                    object_session.expunge( letterpart )
            lettercomposition.append( ( letterpart, criterion ) )
        threadobj = ThreadObject( lettercomposition, contracts, gui_objects )
        threadobj.start()
    # Callbacks
    def lettercompositor_changed_cb( self, lettercompositor, has_contents ):
        """
        Callback function for the LetterCompositor "changed" signal.
        Arguments:
            lettercompositor:
                the LetterCompositor widget that emitted the signal
            has_contents:
                True if the lettercomposition contains items, else False
        """
        page = self._assistant.get_nth_page( LetterExportAssistant.Page.Compose )
        self._assistant.set_page_complete( page, has_contents )
    def hide_cb( self, assistant ):
        """
        Callback for the "hide"-signal of the Gtk.Assistant.
        Rolls back and closes the database session.
        Arguments:
            assistant:
                the Gtk.Assistant that emitted the signal
        """
        LetterExportAssistant.session.rollback()
        LetterExportAssistant.session.close()
    def close_cb( self, assistant ):
        """
        Callback for the "close"-signal of the Gtk.Assistant.
        Hides the assistant.
        Arguments:
            assistant:
                the Gtk.Assistant that emitted the signal
        """
        assistant.hide()
    def cancel_cb( self, assistant ):
        """
        Callback for the "cancel"-signal of the Gtk.Assistant.
        Hides the assistant.
        Arguments:
            assistant:
                the Gtk.Assistant that emitted the signal
        """
        assistant.hide()
    def apply_cb( self, assistant ):
        # FIXME: What to do here?
        pass
    def prepare_cb( self, assistant, page ):
        """
        Callback for the "prepare"-signal of the Gtk.Assistant.
        Calls the prepare_func for the respective page, if neccessary.
        Arguments:
            assistant:
                the Gtk.Assistant that emitted the signal
            page:
                the assistant's page to be prepared
        """
        if page == assistant.get_nth_page( LetterExportAssistant.Page.Intro ):
            assistant.set_page_complete( page, True )
        elif page == assistant.get_nth_page( LetterExportAssistant.Page.Render ):
            self.page_render_prepare_func( assistant, page )

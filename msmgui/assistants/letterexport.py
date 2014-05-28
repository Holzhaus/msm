#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from gi.repository import Gtk, GObject, GLib
import sqlalchemy.orm.session
import core.database
from core.letterrenderer import ComposingRenderer
from core.lettercomposition import ContractLetterComposition
import msmgui.widgets.lettercompositor
from msmgui.widgets.base import ScopedDatabaseObject
class LetterExporter( ComposingRenderer ):
    def __init__( self, lettercomposition, contracts, gui_objects, update_step=25 ):
        output_file = '/tmp/export.pdf'
        super().__init__( lettercomposition, contracts, output_file )
        self._gui_spinner, self._gui_label, self._gui_assistant, self._gui_page = gui_objects
        self._update_step = update_step
    def on_composing_start( self, work_started ):
        text = "Starte Zusammenstellung..."
        GLib.idle_add( self._gui_start )
        GLib.idle_add( self._gui_update, text )
    def on_composing_output( self, work_done, work_started ):
        if self._update_step is not None:
            if not ( work_done % self._update_step == 0 or work_done == 1 ):
                return
        text = "Stelle Briefe für Verträge zusammen... ({}/{})".format( work_done, work_started )
        GLib.idle_add( self._gui_update, text )
    def on_composing_finished( self, num_letters ):
        text = "1 Brief zusammengestellt!" if num_letters == 1 else "{} Briefe zusammengestellt!".format( num_letters )
        GLib.idle_add( self._gui_update, text )
    def on_saving_start( self, num_letters ):
        text = "Speichere 1 Brief in der Datenbank..." if num_letters == 1 else "Speichere {} Briefe in der Datenbank...".format( num_letters )
        GLib.idle_add( self._gui_update, text )
    def on_saving_stop( self, num_letters ):
        text = "1 Brief in der Datenbank gespeichert!" if num_letters == 1 else "{} Briefe in der Datenbank gespeichert!".format( num_letters )
        GLib.idle_add( self._gui_update, text )
    def on_rendering_start( self, work_started ):
        text = "Starte Rendering..."
        GLib.idle_add( self._gui_start )
        GLib.idle_add( self._gui_update, text )
    def on_rendering_output( self, work_done, work_started ):
        if self._update_step is not None:
            if not ( work_done % self._update_step == 0 or work_done == 1 ):
                return
        text = "Rendere Briefe... ({}/{})".format( work_done, work_started )
        GLib.idle_add( self._gui_update, text )
    def on_rendering_finished( self, work_done ):
        text = "1 Brief gerendert!".format( work_done ) if work_done == 1 else "{} Briefe gerendert!".format( work_done )
        GLib.idle_add( self._gui_update, text )
    def on_compilation_start( self, work_done ):
        text = "Kompiliere 1 Brief...".format( work_done ) if work_done == 1 else "Kompiliere {} Briefe...".format( work_done )
        GLib.idle_add( self._gui_update, text )
    def on_compilation_finished( self, work_done ):
        text = "Fertig! 1 Brief kompiliert!".format( work_done ) if work_done == 1 else "Fertig! {} Briefe kompiliert!".format( work_done )
        GLib.idle_add( self._gui_update, text )
        GLib.idle_add( self._gui_stop )
    def _gui_start( self ):
        self._gui_spinner.start()
    def _gui_update( self, text ):
        self._gui_label.set_text( text )
    def _gui_stop( self ):
        self._gui_spinner.stop()
        self._gui_assistant.set_page_complete( self._gui_page, True )
class LetterExportAssistant( GObject.GObject, ScopedDatabaseObject ):
    class Page:
        """
        Enumeration of LetterExportAssistants pages.
        """
        Intro, Compose, Confirm, Render, Summary = range( 5 )
    __gsignals__ = { 'saved': ( GObject.SIGNAL_RUN_FIRST, None, ( int, ) ) }
    def __init__( self ):
        ScopedDatabaseObject.__init__( self )
        GObject.GObject.__init__( self )
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
        # Collect GUI objects to be using during rendering
        assistant.set_page_complete( page, False )
        spinner = self.builder.get_object( "render_spinner" )
        label = self.builder.get_object( "render_label" )
        gui_objects = ( spinner, label, assistant, page )
        # Remove stuff from the session so that it can be re-added in the thread
        self._session.close()
        contracts = core.database.Contract.get_all( session=self._session ) # We expunge everything, use it inside the thread and readd it later
        self._session.expunge_all()
        lettercomposition = ContractLetterComposition()
        for letterpart, criterion in self._lettercompositor.get_composition():
            if isinstance( letterpart, core.database.Note ):
                object_session = sqlalchemy.orm.session.object_session( letterpart )
                if object_session:
                    object_session.expunge( letterpart )
            lettercomposition.append( letterpart, criterion )
        # Start the Thread
        watcher = LetterExporter( lettercomposition, contracts, gui_objects )
        watcher.start()
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
        self._session.rollback()
        self._session.close()
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

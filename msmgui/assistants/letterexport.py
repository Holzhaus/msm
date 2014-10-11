#!/usr/bin/env python
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
from core.database import LetterCollection
logger = logging.getLogger( __name__ )
from gi.repository import Gtk, GObject, GLib
import sqlalchemy.orm.session
from core import paths
import core.database
from core.letterrenderer import ComposingRenderer, LetterCollectionRenderer
from core.lettercomposition import ContractLetterComposition
import msmgui.widgets.lettercompositor
from msmgui.assistants.genericexport import GenericExportAssistant, GenericExportSettings
class BaseRendererGUI( object ):
    def __init__( self, gui_objects, update_step ):
        self._gui_spinner, self._gui_label, self._gui_assistant, self._gui_page = gui_objects
        self._update_step = update_step
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
class ComposingRendererGUI( BaseRendererGUI, ComposingRenderer ):
    def __init__( self, lettercomposition, contracts, collectionname, output_file, gui_objects, update_step=25 ):
        BaseRendererGUI.__init__( self, gui_objects, update_step )
        ComposingRenderer.__init__( self, lettercomposition, contracts, collectionname, output_file )
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
class LetterCollectionRendererGUI( BaseRendererGUI, LetterCollectionRenderer ):
    def __init__( self, lettercollection, output_file, gui_objects, update_step=25 ):
        BaseRendererGUI.__init__( self, gui_objects, update_step )
        LetterCollectionRenderer.__init__( self, lettercollection, output_file )
    def on_init_start( self ):
        text = "Hole Briefe aus der Datenbank..."
        GLib.idle_add( self._gui_start )
        GLib.idle_add( self._gui_update, text )
    def on_init_finished( self, num_letters ):
        text = "1 Brief aus Datenbank geholt." if num_letters == 1 else "{} Briefe aus Datenbank geholt.".format( num_letters )
        GLib.idle_add( self._gui_update, text )
class LetterExportAssistant( GenericExportAssistant ):
    __gsignals__ = { 'saved': ( GObject.SIGNAL_RUN_FIRST, None, ( int, ) ) }
    def __init__( self ):
        filter_pdf = Gtk.FileFilter()
        filter_pdf.set_name( "PDF-Dateien" )
        filter_pdf.add_pattern( "*.pdf" )
        super().__init__( filefilters=[filter_pdf] )
        widget = LetterExportSettings( session=self.session )
        self.set_settingswidget( widget )
        # Customize labels
        self.begin_label = "Willkommen beim Rechnungs-Assistenten."
        self.confirm_label = "Der Exportvorgang kann nun gestartet werden."
        self.summary_label = "Die Rechnungen wurden erfolgreich als PDF exportiert."
    def confirm( self, settingswidget, output_file ):
        lettercollection, new_name, new_composition = settingswidget.get_settings()
        if lettercollection is not None:
            self.confirm_label = "Die Briefsammlung <b>„{}“</b> vom <b>{}</b> wird erneut als PDF gerendert.\nDie Sammlung enthält:\n{}".format( lettercollection.name if lettercollection.name else "Unbenannt", lettercollection.creation_date.strftime("%x"), lettercollection.description )
        elif new_name is not None and new_composition is not None:
            self.confirm_label = "Es wird eine <b>neue Briefsammlung</b> mit der Bezeichnung <b>„{}“</b> angelegt und im Anschluss als PDF gerendert.\nDie Sammlung soll folgendes enthalten:\n{}".format( new_name, new_composition.get_description() )
        else:
            raise RuntimeError( "These settings look strange." )
    def export( self, settingswidget, gui_objects, output_file ):
        """
        Starts the letter rendering thread.
        Arguments:
            settingswidget:
                the widget that stores export settings
            gui_objects:
                a tuple containing spinner, label, assistant, page (in that order)
            output_file:
                a string pointing to the output file
        """
        lettercollection, new_name, new_composition = settingswidget.get_settings()
        if lettercollection is not None:
            watcher = LetterCollectionRendererGUI( lettercollection, output_file, gui_objects )
        elif new_name is not None and new_composition is not None:
            contracts = core.database.Contract.get_all( session=self._session ) # We expunge everything, use it inside the thread and readd it later
            lettercomposition = ContractLetterComposition()
            for letterpart, criterion in new_composition:
                if isinstance( letterpart, core.database.Note ):
                    object_session = sqlalchemy.orm.session.object_session( letterpart )
                    if object_session:
                        object_session.expunge( letterpart )
                lettercomposition.append( letterpart, criterion )
                # Create Thread
                watcher = ComposingRendererGUI( lettercomposition, contracts, new_name, output_file, gui_objects )
        else:
             raise RuntimeError( "These settings look strange." )
        # Remove stuff from the session so that it can be re-added in the thread
        self._session.close()
        # Start the Thread
        watcher.start()
class LetterExportSettings( GenericExportSettings ):
    def __init__( self, session=None ):
        super().__init__( session=session )
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( paths.data("ui","widgets","letterexportsettings.glade" ))
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        self.builder.connect_signals( self )
        self._lettercompositor = msmgui.widgets.lettercompositor.LetterCompositor()
        self.builder.get_object( "lettercompositorbox" ).add( self._lettercompositor )
        self.builder.get_object( "lettercompositorbox" ).set_child_packing( self._lettercompositor, True, True, 0, Gtk.PackType.START )
    def get_settings( self ):
        if self.builder.get_object( "new_radiobutton" ).get_active():
            name = self.builder.get_object( "name_entry" ).get_text().strip()
            if name:
                print( name )
                lettercomposition = self._lettercompositor.get_composition()
                print( len( lettercomposition ) )
                if len( lettercomposition ) > 0:
                    return ( None, name, lettercomposition )
        elif self.builder.get_object( "rerender_radiobutton" ).get_active():
            lettercollection = self.get_lettercollection()
            if lettercollection is not None:
                return ( lettercollection, None, None )
        return None
    def get_lettercollection( self ):
        combo = self.builder.get_object( "lettercollection_combobox" )
        model = combo.get_model()
        treeiter = combo.get_active_iter()
        if model is not None and treeiter is not None:
            lettercollection = model[treeiter][0]
            if isinstance( lettercollection, core.database.LetterCollection ):
                return lettercollection
        return None
    def lettercompositor_changed_cb( self, lettercompositor, has_content ):
        self.emit( "changed", True if self.get_settings() is not None else False )
    def radiobutton_toggled_cb( self, radiobutton ):
        notebook = self.builder.get_object( "settings_notebook" )
        if self.builder.get_object( "new_radiobutton" ).get_active():
            if notebook.get_current_page() != 0:
                notebook.set_current_page( 0 )
        else:
            if notebook.get_current_page() != 1:
                notebook.set_current_page( 1 )
        self.emit( "changed", True if self.get_settings() is not None else False )
    def name_entry_changed_cb( self, entry ):
        self.emit( "changed", True if self.get_settings() is not None else False )
    def lettercollection_combobox_changed_cb( self, combo ):
        label = self.builder.get_object( "lettercollection_label" )
        lettercollection = self.get_lettercollection()
        if lettercollection is not None:
            label.set_text( lettercollection.description )
        else:
            label.set_text( "Bitte Briefsammlung auswählen." )
        self.emit( "changed", True if self.get_settings() is not None else False )
    def refresh( self ):
        selected_lettercollection = self.get_lettercollection()
        model = self.builder.get_object( "lettercollection_liststore" )
        model.clear()
        for lettercollection in LetterCollection.get_all( session=self.session ):
            text_name = lettercollection.name if lettercollection.name else "Unbenannt"
            text_date = lettercollection.creation_date.strftime("%x")
            treeiter = model.append( [lettercollection, "{} ({})".format( text_name, text_date )] )
            if selected_lettercollection is not None and lettercollection.id == selected_lettercollection.id:
                self.builder.get_object( "lettercollection_combobox" ).set_active_iter( treeiter )
        if not self.get_lettercollection() and len( model ) > 0:
            self.builder.get_object( "lettercollection_combobox" ).set_active( 0 )

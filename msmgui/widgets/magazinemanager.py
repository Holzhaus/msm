#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
logger = logging.getLogger( __name__ )
import locale
import dateutil.parser
from gi.repository import Gtk, GObject
import core.database
import msmgui.rowreference
from msmgui.widgets.base import ScopedDatabaseObject
class MagazineManagerRowReference( msmgui.rowreference.GenericRowReference ):
    def get_object( self ):
        """Returns the core.database.Magazine that is associated with the Gtk.TreeRow that this instance references."""
        row = self.get_row()
        obj = row[0]
        if not isinstance( obj, core.database.Magazine ) and not isinstance( obj, core.database.Subscription ):
            raise RuntimeError( "tried to get a magazine that does not exist" )
        return obj

class MagazineManager( Gtk.Box, ScopedDatabaseObject ):
    """Magazine mananger"""
    __gsignals__ = {
        'changed': ( GObject.SIGNAL_RUN_FIRST, None, () ),
    }
    DEFAULT_SUBSCRIPTION_NAME = "Neues Abo"
    DEFAULT_SUBSCRIPTION_VALUE = 10
    DEFAULT_MAGAZINE_NAME = "Neues Magazin"
    DEFAULT_MAGAZINE_ISSUENUM = 12
    def __init__( self, session=None ):
        ScopedDatabaseObject.__init__( self, session )
        Gtk.Box.__init__( self )
        self.signals_blocked = True
        self._customer = None
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/widgets/magazinemanager.glade" )
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        # Connect Signals
        self.builder.connect_signals( self )
        self.builder.get_object( "subscription_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "subscription_cellrenderertext" ), self.subscription_cell_data_func )
        # Add Child Widgets
        self._magazineeditor = MagazineEditor( session=self._session )
        self.builder.get_object( "magazine_page" ).add( self._magazineeditor )
        self._subscriptioneditor = SubscriptionEditor( session=self._session )
        self.builder.get_object( "subscription_page" ).add( self._subscriptioneditor )
        self.signals_blocked = False
    def add_magazine( self, magazine ):
        """Add an magazine to the Gtk.Treemodel"""
        model = self.builder.get_object( "subscriptions_treestore" )
        treeiter = model.append( None, [ magazine ] )
        path = model.get_path( treeiter )
        rowref = MagazineManagerRowReference( model, path )
        for subscription in magazine.subscriptions:
            self.add_subscription( subscription, rowref )
        return rowref
    def add_subscription( self, subscription, rowref ):
        """Add an subscription to the Gtk.Treemodel"""
        model = rowref.get_model()
        treeiter = model.append( rowref.get_iter(), [ subscription ] )
        path = model.get_path( treeiter )
        rowref = MagazineManagerRowReference( model, path )
        return rowref
    def remove( self, rowref ):
        if not isinstance( rowref, MagazineManagerRowReference ):
            raise TypeError( "Expected MagazineManagerRowReference, not {}".format( type( rowref ).__name__ ) )
        magazine = rowref.get_magazine()
        # TODO: Check if magazine is currently in use
        if magazine in self._session.new:
            self._session.remove( magazine )
        else:
            self._session.delete( magazine )
        model = rowref.get_model()
        treeiter = rowref.get_iter()
        model.remove( treeiter ) # Remove row from table
    def _gui_clear( self ):
        self.builder.get_object( "subscriptions_treeview_selection" ).unselect_all()
        self.builder.get_object( "subscriptions_treestore" ).clear()
    def _gui_fill( self ):
        self._gui_clear()
        for magazine in core.database.Magazine.get_all( session=self._session ):
            self.add_magazine( magazine )
    def start_edit( self ):
        self._gui_fill()
    """Cell data funcs (control how Gtk.TreeModel contents are displayed)"""
    def subscription_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = MagazineManagerRowReference( model, model.get_path( treeiter ) )
        obj = rowref.get_object()
        if isinstance( obj, core.database.Magazine ):
            new_text = "{} ({})".format( obj.name, obj.issues_per_year )
        elif isinstance( obj, core.database.Subscription ):
            new_text = "{} ({})".format( obj.name, locale.currency( obj.value ) )
        else:
            raise TypeError
        cellrenderer.set_property( 'text', new_text )
    """Callbacks"""
    def magazines_add_button_clicked_cb( self, button ):
        if self.signals_blocked: return
        magazine = core.database.Magazine( MagazineManager.DEFAULT_MAGAZINE_NAME, MagazineManager.DEFAULT_MAGAZINE_ISSUENUM )
        self._session.add( magazine )
        self.add_magazine( magazine )
        self.emit( "changed" )
    def subscriptions_add_button_clicked_cb( self, button ):
        if self.signals_blocked: return
        model, treeiter = self.builder.get_object( "subscriptions_treeview_selection" ).get_selected()
        if not treeiter:
            raise RuntimeError( "No row selected" )
        rowref = MagazineManagerRowReference( model, model.get_path( treeiter ) )
        magazine = rowref.get_object()
        if not isinstance( magazine, core.database.Magazine ):
            raise TypeError
        subscription = magazine.add_subscription( MagazineManager.DEFAULT_SUBSCRIPTION_NAME, MagazineManager.DEFAULT_SUBSCRIPTION_VALUE )
        self.add_subscription( subscription, rowref )
        self.emit( "changed" )
    def subscriptions_remove_button_clicked_cb( self, removebutton ):
        if self.signals_blocked: return
        selection = self.builder.get_object( 'magazines_treeview_selection' )
        model, treeiter = selection.get_selected()
        if treeiter is None:
            raise RuntimeError( "tried to remove an magazine, but none is currently selected" )
        rowref = MagazineManagerRowReference( model, model.get_path( treeiter ) )
        self.remove( rowref )
        self.emit( "changed" )
    def subscriptions_treeview_selection_changed_cb( self, selection ):
        notebook = self.builder.get_object( 'subscriptions_notebook' )
        subscriptions_addbutton = self.builder.get_object( 'subscriptions_add_button' )
        removebutton = self.builder.get_object( 'subscriptions_remove_button' )
        magazine_page = notebook.page_num( self.builder.get_object( 'magazine_page' ) )
        subscription_page = notebook.page_num( self.builder.get_object( 'subscription_page' ) )
        model, treeiter = selection.get_selected()
        if treeiter is None:
            removebutton.set_sensitive( False )
            subscriptions_addbutton.set_sensitive( False )
            notebook.set_sensitive( False )
        else:
            if notebook.get_current_page() == magazine_page:
                self._magazineeditor.end_edit()
            elif notebook.get_current_page() == subscription_page:
                self._subscriptioneditor.end_edit()
            rowref = MagazineManagerRowReference( model, model.get_path( treeiter ) )
            obj = rowref.get_object()
            if isinstance( obj, core.database.Magazine ):
                subscriptions_addbutton.set_sensitive( True )
                notebook.set_current_page( magazine_page )
                self._magazineeditor.start_edit( obj )
                notebook.set_sensitive( True )
            elif isinstance( obj, core.database.Subscription ):
                subscriptions_addbutton.set_sensitive( False )
                notebook.set_current_page( subscription_page )
                self._subscriptioneditor.start_edit( obj )
                notebook.set_sensitive( True )
            else:
                raise TypeError
            removebutton.set_sensitive( True )

class IssueRowReference( msmgui.rowreference.GenericRowReference ):
    def get_issue( self ):
        """Returns the core.database.Magazine that is associated with the Gtk.TreeRow that this instance references."""
        row = self.get_row()
        obj = row[0]
        if not isinstance( obj, core.database.Issue ):
            raise RuntimeError( "tried to get an Issue that does not exist" )
        return obj
class MagazineEditor( Gtk.Box, ScopedDatabaseObject ):
    """Magazine Editor"""
    __gsignals__ = {
        'changed': ( GObject.SIGNAL_RUN_FIRST, None, () ),
    }
    def __init__( self, session=None ):
        ScopedDatabaseObject.__init__( self, session )
        Gtk.Box.__init__( self )
        self.signals_blocked = True
        self._magazine = None
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/widgets/magazineeditor.glade" )
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        # Connect Signals
        self.builder.connect_signals( self )
        self.builder.get_object( "issues_date_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "issues_date_cellrenderertext" ), self.issues_date_cell_data_func )
        self.builder.get_object( "issues_number_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "issues_number_cellrenderertext" ), self.issues_number_cell_data_func )
        self.builder.get_object( "issues_year_treeviewcolumn" ).set_cell_data_func( self.builder.get_object( "issues_year_cellrenderertext" ), self.issues_year_cell_data_func )
    def add_issue( self, issue ):
        """Add an issue to the Gtk.Treemodel"""
        model = self.builder.get_object( "issues_liststore" )
        treeiter = model.append( [ issue ] )
        path = model.get_path( treeiter )
        rowref = IssueRowReference( model, path )
        return rowref
    def remove( self, rowref ):
        pass
    def _gui_clear( self ):
        self.signals_blocked = True
        self.builder.get_object( "issues_liststore" ).clear()
        self.signals_blocked = False
    def _gui_fill( self ):
        self._gui_clear()
        self.signals_blocked = True
        self.builder.get_object( "magazine_name_entry" ).set_text( self._magazine.name )
        self.builder.get_object( "magazine_issues_spinbutton" ).set_value( self._magazine.issues_per_year )
        for issue in self._magazine.issues:
            self.add_issue( issue )
        self.signals_blocked = False
    def start_edit( self, magazine ):
        self._magazine = magazine
        self._gui_fill()
    def end_edit( self ):
        self._magazine = None
    """Cell data funcs (control how Gtk.TreeModel contents are displayed)"""
    def issues_date_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = IssueRowReference( model, model.get_path( treeiter ) )
        issue = rowref.get_issue()
        if not isinstance( issue, core.database.Issue ):
            raise TypeError
        new_text = issue.date.strftime( locale.nl_langinfo( locale.D_FMT ) ) if issue.date else ""
        cellrenderer.set_property( 'text', new_text )
    def issues_number_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = IssueRowReference( model, model.get_path( treeiter ) )
        issue = rowref.get_issue()
        if not isinstance( issue, core.database.Issue ):
            raise TypeError
        new_text = issue.number
        cellrenderer.set_property( 'text', str( new_text ) )
    def issues_year_cell_data_func( self, column, cellrenderer, model, treeiter, user_data=None ):
        rowref = IssueRowReference( model, model.get_path( treeiter ) )
        issue = rowref.get_issue()
        if not isinstance( issue, core.database.Issue ):
            raise TypeError
        new_text = issue.year
        cellrenderer.set_property( 'text', str( new_text ) )
    """Callbacks"""
    def issues_add_button_clicked_cb( self, button ):
        if self.signals_blocked: return
        issue = self._magazine.add_issue()
        self.add_issue( issue )
        self.emit( "changed" )
    def issues_remove_button_clicked_cb( self, button ):
        pass
    def issues_date_cellrenderertext_edited_cb( self, cellrenderer, path_string, new_text ):
        if self.signals_blocked: return
        model = self.builder.get_object( 'issues_liststore' )
        rowref = IssueRowReference( model, Gtk.TreePath( path_string ) )
        issue = rowref.get_issue()
        new_date = None
        text = new_text.strip()
        if text:
            try:
                new_date = dateutil.parser.parse( text, dayfirst=True )
            except Exception as error:
                logger.warning( 'Invalid date entered: %s (%r)', text, error )
            else:
                new_date = new_date.date()
        issue.date = new_date
        self.emit( "changed" )
    def issues_number_cellrenderertext_edited_cb( self, cellrenderer, path_string, new_text ):
        if self.signals_blocked: return
        model = self.builder.get_object( 'issues_liststore' )
        rowref = IssueRowReference( model, Gtk.TreePath( path_string ) )
        issue = rowref.get_issue()
        issue.number = int( new_text )
        self.emit( "changed" )
    def issues_year_cellrenderertext_edited_cb( self, cellrenderer, path_string, new_text ):
        if self.signals_blocked: return
        model = self.builder.get_object( 'issues_liststore' )
        rowref = IssueRowReference( model, Gtk.TreePath( path_string ) )
        issue = rowref.get_issue()
        issue.year = int( new_text )
        self.emit( "changed" )
    def magazine_name_entry_changed_cb( self, entry ):
        if self.signals_blocked: return
        self._magazine.name = entry.get_text().strip()
        self.emit( "changed" )
    def magazine_issues_spinbutton_value_changed_cb( self, spinbutton ):
        if self.signals_blocked: return
        self._magazine.issues_per_year = int( spinbutton.get_value() )
        self.emit( "changed" )

class SubscriptionEditor( Gtk.Box, ScopedDatabaseObject ):
    """Subscription Editor"""
    __gsignals__ = {
        'changed': ( GObject.SIGNAL_RUN_FIRST, None, () ),
    }
    def __init__( self, session=None ):
        ScopedDatabaseObject.__init__( self, session )
        Gtk.Box.__init__( self )
        self.signals_blocked = True
        self._subscription = None
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/widgets/subscriptioneditor.glade" )
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        # Connect Signals
        self.builder.connect_signals( self )
    def _gui_fill( self ):
        self.signals_blocked = True
        self.builder.get_object( "subscription_name_entry" ).set_text( self._subscription.name )
        self.builder.get_object( "subscription_value_spinbutton" ).set_value( self._subscription.value )
        self.builder.get_object( "subscription_valuechangeable_checkbutton" ).set_active( self._subscription.value_changeable )
        if self._subscription.number_of_issues:
            self.builder.get_object( "subscription_numberofissues_spinbutton" ).set_value( self._subscription.number_of_issues )
            self.builder.get_object( "subscription_numberofissues_spinbutton" ).set_sensitive( True )
            self.builder.get_object( "subscription_numberofissues_checkbutton" ).set_active( True )
        else:
            self.builder.get_object( "subscription_numberofissues_spinbutton" ).set_value( 0 )
            self.builder.get_object( "subscription_numberofissues_spinbutton" ).set_sensitive( False )
            self.builder.get_object( "subscription_numberofissues_checkbutton" ).set_active( False )
        self.signals_blocked = False
    def start_edit( self, subscription ):
        self._subscription = subscription
        self._gui_fill()
    def end_edit( self ):
        self._subscription = None
    """Callbacks"""
    def subscription_name_entry_changed_cb( self, entry ):
        if self.signals_blocked: return
        self._subscription.name = entry.get_text().strip()
        self.emit( "changed" )
    def subscription_value_spinbutton_value_changed_cb( self, spinbutton ):
        if self.signals_blocked: return
        self._subscription.value = spinbutton.get_value()
        self.emit( "changed" )
    def subscription_valuechangeable_checkbutton_toggled_cb( self, togglebutton ):
        if self.signals_blocked: return
        self._subscription.value_changeable = togglebutton.get_active()
        self.emit( "changed" )
    def subscription_numberofissues_checkbutton_toggled_cb( self, togglebutton ):
        if self.signals_blocked: return
        spinbutton = self.builder.get_object( "subscription_numberofissues_spinbutton" )
        if togglebutton.get_active():
            spinbutton.set_value( 0 )
            spinbutton.set_sensitive( True )
        else:
            spinbutton.set_value( 0 )
            self._subscription.number_of_issues = None
            spinbutton.set_sensitive( False )
        self.emit( "changed" )
    def subscription_numberofissues_spinbutton_value_changed_cb( self, spinbutton ):
        if self.signals_blocked: return
        self._subscription.number_of_issues = spinbutton.get_value()
        self.emit( "changed" )

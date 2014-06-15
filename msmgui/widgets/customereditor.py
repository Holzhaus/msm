#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
logger = logging.getLogger( __name__ )
from gi.repository import Gtk, GObject
import core.database
from msmgui.widgets.maineditor import MainEditor
from msmgui.widgets.addresseditor import AddressEditor
from msmgui.widgets.correspondenceeditor import CorrespondenceEditor
from msmgui.widgets.bankaccounteditor import BankaccountEditor
from msmgui.widgets.contracteditor import ContractEditor
from msmgui.widgets.base import ScopedDatabaseObject
class CustomerEditor( Gtk.Box, ScopedDatabaseObject ):
    __gsignals__ = {
        'edit-started': ( GObject.SIGNAL_RUN_FIRST, None, ( int, ) ),
        'edit-ended': ( GObject.SIGNAL_RUN_FIRST, None, () ),
        'changed': ( GObject.SIGNAL_RUN_FIRST, None, () ),
        'reset': ( GObject.SIGNAL_RUN_FIRST, None, () ),
        'save': ( GObject.SIGNAL_RUN_FIRST, None, ( int, bool ) ),
        'expanded-changed': ( GObject.SIGNAL_RUN_FIRST, None, () ),
    }
    def __init__( self ):
        ScopedDatabaseObject.__init__( self )
        Gtk.Box.__init__( self )

        self._gui_signals_blocked = True
        self._expandable = False
        self._expandable_state = False
        self._customer = None
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/widgets/customerwindow/customereditor.glade" )
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        # Connect Signals
        self.builder.connect_signals( self )

        # Add child widgets
        self._maineditor = MainEditor( self._session )
        self.builder.get_object( "maineditorbox" ).add( self._maineditor )
        self._addresseditor = AddressEditor( self._session )
        self.builder.get_object( "addresseditorbox" ).add( self._addresseditor )
        self._correspondenceeditor = CorrespondenceEditor( self._session )
        self.builder.get_object( "correspondenceeditorbox" ).add( self._correspondenceeditor )
        self._bankaccounteditor = BankaccountEditor( self._session )
        self.builder.get_object( "bankaccounteditorbox" ).add( self._bankaccounteditor )
        self._contracteditor = ContractEditor( self._session )
        self.builder.get_object( "contracteditorbox" ).add( self._contracteditor )

        self._maineditor.connect( "changed", self.check_changes )
        self._addresseditor.connect( "changed", self.check_changes )
        self._correspondenceeditor.connect( "changed", self.check_changes )
        self._bankaccounteditor.connect( "changed", self.check_changes )
        self._contracteditor.connect( "changed", self.check_changes )

        self.signals_blocked = False
        """# Misc Stuff
        self.builder.get_object( 'customers_edit_contracts_value_cellrendererspin' ).set_property( 'digits', 2 )
        self.builder.get_object( 'customers_edit_contracts_value_treeviewcolumn' ).set_cell_data_func( self.builder.get_object( 'customers_edit_contracts_value_cellrendererspin' ), signalhandler.customers_edit_contracts_value_cellrendererspin_edited_func )"""
    def start_edit( self, customer_id=None ):
        if not self.end_edit():
            # FIXME This will never happen, as end_edit cannot be canceled right now
            return False
        if customer_id:
            existing_customer = core.database.Customer.get_by_id( customer_id )
            if not existing_customer:
                raise Exception( "Customer ID not found" )
            customer = self._session.merge( existing_customer, load=False )
            self.expandable = True
        else:
            customer = core.database.Customer( "", "" )
            self._session.add( customer )
            self.expanded = True
            self.expandable = False
        self._customer = customer
        self.signals_blocked = True
        self._maineditor.start_edit( self._customer )
        self._addresseditor.start_edit( self._customer )
        self._correspondenceeditor.start_edit( self._customer )
        self._bankaccounteditor.start_edit( self._customer )
        self._contracteditor.start_edit( self._customer )
        self.signals_blocked = False
        self.emit( "edit-started", int( self._customer.id ) if self._customer.id else 0 )
        return True
    def end_edit( self ):
        if self.has_changes():
            if self.data_is_valid():
                response = self.prompt_changes()
            else:
                logger.debug( "Data is invalid" )
                return False
            # FIXME Maybe it's better to check the response here and add a cancel button
        self._session.remove()
        self._gui_clear()
        self.emit( "edit-ended" )
        return True
    def reset( self ):
        customer_id = self._customer.id
        self._session.rollback()
        self.emit( "reset" )
        self.end_edit()
        self.start_edit( customer_id )
    def save( self ):
        # TODO: Maybe do some multithreading here?
        is_new = True if self._customer in self._session.new else False
        self._session.commit()
        self.emit( "save", self._customer.id, is_new )
    def has_changes( self ):
        if self._session.deleted:
            return True
        for obj in self._session.new:
            if obj is not self._customer:
                return True # you added an address, bankaccount, etc. to this customer
            elif not self._customer.equals( core.database.Customer( "", "" ) ):
                return True # you're creating a new customer and already entered some values
        for obj in self._session.dirty:
            if self._session.is_modified( obj ): # session.dirty is "optimistic", so we check if the object was really modified
                return True # you changed the properties of this customer
        """if core.database.session_has_pending_commit( self._session ):
            return True  # you already flushed some changes to the database"""
        return False
    def data_is_valid( self ):
        for obj in ( list( self._session.new ) + list( self._session.dirty ) ):
            if not obj.is_valid():
                logger.info( 'Object has invalid data: %r', obj )
                return False
            if isinstance( obj, core.database.Contract ):
                if obj.bankaccount in self._session.deleted:
                    return False
                if obj.shippingaddress in self._session.deleted:
                    return False
                if obj.billingaddress in self._session.deleted:
                    return False
        return True
    def prompt_changes( self ):
        dialog = Gtk.MessageDialog( self.get_toplevel(), Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO, "Willst du die Änderungen speichern?" )
        customername = "'%s, %s' (ID: %s)" % ( self._customer.familyname, self._customer.prename, str( self._customer.id ) if self._customer.id is not None else "NEU" )
        label = "Du hast Änderungen an „%s“ vorgenommen. Sollen diese Änderungen gespeichert werden?" % customername
        dialog.format_secondary_text( label )
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            self.save()
        elif response == Gtk.ResponseType.NO:
            self.reset()
        dialog.destroy()
    # GUI Interaction
    @property
    def signals_blocked( self ):
        return self._gui_signals_blocked
    @signals_blocked.setter
    def signals_blocked( self, value ):
        if not isinstance( value, bool ):
            raise ValueError
        self._gui_signals_blocked = value
        self._maineditor.signals_blocked = value
        self._addresseditor.signals_blocked = value
        # self._balanceeditor.signals_blocked = value
        self._bankaccounteditor.signals_blocked = value
        self._contracteditor.signals_blocked = value
    @property
    def expanded( self ):
        return self.builder.get_object( "content" ).get_expanded()
    @expanded.setter
    def expanded( self, value ):
        if not isinstance( value, bool ):
            raise ValueError
        self._expandable_state = value
        self.builder.get_object( "content" ).set_expanded( value )
    @property
    def expandable( self ):
        return self._expandable
    @expandable.setter
    def expandable( self, value ):
        if not isinstance( value, bool ):
            raise ValueError
        if value is False:
            self._expandable_state = self.expanded
        self._expandable = value
    @property
    def expandable_state( self ):
        return self._expandable_state
    def expander_expanded_notify_cb ( self, expander, value ):
        """Prevent expanded status from being changed is expandable is False."""
        if not self.expandable:
            if self.expandable_state is not self.expanded:
                self.expanded = self.expandable_state
        else:
            self.emit( "expanded-changed" )
    def _gui_clear( self ):
        self.signals_blocked = True
        self._maineditor._gui_clear()
        self._addresseditor._gui_clear()
        self._correspondenceeditor._gui_clear()
        self._bankaccounteditor._gui_clear()
        self._contracteditor._gui_clear()
        self.builder.get_object( 'save_button' ).set_sensitive( False )
        self.builder.get_object( 'discard_button' ).set_sensitive( False )
        self.signals_blocked = False
    # Callbacks
    def save_button_clicked_cb( self, button ):
        if self.signals_blocked: return
        self.save()
        self.check_changes()
    def discard_button_clicked_cb( self, button=None ):
        if self.signals_blocked: return
        self.reset()
        self.check_changes()
    def check_changes( self, childeditor=None ):
        if self.signals_blocked: return
        if self.expanded:
            logger.debug( "Was the data in CustomerEditor changed? %r", self.has_changes() )
            if self.has_changes():
                if self.data_is_valid():
                    self.expandable = True
                    self.builder.get_object( 'save_button' ).set_sensitive( True )
                    self.builder.get_object( 'discard_button' ).set_sensitive( True )
                else:
                    self.expandable = False
                    self.builder.get_object( 'save_button' ).set_sensitive( False )
                    self.builder.get_object( 'discard_button' ).set_sensitive( True )
            else:
                self.builder.get_object( 'save_button' ).set_sensitive( False )
                self.builder.get_object( 'discard_button' ).set_sensitive( False )
        self.emit( "changed" )

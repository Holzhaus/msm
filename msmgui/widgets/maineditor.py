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
logger = logging.getLogger( __name__ )
import locale
import dateutil.parser
from gi.repository import Gtk, GObject
from core import paths
from core.database import GenderType
from msmgui.widgets.base import ScopedDatabaseObject
class MainEditor( Gtk.Box, ScopedDatabaseObject ):
    """Address editor inside the Customer editor"""
    __gsignals__ = {
        'changed': ( GObject.SIGNAL_RUN_FIRST, None, () ),
    }
    def __init__( self, session ):
        ScopedDatabaseObject.__init__( self, session )
        Gtk.Box.__init__( self )
        self.signals_blocked = True
        self._customer = None
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file(paths.data("ui", "widgets", "customerwindow","customereditor","maineditor.glade" ))
        self.builder.get_object( "content" ).reparent( self )
        self.set_child_packing( self.builder.get_object( "content" ), True, True, 0, Gtk.PackType.START )
        # Connect Signals
        self.builder.connect_signals( self )
    def start_edit( self, customer ):
        self._customer = customer
        self._gui_fill()
    # GUI Functions
    def _gui_clear( self ):
        self.builder.get_object( 'id_entry' ).set_text( "" )
        self.builder.get_object( 'familyname_entry' ).set_text( "" )
        self.builder.get_object( 'prename_entry' ).set_text( "" )
        self._gui_set_combobox_text( self.builder.get_object( 'honourific_comboboxtext' ), "" )
        self._gui_set_combobox_text( self.builder.get_object( 'title_comboboxtext' ), "" )
        self.builder.get_object( 'gender_combobox' ).set_active( GenderType.Undefined )
        self.builder.get_object( 'birthday_entry' ).set_text( "" )
        self.builder.get_object( 'company1_entry' ).set_text( "" )
        self.builder.get_object( 'company2_entry' ).set_text( "" )
        self.builder.get_object( 'department_entry' ).set_text( "" )
        self.builder.get_object( 'email_entry' ).set_text( "" )
        self.builder.get_object( 'phone_entry' ).set_text( "" )
        self.builder.get_object( 'fax_entry' ).set_text( "" )
    def _gui_fill( self ):
        self._gui_clear()
        self.builder.get_object( 'id_entry' ).set_text( str( self._customer.id ) if self._customer.id else "" )
        self.builder.get_object( 'familyname_entry' ).set_text( self._customer.familyname if self._customer.familyname else "" )
        self.builder.get_object( 'prename_entry' ).set_text( self._customer.prename if self._customer.prename else "" )
        self._gui_set_combobox_text( self.builder.get_object( 'honourific_comboboxtext' ), self._customer.honourific )
        self._gui_set_combobox_text( self.builder.get_object( 'title_comboboxtext' ), self._customer.title )
        self.builder.get_object( 'gender_combobox' ).set_active( self._customer.gender if self._customer.gender else GenderType.Undefined )
        self.builder.get_object( 'birthday_entry' ).set_text( self._customer.birthday.strftime( locale.nl_langinfo( locale.D_FMT ) ) if self._customer.birthday else "" )
        self.builder.get_object( 'company1_entry' ).set_text( self._customer.company1 if self._customer.company1 else "" )
        self.builder.get_object( 'company2_entry' ).set_text( self._customer.company2 if self._customer.company2 else "" )
        self.builder.get_object( 'department_entry' ).set_text( self._customer.department if self._customer.department else "" )
        self.builder.get_object( 'email_entry' ).set_text( self._customer.email if self._customer.email else "" )
        self.builder.get_object( 'phone_entry' ).set_text( self._customer.phone if self._customer.phone else "" )
        self.builder.get_object( 'fax_entry' ).set_text( self._customer.fax if self._customer.fax else "" )
    def _gui_set_combobox_text( self, comboboxtext, value ):
        value_set = False
        for i, row in enumerate( comboboxtext.get_model() ):
            if row[0] == value:
                comboboxtext.set_active( i )
                value_set = True
                break
        if not value_set:
            if value != comboboxtext.get_active_text():
                comboboxtext.append_text( value )
                comboboxtext.set_active( i + 1 )
    # Callbacks
    def prename_entry_changed_cb( self, entry, user_data=None ):
        if self.signals_blocked: return
        self._customer.prename = entry.get_text().strip()
        self.emit( "changed" )
    def familyname_entry_changed_cb( self, entry, user_data=None ):
        if self.signals_blocked: return
        self._customer.familyname = entry.get_text().strip()
        self.emit( "changed" )
    def company1_entry_changed_cb( self, entry, user_data=None ):
        if self.signals_blocked: return
        self._customer.company1 = entry.get_text().strip()
        self.emit( "changed" )
    def company2_entry_changed_cb( self, entry, user_data=None ):
        if self.signals_blocked: return
        self._customer.company2 = entry.get_text().strip()
        self.emit( "changed" )
    def department_entry_changed_cb( self, entry, user_data=None ):
        if self.signals_blocked: return
        self._customer.department = entry.get_text().strip()
        self.emit( "changed" )
    def birthday_entry_changed_cb( self, entry, user_data=None ):
        if self.signals_blocked: return
        new_date = None
        text = entry.get_text().strip()
        if text:
            try:
                new_date = dateutil.parser.parse( text, dayfirst=True )
            except Exception as error:
                logger.warning( 'Invalid date entered: %s (%r)', text, error )
            else:
                new_date = new_date.date()
        self._customer.birthday = new_date
        self.emit( "changed" )
    def gender_combobox_changed_cb( self, combo ):
        if self.signals_blocked: return
        self._customer.gender = combo.get_model()[combo.get_active()][0] if ( combo.get_active() > 0 ) else 0
        self.emit( "changed" )
    def honourific_comboboxtext_changed_cb( self, combo ):
        if self.signals_blocked: return
        self._customer.honourific = combo.get_active_text().strip()
        self.emit( "changed" )
    def title_comboboxtext_changed_cb( self, combo ):
        if self.signals_blocked: return
        self._customer.title = combo.get_active_text().strip()
        self.emit( "changed" )
    def email_entry_changed_cb( self, entry, user_data=None ):
        if self.signals_blocked: return
        self._customer.email = entry.get_text().strip()
        self.emit( "changed" )
    def phone_entry_changed_cb( self, entry, user_data=None ):
        if self.signals_blocked: return
        self._customer.phone = entry.get_text().strip()
        self.emit( "changed" )
    def fax_entry_changed_cb( self, entry, user_data=None ):
        if self.signals_blocked: return
        self._customer.fax = entry.get_text().strip()
        self.emit( "changed" )

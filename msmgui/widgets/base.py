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
from gi.repository import Gtk
import sqlalchemy.orm.scoping
import core.database
class RefreshableWindow( Gtk.Overlay ):
    def __init__( self, refreshable_objects ):
        Gtk.Overlay.__init__( self )
        self._objects = set( refreshable_objects )
        for obj in self._objects:
            if not hasattr( obj, "refresh" ) or not hasattr( obj, "needs_refresh" ) or not hasattr( obj, "currently_refreshing" ):
                raise RuntimeError()
            obj.connect( "refresh-started", self._refresh_started_cb )
            obj.connect( "refresh-ended", self._refresh_ended_cb )
        self._loadingspinner = Gtk.Spinner()
        self._loadingspinner.hide()
        self.add_overlay( self._loadingspinner )
    def refresh( self ):
        for obj in self._objects:
            if obj.needs_refresh and not obj.currently_refreshing:
                obj.refresh()
    """
    Callbacks
    """
    def _refresh_started_cb( self, calling_obj, user_data=None ):
        logger.debug( 'Refresh started for obj %r', calling_obj )
        currently_refreshing_objects = [obj for obj in self._objects if obj.currently_refreshing is True and obj is not calling_obj]
        if len( currently_refreshing_objects ) == 0:
            self.set_sensitive( False )
            self._loadingspinner.show()
            self._loadingspinner.start()
    def _refresh_ended_cb( self, calling_obj, user_data=None ):
        logger.debug( 'Refresh ended for obj %r', calling_obj )
        currently_refreshing_objects = [obj for obj in self._objects if obj.currently_refreshing is True and obj is not calling_obj]
        if len( currently_refreshing_objects ) == 0:
            self.set_sensitive( True )
            self._loadingspinner.stop()
            self._loadingspinner.hide()

class ScopedDatabaseObject( object ):
    @property
    def session( self ):
        return self._session
    def _scopefunc( self ):
        """ Needed as scopefunc argument for the scoped_session"""
        return self
    def __init__( self, session=None ):
        if type( session ) is not sqlalchemy.orm.scoping.scoped_session:
            session = core.database.Database.get_scoped_session( self._scopefunc )
        # Store reference to the session
        if type( session ) is not sqlalchemy.orm.scoping.scoped_session:
            raise RuntimeError( "Can't __init__ without a session!" )
        self._session = session

class ConfirmationDialog( Gtk.MessageDialog ):
    def __init__( self, parent_window, message ):
        super().__init__( parent_window, Gtk.DialogFlags.MODAL, Gtk.MessageType.WARNING, Gtk.ButtonsType.YES_NO, "Bist du sicher?" )
        self.format_secondary_text( message )

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from gi.repository import Gtk
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
        currently_refreshing_objects = [obj for obj in self._objects if obj.currently_refreshing is True and obj is not calling_obj]
        if len( currently_refreshing_objects ) == 0:
            self.set_sensitive( False )
            self._loadingspinner.show()
            self._loadingspinner.start()
    def _refresh_ended_cb( self, calling_obj, user_data=None ):
        currently_refreshing_objects = [obj for obj in self._objects if obj.currently_refreshing is True and obj is not calling_obj]
        if len( currently_refreshing_objects ) == 0:
            self.set_sensitive( True )
            self._loadingspinner.stop()
            self._loadingspinner.hide()
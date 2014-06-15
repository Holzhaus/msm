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
from gi.repository import GObject, Gtk
from core.config import Config
import msmgui.widgets.invoicetable
import msmgui.assistants.invoicing
import msmgui.assistants.letterexport
import msmgui.widgets.base
class InvoiceWindow( msmgui.widgets.base.RefreshableWindow ):
    __gsignals__ = {
        'status-changed': ( GObject.SIGNAL_RUN_FIRST, None, ( str, ) )
    }
    def __init__( self ):
        self._invoicetable = msmgui.widgets.invoicetable.InvoiceTable()
        msmgui.widgets.base.RefreshableWindow.__init__( self, [self._invoicetable] )
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/widgets/invoicewindow/invoicewindow.glade" )
        self.builder.get_object( "content" ).reparent( self )
        self.builder.connect_signals( self )

        self.builder.get_object( "tablebox" ).add( self._invoicetable )
        self._invoicetable.connect( "selection-changed", self.invoicetable_selection_changed_cb )

        self._invoicingassistant = msmgui.assistants.invoicing.InvoicingAssistant()
        self._invoicingassistant.connect( "saved", self.invoicingassistant_saved_cb )

        self._letterexportassistant = msmgui.assistants.letterexport.LetterExportAssistant()

        active_only = Config.getboolean( "Interface", "active_only" )
        if not active_only:
            self.builder.get_object( "invoices_showall_switch" ).set_active( not active_only )
    def invoicetable_selection_changed_cb( self, table ):
        pass
    def invoices_search_entry_changed_cb( self, entry ):
        self._invoicetable.filter = entry.get_text().strip()
    def invoices_showall_switch_notify_active_cb( self, switch, param_spec ):
        self._invoicetable.active_only = not switch.get_active()
    def invoices_create_button_clicked_cb( self, button ):
        self._invoicingassistant.set_parent( self.get_toplevel() )
        self._invoicingassistant.show()
    def invoices_export_button_clicked_cb( self, button ):
        self._letterexportassistant.set_parent( self.get_toplevel() )
        self._letterexportassistant.show()
    def invoicingassistant_saved_cb( self, assistant, num_invoices ):
        if num_invoices > 0:
            self.emit( "status-changed", ( "Eine Rechnung erstellt." if num_invoices == 1 else "%d Rechnungen erstellt." % num_invoices ) )
            self._invoicetable.needs_refresh = True
            self.refresh()
        else:
            self.emit( "status-changed", "Keine Rechnungen erstellt." )

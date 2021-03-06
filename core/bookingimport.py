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
import threading
from core.database import Contract, BookkeepingEntry
from msmgui.widgets.base import ScopedDatabaseObject


class BookingImporter(threading.Thread, ScopedDatabaseObject):
    def __init__(self, input_file, importer, update_step=25):
        threading.Thread.__init__(self)
        ScopedDatabaseObject.__init__(self)
        self.logger = logging.getLogger(__name__)
        self._input_file = input_file
        self._importer = importer
        self._update_step = update_step

    def run(self):
        self.logger.info("Lese Datensätze aus Datei...")
        entries = [entry for entry in self._importer.read(self._input_file) if entry is not None]
        num_entries = len(entries)
        self.logger.info("%d Datensätze gelesen", num_entries)
        entries_added = 0
        for i, data in enumerate(entries, start=1):
            if (not self._update_step or
               (i % self._update_step) == 0 or
               i in (0, 1)):
                self.logger.info("Analysiere Datensatz %d von %d...", i, num_entries)
            date, value, description, contractnumber, invoicenumber = data

            if not Contract.is_valid_refid(contractnumber):
                self.logger.debug("Invalid contract refid '%s'" % contractnumber)
                continue

            contract = Contract.get_by_refid(contractnumber, session=self.session)
            if not contract:
                self.logger.debug("Cant find contract for refid '%s'" % contractnumber)
                continue

            invoices = [invoice for invoice in contract.invoices if invoice.number == invoicenumber]
            if len(invoices) != 1:
                self.logger.debug("Cant find invoice '%s-%d'", contractnumber, invoicenumber)
            invoice = invoices[0]

            already_in_db = False
            for entry in invoice.entries:
                if (entry.date == date and
                   entry.value == value and 
                   entry.description == description):
                    already_in_db = True
                    break
            if already_in_db:
                self.logger.debug("Entry already in database, skipping...")
                continue

            invoice.add_entry(date, value, description)
            entries_added += 1
        if entries_added:
            self.logger.info('Schreibe %d von %d Datensätzen in Datenbank...', entries_added, num_entries)
            self._session.commit()
            self.logger.info('Fertig! %d von %d Datensätzen hinzugefügt (%d ignoriert)...', entries_added, num_entries, num_entries - entries_added)
        else:
            self.logger.info('Keine Datensätze hinzugefügt.')
        self._session.expunge_all()
        self._session.remove()

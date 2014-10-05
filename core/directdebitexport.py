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
import threading
from core.database import Invoice, PaymentType
from msmgui.widgets.base import ScopedDatabaseObject


class DirectDebitExporter( threading.Thread, ScopedDatabaseObject ):
    def __init__( self, output_file, formatter, update_step=25 ):
        self.logger = logging.getLogger(__name__)
        threading.Thread.__init__( self )
        ScopedDatabaseObject.__init__( self )
        self._output_file = output_file
        self._formatter = formatter
        self._update_step = update_step

    def run(self):
        self.logger.info("Hole Rechnungen aus Datenbank...")
        # add settings to the local session
        all_invoices = list(Invoice.get_all(session=self.session))
        invoices = []
        for invoice in all_invoices:
            if (invoice.value_left > 0 and
               invoice.contract is not None and
               invoice.contract.bankaccount is not None and
               invoice.contract.paymenttype == PaymentType.DirectWithdrawal):
                invoices.append(invoice)
        num_invoices = len(invoices)
        self.logger.info("1 Rechnung geholt!" if num_invoices == 1 else "{} Rechnungen geholt!".format(num_invoices))
        self.logger.info("Exportiere Daten aus 1 Rechnung..." if num_invoices == 1 else "Exportiere Daten aus {} Rechnungen...".format(num_invoices))

        for work_done, output in enumerate(self._formatter.write(invoices,
                                                         self._output_file),
                                   start=1):
            if (not self._update_step or
               (work_done % self._update_step) == 0 or
               work_done in (0, 1)):
                self.logger.info("Exportiere %d von %s", work_done,
                                  num_invoices)
        
        self._session.expunge_all()
        self._session.remove()
        self.logger.info("Fertig! 1 Datensatz exportiert." if work_done == 1
                          else
                          "Fertig! {} Datensätze exportiert.".format(work_done))

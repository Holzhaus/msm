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
from core.database import Contract
from msmgui.widgets.base import ScopedDatabaseObject

def get_contracts( magazine=None, issue=None, date=None, session=None ):
    contracts = None
    if issue is not None:
        logger.debug( 'Getting contracts for Issue %r', issue )
        contracts = issue.get_contracts( session=session )
    elif magazine is not None:
        logger.debug( 'Getting contracts for Magazine %r and Date %r', magazine, date )
        contracts = magazine.get_contracts( date=date, session=session )
    else:
        if date is not None:
            logger.debug( 'Getting contracts for Date %r', date )
            contracts = Contract.get_running_contracts_by_date( date=date, session=session )
        else:
            logger.debug( 'Getting all contracts' )
            contracts = Contract.get_all( session=session )
    if contracts is None:
        raise RuntimeError( "These settings look strange." )
    return contracts

class ContractExporter( threading.Thread, ScopedDatabaseObject ):
    def __init__( self, output_file, formatter, magazine, issue, date, update_step=25 ):
        self.logger = logging.getLogger(__name__)
        threading.Thread.__init__( self )
        ScopedDatabaseObject.__init__( self )
        self._output_file = output_file
        self._formatter = formatter
        self._magazine = magazine
        self._issue = issue
        self._date = date
        self._update_step = update_step

    def run(self):
        self.logger.info("Hole Verträge aus Datenbank...")
        # add settings to the local session
        magazine = self._session.merge( self._magazine ) if self._magazine is not None else None
        issue = self._session.merge( self._issue ) if self._issue is not None else None
        date = self._date
        contracts = get_contracts( magazine=magazine, issue=issue, date=date, session=self.session )
        num_contracts = len(list(contracts))
        self.logger.info("1 Vetrag geholt!" if num_contracts == 1 else "{} Verträge geholt!".format(num_contracts))
        self.logger.info("Exportiere Daten aus 1 Vetrag..." if num_contracts == 1 else "Exportiere Daten aus {} Veträgen...".format(num_contracts))

        for work_done, output in enumerate(self._formatter.write(contracts,
                                                         self._output_file),
                                   start=1):
            if (not self._update_step or
               (work_done % self._update_step) == 0 or
               work_done in (0, 1)):
                self.logger.info("Exportiere %d von %s", work_done,
                                  num_contracts)

        self._session.expunge_all()
        self._session.remove()
        self.logger.info("Fertig! 1 Datensatz exportiert." if work_done == 1
                          else
                          "Fertig! {} Datensätze exportiert.".format(work_done))

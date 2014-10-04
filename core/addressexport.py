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
import csv
import pytz
from core.database import Contract
from msmgui.widgets.base import ScopedDatabaseObject

def get_contracts( magazine=None, issue=None, date=None, session=None ):
    contracts = None
    if issue is not None:
        logger.debug( 'Getting shippingaddresses for Issue %r', issue )
        contracts = issue.get_contracts( session=session )
    elif magazine is not None:
        logger.debug( 'Getting shippingaddresses for Magazine %r and Date %r', magazine, date )
        contracts = magazine.get_contracts( date=date, session=session )
    else:
        if date is not None:
            logger.debug( 'Getting shippingaddresses for Date %r', date )
            contracts = Contract.get_running_contracts_by_date( date=date, session=session )
        else:
            logger.debug( 'Getting ALL shippingaddresses' )
            contracts = Contract.get_all( session=session )
    if contracts is None:
        raise RuntimeError( "These settings look strange." )
    return contracts

class AddressExporter( threading.Thread, ScopedDatabaseObject ):
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
    def run( self ):
        self.logger.info("Hole Adressen aus Datenbank...")
        # add settings to the local session
        magazine = self._session.merge( self._magazine ) if self._magazine is not None else None
        issue = self._session.merge( self._issue ) if self._issue is not None else None
        date = self._date
        unfiltered_contracts = get_contracts( magazine=magazine, issue=issue, date=date, session=self.session )
        contracts = []
        for contract in unfiltered_contracts:
            address = contract.shippingaddress
            if not address:
                logger.warning( 'Contract %s (%s) has no shippingaddress', contract.refid, contract.customer.name )
            else:
                contracts.append( contract )
        num_contracts = len(contracts)
        self.logger.info("1 Adresse geholt!" if num_contracts == 1 else "{} Adressen geholt!".format(num_contracts))
        self.logger.info("Exportiere 1 Adresse..." if num_contracts == 1 else "Exportiere {} Adressen...".format(num_contracts))

        for work_done, work_total in self._formatter.write(contracts,
                                                           self._output_file):
            if (not self._update_step or
               (work_done % self._update_step) == 0 or
               work_done in (0, 1)):
                self.logger.info("Exportiere %d von %s", work_done,
                                  work_total)

        self._session.expunge_all()
        self._session.remove()
        self.logger.info("Fertig! 1 Adresse exportiert." if work_done == 1
                          else
                          "Fertig! {} Adressen exportiert.".format(work_done))

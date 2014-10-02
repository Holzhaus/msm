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

class AddressExporterGeneric( threading.Thread, ScopedDatabaseObject ):
    def __init__( self, output_file, magazine, issue, date ):
        threading.Thread.__init__( self )
        ScopedDatabaseObject.__init__( self )
        self._output_file = output_file
        self._magazine = magazine
        self._issue = issue
        self._date = date
    def run( self ):
        self.on_init_start()
        # add settings to the local session
        magazine = self._session.merge( self._magazine ) if self._magazine is not None else None
        issue = self._session.merge( self._issue ) if self._issue is not None else None
        date = self._date
        unfiltered_contracts = get_contracts( magazine=magazine, issue=issue, date=date, session=self.session )
        contracts = []
        for contract in unfiltered_contracts:
            address = contract.shippingaddress
            if not address:
                logger.critical( 'Contract %s (%s) has no shippingaddress', contract.refid, contract.customer.name )
            else:
                contracts.append( contract )
        self.on_init_finished( len( contracts ) )

        self.on_export_start( len( contracts ) )
        self.begin_write( self._output_file )
        work_done = 0
        for contract in contracts:
            self.write( contract )
            work_done += 1
            self.on_export_output( work_done, len( contracts ) )
        self.end_write( self._output_file )
        self._session.expunge_all()
        self._session.remove()
        self.on_export_finished( work_done )
    def begin_write( self, output_file ):
        raise NotImplementedError
    def write( self, address ):
        raise NotImplementedError
    def end_write( self, output_file ):
        raise NotImplementedError
    def on_init_start( self ):
        """
        Called when database query starts
        """
        pass
    def on_init_finished( self, addresses_fetched ):
        """
        Called when database query finishes
        """
        pass
    def on_export_start( self, work_started ):
        """
        Called when exporting starts
        """
        pass
    def on_export_output( self, work_done, work_started ):
        """
        Called when exporting produces output
        """
        pass
    def on_export_finished( self, work_done ):
        """
        Called when exporting finishes
        """
        pass
class AddressExporterCSV( AddressExporterGeneric ):
    def begin_write( self, output_file ):
        fieldnames = ['RECIPIENT', 'CO', 'STREET', 'CITY', 'POSTALCODE', 'COUNTRYCODE', 'COUNTRYNAME', 'CONTRACTNUMBER']
        self._csvfile = open( output_file, 'w', newline='' )
        self._csvwriter = csv.writer( self._csvfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL )
        self._csvwriter.writerow( fieldnames )
    def write( self, contract ):
        address = contract.shippingaddress
        recipient = address.recipient if address.recipient else address.customer.name
        countryname = pytz.country_names[address.countrycode.lower()]
        row = [recipient, address.co, address.street, address.city, address.zipcode, address.countrycode, countryname, contract.refid] # FIXME: improvement needed
        self._csvwriter.writerow( row )
    def end_write( self, output_file ):
        self._csvfile.close()

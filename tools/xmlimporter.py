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
import sys
import os
import logging
if __name__ == "__main__":
    logger = logging.getLogger()
    sys.path = [os.path.abspath( '..' )] + sys.path
else:
    logger = logging.getLogger( __name__ )
import locale
try:
    from lxml import etree
    logger.debug( "running with lxml.etree" )
except ImportError:
    try:
        # Python 2.5
        import xml.etree.cElementTree as etree
        logger.debug( "running with cElementTree on Python 2.5+" )
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.ElementTree as etree
            logger.debug( "running with ElementTree on Python 2.5+" )
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as etree
                logger.debug( "running with cElementTree" )
            except ImportError:
                try:
                    # normal ElementTree install
                    import elementtree.ElementTree as etree
                    logger.debug( "running with ElementTree" )
                except ImportError:
                    logger.debug( "Failed to import ElementTree from any known place" )
import dateutil.parser
from core.config import Config
import core.database
def import_xml( session, filename ):
    subscription_mapping = ( ( 1, 'Normalabo Position' ), ( 2, 'Soliabo Position' ) )
    tree = etree.parse( filename )
    root = tree.getroot()
    for el_customer in root:
        customer = core.database.Customer( el_customer.get( 'familyname' ), el_customer.get( 'prename' ) )
        customer.company1 = el_customer.get( 'company' )
        customer.honourific = el_customer.get( 'honourific' )
        customer.title = el_customer.get( 'title' )
        if el_customer.get( 'birthday' ):
            customer.birthday = dateutil.parser.parse( el_customer.get( 'birthday' ), dayfirst=True ).date()
        if el_customer.get( 'gender' ):
            if el_customer.get( 'gender' ) == 'm':
                customer.gender = core.database.GenderType.Male
            elif el_customer.get( 'gender' ) == 'f':
                customer.gender = core.database.GenderType.Female
        if el_customer.get( 'telephone' ):
            if el_customer.get( 'telephone-prefix' ):
                customer.phone = "-".join( ( el_customer.get( 'telephone-prefix' ), el_customer.get( 'telephone' ) ) )
        if el_customer.get( 'telefax' ):
            customer.fax = el_customer.get( 'telefax' )
        if el_customer.get( 'email' ):
            customer.email = el_customer.get( 'email' )
        address = None
        for el_address in el_customer.find( 'addresses' ):
            address = customer.add_address( el_address.get( 'street' ), el_address.get( 'zipcode' ), el_address.get( 'city' ), el_address.get( 'country' ) )
        bankaccount = None
        for el_bankaccount in el_customer.find( 'bankaccounts' ):
            bankaccount = customer.add_bankaccount( el_bankaccount.get( 'iban' ), el_bankaccount.get( 'bic' ), el_bankaccount.get( 'name' ), "" )
        el_contracts = el_customer.find( 'contracts' )
        if el_contracts is not None:
            for el_contract in el_customer.find( 'contracts' ):
                startdate = dateutil.parser.parse( el_contract.get( 'startdate' ), dayfirst=True ).date()
                enddate = dateutil.parser.parse( el_contract.get( 'enddate' ), dayfirst=True ).date() if el_contract.get( 'enddate' ) else None
                subscription = None
                for s_id, s_name in subscription_mapping:
                    if el_contract.get( 'old-subscription-name' ) == s_name:
                        subscription = core.database.Subscription.get_by_id( s_id, session=session )
                if subscription is None:
                    logger.critical( "Can't find subscription: '%s'", el_contract.get( 'old-subscription-name' ) )
                try:
                    value = locale.atof( el_contract.get( 'value' ) )
                except ValueError:
                    logger.warning( "Customer '%s' - Wrong contract value, using subscription value instead", customer.name )
                    value = subscription.value
                paymenttype = core.database.PaymentType.DirectWithdrawal if bankaccount is not None else core.database.PaymentType.Invoice
                contract = customer.add_contract( subscription, startdate, enddate , value, paymenttype, address, address, bankaccount )
        session.add( customer )
    session.commit()
if __name__ == "__main__":
    if not len( sys.argv ) == 2:
        print( "Usage:" )
        print( "  {} XML_FILE".format( sys.argv[0] ) )
        sys.exit( 1 )
    filename = os.path.abspath( sys.argv[1] )
    if not os.path.exists( filename ):
        print( "File '{}' does not exist".format( filename ) )
        sys.exit( 2 )
    db_uri = Config.get( "Database", "db_uri" )
    database = core.database.Database( db_uri )
    session = core.database.Database.get_scoped_session()
    import_xml( session, filename )

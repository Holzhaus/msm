#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
if __name__ == "__main__":
    sys.path = [os.path.abspath( '..' )] + sys.path
import locale
try:
    from lxml import etree
    print( "running with lxml.etree" )
except ImportError:
    try:
        # Python 2.5
        import xml.etree.cElementTree as etree
        print( "running with cElementTree on Python 2.5+" )
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.ElementTree as etree
            print( "running with ElementTree on Python 2.5+" )
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as etree
                print( "running with cElementTree" )
            except ImportError:
                try:
                    # normal ElementTree install
                    import elementtree.ElementTree as etree
                    print( "running with ElementTree" )
                except ImportError:
                    print( "Failed to import ElementTree from any known place" )
import dateutil.parser
import core.config
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
        for el_contract in el_customer.find( 'contracts' ):
            startdate = dateutil.parser.parse( el_contract.get( 'startdate' ), dayfirst=True ).date()
            enddate = dateutil.parser.parse( el_contract.get( 'enddate' ), dayfirst=True ).date() if el_contract.get( 'enddate' ) else None
            subscription = None
            for s_id, s_name in subscription_mapping:
                if el_contract.get( 'subscription' ) == s_name:
                    subscription = core.database.Subscription.get_by_id( s_id, session=session )
            try:
                value = locale.atof( el_contract.get( 'value' ) )
            except ValueError:
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
    os.chdir( '..' )
    db_uri = core.config.Configuration().get( "Database", "db_uri" )
    database = core.database.Database( db_uri )
    session = core.database.Database.get_scoped_session()
    import_xml( session, filename )

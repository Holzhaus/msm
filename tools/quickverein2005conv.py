#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
if __name__ == "__main__":
    sys.path = [os.path.abspath( '..' )] + sys.path
import csv
from core.autocompletion import Banks, Cities
import core.lib.iban as iban
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

def get_bankaccount( row, i ):
    if row['KONTO%d' % i] or row['BLZ%d' % i] or row['BANK%d' % i]:
        if row['KONTO%d' % i] == 'SEPA':
            acc_iban = row['BANK%d' % i]
            acc_bic = row['BLZ%d' % i]
            acc_bankname = ''
            bank = Banks.get_by_bic( acc_bic )
            if not bank:
                try:
                    iban.check_iban( acc_iban )
                except iban.IBANError:
                    return
                else:
                    bank = Banks.get_by_iban( acc_iban )
                    if not bank:
                        return
            acc_bic = bank.bic
            acc_bankname = bank.name_short
        else:
            try:
                bankcode = row['BLZ%d' % i]
                accountnumber = row['KONTO%d' % i]
                acc_iban = iban.create_iban( "DE", bankcode, accountnumber )
            except iban.IBANError:
                return
            else:
                bank = Banks.get( 'DE', 'bankcode', bankcode )
                if not bank:
                    return
                acc_bic = bank.bic
                acc_bankname = bank.name_short
                # print("  Correct IBAN: %s << %s ?? %s %s" % (acc_iban, "DE", bankcode, accountnumber))
        acc = etree.Element( "bankaccount" )
        acc.set( 'iban', acc_iban )
        acc.set( 'bic', acc_bic )
        acc.set( 'name', acc_bankname )
        return acc
def get_address( row ):
    street = row['STRASSE']
    city = row['ORT']
    zipcode = row['PLZ']
    if '-' in zipcode:
        country, zipcode = zipcode.split( '-' )
        country = 'AT' if country == 'A' else country
        country = 'BE' if country == 'B' else country
    else:
        country = 'DE'
    country = 'GB' if zipcode.startswith( 'BT ' ) else country # FIXME: superdirty
    addr = etree.Element( "address" )
    addr.set( 'street', street )
    addr.set( 'zipcode', zipcode )
    addr.set( 'city', city )
    addr.set( 'country', country )
    return addr
def get_contract( row, external_contracts ):
    # startdate = row['EINTRITT']
    # enddate = row['AUSTRITT']
    old_refid = row['MITGLNR']
    data = external_contracts[old_refid] if old_refid in external_contracts else None
    if not data:
        return
    contr = etree.Element( "contract" )
    contr.set( 'startdate', data['startdate'] )
    contr.set( 'enddate', data['enddate'] )
    contr.set( 'value', data['value'] )
    contr.set( 'subscription', data['subscription'] )
    return contr

def read_contracts( filename ):
    contracts = {}
    subscription_name = ""
    with open( filename, 'r', encoding='iso-8859-1' ) as csvfile:
        csvreader = csv.reader( csvfile, delimiter=';' )
        for row in csvreader:
            if not row[0]:
                continue
            if row[0] == 'Beitragsart:':
                subscription_name = row[2]
            else:
                try: int( row[0] )
                except: continue
            refid = row[1]
            startdate = row[8]
            enddate = row[9]
            value = row[10]
            contracts[refid] = {'startdate': startdate, 'enddate':enddate, 'value':value, 'subscription': subscription_name}
    return contracts

if __name__ == "__main__":
    if not ( len( sys.argv ) == 3 or len( sys.argv ) == 4 ):
        print( "Usage:" )
        print( "  {} ADDRESSEEXCEL_FILE LINEAR_FILE [OUTFILE]".format( sys.argv[0] ) )
        sys.exit( 1 )
    infile1 = os.path.abspath( sys.argv[1] )
    if not os.path.exists( infile1 ):
        print( "File '{}' does not exist".format( infile1 ) )
        sys.exit( 2 )
    infile2 = os.path.abspath( sys.argv[2] )
    if not os.path.exists( infile2 ):
        print( "File '{}' does not exist".format( infile2 ) )
        sys.exit( 3 )
    if len( sys.argv ) == 4:
        outfile = sys.argv[3]
    else:
        outfile = None
    external_contracts = read_contracts( infile2 )
    with open( infile1, 'r', encoding='iso-8859-1' ) as csvfile:
        csvreader = csv.DictReader( csvfile, delimiter=';' )
        customers = etree.Element( 'customers' )
        for row in csvreader:
            customer = etree.Element( 'customer' )
            company = ""
            prename = ""
            familyname = ""
            if not row['VORNAME']:
                company = row['NACHNAME']
            else:
                prename = row['VORNAME'].title()
                familyname = row['NACHNAME'].title()
            customer.set( 'company', company )
            customer.set( 'prename', prename )
            customer.set( 'familyname', familyname )
            customer.set( 'old-id', row['MITGLNR'] )
            customer.set( 'honourific', row['ANREDE'] )
            customer.set( 'title', row['TITEL'] )
            customer.set( 'birthday', row['TITEL'] )
            customer.set( 'maritial-status', row['FAMILIENST'] )
            customer.set( 'matchcode', row['MATCHCODE'] )
            customer.set( 'email', row['EMAIL'] )
            customer.set( 'telephone-prefix', row['VORWAHL'] )
            customer.set( 'telephone', row['TELEFON'] )
            customer.set( 'telefax', row['FAX'] )
            gender = ""
            if row['GESCHLECHT']:
                if row['GESCHLECHT'] == 'MÄNNLICH':
                    gender = 'm'
                elif row['GESCHLECHT'] == 'WEIBLICH':
                    gender = 'f'
            customer.set( 'gender', gender )
            # Bankaccounts
            bankaccounts = etree.SubElement( customer, "bankaccounts" )
            for i in range( 1, 4 ):
                bankaccount = get_bankaccount( row, i )
                if bankaccount is not None:
                    bankaccounts.append( bankaccount )
            # Addresses
            addresses = etree.SubElement( customer, "addresses" )
            address = get_address( row )
            if address is not None:
                addresses.append( address )
            # Contracts
            contracts = etree.SubElement( customer, "contracts" )
            contract = get_contract( row, external_contracts )
            if contract is not None:
                contracts.append( contract )
            customers.append( customer )
    output = etree.tostring( customers, pretty_print=True, xml_declaration=True, encoding='utf-8' )
    if outfile:
        f = open( outfile, 'wb' )
        f.write( output )
    else:
        print( output.decode( 'utf-8' ) )

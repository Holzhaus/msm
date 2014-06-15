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
import csv
from core.autocompletion import Banks, Cities
import core.lib.iban as iban
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
                    logger.critical( "Failed to import ElementTree from any known place" )
                    sys.exit( 1 )
class CustomerParser:
    @staticmethod
    def get_customer_name( customer ):
        if customer.get( 'prename' ):
            name = "%s, %s" % ( customer.get( 'familyname' ), customer.get( 'prename' ) )
        else:
            name = customer.get( 'company' )
        return name
    @classmethod
    def parse( cls, row, additional_data=None ):
        customer = etree.Element( 'customer' )
        cls.parse_data( customer, row )
        cls.parse_addresses( customer, row )
        cls.parse_bankaccounts( customer, row )
        if additional_data:
            customer_id = customer.get( 'old-id' )
            if customer_id in additional_data:
                data = additional_data.pop( customer_id )
                for elem in data:
                    customer.append( elem )
            else:
                customer_name = cls.get_customer_name( customer )
                logger.warning( "Customer '%s' (%s) - No contract found", customer_id, customer_name )
        return customer
    @staticmethod
    def parse_data( customer, row ):
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
    @classmethod
    def parse_bankaccounts( cls, customer, row ):
        # Bankaccounts
        bankaccounts = etree.SubElement( customer, "bankaccounts" )
        for i in range( 1, 4 ):
            bankaccount = cls.get_bankaccount( customer, row, i )
            if bankaccount is not None:
                bankaccounts.append( bankaccount )
        customer.append( bankaccounts )
    @classmethod
    def parse_addresses( cls, customer, row ):
        # Addresses
        addresses = etree.SubElement( customer, "addresses" )
        customer_id = customer.get( 'old-id' )
        address = cls.get_address( customer_id, row )
        if address is not None:
            addresses.append( address )
        customer.append( addresses )
    @classmethod
    def parse_contracts( cls, customer, contracts_data ):
        # Contracts
        contracts = etree.SubElement( customer, "contracts" )
        customer_id = customer.get( 'old-id' )
        if customer_id in contracts_data:
            contract_data = contracts_data[customer_id]
            contract = cls.get_contract( customer_id, contract_data )
            if contract is not None:
                contracts.append( contract )
        else:
            logger.warning( "Customer '%s' (%s) - No contracts found", customer_id, cls.get_customer_name( customer ) )
        customer.append( contracts )
    @classmethod
    def get_bankaccount( cls, customer, row, i ):
        customer_id = customer.get( 'old-id' )
        customer_name = cls.get_customer_name( customer )
        if ( row['KONTO%d' % i] and row['KONTO%d' % i] != '0' ) or row['BLZ%d' % i] or row['BANK%d' % i]:
            if row['KONTO%d' % i] == 'SEPA':
                acc_iban = row['BANK%d' % i].replace( ' ', '' )
                acc_bic = row['BLZ%d' % i]
                acc_bankname = ''
                bank = Banks.get_by_bic( acc_bic )
                if not bank:
                    try:
                        iban.check_iban( acc_iban )
                    except iban.IBANError:
                        logger.warning( "Customer '%s' (%s) - Invalid IBAN: '%s' )", customer_id, customer_name, acc_iban )
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
                    logger.warning( "Customer '%s' (%s) - Could not convert to IBAN: ('%s', BC '%s' )", customer_id, customer_name, accountnumber, bankcode )
                    return
                else:
                    bank = Banks.get( 'DE', 'bankcode', bankcode )
                    if not bank:
                        return
                    acc_bic = bank.bic
                    acc_bankname = bank.name_short
            acc = etree.Element( "bankaccount" )
            acc.set( 'iban', acc_iban )
            acc.set( 'bic', acc_bic )
            acc.set( 'name', acc_bankname )
            return acc
    @staticmethod
    def get_address( customer_id, row ):
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

def parse_contract_file( filename ):
    contracts = {}
    subscription_name = ""
    with open( filename, 'r', encoding='iso-8859-1' ) as csvfile:
        csvreader = csv.reader( csvfile, delimiter=';' )
        additional_data = {}
        for row in csvreader:
            if not row[0]:
                continue
            if row[0] == 'Beitragsart:':
                subscription_name = row[2]
            else:
                try: int( row[0] )
                except: continue
            customer_id = row[1]
            startdate = dateutil.parser.parse( row[8], dayfirst=True ).isoformat()
            enddate = dateutil.parser.parse( row[9], dayfirst=True ).isoformat()
            value = str( locale.atof( row[10] ) ) if row[10] else ''
            contr = etree.Element( "contract" )
            contr.set( 'startdate', startdate )
            contr.set( 'enddate', enddate )
            contr.set( 'value', value )
            contr.set( 'old-subscription-name', subscription_name )
            additional_data[customer_id] = ( contracts, )
    return additional_data
import io
import locale
locale.setlocale( locale.LC_NUMERIC, 'de_DE' )
import dateutil.parser
def parse_contract_file2( filename ):
    def extract_section( sections, name ):
        try:
            i = sections.index( name )
        except ValueError: return
        else:
            return sections.pop( i + 1 )
    def parse_bookings( txt ):
        txt = strip_last_line( strip_first_line( txt ) )
        csvfile = io.StringIO( txt )
        fieldnames = ['date', None, 'year', 'month', 'description', None, 'debt', 'payment', 'cumulated']
        csvreader = csv.DictReader( csvfile, fieldnames=fieldnames, delimiter=';' )
        bookings = etree.Element( "bookings" )
        for row in csvreader:
            bk = etree.Element( "booking" )
            bk.set( 'date', row['date'] )
            bk.set( 'year', row['year'][:-3] )
            bk.set( 'month', row['month'][:-3] )
            bk.set( 'description', row['description'] )
            bk.set( 'debt', str( locale.atof( row['debt'] ) ) if row['debt'] else '' )
            bk.set( 'payment', str( locale.atof( row['payment'] ) ) if row['payment'] else '' )
            bk.set( 'cumulated', str( locale.atof( row['cumulated'] ) ) )
            bookings.append( bk )
        return bookings
    def parse_contracts( txt ):
        txt = strip_first_line( txt )
        csvfile = io.StringIO( txt )
        fieldnames = [None, 'contract-id', 'subscription-id', 'subscription-name', None, None, 'payment-frequency', 'value', None, 'startdate', 'enddate']
        csvreader = csv.DictReader( csvfile, fieldnames=fieldnames, delimiter=';' )
        contracts = etree.Element( "contracts" )
        for row in csvreader:
            contr = etree.Element( "contract" )
            contr.set( 'old-contract-id', row['contract-id'] )
            contr.set( 'old-subscription-id', row['subscription-id'][:-3] )
            contr.set( 'old-subscription-name', row['subscription-name'] )
            payment_frequency = row['payment-frequency'].strip()
            if payment_frequency == 'jährlich':
                contr.set( 'payment-frequency', 'annual' )
            else:
                raise ValueError( "Unknown Payment Frequency: '%s'" % payment_frequency )
            try:
                contr.set( 'value', str( locale.atof( row['value'] ) ) )
            except ValueError:
                logger.warning( "Invalid contract value: '%s'", row['value'] )
                contr.set( 'value', '' )
            contr.set( 'startdate', dateutil.parser.parse( row['startdate'], dayfirst=True ).isoformat() )
            if row['enddate'].strip():
                enddate = dateutil.parser.parse( row['enddate'], dayfirst=True ).isoformat()
            else:
                enddate = ""
            contr.set( 'enddate', enddate )
            contracts.append( contr )
        return contracts
    def strip_first_line( txt ):
        return "\n".join( txt.strip().split( '\n' )[1:] )
    def strip_last_line( txt ):
        return "\n".join( txt.strip().split( '\n' )[:-1] )
    with open( filename, 'r', encoding='iso-8859-1' ) as f:
        import re
        pattern_split = re.compile( '\n;[^;]+;;;;;;;;;\n;;;;;;;;Seite:;(?:\d+),00;\n;;;;Mitgliedskonto;;;;;;\n' )
        pattern_oldid = re.compile( '\n;Mitgl\.-Nr\.:;(?P<oldid>\d+);(?P<desc>(?:"[^"]+")|(?:[^;]+));;;;;;;\n' )
        pattern_sections = re.compile( '\n(?P<sec>(?:Verträge)|(?:Buchungen));;;;;;;;;;\n' )
        additional_data = {}
        for data in pattern_split.split( f.read() ):
            search_oldid = pattern_oldid.search( data )
            if not search_oldid:
                logger.warning( 'Couldnt match id, continuing...' )
                print( data )
                continue
            oldid = search_oldid.group( 'oldid' )
            desc = search_oldid.group( 'desc' )
            sections = pattern_sections.split( data )
            sec_contracts = extract_section( sections, 'Verträge' )
            sec_bookings = extract_section( sections, 'Buchungen' )
            contracts = parse_contracts( sec_contracts )
            bookings = parse_bookings( sec_bookings )
            additional_data[oldid] = [ contracts, bookings ]
            if desc:
                description = etree.Element( "description" )
                description.set( 'text', desc )
                additional_data[oldid].append( description )
        return additional_data
def parse_customer_file( filename, contract_data ):
    with open( filename, 'r', encoding='iso-8859-1' ) as csvfile:
        csvreader = csv.DictReader( csvfile, delimiter=';' )
        customers = etree.Element( 'customers' )
        for row in csvreader:
            customer = CustomerParser.parse( row, contract_data )
            customers.append( customer )
    return customers
def parse( customer_file, contract_file ):
    contract_data = parse_contract_file2( contract_file )
    customers = parse_customer_file( customer_file, contract_data )
    if contract_data:
        logger.warning( 'Some ophaned contract data left: %r', list( contract_data.keys() ) )
    return customers

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
    customers = parse( infile1, infile2 )
    output = etree.tostring( customers, pretty_print=True, xml_declaration=True, encoding='utf-8' )
    if outfile:
        f = open( outfile, 'wb' )
        f.write( output )
    else:
        # print( output.decode( 'utf-8' ) )
        pass

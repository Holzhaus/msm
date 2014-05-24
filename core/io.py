#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv, struct, tempfile, os, shutil, datetime, dateutil, locale, subprocess, re
from string import Template
csv.register_dialect( 'deutschepost', delimiter=';', quoting=csv.QUOTE_ALL, skipinitialspace=True, quotechar='"', doublequote=True )
csv.register_dialect( 'spardabank', delimiter='\t', quoting=csv.QUOTE_ALL, skipinitialspace=True, quotechar='"', doublequote=True )
csv.register_dialect( 'opengeodb', delimiter='    ', quoting=csv.QUOTE_NONE, skipinitialspace=False, quotechar='', doublequote=False )
# fieldnames = ['Firma1', 'Firma2', 'Abteilung', 'Anrede', 'Titel', 'ZUHAENDEN', 'GESCHLECHT', 'Vorname', 'Nachname', 'STRASSE', "HAUSNUMMER", "STRASSE-PLZ", "STRASSE-ORT", "POSTFACH", "POSTFACH-PLZ", "POSTFACH-ORT", "GROSSEMPFAENGER-PLZ", "GROSSEMPFAENGER-ORT", "LAND"]
class SubscriptionManagerIO:
    DEUTSCHEPOST_KEYMAP = [( 'Nachname', 'familyname', str, '' ),
                           ( 'Vorname', 'prename', str, '' ),
                           ( 'Anrede', 'honourific', str, '' ),
                           ( 'Titel', 'title', str, '' ),
                           ( 'Geschlecht', 'gender', int, 0 ),
                           ( 'Firma1', 'company1', str, '' ),
                           ( 'Firma2', 'company2', str, '' ),
                           ( 'Abteilung', 'department', str, '' ),
                           ( 'ZuHaenden', 'co', str, '' ),
                           ( 'Strasse', 'street', str, '' ),
                           ( 'PLZ', 'zipcode', str, '' ),
                           ( 'Ort', 'city', str, '' ),
                           ( 'Land', 'country', str, '' )]
    @staticmethod
    def csvexport( filename, data, fencoding='latin1' ):
        # fieldnames = ['Firma1', 'Firma2', 'Abteilung', 'Anrede', 'Titel', 'ZuHaenden', 'Geschlecht', 'Vorname', 'Nachname', 'Strasse', 'PLZ', 'Ort', 'Land', 'Briefanrede']
        fieldnames = [x[0] for x in SubscriptionManagerIO.DEUTSCHEPOST_KEYMAP ]
        with open( filename, 'w', newline='', encoding=fencoding ) as csvfile:
            writer = csv.DictWriter( csvfile, fieldnames, dialect='deutschepost', extrasaction='ignore' )
            writer.writeheader()
            i = 0
            for row in data:
                for ( newkey, oldkey, datatype, default ) in SubscriptionManagerIO.DEUTSCHEPOST_KEYMAP:
                    if oldkey in row:
                        row[newkey] = row.pop( oldkey )
                        if not row[newkey]:
                            row[newkey] = default
                writer.writerow( row )
                i += 1
        return i
    @staticmethod
    def csvimport( fname, fencoding='latin1' ):
        with open( fname, newline='', encoding=fencoding ) as f:
            reader = csv.DictReader( f, dialect='deutschepost' )
            reader.fieldnames = [field.strip().lower() for field in reader.fieldnames] # make keys lowercase
            customers = []
            for row in reader:
                customerdata = {}
                # Map fieldnames of Deutsche Post to ours
                for ( oldkey, newkey, datatype, default ) in SubscriptionManagerIO.DEUTSCHEPOST_KEYMAP:
                    oldkey = oldkey.lower()
                    if oldkey in row:
                        customerdata[newkey] = row.pop( oldkey )
                        if not isinstance( customerdata[newkey], datatype ):
                            try:
                                customerdata[newkey] = datatype( customerdata[newkey] )
                            except:
                                customerdata[newkey] = default
                        if not customerdata[newkey]:
                            customerdata[newkey] = default
                customers.append( customerdata )
            return customers
    @staticmethod
    def importXLS( filename ):
        return SpardaBankTransactionXLSImporter.readFile( filename )
class SpardaBankTransactionXLSImporter:
    @staticmethod
    def readFile( filename, fencoding='latin1' ):
        file_is_invalid = False
        pattern = re.compile( '\AKontoumsätze Girokonto\n\nKontoinhaber:\t"(?P<account_owner>.+)"\nKundennummer:\t"(?P<customer_number>\d+)"\n\nUmsätze ab\tEnddatum\tKontonummer\tSaldo\tWährung\n"(?P<startdate>\d{2}\.\d{2}\.\d{4})"\t"(?P<enddate>\d{2}\.\d{2}\.\d{4})"\t"(?P<account_number>\d+)"\t"(?P<saldo>[0-9\,.]+)"\t"EUR"\n\n\nBuchungstag\tWertstellungstag\tVerwendungszweck\tUmsatz\tWährung', re.MULTILINE )
        try:
            with open( filename, "r", encoding=fencoding ) as f:
                content = f.readlines()
                f.close()
            head = content[:10]
            foot = content[-1]
            body = content[10:-1]
            matchobj = pattern.match( ''.join( head ) )
            if not matchobj:
                raise ValueError()
        except OSError:
            print( "File doen't exist!" )
            return None
        except IndexError or ValueError or UnicodeDecodeError:
            print( "Invalid File!" )
            return None
        fieldnames = ["booking_date", "value_date", "reference", "value", "currency", "not_executed"]
        reader = csv.DictReader( body, fieldnames, dialect='spardabank' )
        transactions = []
        for row in reader:
            if row['not_executed'] == '*':
                continue
            if row['currency'] != 'EUR':
                print( 'Invalid currency!' )
                continue
            booking_date = dateutil.parser.parse( row['booking_date'] ).date()
            value_date = dateutil.parser.parse( row['value_date'] ).date()
            value = locale.atof( row['value'] )
            reference = row['reference']
            transactions.append( {'value':value, 'booking_date':booking_date, 'value_date':value_date, 'reference':reference} )
        return transactions

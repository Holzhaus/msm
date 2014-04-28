#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv, struct, tempfile, os, shutil, datetime, dateutil, locale, subprocess, re
from string import Template
csv.register_dialect( 'deutschepost', delimiter=';', quoting=csv.QUOTE_ALL, skipinitialspace=True, quotechar='"', doublequote=True )
csv.register_dialect( 'spardabank', delimiter='\t', quoting=csv.QUOTE_ALL, skipinitialspace=True, quotechar='"', doublequote=True )
csv.register_dialect( 'opengeodb', delimiter='	', quoting=csv.QUOTE_NONE, skipinitialspace=False, quotechar='', doublequote=False )
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
			reader.fieldnames = [field.strip().lower() for field in reader.fieldnames]  # make keys lowercase
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
	@staticmethod
	def export_dta( filename, transactions, accountowner, accountnumber, bankcode, bankname, reference="" ):
		pass
		""""from DTAUS import DTAUS
		dta = DTAUS( accountowner, accountnumber, bankcode, bankname, reference )
		i = 0
		for transaction_type, customer_id, name, accountnumber, bankcode, bankname, value, reference in transactions:
			dta.addTransaction( transaction_type, customer_id, name, accountnumber, bankcode, bankname, value, reference )
			i += 1
		f = open( filename, "w", encoding='latin1' )
		f.write( dta.getString() )
		f.close()
		return i"""
	@staticmethod
	def load_opengeodb_zipcodes( fname, fencoding='utf-8' ):
		with open( fname, newline='', encoding=fencoding ) as f:
			reader = csv.DictReader( f, dialect='opengeodb' )
			zipcodes = {}
			for row in reader:
				zipcodes[row['plz']] = row['Ort']
			return zipcodes
	@staticmethod
	def load_bundesbank_bankcodes( fname, fencoding='latin1' ):
		fieldwidths = ( 8, 1, 58 )
		fmtstring = ''.join( '%ds' % f for f in fieldwidths )
		parse = struct.Struct( fmtstring ).unpack_from
		with open( fname, mode='rb' ) as f:
			bankcodes = {}
			for line in f:
				bankcode, bankcode_sub, bankname = parse( line )
				bankcode = bankcode.decode( fencoding )
				bankname = bankname.decode( fencoding ).strip()
				if not bankcode in bankcodes:
					bankcodes[bankcode] = bankname
			return bankcodes
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

class PDFGenerator():
	templatepath = "/home/jan/Dokumente/SDAJ/Stelle/SDAJ/template"
	def __init__( self, templatename ):
		template_file = open( os.path.join( PDFGenerator.templatepath, '%s.template' % templatename ), 'r' )
		if not template_file:
			return
		self.template = Template( template_file.read() )
	def generatePDF( self, templatevars, output_file='/tmp/output.pdf', documentoptions='position', documentclass='scrlttr2' ):
		""""
		templatevars = {'recipient':'Max Mustermann',
				'signature':'Theodor Tester',
				'date':datetime.date.today().strftime( '%d.~%m~%Y' ),
				'subject':'Testbrief',
				'opening':'Sehr geehrter Herr Mustermann,',
				'text':'Dies ist ein ein einfaches Testbrief. Keine Angst.',
				'closing':'Mit freundlichen Grüßen,'}"""
		for key, value in templatevars.items():
			if '\n' in value:
				templatevars[key] = value.replace( '\n', '\\\\' )
		document = self.template.safe_substitute( templatevars )
		f = tempfile.NamedTemporaryFile( delete=False )
		f.write( bytes( document, 'UTF-8' ) )
		f.close()
		PDFGenerator.pdflatex( "\documentclass[%s]{%s}\input{%s}\endinput" % ( documentoptions, documentclass, f.name ), output_file )
		os.remove( f.name )
		del f
	@staticmethod
	def pdflatex( latex, output_file ):
		jobname = 'document'
		env = os.environ.copy()
		if not 'TEXINPUTS' in env:
			env['TEXINPUTS'] = ''
		env['TEXINPUTS'] = ':'.join( [os.path.join( PDFGenerator.templatepath, 'latex' ), env['TEXINPUTS']] )
		with tempfile.TemporaryDirectory() as tmpdirname:
			cmd = ['pdflatex',
			       '-halt-on-error',
			       '-interaction', 'nonstopmode',
			       '-jobname', jobname,
			       '-output-directory', tmpdirname,
			       latex]
			latex = subprocess.call( cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env )
			if latex != 0:
				raise Exception
			tmp_uri = os.path.join( tmpdirname, '%s.pdf' % jobname )
			shutil.copy( tmp_uri, output_file )
class LetterGenerator:
	def __init__( self, output_dir="/tmp/", date=datetime.date.today() ):
		self._generator = PDFGenerator( "letter" )
		self._output_dir = output_dir
		self._date = date
	def generateInvoice( self, contract, output_dir=None, date=None ):
		if output_dir == None:
			output_dir = self._output_dir
		if date == None:
			date = self._date
		filename = '%d-%s-%s-%s.pdf' % ( contract.customer.id, contract.customer.familyname, contract.customer.prename, date.strftime( "%Y-%m-%d" ) )
		output_file = os.path.join( output_dir, filename )
		documentoptions = 'position'
		documentclass = 'scrlttr2'
		templatevars = {'recipient': "%s\n%s\n%s %s" % ( contract.customer.name, contract.billingaddress.street, contract.billingaddress.zipcode, contract.billingaddress.city ),
				'signature':'POSITION\nAbo-Service',
				'date':date.strftime( '%d.~%m~%Y' ),
				'subject':'Rechnung',
				'opening':'Sehr geehrter Herr %s,' % contract.customer.familyname,
				'closing':'Mit freundlichen Grüßen,'}
		templatevars['text'] = 'Dies ist ein ein einfaches Testbrief. Keine Angst.'
		self._generator.generatePDF( templatevars, output_file, documentoptions, documentclass )
		return output_file

import struct
import csv
import os.path
import zipfile
import itertools
import io
from core.config import Config
csv.register_dialect( 'opengeodb', delimiter="\t", quoting=csv.QUOTE_NONE, skipinitialspace=False, quotechar='', doublequote=False )
csv.register_dialect( 'semicolonsep', delimiter=";", quoting=csv.QUOTE_MINIMAL, skipinitialspace=False, quotechar='"', doublequote=False )
class TaggedInfoStore:
    """
    An Object that stores objects and makes them accessible through their attributes. Should only be used through subclasses.
    """
    def __init__( self, keys ):
        """
        __init__ function.
        Arguments:
            keys:
                A list of attribute names that should be indexed
        """
        self._data = {}
        self._keys = keys
    def load( self, tag, fname, fencoding='utf-8' ):
        """
        Opens file and loads the data into the given tag.
        Arguments:
            tag:
                The tag the data will be stored in
            fname:
                The filename of the file that contains the data
            fencoding:
                The file encoding of the file
        """
        getattr( self, "load_{}".format( tag ) )( fname, fencoding )
    def clear( self, tag=None ):
        """
        Clears all data. If tag is given, only clears data for this tag.
        Arguments:
            tag:
                The tag to be cleared
        """
        if tag is None:
            for tag in self._data:
                self.clear_tag( tag )
        else:
            self.clear_tag( tag )
    def clear_tag( self, tag ):
        """
        Clears data for given tag.
        Arguments:
            tag:
                The tag to be cleared
        """
        if tag in self._data:
            for key in self._data[tag].keys():
                self._data[tag][key].clear()
    def add( self, tag, obj ):
        """
        Adds an Object to a tag.
        Arguments:
            obj:
                The object to be indexed
            tag:
                tag for this object
        """
        if tag not in self._data:
            self._data[tag] = {}
            for key in self._keys:
                self._data[tag][key] = {}
        for key in self._data[tag].keys():
            self._data[tag][key][getattr( obj, key )] = obj
    def get( self, tag, key, value ):
        """
        Gets an object from tag where key has a specific value.
        Arguments:
            tag:
                tag to search
            key:
                attribute name of object
            tag:
                attribute value of object
        Returns:
            object or None
        """
        if tag in self._data:
            if key in self._data[tag]:
                if value in self._data[tag][key]:
                    return self._data[tag][key][value]
class AbstractBankInfoStore( TaggedInfoStore ):
    def __init__( self ):
        keys = ( 'bic', 'bankcode' )
        TaggedInfoStore.__init__( self, keys )
    def get_by_iban( self, value ):
        iban = value.upper()
        countrycode = iban[:2]
        if countrycode in self.__class__.BANKCODE_FMT:
            bankcode_length = self.__class__.BANKCODE_FMT[countrycode]['length']
            bankcode = iban[4:( 4 + bankcode_length )]
        return self.get( countrycode, "bankcode", bankcode )
    def get_by_bic( self, value ):
        for tag in self._data.keys():
            obj = self.get( tag, 'bic', value )
            if obj:
                return obj
    def get( self, tag, key, value ):
        if key == 'bankcode' and tag in self.__class__.BANKCODE_FMT and self.__class__.BANKCODE_FMT[tag]['can_be_shorter']:
            value = value.lstrip( '0' )
        return super().get( tag, key, value )
class BankInfoStore( AbstractBankInfoStore ):
    BANKCODE_FMT = { 'DE': {'length': 8, 'can_be_shorter':False},
                     'AT': {'length': 5, 'can_be_shorter':False},
                     'CH': {'length': 5, 'can_be_shorter':True} }
    def load_DE( self, fname, fencoding='latin1' ):
        tag = 'DE'
        self.clear_tag( tag )
        fieldwidths = ( 8, # BLZ
                        1, # Merkmal
                       58, # Bezeichnung
                        5, # PLZ
                       35, # Ort
                       27, # Kurzbezeichnung
                        4, # PAN
                       11, # BIC
                        2, # Prüfzifferberechnungsmethode
                        6, # Datensatznummer
                        1, # Änderungskennzeichen
                        1, # Bankleitzahllöschung
                        8 ) # Nachfolge-BLZ
        fmtstring = ''.join( '%ds' % f for f in fieldwidths )
        parse = struct.Struct( fmtstring ).unpack_from
        with open( fname, mode='rb' ) as f:
            for line in f:
                data = parse( line )
                bankcode, bic, name, name_short = data[0].decode( fencoding ).strip(), data[7].decode( fencoding ).strip(), data[2].decode( fencoding ).strip(), data[5].decode( fencoding ).strip()
                if len( bankcode ) == 8 and len( bic ) == 11:
                    obj = BankInfo( bankcode, bic, name, name_short )
                    self.add( tag, obj )
    def load_AT( self, fname, fencoding='latin1' ):
        tag = 'AT'
        self.clear_tag( tag )
        with zipfile.ZipFile( fname, 'r' ) as archive:
            if len( archive.namelist() ) == 1 and archive.namelist()[0].startswith( 'SEPA-ZV-VZ_gesamt_de_' ):
                with archive.open( archive.namelist()[0], 'r' ) as encoded_f:
                    with io.TextIOWrapper( encoded_f, fencoding ) as f:
                        fieldnames = ( 'Kennzeichen',
                                       'Identnummer',
                                       'Bankleitzahl',
                                       'Institutsart',
                                       'Sektor',
                                       'Firmenbuchnummer',
                                       'Bankenname',
                                       'Straße',
                                       'PLZ',
                                       'Ort',
                                       'Politischer Bezirk',
                                       'Postadresse / Straße',
                                       'Postadresse / PLZ',
                                       'Postadresse / Ort',
                                       'Postfach',
                                       'Bundesland',
                                       'Telefon',
                                       'Fax',
                                       'E-Mail',
                                       'SWIFT-Code',
                                       'Homepage',
                                       'Gruendungsdatum',
                                       'ZweigniederlassungVon' )
                        reader = csv.DictReader( f, fieldnames, dialect='semicolonsep' )
                        for row in itertools.islice( reader, 6, None ):
                            bankcode, bic, name, name_short = row['Bankleitzahl'].strip().zfill( 5 ), row['SWIFT-Code'].strip(), row['Bankenname'].strip(), row['Bankenname'].strip()
                            if len( bankcode ) == 5 and len( bic ) == 11:
                                obj = BankInfo( bankcode, bic, name, name_short )
                                self.add( tag, obj )
    def load_CH( self, fname, fencoding='latin1' ):
        tag = 'CH'
        self.clear_tag( tag )
        fieldwidths = ( 2, # Gruppe
                        5, # BCNr
                        4, # Filial-ID
                        5, # BCNr neu
                        6, # SIC-Nr
                        5, # Hauptsitz (BCNr)
                        1, # BC-Art (1=Hauptsitz, 2=Kopfstelle, 3=Filiale)
                        8, # gültig ab
                        1, # SIC
                        1, # euroSIC
                        1, # Sprache
                       15, # Kurzbez.
                       60, # Bank/Institut
                       35, # Domizil
                       35, # Postadresse
                       10, # PLZ
                       35, # Ort
                       18, # Telefon
                       18, # Fax
                        5, # Vorwahl
                        2, # Landcode
                       12, # Postkonto
                       14 ) # SWIFT
        fmtstring = ''.join( '%ds' % f for f in fieldwidths )
        parse = struct.Struct( fmtstring ).unpack_from
        with open( fname, mode='rb' ) as f:
            for line in f:
                data = parse( line )
                bankcode, bic, name, name_short = data[1].decode( fencoding ).strip(), data[22].decode( fencoding ).strip(), data[12].decode( fencoding ).strip(), data[11].decode( fencoding ).strip()
                if bankcode and len( bic ) == 11:
                    obj = BankInfo( bankcode, bic, name, name_short )
                    self.add( tag, obj )
class BankInfo:
    def __init__( self, bankcode, bic, name, name_short ):
        self._bankcode = bankcode
        self._bic = bic
        self._name = name
        self._name_short = name_short
    @property
    def bankcode( self ):
        return self._bankcode
    @property
    def bic( self ):
        return self._bic
    @property
    def name( self ):
        return self._name
    @property
    def name_short( self ):
        return self._name_short

class CityInfoStore( TaggedInfoStore ):
    def __init__( self ):
        keys = ( 'zipcode', 'name' )
        TaggedInfoStore.__init__( self, keys )
    def load( self, tag, fname, fencoding='utf-8' ):
        self.clear_tag( tag )
        with open( fname, newline='', encoding=fencoding ) as f:
            reader = csv.DictReader( f, dialect='opengeodb' )
            for row in reader:
                try:
                    zipcode, lat, lon = row['plz'].strip(), float( row['lat'].strip() ), float( row['lon'].strip() )
                except ValueError:
                    continue
                name = row['Ort'].strip() if 'Ort' in row else row['name'].strip()
                if name and zipcode:
                    if "," in zipcode:
                        for zipcode_single in zipcode.split( "," ):
                            if zipcode_single:
                                obj = CityInfo( zipcode_single, name, lat, lon, tag )
                                self.add( tag, obj )
                    else:
                        obj = CityInfo( zipcode, name, lat, lon, tag )
                        self.add( tag, obj )
    def iso_zipcode_split( self, iso3661zipcode ):
        if len( iso3661zipcode ) > 3 and '-' in iso3661zipcode:
            countrycode, zipcode = iso3661zipcode.split( '-', 2 )
            if len( countrycode ) == 2:
                countrycode = countrycode.upper()
                return countrycode, zipcode
    def get_by_iso_zipcode( self, iso3661zipcode ):
        result = self.iso_zipcode_split( iso3661zipcode )
        if result:
            countrycode, zipcode = result
            return self.get( countrycode, 'zipcode', zipcode )
class CityInfo:
    def __init__( self, zipcode, name, lat, lon, country ):
        self._zipcode = zipcode
        self._name = name
        self._lat = lat
        self._lon = lon
        self._country = country
    @property
    def zipcode( self ):
        return self._zipcode
    @property
    def name( self ):
        return self._name
    @property
    def lat( self ):
        return self._lat
    @property
    def lon( self ):
        return self._lon
    @property
    def country( self ):
        return self._country

Banks = BankInfoStore()
Cities = CityInfoStore()
def reload_data():
    global Banks
    global Cities
    for option in Config.options( 'Autocompletion' ):
        if option.startswith( 'bic_file_' ) or option.startswith( 'zipcode_file_' ):
            filename = Config.getfilepath( 'Autocompletion', option )
            if os.path.exists( filename ):
                if option.startswith( 'bic_file_' ):
                    tag = option[9:].upper()
                    Banks.clear( tag )
                    Banks.load( tag, filename, 'latin1' )
                elif option.startswith( 'zipcode_file_' ):
                    tag = option[13:].upper()
                    Cities.clear( tag )
                    Cities.load( tag, filename, 'utf-8' )
reload_data()

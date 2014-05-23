import struct
import csv
import os.path
from core.config import Configuration
csv.register_dialect( 'opengeodb', delimiter="\t", quoting=csv.QUOTE_NONE, skipinitialspace=False, quotechar='', doublequote=False )
class AbstractInfoLoader:
    def __init__( self, keys ):
        self._filename = ''
        self._data = {}
        for key in keys:
            self._data[key] = {}
    def load( self, fname, fencoding='utf-8' ):
        raise NotImplementedError
    def clear( self ):
        for key in self._data.keys():
            self._data[key].clear()
    def add( self, obj ):
        for key in self._data.keys():
            self._data[key][getattr( obj, key )] = obj
    def get( self, key, value ):
        if key in self._data:
            if value in self._data[key]:
                return self._data[key][value]
class BankInfoLoader( AbstractInfoLoader ):
    def __init__( self ):
        keys = ( 'bic', 'bankcode' )
        AbstractInfoLoader.__init__( self, keys )
    def load( self, fname, fencoding='latin1' ):
        self.clear()
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
                    self.add( obj )
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

class CityInfoLoader( AbstractInfoLoader ):
    def __init__( self ):
        keys = ( 'zipcode', 'name' )
        AbstractInfoLoader.__init__( self, keys )
    def load( self, fname, fencoding='utf-8' ):
        self.clear()
        with open( fname, newline='', encoding=fencoding ) as f:
            reader = csv.DictReader( f, dialect='opengeodb' )
            for row in reader:
                zipcode, name, lat, lon = row['plz'], row['Ort'], float( row['lat'] ), float( row['lon'] )
                obj = CityInfo( zipcode, name, lat, lon )
                self.add( obj )
class CityInfo:
    def __init__( self, zipcode, name, lat, lon ):
        self._zipcode = zipcode
        self._name = name
        self._lat = lat
        self._lon = lon
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

Banks = BankInfoLoader()
Cities = CityInfoLoader()
def reload_data():
    global Banks
    global Cities
    bic_file = Configuration().get( 'Autocompletion', 'bic_file' )
    Banks.clear()
    if os.path.exists( bic_file ):
        Banks.load( bic_file, 'latin1' )
    zipcode_file = Configuration().get( 'Autocompletion', 'zipcode_file' )
    Cities.clear()
    if os.path.exists( zipcode_file ):
        Cities.load( zipcode_file, 'utf-8' )
reload_data()

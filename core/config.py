'''
Created on 28.03.2014

@author: jan
'''
import configparser
import platform
import os

CONFIG_DIRNAME = "PositionsManager"
CONFIG_FILENAME = "manager.cfg"
CONFIG_APPDIR = os.path.join( os.path.dirname( __file__ ), os.pardir )

class Configuration( object ):
    def __init__( self ):
        self.defaults = configparser.ConfigParser()
        defaults_file = self._mkabsfilepath( os.path.join( 'data', 'default.cfg' ) )
        self.defaults.read_file( open( defaults_file, encoding='utf8' ) )
        self.cp = configparser.ConfigParser()
        self.cp.read( [self.config_filename], encoding='utf8' )
    @property
    def config_path( self ):
        if platform.system() == 'Windows':
            config_path = os.path.join( os.environ['APPDATA'], CONFIG_DIRNAME )
        else:
            config_path = os.path.expanduser( '~/.%s' % CONFIG_DIRNAME )
        return os.path.abspath( config_path )
    @property
    def config_filename( self ):
        return os.path.join( self.config_path, CONFIG_FILENAME )
    def _mkabsfilepath( self, filepath ):
        if not os.path.isabs( filepath ):
            filepath = os.path.abspath( os.path.join( CONFIG_APPDIR, filepath ) )
        return filepath
    def options( self, section ):
        return set( self.cp.options( section ) ).union( set( self.defaults.options( section ) ) )
    def get( self, section, option ):
        return self.cp.get( section, option, fallback=self.defaults.get( section, option ) )
    def getboolean( self, section, option ):
        return self.cp.getboolean( section, option, fallback=self.defaults.getboolean( section, option ) )
    def getfilepath( self, section, option ):
        filepath = self.get( section, option )
        return self._mkabsfilepath( filepath )
    def set( self, section, option, value ):
        if not isinstance( value, str ):
            if isinstance( value, bool ):
                if value:
                    value = "yes"
                else:
                    value = "no"
            else:
                raise ValueError( "Unsupported Datatype" )
        if not self.cp.has_section( section ):
            self.cp.add_section( section )
        self.cp.set( section, option, value )
        self.save()
    def save( self ):
        f = open( self.config_filename, "w" )
        if f:
            self.cp.write( f )
            f.close()
Config = Configuration()
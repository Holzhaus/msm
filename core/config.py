'''
Created on 28.03.2014

@author: jan
'''
import configparser
import platform
import os

CONFIG_DIRNAME = "PositionsManager"
CONFIG_FILENAME = "manager.cfg"

class Configuration( object ):
    def __init__( self ):
        self.defaults = configparser.ConfigParser()
        self.defaults.read_file( open( 'data/default.cfg', encoding='utf8' ) )
        self.cp = configparser.ConfigParser()
        self.cp.read( [self.get_config_filename()], encoding='utf8' )
    def get_config_path( self ):
        if platform.system() == 'Windows':
            return os.path.join( os.environ['APPDATA'], CONFIG_DIRNAME )
        else:
            return os.path.expanduser( '~/.%s' % CONFIG_DIRNAME )
    def options( self, section ):
        return set( self.cp.options( section ) ).union( set( self.defaults.options( section ) ) )
    def get_config_filename( self ):
        return os.path.join( self.get_config_path(), CONFIG_FILENAME )
    def get( self, section, option ):
        return self.cp.get( section, option, fallback=self.defaults.get( section, option ) )
    def getboolean( self, section, option ):
        return self.cp.getboolean( section, option, fallback=self.defaults.getboolean( section, option ) )
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
        f = open( self.get_config_filename(), "w" )
        if f:
            self.cp.write( f )
            f.close()

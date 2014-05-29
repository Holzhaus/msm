#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
logger = logging.getLogger( __name__ )
import configparser
import platform
import os
import shutil
import string

CONFIG_DIRNAME = "msm"
CONFIG_FILENAME = "msm.cfg"
CONFIG_APPDIR = os.path.abspath( os.path.join( os.path.dirname( __file__ ), os.pardir ) )

class Configuration( object ):
    def __init__( self ):
        if not os.path.exists( self.config_filename ):
            logger.info( "config file '%s' does not exist, creating...", self.config_filename )
            shutil.copyfile( self.defaults_filename, self.config_filename )
        self.defaults = configparser.ConfigParser()
        self.defaults.read_file( open( self.defaults_filename, encoding='utf8' ) )
        self.cp = configparser.ConfigParser()
        self.cp.read_file( open( self.config_filename, encoding='utf8' ) )
    @property
    def config_path( self ):
        if platform.system() == 'Windows':
            config_path = os.path.join( os.environ['APPDATA'], CONFIG_DIRNAME )
        else:
            config_path = os.path.expanduser( '~/.%s' % CONFIG_DIRNAME )
        if not os.path.exists( config_path ):
            logger.info( "config dir '%s' does not exist, creating...", config_path )
            os.mkdir( config_path, mode=0o700 )
        return os.path.abspath( config_path )
    @property
    def config_filename( self ):
        return os.path.join( self.config_path, CONFIG_FILENAME )
    @property
    def defaults_filename( self ):
        if platform.system() == 'Windows':
            defaults_filename = self._mkabsfilepath( os.path.join( 'data', 'default_win.cfg' ) )
        else:
            defaults_filename = self._mkabsfilepath( os.path.join( 'data', 'default.cfg' ) )
        return defaults_filename
    def _mkabsfilepath( self, filepath ):
        if not os.path.isabs( filepath ):
            filepath = os.path.abspath( os.path.join( CONFIG_APPDIR, filepath ) )
        return filepath
    def options( self, section ):
        return set( self.cp.options( section ) ).union( set( self.defaults.options( section ) ) )
    def get( self, section, option ):
        value = self.cp.get( section, option, fallback=self.defaults.get( section, option ) )
        value = string.Template( value ).safe_substitute( CONFIGDIR=self.config_path, APPDIR=CONFIG_APPDIR )
        return value
    def getboolean( self, section, option ):
        return self.cp.getboolean( section, option, fallback=self.defaults.getboolean( section, option ) )
    def getfilepath( self, section, option ):
        filepath = self.get( section, option )
        return self._mkabsfilepath( filepath )
    def set( self, section, option, value ):
        if isinstance( value, str ):
            value = value.replace( CONFIG_APPDIR, '${APPDIR}' ).replace( self.config_path, '${CONFIGDIR}' )
        elif isinstance( value, bool ):
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

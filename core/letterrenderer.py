#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import tempfile
import re
import locale
import jinja2
import abc
import core.database
from core.lib import pdflatex
from core.lib import threadqueue
if sys.platform.startswith( 'linux' ):
    from gi.repository import Gio # We need this as xdg-open replacement (see below)
LATEX_SUBS = ( ( re.compile( r'\\' ), r'\\textbackslash' ),
              ( re.compile( r'([{}_#%&$])' ), r'\\\1' ),
              ( re.compile( r'~' ), r'\~{}' ),
              ( re.compile( r'\^' ), r'\^{}' ),
              ( re.compile( r'"' ), r"''" ),
              ( re.compile( r'\.\.\.+' ), r'\\ldots' ),
              ( re.compile( r'€' ), r'\\euro\{\}' ) )
NEWLINE_SUB = ( re.compile( r'\n' ), r'{\\newline}' )
def _escape_tex( value ):
    newval = value
    for pattern, replacement in LATEX_SUBS:
        newval = pattern.sub( replacement, newval )
        return newval
def _escape_nl( value ):
    pattern, replacement = NEWLINE_SUB
    newval = pattern.sub( replacement, value )
    return newval
template_env = jinja2.Environment( loader=jinja2.FileSystemLoader( 'data/templates' ) )
template_env.block_start_string = '((*'
template_env.block_end_string = '*))'
template_env.variable_start_string = '((('
template_env.variable_end_string = ')))'
template_env.comment_start_string = '((='
template_env.comment_end_string = '=))'
template_env.filters['escape_tex'] = _escape_tex
template_env.filters['escape_nl'] = _escape_nl

class PrerenderThread( threadqueue.AbstractQueueThread ):
    def run( self ):
        self._session = core.database.Database.get_scoped_session()
        super().run()
        self._session.expunge_all() # expunge everything afterwards
        self._session.remove()
    def work( self, letter ):
        letter = self._session.merge( letter )
        return '\n'.join( list( self._prerender( letter ) ) )
    def _prerender( self, letter ):
        """ Generator function that prerenders a whole letter (yields it part by part). """
        templatevars = {'closing':'Mit freundlichen Grüßen',
                        'signature':'POSITION\nAbo-Service',
                        'recipient':"%s\n%s\n%s %s" % ( letter.contract.customer.name, letter.contract.billingaddress.street, letter.contract.billingaddress.zipcode, letter.contract.billingaddress.city ),
                        'opening':letter.contract.customer.letter_salutation,
                        'date':letter.date.strftime( '%d.~%m~%Y' ),
                        'customer': letter.contract.customer,
                        'contract': letter.contract}
        for part in letter.contents:
            prerendered_part = self._prerender_part( templatevars, part )
            if prerendered_part:
                yield prerendered_part
    def _prerender_part( self, templatevars, part ):
        """ function that prerenders a letter part. """
        if isinstance( part, core.database.Invoice ):
            rendered_text = self._prerender_invoice( templatevars, part )
        elif isinstance( part, core.database.Note ):
            rendered_text = self._prerender_note( templatevars, part )
        else:
            raise TypeError( "Unknown letter part type" )
        return rendered_text
    # Rendering functions for the different parts
    def _prerender_invoice( self, generic_templatevars, invoice ):
        invoice_no = "%s-%s" % ( invoice.contract.refid, invoice.number )
        templatevars = generic_templatevars.copy()
        templatevars.update( { 'invoice_no': invoice_no,
                               'subject':'Rechnung Nr. %s' % invoice_no,
                               'subscription_name':invoice.contract.subscription.name,
                               'magazine_name':invoice.contract.subscription.magazine.name,
                               'total':locale.currency( invoice.value_left ),
                               'maturity_date': invoice.maturity_date.strftime( locale.nl_langinfo( locale.D_FMT ) )
                             } )
        entries = []
        for i, entry in enumerate( invoice.entries ):
            entries.append( {'position':str( i + 1 ),
                            'value':locale.currency( entry.value ),
                            'description':entry.description} )
        templatevars['entries'] = entries
        template = template_env.get_template( "{}.template".format( "invoice" ) )
        return template.render( templatevars )
    def _prerender_note( self, generic_templatevars, note ):
        templatevars = generic_templatevars.copy()
        templatevars.update( {'subject': note.subject,
                              'text': template_env.from_string( note.text ).render( templatevars ) } )
        template = template_env.get_template( "{}.template".format( "note" ) )
        return template.render( templatevars )
class PrerenderQueue( threadqueue.AbstractQueue ):
    def _create_thread( self ):
        return PrerenderThread()
from msmgui.widgets.base import ScopedDatabaseObject
class PrerenderWatcher( threadqueue.QueueWatcherThread, ScopedDatabaseObject ):
    """
    Usage:
        watcher = PrerenderWatcher(letters)
        watcher.start()
        watcher.join()
    """
    def __init__( self, unmerged_letters ):
        ScopedDatabaseObject.__init__( self )
        letters = []
        for unmerged_letter in unmerged_letters:
            letter = self._session.merge( unmerged_letter )
            letters.append( letter )
        self._session.expunge_all()
        self._session.remove()
        queue = PrerenderQueue()
        queue.put_multiple( letters )
        super().__init__( queue )
class ComposeAndPrerenderThread( PrerenderThread ):
    def __init__( self, lettercomposition ):
        self._lettercomposition = lettercomposition
        super().__init__()
    def work( self, unmerged_contract ):
        contract = self._session.merge( unmerged_contract ) # add them to the local session
        letter = self._lettercomposition.compose( contract )
        if letter.has_contents():
            return super().work( letter )
class ComposeAndPrerenderQueue( threadqueue.AbstractQueue ):
    def __init__( self, lettercomposition ):
        self._lettercomposition = lettercomposition
        super().__init__()
    def _create_thread( self ):
        return ComposeAndPrerenderThread( self._lettercomposition )
class AbstractRenderer( threadqueue.QueueWatcherThread ):
    __metaclass__ = abc.ABCMeta
    def on_finished( self, rendered_letters ):
        template = template_env.get_template( "{}.template".format( "base" ) )
        if len( rendered_letters ) == 0:
            raise ValueError( "No rendered letters" )
        rendered_document = template.render( {'prerendered_letters':rendered_letters} )
        datadir = os.path.normpath( os.path.join( os.path.dirname( __file__ ), os.pardir, 'data' ) )
        latexdir = os.path.join( datadir, 'templates', 'latex' )
        imagedir = os.path.join( datadir, 'images' )
        pdflatex.compile_str( rendered_document, self._output_file, [latexdir, imagedir] )
class LetterRenderer( AbstractRenderer ):
    def __init__( self, output_file, letters ):
        queue = PrerenderQueue()
        queue.put_multiple( letters )
        super().__init__( queue )
        self._output_file = output_file
class ComposingRenderer( AbstractRenderer ):
    def __init__( self, output_file, lettercomposition, contracts ):
        queue = ComposeAndPrerenderQueue( lettercomposition )
        queue.put_multiple( contracts )
        super().__init__( queue )
        self._output_file = output_file
class LetterPreviewRenderer( LetterRenderer ):
    """
    Usage:
        watcher = LetterPreviewRenderer(letter)
        watcher.start()
        watcher.join() # if needed
    """
    def __init__( self, letter ):
        # Make a named tempfile, close it, and get the filename
        tmp_file = tempfile.NamedTemporaryFile( suffix=os.extsep + "pdf", delete=False )
        tmp_filepath = tmp_file.name
        tmp_file.close()
        super().__init__( tmp_filepath, [letter] )
    @staticmethod
    def show_viewer( filepath, delete_file_after=False ):
        """
        Opens the file specified by filepath in the default viewing application,
        waits for the app to exit and deletes the file afterwards if
        delete_file_after was set to True.
        """
        if not filepath or not os.path.exists( filepath ):
            raise IOError( "File does not exist" )
        FNULL = open( os.devnull, "wb" )
        if sys.platform.startswith( 'darwin' ):
            subprocess.call( ["open", "-W", filepath], stdout=FNULL, stderr=FNULL )
        elif sys.platform.startswith( 'linux' ):
            # FIXME: On Linux, we need to use gi.repository.Gio, because I don't want parse all that fucking XDG info, just because it doesn't have a WAIT option
            mime_type, must_support_uris = Gio.content_type_guess( filepath )
            app_info = Gio.AppInfo.get_default_for_type( mime_type, must_support_uris )
            if app_info:
                opener = app_info.get_executable()
                subprocess.call( [opener, filepath], stdout=FNULL, stderr=FNULL, shell=False )
            else:
                print( "Can't find app that can open '{}' files".format( mime_type ) )
        elif sys.platform.startswith( 'win32' ):
            # can't use os.startfile here, because maybe we need to remove the tempfile afterwards
            subprocess.call( ["start", "/WAIT", filepath], stdout=FNULL, stderr=FNULL, shell=True )
        if delete_file_after:
            os.remove( filepath )
    def on_finished( self, rendered_letters ):
        super().on_finished( rendered_letters )
        self.__class__.show_viewer( self._output_file, delete_file_after=False )

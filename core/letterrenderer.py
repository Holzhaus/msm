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
import threading
import core.database
from core.lib import pdflatex
from core.lib import threadqueue
from msmgui.widgets.base import ScopedDatabaseObject
from core import lettercomposition
if sys.platform.startswith( 'linux' ):
    from gi.repository import Gio # We need this as xdg-open replacement (see below)
class LatexEnvironment( jinja2.Environment ):
    LATEX_SUBS = ( ( re.compile( r'\\' ), r'\\textbackslash' ),
                   ( re.compile( r'([{}_#%&$])' ), r'\\\1' ),
                   ( re.compile( r'~' ), r'\~{}' ),
                   ( re.compile( r'\^' ), r'\^{}' ),
                   ( re.compile( r'"' ), r"''" ),
                   ( re.compile( r'\.\.\.+' ), r'\\ldots' ) )
    NEWLINE_SUB = ( re.compile( r'\n' ), r'{\\newline}' )
    def escape_tex( self, value ):
        newval = value
        for pattern, replacement in self.__class__.LATEX_SUBS:
            newval = pattern.sub( replacement, newval )
        return newval
    def escape_nl( self, value ):
        pattern, replacement = self.__class__.NEWLINE_SUB
        newval = pattern.sub( replacement, value )
        return newval
    def __init__( self, template_path ):
        super().__init__( loader=jinja2.FileSystemLoader( template_path ) )
        self.block_start_string = '((*'
        self.block_end_string = '*))'
        self.variable_start_string = '((('
        self.variable_end_string = ')))'
        self.comment_start_string = '((='
        self.comment_end_string = '=))'
        self.filters['escape_tex'] = self.escape_tex
        self.filters['escape_nl'] = self.escape_nl
env_latex = LatexEnvironment( 'data/templates' )

class AbstractRendererQueue( threadqueue.AbstractQueue ):
    __metaclass__ = abc.ABCMeta
    def __init__( self, template_env, num_worker_threads=None ):
        self._template_env = template_env
        super().__init__( num_worker_threads )
    @abc.abstractmethod
    def _create_thread( self ):
        super()._create_thread( self )
class PrerenderThread( threadqueue.AbstractQueueThread, ScopedDatabaseObject ):
    def __init__( self, template_env ):
        threadqueue.AbstractQueueThread.__init__( self )
        ScopedDatabaseObject.__init__( self )
        self._template_env = template_env
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
        template = self._template_env.get_template( "{}.template".format( "invoice" ) )
        return template.render( templatevars )
    def _prerender_note( self, generic_templatevars, note ):
        templatevars = generic_templatevars.copy()
        template = self._template_env.get_template( os.path.join( "notes", "{}.template".format( note.template ) ) )
        return template.render( templatevars )
class PrerenderQueue( AbstractRendererQueue ):
    def _create_thread( self ):
        return PrerenderThread( self._template_env )
class Prerenderer( threadqueue.QueueWatcherThread, ScopedDatabaseObject ):
    """
    Usage:
        watcher = Prerenderer(letters)
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
class ComposeThread( threadqueue.AbstractQueueThread, ScopedDatabaseObject ):
    def __init__( self, lettercomposition ):
        threadqueue.AbstractQueueThread.__init__( self )
        ScopedDatabaseObject.__init__( self )
        self._lettercomposition = lettercomposition
    def work( self, unmerged_contract ):
        contract = self._session.merge( unmerged_contract ) # add them to the local session
        lettercomp = self._lettercomposition.merge( self._session )
        letter = lettercomp.compose( contract )
        self._session.expunge_all()
        self._session.remove()
        return letter
class ComposeQueue( threadqueue.AbstractQueue ):
    def __init__( self, lettercomposition ):
        self._lettercomposition = lettercomposition
        super().__init__()
    def _create_thread( self ):
        return ComposeThread( self._lettercomposition )
class Composer( threadqueue.QueueWatcherThread ):
    def __init__( self, lettercomposition, contracts ):
        queue = ComposeQueue( lettercomposition )
        queue.put_multiple( contracts )
        super().__init__( queue )
class AbstractRenderer( threadqueue.QueueWatcherThread ):
    __metaclass__ = abc.ABCMeta
    def _get_template_env( self, template_env ):
        return template_env if template_env is not None else env_latex
    def __init__( self, q, template_env=None ):
        self._template_env = self._get_template_env( template_env )
        super().__init__( q )
    def on_finished( self, rendering_results ):
        template = self._template_env.get_template( "{}.template".format( "base" ) )
        rendered_letters = [rendered_letter for rendered_letter in rendering_results if rendered_letter is not None]
        if len( rendered_letters ) == 0:
            raise ValueError( "No rendered letters" )
        rendered_document = template.render( {'prerendered_letters':rendered_letters} )
        datadir = os.path.normpath( os.path.join( os.path.dirname( __file__ ), os.pardir, 'data' ) )
        latexdir = os.path.join( datadir, 'templates', 'latex' )
        imagedir = os.path.join( datadir, 'images' )
        pdflatex.compile_str( rendered_document, self._output_file, [latexdir, imagedir] )
class LetterRenderer( AbstractRenderer ):
    def __init__( self, letters, output_file, _template_env=None ):
        template_env = self._get_template_env( _template_env )
        queue = PrerenderQueue( template_env )
        queue.put_multiple( letters )
        super().__init__( queue, template_env )
        self._output_file = output_file
class ComposingRenderer( threading.Thread, ScopedDatabaseObject ):
    class SubComposer( Composer ):
        def __init__( self, parent, lettercomposition, contracts ):
            super().__init__( lettercomposition, contracts )
            self._parent = parent
        def on_start( self, work_left ):
            self._parent.on_composing_start( work_left )
            super().on_start( work_left )
        def on_output( self, work_left, output ):
            self._parent.on_composing_output( self.work_done, self.work_started )
            super().on_output( work_left, output )
        def on_finished( self, output_list ):
            letters = [letter for letter in output_list if letter is not None and letter.has_contents()]
            self._parent.on_composing_finished( len( letters ) )
            self._parent._save( letters )
    class SubLetterRenderer( LetterRenderer ):
        def __init__( self, parent, letters, output_file, template_env=None ):
            super().__init__( letters, output_file, template_env )
            self._parent = parent
        def on_start( self, work_left ):
            self._parent.on_rendering_start( self.work_started )
            super().on_start( work_left )
        def on_output( self, work_left, output ):
            self._parent.on_rendering_output( self.work_done, self.work_started )
            super().on_output( work_left, output )
        def on_finished( self, output_list ):
            self._parent.on_rendering_finished( self.work_done )
            self._parent.on_compilation_start( self.work_done )
            super().on_finished( output_list )
            self._parent.on_compilation_finished( self.work_done )
    def __init__( self, lettercomposition, contracts, output_file, template_env=None ):
        threading.Thread.__init__( self )
        ScopedDatabaseObject.__init__( self )
        self._lettercomposition = lettercomposition
        self._contracts = contracts
        self._output_file = output_file
        self._template_env = template_env
        self._composer = self.__class__.SubComposer( self, self._lettercomposition, self._contracts )
        self._letterrenderer = None
    def run( self ):
        self._composer.start()
        self._composer.join()
    def _save( self, letters ):
        num_letters = len( letters )
        self.on_saving_start( num_letters )
        merged_letters = []
        lettercomposition = self._lettercomposition.merge( self._session )
        lettercollection = core.database.LetterCollection( description=lettercomposition.get_description() )
        self._session.add( lettercollection )
        for unmerged_letter in letters:
            merged_letter = self.session.merge( unmerged_letter )
            lettercollection.add_letter( merged_letter )
            merged_letters.append( merged_letter )
        # Save merged Letters
        self._session.commit()
        self._session.remove()
        self.on_saving_finished( num_letters )
        self._render( letters )
    def _render( self, letters ):
        self._letterrenderer = self.__class__.SubLetterRenderer( self, letters, self._output_file )
        self._letterrenderer.start()
        self._letterrenderer.join()
    def on_composing_start( self, work_started ):
        """
        Called when rendering starts
        """
        pass
    def on_composing_output( self, work_done, work_started ):
        """
        Called when composing produces output
        """
        pass
    def on_composing_finished( self, num_letters ):
        """
        Called when composing done
        """
        pass
    def on_saving_start( self, num_letters_to_save ):
        """
        Called when saving starts
        """
        pass
    def on_saving_finished( self, num_letters_saved ):
        """
        Called when saving has finished
        """
        pass
    def on_rendering_start( self, work_started ):
        """
        Called when rendering start
        """
    def on_rendering_output( self, work_done, work_started ):
        """
        Called when rendering produces output
        """
        pass
    def on_rendering_finished( self, work_done ):
        """
        Called when rendering has finished
        """
        pass
    def on_compilation_finished( self, work_done ):
        """
        Called when rendering has finished
        """
        pass
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
        super().__init__( [letter], tmp_filepath )
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
            # FIXME: On Linux, we need to use gi.repository.Gio, because I don't want to parse all that fucking XDG info, just coz it doesn't have a WAIT option
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
        self.__class__.show_viewer( self._output_file, delete_file_after=True )

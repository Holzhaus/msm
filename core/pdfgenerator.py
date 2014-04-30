#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import shutil
import tempfile
import subprocess
import re
import jinja2
import locale
import core.database
import threading
import datetime
from PyPDF2 import PdfFileMerger, PdfFileReader
if sys.platform.startswith( 'linux' ):
    from gi.repository import Gio # We need this as xdg-open replacement (see below)
LATEX_SUBS = ( ( re.compile( r'\\' ), r'\\textbackslash' ),
              ( re.compile( r'([{}_#%&$])' ), r'\\\1' ),
              ( re.compile( r'~' ), r'\~{}' ),
              ( re.compile( r'\^' ), r'\^{}' ),
              ( re.compile( r'"' ), r"''" ),
              ( re.compile( r'\.\.\.+' ), r'\\ldots' ),
              ( re.compile( r'€' ), r'\\euro\{\}' ) )
NEWLINE_SUB = ( re.compile( r'\n' ), r'\\\\' )
def escape_tex( value ):
    newval = value
    for pattern, replacement in LATEX_SUBS:
        newval = pattern.sub( replacement, newval )
        return newval
def escape_nl( value ):
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
template_env.filters['escape_tex'] = escape_tex
template_env.filters['escape_nl'] = escape_nl
class PdfGenerator():
    @staticmethod
    def latexstr_to_pdf( latexstr, output_file='/tmp/output.pdf' ):
        f = tempfile.NamedTemporaryFile( delete=False )
        f.write( bytes( latexstr, 'UTF-8' ) )
        f.close()
        PdfGenerator.pdflatex( f.name , output_file )
        os.remove( f.name )
    @staticmethod
    def pdflatex( latexfile, output_file ):
        jobname = 'document'
        env = os.environ.copy()
        if not 'TEXINPUTS' in env:
            env['TEXINPUTS'] = ''
        env['TEXINPUTS'] = ':'.join( [os.path.abspath( 'data/templates/latex' ), env['TEXINPUTS']] )
        with tempfile.TemporaryDirectory() as tmpdirname:
            cmd = ['pdflatex',
                   '-halt-on-error',
                   '-interaction', 'nonstopmode',
                   '-jobname', jobname,
                   '-output-directory', tmpdirname,
                   latexfile]
            print( tmpdirname )
            latex = subprocess.call( cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
            if latex != 0:
                raise Exception
            tmp_uri = os.path.join( tmpdirname, '%s.pdf' % jobname )
            shutil.copy( tmp_uri, output_file )
class Note:
    def __init__( self, customer, address, subject, text, date=datetime.date.today() ):
        self.customer = customer
        self.address = address
        self.subject = subject
        self.date = date
class Letter:
    def __init__( self, contents=None ):
        if not contents:
            contents = []
        else:
            contents = contents.copy()
        self.contents = contents
    def save( self, output_filename ):
        f = open( output_filename, "wb" )
        self.render( f )
    def render( self, handle ):
        LetterRenderer.render( self, handle )
    def preview( self ):
        LetterRenderer.preview( self )
class LetterRenderer:
    @staticmethod
    def preview( letter ):
        """
        Runs the default PDF viewer in a subprocess.Popen, and then calls the function
        preview on exit when the subprocess completes.
        """
        tmp_file = tempfile.NamedTemporaryFile( suffix=os.extsep + "pdf", delete=False )
        letter.render( tmp_file )
        filepath = tmp_file.name
        tmp_file.close()
        thread = threading.Thread( target=LetterRenderer.show_viewer, args=( filepath, ), kwargs={'delete_file_after': True} )
        thread.start()
        # returns immediately after the thread starts
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
        shell = False
        if sys.platform.startswith( 'darwin' ):
            proc = subprocess.call( ["open", "-W", filepath], stdout=FNULL, stderr=FNULL )
        elif sys.platform.startswith( 'linux' ):
            # FIXME: On Linux, we need to use gi.repository.Gio, because I don't want parse all that fucking XDG info, just because it doesn't have a WAIT option
            mime_type, must_support_uris = Gio.content_type_guess( filepath )
            app_info = Gio.AppInfo.get_default_for_type( mime_type, must_support_uris )
            if app_info:
                opener = app_info.get_executable()
                proc = subprocess.call( [opener, filepath], stdout=FNULL, stderr=FNULL, shell=False )
            else:
                print( "Can't find app that can open '{}' files".format( mime_type ) )
        elif sys.platform.startswith( 'win32' ):
            # can't use os.startfile here, because maybe we need to remove the tempfile afterwards
            proc = subprocess.call( ["start", "/WAIT", filepath], stdout=FNULL, stderr=FNULL, shell=True )
        if delete_file_after:
            os.remove( filepath )
    @staticmethod
    def render( letter, handle ):
        with tempfile.TemporaryDirectory() as tmp_dir:
            merger = PdfFileMerger()
            for obj in letter.contents:
                tmp_file = tempfile.NamedTemporaryFile( suffix=os.extsep + "pdf", dir=tmp_dir, delete=False )
                tmp_filename = tmp_file.name
                tmp_file.close()
                LetterRenderer._render_part( obj, tmp_filename )
                merger.append( PdfFileReader( open( tmp_filename, 'rb' ) ) )
                os.remove( tmp_filename )
            merger.write( handle )
    @staticmethod
    def _render_part( obj, output_file ):
        if isinstance( obj, core.database.Invoice ):
            return LetterRenderer._render_invoice( obj, output_file )
    @staticmethod
    def _render_invoice( invoice, output_file ):
        invoice_no = "%s-%s" % ( invoice.contract.refid, invoice.number )
        templatevars = {'recipient': "%s\n%s\n%s %s" % ( invoice.contract.customer.name, invoice.contract.billingaddress.street, invoice.contract.billingaddress.zipcode, invoice.contract.billingaddress.city ),
                        'signature':'POSITION\nAbo-Service',
                        'opening':'Sehr geehrter Herr %s,' % invoice.contract.customer.familyname,
                        'closing':'Mit freundlichen Grüßen,',
                        'date':invoice.date.strftime( '%d.~%m~%Y' ),
                        'invoice_no': invoice_no,
                        'subject':'Rechnung Nr. %s' % invoice_no,
                        'subscription_name':invoice.contract.subscription.name,
                        'magazine_name':invoice.contract.subscription.magazine.name,
                        'total':locale.currency( invoice.value_left )}
        entries = []
        for i, entry in enumerate( invoice.entries ):
            entries.append( {'position':str( i + 1 ),
                            'value':locale.currency( entry.value ),
                            'description':entry.description} )
        templatevars['entries'] = entries
        template = template_env.get_template( "{}.template".format( "invoice" ) )
        rendered_document = template.render( templatevars )
        PdfGenerator.latexstr_to_pdf( rendered_document, output_file )
        return output_file
    @staticmethod
    def _render_note( none, output_file ):
        templatevars = {'recipient': "%s\n%s\n%s %s" % ( note.customer.name, note.address.street, note.address.zipcode, note.address.city ),
                        'signature':'POSITION\nAbo-Service',
                        'opening':'Sehr geehrter Herr %s,' % note.customer.familyname,
                        'closing':'Mit freundlichen Grüßen,',
                        'date':note.date.strftime( '%d.~%m~%Y' ),
                        'subject': note.subject,
                        'text':note.text}
        template = template_env.get_template( "{}.template".format( "note" ) )
        rendered_document = template.render( templatevars )
        PdfGenerator.latexstr_to_pdf( rendered_document, output_file )
        return output_file

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os.path
import shutil
import tempfile
import datetime
import subprocess
import re
import jinja2
import locale
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
class LetterGenerator():
    @staticmethod
    def render_invoice( invoice ):
        output_dir = "/tmp"
        filename = '%d-%s-%s-%s.pdf' % ( invoice.contract.customer.id, invoice.contract.customer.familyname, invoice.contract.customer.prename, invoice.date.strftime( "%Y-%m-%d" ) )
        output_file = os.path.join( output_dir, filename )

        invoice_no = "%s-%s" % ( invoice.contract.refid, invoice.number )
        templatevars = {'recipient': "%s\n%s\n%s %s" % ( invoice.contract.customer.name, invoice.contract.billingaddress.street, invoice.contract.billingaddress.zipcode, invoice.contract.billingaddress.city ),
                        'signature':'POSITION\nAbo-Service',
                        'date':invoice.date.strftime( '%d.~%m~%Y' ),
                        'invoice_no': invoice_no,
                        'subject':'Rechnung Nr. %s' % invoice_no,
                        'opening':'Sehr geehrter Herr %s,' % invoice.contract.customer.familyname,
                        'closing':'Mit freundlichen Grüßen,',
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

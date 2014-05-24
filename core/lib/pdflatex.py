#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import subprocess
from core.errors import LatexError
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
            with tempfile.TemporaryFile() as out:
                latex = subprocess.call( cmd, env=env, stdout=out, stderr=subprocess.STDOUT )
                if latex != 0:
                    out.seek( 0 )
                    print( out.read().decode( "utf-8" ) )
                    raise LatexError()
            tmp_uri = os.path.join( tmpdirname, '%s.pdf' % jobname )
            shutil.copy( tmp_uri, output_file )
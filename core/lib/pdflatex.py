#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import subprocess
from core.errors import LatexError
def compile_str( latexstr, output_file, texinputs=None ):
    """
    Directly compiles a LaTeX-String to a PDF via pdflatex.
    Args:
        latexstr:
            string containing LaTeX commands that is compilable by pdflatex
        output_file:
            the filepath of the pdf file to render
        texinputs:
            a list of additional paths to add to the TEXINPUTS environment variable before compiling (Defaults to None)
    """
    f = tempfile.NamedTemporaryFile( delete=False )
    f.write( bytes( latexstr, 'UTF-8' ) )
    f.close()
    compile_file( f.name , output_file, texinputs )
    os.remove( f.name )
def compile_file( latexfile, output_file, texinputs=None ):
    """
    Compiles a LaTeX-file with pdflatex from Python.
    Args:
        latexfile:
            the filepath of a LaTex-file that is compilable by pdflatex.
        output_file:
            the filepath of the pdf file to render
        texinputs:
            a list of additional paths to add to the TEXINPUTS environment variable before compiling (Defaults to None)
    """
    jobname = 'document'
    # Modify environment (if needed)
    env = os.environ.copy()
    if not 'TEXINPUTS' in env:
        env['TEXINPUTS'] = ''
    if texinputs is None:
        new_texinputs = []
    elif type( texinputs ) is not list:
        if type( texinputs ) is str:
            new_texinputs = [ texinputs ]
        else:
            new_texinputs = list( texinputs )
    env['TEXINPUTS'] = os.pathsep.join( new_texinputs + [ env['TEXINPUTS'] ] )
    # Compile the file in a temporary directory (so we don't have to worry about cleaning up the auxiliary files after compilation)
    with tempfile.TemporaryDirectory() as tmp_dirname:
        cmd = ['pdflatex',
               '-halt-on-error',
               '-interaction', 'nonstopmode',
               '-jobname', jobname,
               '-output-directory', tmp_dirname,
               latexfile]
        with tempfile.TemporaryFile() as out:
            latex = subprocess.call( cmd, env=env, stdout=out, stderr=subprocess.STDOUT )
            if latex != 0:
                out.seek( 0 )
                print( out.read().decode( "utf-8" ) )
                raise LatexError()
        # The file was compile successfully, now move the file out of the folder, so that it won't be deleted automatically
        tmp_filename = jobname + os.extsep + 'pdf'
        tmp_filepath = os.path.join( tmp_dirname, tmp_filename )
        shutil.copy( tmp_filepath, output_file )

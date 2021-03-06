#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import subprocess
import logging
import platform

if platform.system() == 'Windows':
    import win32file

from core.errors import LatexError


def compile_str(latexstr, *args, **kwargs):
    """
    Directly compiles a LaTeX-String to a PDF via pdflatex.
    Args:
        latexstr:
            string containing LaTeX commands that is compilable by pdflatex
        *args:
            args to be passed to compile_file
        **kwargs:
            kwargs to be passed to compile_file
    """
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(latexstr.encode('UTF-8'))
    compile_file(f.name, *args, **kwargs)
    os.remove(f.name)


def compile_file(latexfile, output_file, texinputs=None):
    """
    Compiles a LaTeX-file with pdflatex from Python.
    Args:
        latexfile:
            the filepath of a LaTex-file that is compilable by pdflatex.
        output_file:
            the filepath of the pdf file to render
        texinputs:
            a list of additional paths to add to the TEXINPUTS environment
            variable before compiling (Defaults to None)
    """
    logger = logging.getLogger(__name__)
    # Create Environment
    env = os.environ.copy()
    # Modify environment (add $TEXINPUTS)
    if type(texinputs) is list:
        new_texinputs = texinputs.copy()
    else:
        new_texinputs = []
        if type(texinputs) is not None:
            if type(texinputs) is str:
                new_texinputs = [texinputs]
            else:
                new_texinputs = list(texinputs)
    if 'TEXINPUTS' in env and env['TEXINPUTS']:
        new_texinputs += env['TEXINPUTS'].split(os.pathsep)
    else:
        # Empty string, so that a trailing os.pathsep will be added (this
        # includes default data path)
        new_texinputs += ['']
    env['TEXINPUTS'] = os.pathsep.join(new_texinputs)
    # Specify filename of pdf output file
    jobname = 'document'

    startupinfo = None
    if platform.system() == 'Windows':
        # Yet another Windows workaround: This time we want to hide the command
        # prompt that pops up when executing pdflatex. Thank you, Bill Gates!
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    # Compile the file in a temporary directory (so we don't have to worry
    # about cleaning up the auxiliary files after compilation)
    with tempfile.TemporaryDirectory() as tmp_dirname:
        if platform.system() == 'Windows':
            # This is kind of a hack. I initalially thought that using Python I
            # won't have to care about all these OS based issues. But I was
            # wrong. Unfortunately, pdflatex is not able to handle abbreviated
            # filenames in Windows' almighty 8-3 syntax. So we need to get the
            # long filename from an abbreviated ones by using pywin32.
            # Gosh, I hate Windows.
            # PS: To be fair, I hate Python and pdflatex for this, too
            latexfile = win32file.GetLongPathName(latexfile)
            tmp_dirname = win32file.GetLongPathName(tmp_dirname)
        cmd = ['pdflatex',
               '-halt-on-error',
               '-interaction', 'nonstopmode',
               '-jobname', jobname,
               '-output-directory', tmp_dirname,
               latexfile]
        # Redirect pdflatex' stdout to tempfile (and show it if an error
        # occurs)
        with tempfile.SpooledTemporaryFile() as out_f:
            try:
                subprocess.check_call(cmd, env=env, stdout=out_f,
                                      stderr=subprocess.STDOUT,
                                      startupinfo=startupinfo)
            except subprocess.CalledProcessError as e:
                logger.error("Command failed with returncode %d: %r",
                             e.returncode, e.cmd)
                out_f.seek(0)
                pdflatexlog = out_f.read().decode("utf-8")
                logger.critical(pdflatexlog)
                raise LatexError()
        # Get the filename of the compiled pdf
        tmp_filename = jobname + os.extsep + 'pdf'
        tmp_filepath = os.path.join(tmp_dirname, tmp_filename)
        if not os.path.exists(tmp_filepath):
            raise LatexError()
        # The file was compile successfully, now move the file out of the
        # folder, so that it won't be deleted automatically
        shutil.copy(tmp_filepath, output_file)

# -*- coding: utf-8-*-
import os
import platform

# MSM main directory
APP_PATH = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir))
DATA_PATH = os.path.join(APP_PATH, "data")
CORE_PATH = os.path.join(APP_PATH, "core")
PLUGIN_PATH = os.path.join(APP_PATH, "plugins")
CONFIG_PATH = (os.path.join(os.environ['APPDATA'], 'msm')
               if platform.system() == 'Windows' else
               os.path.expanduser('~/.msm'))


def config(*fname):
    return os.path.join(CONFIG_PATH, *fname)


def data(*fname):
    return os.path.join(DATA_PATH, *fname)

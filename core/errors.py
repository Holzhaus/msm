#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
logger = logging.getLogger( __name__ )
class BaseError( Exception ):
    pass
class InvoiceError( BaseError ):
    pass
class LatexError( BaseError ):
    pass

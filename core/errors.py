#!/usr/bin/env python3
# -*- coding: utf-8 -*-
class BaseError( Exception ):
    pass
class InvoiceError( BaseError ):
    pass
class LatexError( BaseError ):
    pass

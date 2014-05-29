#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
logger = logging.getLogger( __name__ )
import datetime
from core.database import Letter, LetterPart, Note, PaymentType
class Criterion:
    Always, OnlyOnInvoice, OnlyOnDirectWithdrawal = range( 3 )
    @staticmethod
    def get_text( criterion ):
        if criterion is None or criterion == Criterion.Always:
            text = "Immer"
        elif criterion == Criterion.OnlyOnInvoice:
            text = "Nur bei Bezahlung per Rechnung"
        elif criterion == Criterion.OnlyOnDirectWithdrawal:
            text = "Nur bei Bezahlung per Lastschrift"
        return text
class InvoicePlaceholder:
    pass
class LetterComposition( list ):
    def get_description( self ):
        desc = ""
        for part, criterion in self:
            if type( part ) is InvoicePlaceholder:
                desc += "Rechnung"
            elif type( part ) is Note:
                desc += part.name
            else:
                raise TypeError( "Unknown Letterpart" )
            desc += " ({})\n".format( Criterion.get_text( criterion ) )
        return desc.strip()
    def append( self, part, criterion ):
        if not ( isinstance( part, LetterPart ) or isinstance( part, InvoicePlaceholder ) ):
            raise TypeError( 'instance %r has invalid type: %r' % ( part, type( part ) ) )
        if not ( criterion == Criterion.Always or criterion == Criterion.OnlyOnInvoice or criterion == Criterion.OnlyOnDirectWithdrawal or criterion is None ):
            raise ValueError( 'not a criterion' )
        super().append( ( part, criterion ) )
    def expunge_contents( self ):
        for part, criterion in self:
            if isinstance( part, LetterPart ):
                obj_session = part.session
                if obj_session:
                    obj_session.expunge( part )
    def merge( self, session ):
        merged_lettercomposition = self.__class__()
        for part, criterion in self:
            if isinstance( part, LetterPart ):
                merged_part = session.merge( part )
            else:
                merged_part = part
            merged_lettercomposition.append( merged_part, criterion )
        return merged_lettercomposition
class ContractLetterComposition( LetterComposition ):
    def compose( self, contract, date=datetime.date.today() ):
        letter = Letter( contract, date=date )
        for part, criterion in self:
            if criterion is None or criterion == Criterion.Always or \
            ( criterion == Criterion.OnlyOnInvoice and contract.paymenttype == PaymentType.Invoice ) or \
            ( criterion == Criterion.OnlyOnDirectWithdrawal and contract.paymenttype == PaymentType.DirectWithdrawal ):
                if type( part ) is InvoicePlaceholder:
                    for invoice in contract.invoices:
                        letter.add_content( invoice )
                else:
                    letter.add_content( part )
        return letter

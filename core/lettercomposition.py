#!/usr/bin/env python3
# -*- coding: utf-8 -
import datetime
from core.database import Letter, PaymentType
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
    def append( self, part, criterion ):
        super().append( ( part, criterion ) )
class ContractLetterComposition( LetterComposition ):
    def compose( self, contract, date=datetime.date.today() ):
        letter = Letter( contract, date=date )
        for letterpart, criterion in self:
            if criterion is None or criterion == Criterion.Always or \
            ( criterion == Criterion.OnlyOnInvoice and contract.paymenttype == PaymentType.Invoice ) or \
            ( criterion == Criterion.OnlyOnDirectWithdrawal and contract.paymenttype == PaymentType.DirectWithdrawal ):
                if type( letterpart ) is InvoicePlaceholder:
                    for invoice in contract.invoices:
                        letter.add_content( invoice )
                else:
                    letter.add_content( letterpart )
            else:
                raise RuntimeError( "unknown type: %s", letterpart )
        return letter

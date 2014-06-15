#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import logging
if __name__ == "__main__":
    logger = logging.getLogger()
    sys.path = [os.path.abspath( '..' )] + sys.path
else:
    logger = logging.getLogger( __name__ )
import locale
locale.setlocale( locale.LC_ALL, 'de_DE.UTF-8' )
import datetime
from core.config import Config
import core.database

def print_table( contractnums ):
    fields = ['ID', 'ABO', 'PREIS', 'ABONNENTEN']
    rows = []
    for subscription_dict in contractnums.values():
        for value, number in subscription_dict['values'].items():
            rows.append( [subscription_dict['id'], subscription_dict['name'], locale.currency( value ), number] )
    if len( rows ) > 0:
        colwidth = []
        for i, col in enumerate( fields ):
            maxlen = max( [len( str( row[i] ) ) for row in rows] )
            colwidth.append( maxlen )
            if len( col ) > colwidth[i]:
                colwidth[i] = len( col )
            if i != 0:
                colwidth[i] += 1
    row_format = ""
    for width in colwidth:
        row_format += "{{:>{}}}".format( width )
    print( row_format.format( *fields ) )
    for row in rows:
        print( row_format.format( *row ) )

if __name__ == "__main__":
    db_uri = Config.get( "Database", "db_uri" )
    database = core.database.Database( db_uri )
    session = core.database.Database.get_scoped_session()

    dateobj = datetime.date.today()
    print( 'Anzahl der Verträge am {}'.format( dateobj.strftime( locale.nl_langinfo( locale.D_FMT ) ) ) )
    contractnums = {}
    for contract in core.database.Contract.get_all():
        if contract.is_running( dateobj ):
            key = contract.subscription.id
            if key not in contractnums:
                contractnums[key] = {'id': contract.subscription.id, 'name':contract.subscription.name, 'values':{}}
            else:
                value = contract.value
                if value not in contractnums[key]['values']:
                    contractnums[key]['values'][value] = 1
                else:
                    contractnums[key]['values'][value] += 1
    print_table( contractnums )

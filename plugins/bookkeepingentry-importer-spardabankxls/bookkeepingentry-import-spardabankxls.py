import re
import locale
import dateutil.parser
import core.plugintypes


class BookingImporterSpardaBankXLS(core.plugintypes.BookingImporter):
    FILE_EXT = 'xls'
    PATTERN_HEADER = re.compile(r'Kontoumsätze Girokonto\n\nKontoinhaber:\t"(?P<kontoinhaber>.+)"\nKundennummer:\t"(?P<kundennummer>\d+)"\n\nUmsätze ab\tEnddatum\tKontonummer\tSaldo\tWährung\n"(?P<startdatum>\d{2}.\d{2}.\d{4})"\t"(?P<enddatum>\d{2}.\d{2}.\d{4})"\t"(?P<kontonummer>\d+)"\t"(?P<saldo>-{0,1}\d{1,3}(?:\.\d{3})*,\d{2})"\t"(?P<waehrung>[A-Z]{3})"\n\n\nBuchungstag\tWertstellungstag\tVerwendungszweck\tUmsatz\tWährung\n')
    PATTERN_FOOTER = re.compile(r'"\* noch nicht ausgeführte Umsätze"')
    PATTERN_LINE = re.compile(r'"(?P<bookingdate>\d{2}.\d{2}.\d{4})"\t"(?P<valuedate>\d{2}.\d{2}.\d{4})"\t"(?P<description>[^"]+)"\t"(?P<value>-{0,1}\d{1,3}(?:\.\d{3})*,\d{2})"\t"(?P<currency>[A-Z]{3})"\t""\n')
    PATTERN_CONTRACT = re.compile(r'SVWZ\+[^+]*(?P<contractnumber>[A-Z0-9]{8})-(?P<invoicenumber>\d{1})')

    def read(self, input_file):
        with open(input_file, 'r', newline='', encoding='latin1') as f:
            headerlines = [f.readline() for i in range(10)]
            headertext = "".join(headerlines)
            lines = f.readlines()
            content, footertext = lines[:-1], lines[-1]
            header = self.PATTERN_HEADER.match(headertext)
            footer = self.PATTERN_FOOTER.match(footertext)
        if header is not None and footer is not None:
            for line in content:
                matchobj = self.PATTERN_LINE.match(line)
                if not matchobj:
                    continue
                info = matchobj.groupdict()
                if not info['currency'] == 'EUR':
                    continue
                date = dateutil.parser.parse(info['valuedate'])
                value = locale.atof(info['value'])
                description = "{description} (Buchungstag: {bookingdate}, Wertstellungstag: {valuedate}, Betrag: {value}, Währung: {currency})".format(**info)
                contractsearch = self.PATTERN_CONTRACT.search(info['description'])
                if not contractsearch:
                    continue
                contractinfo = contractsearch.groupdict()
                yield (date, value, description, contractinfo['contractnumber'], contractinfo['invoicenumber'])
        else:
            yield

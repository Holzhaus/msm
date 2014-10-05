import csv
import pytz
import locale
import core.plugintypes


class DirectDebitExportFormatterCSV(core.plugintypes.DirectDebitExportFormatter):
    FILE_EXT = 'csv'

    def write(self, invoices, output_file):
        fieldnames = ['NAME', 'CONTRACTNUMBER', 'INVOICENUMBER', 'VALUE',
                      'CURRENCY', 'IBAN', 'BIC', 'BANK', 'DESCRIPTION',
                      'CO', 'STREET', 'CITY', 'POSTALCODE', 'COUNTRYCODE',
                      'COUNTRYNAME']
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            csvwriter = csv.writer(f, delimiter=';', quotechar='"',
                                   quoting=csv.QUOTE_ALL)
            csvwriter.writerow(fieldnames)
            for invoice in invoices:
                address = contract.billingaddress
                if not address:
                    continue
                countryname = pytz.country_names[address.countrycode.lower()]
                # FIXME: improvement needed
                description = "{magazine}, {subscription} ({contractnumber}-{invoicenumber}), Abrechnungzeitraum {startdate} bis {enddate}".format(magazine=contract.subscription.magazine.name,
                  contractnumber=contract.refid, invoicenumber=invoice.number, subscription=contract.subscription.name,
                  startdate=invoice.accounting_startdate.strftime(locale.nl_langinfo(locale.D_FMT)), enddate=invoice.accounting_enddate.strftime(locale.nl_langinfo(locale.D_FMT)))

                row = [contract.customer.name,
                       contract.refid,
                       invoice.number,
                       invoice.value_left,
                       "EUR",
                       bankaccount.iban,
                       bankaccount.bic,
                       bankaccount.bank,
                       description,
                       address.co,
                       address.street,
                       address.city,
                       address.zipcode,
                       address.countrycode,
                       countryname]
                csvwriter.writerow(row)
                yield contract.refid
            yield

import csv
import pytz
import core.plugintypes


class AddressExportFormatterCSV(core.plugintypes.ContractExportFormatter):
    FILE_EXT = 'csv'

    def write(self, contracts, output_file):
        fieldnames = ['RECIPIENT', 'CO', 'STREET', 'CITY', 'POSTALCODE',
                      'COUNTRYCODE', 'COUNTRYNAME', 'CONTRACTNUMBER']
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            csvwriter = csv.writer(f, delimiter=';', quotechar='"',
                                   quoting=csv.QUOTE_ALL)
            csvwriter.writerow(fieldnames)
            for contract in contracts:
                address = contract.shippingaddress
                if not address:
                    continue
                recipient = (address.recipient if address.recipient
                             else address.customer.name)
                countryname = pytz.country_names[address.countrycode.lower()]
                # FIXME: improvement needed
                row = [recipient, address.co, address.street, address.city,
                       address.zipcode, address.countrycode, countryname,
                       contract.refid]
                csvwriter.writerow(row)
                yield

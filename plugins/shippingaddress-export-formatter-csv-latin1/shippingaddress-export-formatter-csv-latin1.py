import csv
import pytz
import core.plugintypes


class AddressExportFormatterCSV(core.plugintypes.AddressExportFormatter):
    FILE_EXT = 'csv'

    def write(self, contracts, output_file):
        fieldnames = ['RECIPIENT', 'CO', 'STREET', 'CITY', 'POSTALCODE',
                      'COUNTRYCODE', 'COUNTRYNAME', 'CONTRACTNUMBER']
        with open(output_file, 'w', newline='', encoding='latin1') as f:
            csvwriter = csv.writer(f, delimiter=';', quotechar='"',
                                   quoting=csv.QUOTE_ALL)
            csvwriter.writerow(fieldnames)
            num_contracts = len(contracts)
            for i, contract in enumerate(contracts, start=1):
                address = contract.shippingaddress
                recipient = (address.recipient if address.recipient
                             else address.customer.name)
                countryname = pytz.country_names[address.countrycode.lower()]
                # FIXME: improvement needed
                row = [recipient, address.co, address.street, address.city,
                       address.zipcode, address.countrycode, countryname,
                       contract.refid]
                csvwriter.writerow(row)
                yield (i, num_contracts)

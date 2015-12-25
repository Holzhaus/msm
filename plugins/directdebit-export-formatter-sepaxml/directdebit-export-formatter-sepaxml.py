import datetime
import random
import unidecode
import core.plugintypes
try:
    from lxml import etree
    print('running with lxml.etree')
    USING_LXML = True
except ImportError:
    USING_LXML = False
    try:
        # Python 2.5
        import xml.etree.cElementTree as etree
        print('running with cElementTree on Python 2.5+')
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.ElementTree as etree
            print('running with ElementTree on Python 2.5+')
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as etree
                print('running with cElementTree')
            except ImportError:
                try:
                    # normal ElementTree install
                    import elementtree.ElementTree as etree
                    print('running with ElementTree')
                except ImportError:
                    print('Failed to import ElementTree from any known place')


class DirectDebitExportFormatterSEPAXML(
        core.plugintypes.DirectDebitExportFormatter):
    FILE_EXT = 'xml'

    def write(self, invoices, output_file):
        sepaddbuilder = SepaDDXMLBuilder()

        for invoice in invoices:
            sepaddbuilder.transactions.append({
                'e2eid': 'FIXME',
                'value': invoice.value_left,
                'currency': 'EUR',
                'mandate_id': invoice.contract.refid,  # FIXME: Is this okay?
                'mandate_date': invoice.contract.startdate,
                'debtor_name': unidecode.unidecode(
                    invoice.contract.customer.name),
                'debtor_bic': invoice.contract.bankaccount.bic,
                'debtor_iban': invoice.contract.bankaccount.iban,
                'remittance_info': 'Rechnung %s-%d' % (
                    invoice.contract.refid, invoice.number)
            })
            yield invoice.contract.refid

        tree = sepaddbuilder.get_tree()
        yield

        xml = etree.ElementTree(tree)
        xml.write(output_file, encoding='utf-8', xml_declaration=True)


class SepaDDXMLBuilder(object):
    def __init__(self):
        self.transactions = []
        now = datetime.datetime.now()
        self.message_id = '%sX%03d' % (now.strftime('%Y%m%d%H%M%S'),
                                       random.randint(0, 999))
        #  self.message_id = 'MSGID12345678912'
        self.creation_datetime = now
        self.initiator_name = 'Verein Position e.V.'
        self.paymentinfo_id = 'PMTINFID1'
        self.requested_collection_date = now.date()  # FIXME!
        self.creditor_name = 'Verein Position e.V.'
        self.creditor_iban = 'DE11360605910001374180'
        self.creditor_bic = 'GENODED1SPE'
        self.creditor_id = 'DE88ABO00001194007'

    @property
    def num_transactions(self):
        return len(self.transactions)

    def control_sum(self):
        return sum(t['value'] for t in self.transactions)

    def get_tree(self):
        if USING_LXML:
            root = etree.Element('Document', nsmap={
                    None: 'urn:iso:std:iso:20022:tech:xsd:pain.008.002.02',
                    'xsi': 'http://www.w3.org/2001/XMLSchema-instance'})
        else:
            root = etree.Element('Document', {
                'xmlns': 'urn:iso:std:iso:20022:tech:xsd:pain.008.002.02',
                'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance'})

        cddi = etree.SubElement(root, 'CstmrDrctDbtInitn')
        cddi.append(self._get_grphdr_tree())
        cddi.append(self._get_pmtinf_tree())
        return root

    def _get_grphdr_tree(self):
        # Group Header
        grphdr = etree.Element('GrpHdr')
        msgid = etree.SubElement(grphdr, 'MsgId')
        msgid.text = self.message_id
        credttm = etree.SubElement(grphdr, 'CreDtTm')
        credttm.text = self.creation_datetime.strftime('%Y-%m-%dT%H-%M-%S%Z')
        nboftxs = etree.SubElement(grphdr, 'NbOfTxs')
        nboftxs.text = '%d' % self.num_transactions
        '''ctrlsum = etree.SubElement(grphdr, 'CtrlSum')
        ctrlsum.text = '%f' % self.sum_transactions'''
        initgpty = etree.SubElement(grphdr, 'InitgPty')
        initgpty_nm = etree.SubElement(initgpty, 'Nm')
        initgpty_nm.text = self.initiator_name
        '''initgpty_id = etree.SubElement(initgpty, 'Id')
        initgpty_prvtid = etree.SubElement(initgpty_id, 'PrvtId')
        initgpty_othr = etree.SubElement(initgpty_prvtid, 'Othr')
        initgpty_othr_id = etree.SubElement(initgpty_othr, 'Id')
        initgpty_othr_id.text = 'IE97ZZZ123456'''
        return grphdr

    def _get_pmtinf_tree(self):
        # Payment Instruction Information
        pmtinf = etree.Element('PmtInf')
        pmtinfid = etree.SubElement(pmtinf, 'PmtInfId')
        pmtinfid.text = self.paymentinfo_id
        pmtmtd = etree.SubElement(pmtinf, 'PmtMtd')
        pmtmtd.text = 'DD'
        nboftxs = etree.SubElement(pmtinf, 'NbOfTxs')
        nboftxs.text = '%d' % self.num_transactions
        ctrlsum = etree.SubElement(pmtinf, 'CtrlSum')
        ctrlsum.text = '%.2f' % self.control_sum()

        pmttpinf = etree.SubElement(pmtinf, 'PmtTpInf')
        pmttpinf_svclvl = etree.SubElement(pmttpinf, 'SvcLvl')
        pmttpinf_svclvl_cd = etree.SubElement(pmttpinf_svclvl, 'Cd')
        pmttpinf_svclvl_cd.text = 'SEPA'
        pmttpinf_lclinstrm = etree.SubElement(pmttpinf, 'LclInstrm')
        pmttpinf_lclinstrm_cd = etree.SubElement(pmttpinf_lclinstrm, 'Cd')
        pmttpinf_lclinstrm_cd.text = 'CORE'
        pmttpinf_seqtp = etree.SubElement(pmttpinf, 'SeqTp')
        pmttpinf_seqtp.text = 'FRST'

        reqdcolltndt = etree.SubElement(pmtinf, 'ReqdColltnDt')
        reqdcolltndt.text = self.requested_collection_date.isoformat()

        cdtr = etree.SubElement(pmtinf, 'Cdtr')
        cdtr_nm = etree.SubElement(cdtr, 'Nm')
        cdtr_nm.text = self.creditor_name

        cdtracct = etree.SubElement(pmtinf, 'CdtrAcct')
        cdtracct_id = etree.SubElement(cdtracct, 'Id')
        cdtracct_iban = etree.SubElement(cdtracct_id, 'IBAN')
        cdtracct_iban.text = self.creditor_iban

        cdtragt = etree.SubElement(pmtinf, 'CdtrAgt')
        cdtragt_fininstnid = etree.SubElement(cdtragt, 'FinInstnId')
        cdtragt_bic = etree.SubElement(cdtragt_fininstnid, 'BIC')
        cdtragt_bic.text = self.creditor_bic

        cdtrschmeid = etree.SubElement(pmtinf, 'CdtrSchmeId')
        cdtrschmeid_id = etree.SubElement(cdtrschmeid, 'Id')
        cdtrschmeid_prvtid = etree.SubElement(cdtrschmeid_id, 'PrvtId')
        cdtrschmeid_othr = etree.SubElement(cdtrschmeid_prvtid, 'Othr')
        cdtrschmeid_othr_id = etree.SubElement(cdtrschmeid_othr, 'Id')
        cdtrschmeid_othr_id.text = self.creditor_id
        cdtrschmeid_schmenm = etree.SubElement(cdtrschmeid_othr, 'SchmeNm')
        cdtrschmeid_prtry = etree.SubElement(cdtrschmeid_schmenm, 'Prtry')
        cdtrschmeid_prtry.text = 'SEPA'

        for transaction in self.transactions:
            inf = self._get_drctdbttxinf(transaction)
            pmtinf.append(inf)
        return pmtinf

    def _get_drctdbttxinf(self, transaction):
        inf = etree.Element('DrctDbtTxInf')
        pmtid = etree.SubElement(inf, 'PmtId')
        pmtid_e2eid = etree.SubElement(pmtid, 'EndToEndId')
        pmtid_e2eid.text = transaction['e2eid']
        instdamt = etree.SubElement(inf, 'InstdAmt',
                                    Ccy=transaction['currency'])
        instdamt.text = '%.2f' % transaction['value']
        drctdbttx = etree.SubElement(inf, 'DrctDbtTx')
        drctdbttx_mndt = etree.SubElement(drctdbttx, 'MndtRltdInf')
        drctdbttx_mndtid = etree.SubElement(drctdbttx_mndt, 'MndtId')
        drctdbttx_dtofsgntr = etree.SubElement(drctdbttx_mndt, 'DtOfSgntr')
        drctdbttx_mndtid.text = transaction['mandate_id']
        drctdbttx_dtofsgntr.text = transaction['mandate_date'].isoformat()
        dbtragt = etree.SubElement(inf, 'DbtrAgt')
        dbtragt_fininstnid = etree.SubElement(dbtragt, 'FinInstnId')
        dbtragt_bic = etree.SubElement(dbtragt_fininstnid, 'BIC')
        dbtragt_bic.text = transaction['debtor_bic']
        dbtr = etree.SubElement(inf, 'Dbtr')
        dbtr_nm = etree.SubElement(dbtr, 'Nm')
        dbtr_nm.text = transaction['debtor_name']
        dbtracct = etree.SubElement(inf, 'DbtrAcct')
        dbtracct_id = etree.SubElement(dbtracct, 'Id')
        dbtracct_iban = etree.SubElement(dbtracct_id, 'IBAN')
        dbtracct_iban.text = transaction['debtor_iban']
        rmtinf = etree.SubElement(inf, 'RmtInf')
        rmtinf_ustrd = etree.SubElement(rmtinf, 'Ustrd')
        rmtinf_ustrd.text = transaction['remittance_info']
        return inf

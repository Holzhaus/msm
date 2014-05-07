#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import event, orm, create_engine, func, sql
from sqlalchemy import Table, Column, Integer, Float, Boolean, String, Text, Date, ForeignKey
from sqlalchemy.orm import backref, relationship, sessionmaker, scoped_session
Base = declarative_base()
import datetime, random, string, re

zipcodes = {}
bankcodes = {}
Session = None

import sqlalchemy
import weakref
transactions_with_flushes = weakref.WeakSet()

@sqlalchemy.event.listens_for( sqlalchemy.orm.session.Session, "after_flush" )
def log_transaction( session, flush_context ):
    for trans in session.transaction._iterate_parents():
        transactions_with_flushes.add( trans )

def session_has_pending_commit( session ):
    return session.transaction in transactions_with_flushes

class Database( object ):
    session_factory = None
    def _scopefunc( self ):
        """ Needed as scopefunc argument for the scoped_session"""
        return self
    def __init__( self, database ):
        global Session
        Database._database = database
        Database._engine = create_engine( self._database )
        print( "db:", database )
        metadata = Base.metadata
        metadata.create_all( self._engine ) # create tables in database
        Database.session_factory = sessionmaker( bind=self._engine, autoflush=False )
        Session = Database.get_scoped_session( self._scopefunc )
    @staticmethod
    def get_scoped_session( scope_function=None ):
        if Database.session_factory is None:
            raise RuntimeError( "Database has to be initialized first." )
        if scope_function:
            scoped_session_obj = scoped_session( Database.session_factory, scopefunc=scope_function )
        else:
            scoped_session_obj = scoped_session( Database.session_factory )
        return scoped_session_obj
    @staticmethod
    def get_engine_info():
        name = Database._database
        driver = Database._engine.driver
        version = Database._engine.dialect.server_version_info
        return ( name, driver, version )
    """@staticmethod
    def clearCustomers():
        # Can't use this because of cascades: Session().query( Customer ).delete()
        for customer in Database.getCustomers():
            Session().delete( customer )
    @staticmethod
    def getContracts():
        return Session().query( Contract ).order_by( Contract.customer_id )
    @staticmethod
    def importCustomers( filename ):
        data = io.SubscriptionManagerIO.csvimport( filename );
        count = 0
        for row in data:
            # Adresses
            addressdata = row.pop( 'addressdata' ) if 'addressdata' in row else None
            # Contracts
            contractdata = row.pop( 'contractdata' ) if 'contractdata' in row else None
            # Basic customer information
            if ( set( ( 'prename', 'familyname' ) ) <= row.keys() and row['prename'] and row['familyname'] ) or ( 'company1' in row.keys() and row['company1'] ):
                if 'honourific' not in row: row['honourific'] = ""
                if 'title' not in row:      row['title'] = ""
                if 'birthday' not in row:   row['birthday'] = None
                if 'sex' not in row:        row['sex'] = ""
                if 'company1' not in row:   row['company1'] = ""
                if 'company2' not in row:   row['company2'] = ""
                if 'department' not in row: row['department'] = ""
                if self.addCustomer( row['familyname'], row['prename'], row['honourific'], row['title'], row['birthday'], row['sex'], row['company1'], row['company2'], row['department'], addressdata, contractdata ):
                    count += 1
        return count
        pass
    def importBankTransactions( self, filename ):
        pass
        transactions = SubscriptionManagerIO.SpardaBankTransactionXLSImporter.readFile( filename )
        if transactions:
            for t in transactions:
                if t['value'] < 0:
                    entry = Debit( t['booking_date'], abs( t['value'] ), t['reference'] )
                    q = Session().query( Debit )
                else:
                    entry = Credit( t['booking_date'], abs( t['value'] ), t['reference'] )
                    q = Session().query( Credit )
                if entry:
                    contract = Contract.scanReferenceForContract( t['reference'] )
                    if contract:
                        entry.contract_id = contract.id
                    if q.filter_by( date=entry.date, value=entry.value, description=entry.description, contract_id=entry.contract_id ).count() == 0:
                        Session().add( entry )
                    else:
                        print( entry, "already in database" )
    def exportShippingData( self, filename, date=datetime.date.today() ):
        shippingdata = []
        for contract in self.getContracts():
            if contract.isRunning( date ):
                row = {'familyname': contract.customer.familyname,
                       'prename': contract.customer.prename,
                       'honourific': contract.customer.honourific,
                       'title': contract.customer.title,
                       'gender': contract.customer.gender,
                       'company1': contract.customer.company1,
                       'company2': contract.customer.company2,
                       'department': contract.customer.department,
                       'co': contract.shippingaddress.co,
                       'street': contract.shippingaddress.street,
                       'zipcode': contract.shippingaddress.zipcode,
                       'city': contract.shippingaddress.city,
                       'country': contract.shippingaddress.countrycode}
                shippingdata.append( row )
        shippingdata.sort( key=operator.itemgetter( 'zipcode', 'familyname', 'prename' ) )
        return SubscriptionManagerIO.SubscriptionManagerIO.csvexport( filename, shippingdata )
    def exportBankTransactions( self, filename, type='DTA', creation_date=datetime.date.today(), execution_date=datetime.date.today() ):
        if not creation_date or not execution_date or creation_date > execution_date or ( execution_date - execution_date ) > datetime.timedelta( days=15 ):
            raise ValueError( "invalid dates" )
        transactions = []
        for customer in self.getCustomers():
            for contract in customer.contracts:
                if contract.paymenttype == PaymentType.DirectWithdrawal:
                    balance = contract.getActiveEntries( execution_date )[0]
                    if balance >= 0.0:
                        continue
                    if type == 'DTA':
                        from DTAUS import DTAUS
                        transactions.append( ( DTAUS.TransactionType.LK, customer.id, customer.name, contract.bankaccount.number, contract.bankaccount.bankcode, contract.bankaccount.bankname, balance, "POSITION, Vertragsnr. %s" % contract.refid ) )
        if type == 'DTA':
            accountowner = "POSITION e.V."
            accountnumber = "192837465"
            bankcode = "36060591"
            bankname = "Sparda-Bank West eG"
            reference = "Dies ist ein TeST"
            print( SubscriptionManagerIO.SubscriptionManagerIO.export_dta( filename, transactions, accountowner, accountnumber, bankcode, bankname, reference ) )
    def loadZipcodes( self, filename ):
        global zipcodes
        zipcodes = SubscriptionManagerIO.SubscriptionManagerIO.load_opengeodb_zipcodes( filename );
    def loadBankcodes( self, filename ):
        global bankcodes
        bankcodes = SubscriptionManagerIO.SubscriptionManagerIO.load_bundesbank_bankcodes( filename );

    def getAddressById( self, address_id ):
        q = Session().query( Address ).filter_by( id=address_id )
        return q.first() if q else None
    def getBankaccountById( self, bankaccount_id ):
        q = Session().query( Bankaccount ).filter_by( id=bankaccount_id )
        return q.first() if q else None
    def getContractById( self, contract_id ):
        q = Session().query( Contract ).filter_by( id=contract_id )
        return q.first() if q else None
    def getMagazineById( self, magazine_id ):
        q = Session().query( Magazine ).filter_by( id=magazine_id )
        return q.first() if q else None
    def getSubscriptionById( self, subscription_id ):
        q = Session().query( Subscription ).filter_by( id=subscription_id )
        return q.first() if q else None
    def getIssueById( self, issue_id ):
        q = Session().query( Issue ).filter_by( id=issue_id )
        return q.first() if q else None
    def addMagazine( self, name, issues_per_year ):
        magazine = Magazine( name, issues_per_year )
        Session().add( magazine )
        return magazine
    def delete( self, obj, flush=True ):
        Session().delete( obj )
        if flush:
            self.flush()
    def flush( self ):
        Session().flush()
    def session_changed( self ):
        print( Session().dirty )
        print( Session().deleted )
        return True
    def save( self ):
        Session().flush()
        rollback = False
        try:
            Session().commit()
        except Exception as e:
            Session().rollback();
            print( "FIX" + "ME:", type( e ), e.args )
            rollback = True
        return not rollback
        return False"""
class GenderType:
    Undefined, Male, Female, Queer = range( 4 )
class PaymentType:
    DirectWithdrawal, Invoice = range( 2 )
class Customer( Base ):
    __tablename__ = 'customers'
    id = Column( Integer, primary_key=True )
    familyname = Column( String )
    prename = Column( String )
    honourific = Column( String )
    title = Column( String )
    birthday = Column( Date )
    gender = Column( Integer, nullable=False, default=GenderType.Undefined )
    company1 = Column( String )
    company2 = Column( String )
    department = Column( String )
    @property
    def name( self ):
        return "%s %s" % ( self.prename, self.familyname )
    def __eq__( self, other ):
        if isinstance( other, self.__class__ ):
            attr1 = self.__dict__.copy() # We copy the dicts, since we don't want to alter the original ones
            attr2 = other.__dict__.copy()
            for key in list( attr1.keys() ):
                if key.startswith( "_" ):
                    attr1.pop( key )
            for key in list( attr2.keys() ):
                if key.startswith( "_" ):
                    attr2.pop( key )
            return ( attr1 == attr2 )
        else:
            return False
    def __ne__( self, other ):
        return not self.__eq__( other )
    @staticmethod
    def count():
        return Session().query( func.count( Customer.id ) ).scalar()
    @staticmethod
    def get_by_id( customer_id ):
        q = Session().query( Customer ).filter_by( id=customer_id )
        return q.first() if q else None
    @staticmethod
    def get_all( session=None ):
        if session is None:
            session = Session
        else:
            if not isinstance( session, type( Session ) ):
                raise TypeError( "Expected {}, not {}".format( type( Session ).__name__ , type( session ).__name__ ) )
        return list( session().query( Customer ).order_by( Customer.id ) )
    """@staticmethod
    def add( self, familyname, prename, honourific, title, birthday, gender, company1, company2, department,
                     flush=True ):
        if gender not in [GenderType.Undefined, GenderType.Male, GenderType.Female, GenderType.Queer]:
            gender = GenderType.Undefined
        customer = Customer( familyname, prename, honourific, title, birthday, gender, company1, company2, department )
        if customer:
            Session().add( customer )
            if flush:
                Session().flush()
            return customer
        return None"""
    def __init__( self, familyname, prename, honourific="Herr", title="", birthday=None, gender=GenderType.Undefined, company1="", company2="", department="" ):
        # if not ( familyname or company1 ):
        #     raise ValueError
        self.familyname = familyname.title()
        self.prename = prename.title()
        self.honourific = honourific.title()
        self.title = title.title()
        self.birthday = birthday
        self.gender = gender
        self.company1 = company1
        self.company2 = company2
        self.department = department
        self.id # this call is necessary
    def add_address( self, street, zipcode, city="", countrycode="DE", co="" ):
        address = Address( street, zipcode, city, countrycode, co )
        self.addresses.append( address )
        return address
    def add_bankaccount( self, iban, bic="", bank="", owner="" ):
        bankaccount = Bankaccount( iban, bic, bank, owner )
        self.bankaccounts.append( bankaccount )
        return bankaccount
    def add_contract( self, subscription=None, startdate=None, enddate=None, value=None, paymenttype=PaymentType.Invoice, shippingaddress=None, billingaddress=None, bankaccount=None ):
        contract = Contract( subscription, startdate, enddate, value, paymenttype, shippingaddress, billingaddress, bankaccount )
        self.contracts.append( contract )
        return contract
    def is_valid( self ):
        if not ( self.prename and self.familyname ) and not self.company1:
            return False
        return True
    def get_running_contracts( self, date=datetime.date.today() ):
        running_contracts = []
        for contract in self.contracts:
            if contract.is_running( date ):
                running_contracts.append( contract )
        return running_contracts
    def has_running_contracts( self, date=datetime.date.today() ):
        if len( self.get_running_contracts( date ) ):
            return True
        return False

class Address( Base ):
    __tablename__ = 'addresses'
    id = Column( Integer, primary_key=True )
    customer_id = Column( None, ForeignKey( 'customers.id' ) )
    co = Column( String )
    street = Column( String, nullable=False )
    zipcode = Column( String, nullable=False )
    city = Column( String, nullable=False )
    countrycode = Column( String, default="DE" )
    customer = relationship( Customer, primaryjoin=( customer_id == Customer.id ), backref=backref( 'addresses', order_by=id, cascade="all, delete, delete-orphan" ) )
    def __init__( self, street, zipcode, city="", countrycode="DE", co="" ):
        self.street = street
        self.zipcode = zipcode
        self.city = city if city else Address.getCityByZip( self.zipcode )
        self.countrycode = countrycode
        self.co = co
    @staticmethod
    def get_by_id( address_id, session=None ):
        if session is None:
            session = Session
        else:
            if not isinstance( session, type( Session ) ):
                raise TypeError( "Expected {}, not {}".format( type( Session ).__name__ , type( session ).__name__ ) )
        q = session().query( Address ).filter_by( id=address_id )
        return q.first() if q else None
    @staticmethod
    def count():
        return Session().query( func.count( Address.id ) ).scalar()
    @staticmethod
    def getCityByZip( zipcode ):
        if zipcode and zipcodes and zipcode in zipcodes:
                return zipcodes[zipcode]
        return ""
    def is_valid( self ):
        if not self.street or not self.zipcode or not self.city or not self.countrycode:
            return False
        return True

class Magazine( Base ):
    __tablename__ = 'magazines'
    id = Column( Integer, primary_key=True )
    name = Column( String, nullable=False )
    issues_per_year = Column( Integer, nullable=False )
    def __init__( self, name, issues_per_year ):
        self.name = name
        self.issues_per_year = issues_per_year
    def add_subscription( self, name, value, value_changeable=False, number_of_issues=None ):
        subscription = Subscription( name, value, value_changeable, number_of_issues )
        if subscription:
            self.subscriptions.append( subscription )
            return subscription
        return None
    def add_issue( self, year=datetime.date.today().year, number=0, date=datetime.date.today() ):
        issue = Issue( year, number, date )
        print( issue )
        if issue:
            self.issues.append( issue )
            return issue
        return None
    def is_valid( self ):
        if not self.name or not self.issues_per_year:
            return False
        return True
    def get_issues( self, issue_id=None, startdate=None, enddate=None, limit=None ):
        result = []
        for issue in self.issues:
            if issue_id is not None and issue.id != issue_id: continue
            if startdate is not None and issue.date < startdate: continue
            if enddate is not None and issue.date > enddate: continue
            result.append( issue )
        result = result[:limit] if limit is not None else result
        return result
        """if issue_id:
            query = query.filter_by( id=issue_id )
        if startdate:
            query = query.filter( Issue.date >= startdate ) # FIXME: use shipment_date instead
        if enddate:
            query = query.filter( Issue.date <= enddate ) # FIXME: use shipment_date instead
        query = query.order_by( Issue.date )
        query = query[:limit] if limit != None else query.all()
        return query"""
    @staticmethod
    def get_all( session=None ):
        if session is None:
            session = Session
        else:
            if not isinstance( session, type( Session ) ):
                raise TypeError( "Expected {}, not {}".format( type( Session ).__name__ , type( session ).__name__ ) )
        return list( session().query( Magazine ).order_by( Magazine.id ) )
    @staticmethod
    def count():
        return Session().query( func.count( Magazine.id ) ).scalar()
class Subscription( Base ):
    __tablename__ = 'subscriptions'
    id = Column( Integer, primary_key=True )
    magazine_id = Column( None, ForeignKey( 'magazines.id' ) )
    name = Column( String, nullable=False )
    value = Column( Float( 2 ), nullable=False )
    value_changeable = Column( Boolean, nullable=False, default=False )
    number_of_issues = Column( Integer, nullable=True, default=None )
    magazine = relationship( Magazine, backref=backref( 'subscriptions', order_by=id, cascade="all, delete, delete-orphan" ) )
    @property
    def total_number_of_issues( self ):
        """Returns either the number_of_issues of this Subscription (if set) or the according magazines issues_per_year"""
        return self.number_of_issues if self.number_of_issues else self.magazine.issues_per_year
    def __init__( self, name, value, value_changeable=False, number_of_issues=None ):
        self.name = name
        self.value = value
        self.value_changeable = value_changeable
        self.number_of_issues = number_of_issues
    def is_valid( self ):
        if not self.magazine or not self.name or not self.value:
            return False
        return True
    @staticmethod
    def get_by_id( subscription_id, session=None ):
        if session is None:
            session = Session
        else:
            if not isinstance( session, type( Session ) ):
                raise TypeError( "Expected {}, not {}".format( type( Session ).__name__ , type( session ).__name__ ) )
        q = session().query( Subscription ).filter_by( id=subscription_id )
        return q.first() if q else None
    @staticmethod
    def get_all( session=None ):
        if session is None:
            session = Session
        else:
            if not isinstance( session, type( Session ) ):
                raise TypeError( "Expected {}, not {}".format( type( Session ).__name__ , type( session ).__name__ ) )
        return list( session().query( Subscription ).order_by( Subscription.id ) )
    @staticmethod
    def count():
        return Session().query( func.count( Subscription.id ) ).scalar()
class Issue( Base ):
    __tablename__ = 'issues'
    id = Column( Integer, primary_key=True )
    magazine_id = Column( None, ForeignKey( 'magazines.id' ) )
    year = Column( Integer, nullable=False )
    number = Column( Integer, nullable=False )
    date = Column( Date, nullable=False )
    magazine = relationship( Magazine, backref=backref( 'issues', order_by=id, cascade="all, delete, delete-orphan" ) )
    def __init__( self, year, number, date ):
        self.year = year
        self.number = number
        self.date = date
    @staticmethod
    def count():
        return Session().query( func.count( Issue.id ) ).scalar()
    def is_valid( self ):
        if not self.magazine or not self.year or not self.number or not self.date:
            return False
        return True
class Bankaccount( Base ):
    __tablename__ = 'bankaccounts'
    id = Column( Integer, primary_key=True )
    customer_id = Column( None, ForeignKey( 'customers.id' ) )
    owner = Column( String, nullable=False )
    iban = Column( String, nullable=False )
    bic = Column( String( 8 ), nullable=False )
    bank = Column( String, nullable=False )
    customer = relationship( Customer, backref=backref( 'bankaccounts', order_by=id, cascade="all, delete, delete-orphan" ) )
    def __init__( self, iban, bic="", bank="", owner="" ):
        self.iban = iban
        self.bic = bic # if bic else  Bankaccount.get_bic_by_iban( self.bic )
        self.bank = bank # if bank else Bankaccount.get_bank_by_bic( self.bic )
        self.owner = owner
    @staticmethod
    def get_by_id( bankaccount_id, session=None ):
        if session is None:
            session = Session
        else:
            if not isinstance( session, type( Session ) ):
                raise TypeError( "Expected {}, not {}".format( type( Session ).__name__ , type( session ).__name__ ) )
        q = session().query( Bankaccount ).filter_by( id=bankaccount_id )
        return q.first() if q else None
    @staticmethod
    def get_bank_by_bic( bic ):
        raise NotImplementedError
        """if bank and bank and bankcode in bankcodes:
                return bankcodes[bankcode]"""
        return ""
    @staticmethod
    def get_bic_by_iban( bic ):
        raise NotImplementedError
    @staticmethod
    def count():
        return Session().query( func.count( Bankaccount.id ) ).scalar()
    def is_valid( self ):
        if not self.customer or not self.iban or not self.bic:
            return False
        return True
class Contract( Base ):
    __tablename__ = 'contracts'
    id = Column( Integer, primary_key=True )
    refid = Column( String( 8 ), unique=True, nullable=False )
    value = Column( Float( 2 ), nullable=False )
    startdate = Column( Date, nullable=False )
    enddate = Column( Date )
    paymenttype = Column( Integer )
    # Foreign Keys
    customer_id = Column( None, ForeignKey( 'customers.id' ) )
    subscription_id = Column( None, ForeignKey( 'subscriptions.id' ) )
    bankaccount_id = Column( None, ForeignKey( 'bankaccounts.id' ) )
    shippingaddress_id = Column( None, ForeignKey( 'addresses.id' ) )
    billingaddress_id = Column( None, ForeignKey( 'addresses.id' ) )
    # Relationships
    customer = relationship( Customer, backref=backref( 'contracts', order_by=id, cascade="all, delete, delete-orphan" ) )
    subscription = relationship( Subscription, backref=backref( 'contracts', order_by=id, cascade="all, delete, delete-orphan" ) )
    bankaccount = relationship( Bankaccount, backref=backref( 'contracts', order_by=id, cascade="save-update" ) )
    shippingaddress = relationship( Address, primaryjoin=( shippingaddress_id == Address.id ) )
    billingaddress = relationship( Address, primaryjoin=( billingaddress_id == Address.id ) )
    @property
    def price_per_issue( self ):
        import decimal
        ctx = decimal.Context( prec=2, rounding=decimal.ROUND_HALF_EVEN )
        val = ctx.create_decimal( self.value )
        num = ctx.create_decimal( self.subscription.total_number_of_issues )
        result = val / num
        return float( result )
    REFID_SIZE = 6
    REFID_CHECKSUM_SIZE = 2
    REFID_CHARS = string.ascii_uppercase.replace( "O", "" ).replace( "I", "" ) + string.digits.replace( "0", "" )
    def __init__( self, subscription, startdate=None, enddate=None, value=None, paymenttype=PaymentType.Invoice, shippingaddress=None, billingaddress=None, bankaccount=None ):
        self.subscription = subscription
        self.startdate = startdate if startdate else datetime.date.today()
        self.enddate = enddate
        self.value = value if value else 0
        self.paymenttype = paymenttype
        self.shippingaddress = shippingaddress
        self.billingaddress = billingaddress
        self.bankaccount = bankaccount
        self.refid = Contract.generate_refid()
    @staticmethod
    def get_by_id( contract_id, session=None ):
        if session is None:
            session = Session
        else:
            if not isinstance( session, type( Session ) ):
                raise TypeError( "Expected {}, not {}".format( type( Session ).__name__ , type( session ).__name__ ) )
        q = session().query( Contract ).filter_by( id=contract_id )
        return q.first() if q else None
    @staticmethod
    def get_by_refid( contract_refid, session=None ):
        if session is None:
            session = Session
        else:
            if not isinstance( session, type( Session ) ):
                raise TypeError( "Expected {}, not {}".format( type( Session ).__name__ , type( session ).__name__ ) )
        q = session().query( Contract ).filter_by( refid=contract_refid )
        return q.first() if q else None
    @staticmethod
    def get_all( session=None ):
        if session is None:
            session = Session
        else:
            if not isinstance( session, type( Session ) ):
                raise TypeError( "Expected {}, not {}".format( type( Session ).__name__ , type( session ).__name__ ) )
        return list( session().query( Contract ).order_by( Contract.id ) )
    @staticmethod
    def count():
        return Session().query( func.count( Contract.id ) ).scalar()
    @staticmethod
    def scan_refid_for_contract( reference ):
        for needle in re.findall( "[0-9A-Z]{%d}" % ( Contract.REFID_SIZE + Contract.REFID_CHECKSUM_SIZE ), reference ):
            if Contract.isValidRefId( needle ):
                contract = Contract.get_by_refid( needle )
                if contract:
                    return contract
        return None
    @staticmethod
    def is_valid_refid( refid ):
        if not re.match( '^[A-Z0-9]{%d}$' % ( Contract.REFID_SIZE + Contract.REFID_CHECKSUM_SIZE ), refid ):
            return False
        checksum1 = Contract.get_refid_checksum( refid )
        checksum2 = refid[Contract.REFID_SIZE:]
        if checksum1 == checksum2:
            return True
        else:
            return False
    @staticmethod
    def get_refid_checksum( refid ):
        import math
        refid = refid[0:Contract.REFID_SIZE]
        checksum = []
        for i in range( 1, Contract.REFID_CHECKSUM_SIZE + 1 ):
            weight = list( map( int, str( math.floor( math.pi * pow( 10, Contract.REFID_SIZE * i ) ) ) ) )[-Contract.REFID_SIZE:]
            charsum = 0
            for i, char in enumerate( refid ):
                charsum += ord( char ) * weight[i]
            checksum.append( charsum % len( Contract.REFID_CHARS ) )
        return ''.join( Contract.REFID_CHARS[c] for c in checksum )
    @staticmethod
    def generate_refid():
        def generatorfunc( size, chars ):
            refid = ''.join( random.choice( chars ) for x in range( size ) )
            refid += Contract.get_refid_checksum( refid )
            return refid
        refid = generatorfunc( Contract.REFID_SIZE, Contract.REFID_CHARS )
        while Session().query( Contract ).filter( Contract.refid == refid ).count():
            refid = generatorfunc( Contract.REFID_SIZE, Contract.REFID_CHARS )
        return refid
    def is_valid( self ):
        if not self.customer or not self.subscription or not self.billingaddress or not self.shippingaddress:
            return False
        if not self.startdate:
            return False
        if self.enddate and self.enddate > self.startdate:
            return False
        if self.subscription.value_changeable and not self.value:
            return False
        if self.paymenttype == PaymentType.DirectWithdrawal and not self.bankaccount:
            return False
        return True
    def is_running( self, date=datetime.date.today() ):
        if self.startdate <= date:
            if not self.enddate or self.enddate > date:
                if self.subscription:
                    if not self.subscription.number_of_issues:
                        return True
                    elif self.subscription.number_of_issues > len( self.get_issues_received( startdate=self.startdate, enddate=date ) ):
                        return True
        return False
    def get_issues_received( self, startdate=None, enddate=None ):
        if self.startdate:
            startdate = self.startdate if not startdate or self.startdate > startdate else startdate
        if self.enddate:
            enddate = self.enddate if not enddate or self.enddate < enddate else enddate
        if self.subscription.number_of_issues:
            limit = self.subscription.number_of_issues
            if startdate > self.startdate:
                issues_received_before = len( self.get_issues_received( enddate=( startdate - datetime.timedelta( days=1 ) ) ) )
                limit -= issues_received_before
        else:
            limit = None
        issues = self.subscription.magazine.get_issues( startdate=startdate, enddate=enddate, limit=limit )
        print( startdate, enddate, issues )
        return issues
    @property
    def invoices_open( self ):
        invoices = []
        for invoice in self.invoices:
            if invoice.value_left:
                invoice.append( invoice )
        return invoice
    def add_invoice( self, date=datetime.date.today(), due_date=None, maturity=datetime.timedelta( days=14 ), accounting_startdate=None, accounting_enddate=datetime.date.today() ):
        # assume missing values and do some crazy value checking
        if not isinstance( date, datetime.date ):
            raise TypeError( "date has to be of type datetime.date, not {}".format( type( date ).__name__ ) )
        if due_date is None:
            if maturity is None:
                raise ValueError( "Either due_date or maturity has to be set" )
            elif not isinstance( maturity, datetime.timedelta ):
                raise TypeError( "maturity has to be of type datetime.timedelta, not {}".format( type( maturity ).__name__ ) )
            due_date = date + maturity
        elif not isinstance( due_date, datetime.date ):
            raise TypeError( "due_date has to be of type datetime.date, not {}".format( type( due_date ).__name__ ) )
        if not isinstance( accounting_enddate, datetime.date ):
            raise TypeError( "accounting_enddate has to be of type datetime.date, not {}".format( type( due_date ).__name__ ) )
        if len( self.invoices ) > 0:
            previous_invoice = self.invoices[-1]
        else:
            previous_invoice = None
        if not isinstance( accounting_startdate, datetime.date ):
            if previous_invoice is not None:
                accounting_startdate = previous_invoice.accounting_enddate + datetime.timedelta( days=1 ) # assume this invoice's accounting period starts just after the previous invoice's accounting period ended
            else:
                accounting_startdate = self.startdate # assume this invoice's accounting period starts on the contract's startdate
        else:
            if previous_invoice is not None and accounting_startdate <= previous_invoice.enddate: # we don't want that our customers have to pay twice
                raise ValueError( "accounting period overlaps with the accounting period of the last invoice" )
            elif accounting_startdate <= self.startdate:
                raise ValueError( "accounting period starts before the contract" )
        if accounting_startdate >= accounting_enddate:
            raise ValueError( "accounting_startdate has to be earlier than accountig_enddate." )
        # Now we can continue as everything should be fine now
        invoice = Invoice( date=date, due_date=due_date, accounting_startdate=accounting_startdate, accounting_enddate=accounting_enddate )
        self.invoices.append( invoice )
        invoice.add_automatic_entries()
        if invoice.value == 0:
            self.invoices.remove( invoice )
            session = sqlalchemy.inspect( invoice ).session
            if session:
                session.expunge( invoice )
            raise ValueError( "value is zero." )
        invoice.assign_number()
        return invoice
    def _generateContractRefNumber( self ):
        q = Session.query( func.count( Contract.id ) ).filter( Contract.customer_id == self.customer_id, Contract.id <= self.id ).order_by( Contract.id )
        return q.first()[0]

class BookkeepingEntry( Base ):
    __tablename__ = 'bookkeeping_entries'
    id = Column( Integer, primary_key=True )
    contract_id = Column( None, ForeignKey( 'contracts.id' ) )
    date = Column( Date, nullable=False )
    value = Column( Float( 2 ), nullable=False )
    description = Column( String )
    contract = relationship( Contract, backref=backref( 'bookkeeping_entries', order_by=date ) )
    def __init__( self, date, value, description, customer_id=None, contract_id=None ):
        self.date = date
        self.value = value
        self.description = description
        if customer_id:
            self.customer_id = customer_id
        if contract_id:
            self.contract_id = contract_id
    @staticmethod
    def count():
        return Session().query( func.count( BookkeepingEntry.id ) ).scalar()
    def is_valid( self ):
        if not self.customer or not self.contract or not self.date or not self.value or not self.description:
            return False
        return True

association_table = Table( 'association', Base.metadata,
    Column( 'invoice_id', Integer, ForeignKey( 'invoices.id' ) ),
    Column( 'bookkeepingentry_id', Integer, ForeignKey( 'bookkeeping_entries.id' ) )
 )

class Invoice( Base ):
    __tablename__ = 'invoices'
    id = Column( Integer, primary_key=True )
    contract_id = Column( None, ForeignKey( 'contracts.id' ) )
    accounting_startdate = Column( Date, nullable=False )
    accounting_enddate = Column( Date, nullable=False )
    date = Column( Date, nullable=False )
    due_date = Column( Date, nullable=False )
    number = Column( Integer )
    contract = relationship( Contract, backref=backref( 'invoices', order_by=date, cascade="all, delete" ) )
    entries = relationship( BookkeepingEntry, secondary=association_table, backref="invoices", cascade="all, delete" )
    @property
    def value( self ):
        value = 0
        for entry in self.entries:
            if entry.value > 0:
                value += entry.value
        return value
    @property
    def value_paid( self ):
        value = 0
        for entry in self.entries:
            if entry.value < 0:
                value += entry.value
        return value
    @property
    def value_left( self ):
        value = 0
        for entry in self.entries:
            value += entry.value
        return value
    def add_entry( self, date, value, desc ):
        entry = BookkeepingEntry( date, value, desc )
        self.entries.append( entry )
        return entry
    def add_automatic_entries( self ):
        issues_received = self.contract.get_issues_received( startdate=self.accounting_startdate, enddate=self.accounting_enddate )
        value = self.contract.price_per_issue * float( len( issues_received ) )
        for issue in issues_received:
            desc = "{}, Ausgabe {}/{}".format( issue.magazine.name, issue.number, issue.year )
            self.add_entry( issue.date, value, desc )
    def assign_number( self ):
        """Get a new invoice number. The reason why we can't just use the id column is, that invoice numbers need to be ascending *per contract* (according to german law)."""
        if self.number:
            return self.number
        if not self.contract:
            return AttributeError( "contract not yet assigned" )
        previous_invoicenumbers = [ invoice.number for invoice in self.contract.invoices if invoice.number is not None ]
        try:
            number = max( previous_invoicenumbers )
        except ValueError:
            number = None
        if not number:
            number = 0
        number += 1
        self.number = number
    @staticmethod
    def get_all( session=None ):
        if session is None:
            session = Session
        else:
            if not isinstance( session, type( Session ) ):
                raise TypeError( "Expected {}, not {}".format( type( Session ).__name__ , type( session ).__name__ ) )
        return list( session().query( Invoice ).order_by( Invoice.id ) )
    @staticmethod
    def count():
        return Session().query( func.count( Invoice.id ) ).scalar()
    def is_valid( self ):
        if not self.contract or not self.date or not self.entries:
            return False
        return True

class Note( Base ):
    __tablename__ = 'notes'
    id = Column( Integer, primary_key=True )
    subject = Column( String( 50 ) )
    text = Column( Text )
    def __init__( self, subject, text ):
        self.subject = subject
        self.text = text
    @staticmethod
    def get_all( session=None ):
        if session is None:
            session = Session
        else:
            if not isinstance( session, type( Session ) ):
                raise TypeError( "Expected {}, not {}".format( type( Session ).__name__ , type( session ).__name__ ) )
        return list( session().query( Note ).order_by( Note.subject ) )
    @staticmethod
    def count():
        return Session().query( func.count( Note.id ) ).scalar()

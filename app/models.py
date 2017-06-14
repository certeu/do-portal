import os
import base64
import datetime
import binascii
import hashlib
from urllib.error import HTTPError
from mailmanclient import MailmanConnectionError, Client
import onetimepass
from app import db, login_manager, config
from sqlalchemy import desc
from sqlalchemy.dialects import mysql
from flask_sqlalchemy import BaseQuery
from flask import current_app, request
from sqlalchemy.ext.associationproxy import association_proxy
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from itsdangerous import BadTimeSignature, TimedJSONWebSignatureSerializer
from app.utils.mixins import SerializerMixin
from app.utils.inflect import pluralize


#: we don't have an app context yet,
#: we need to load the configuration from the config module
_config = config.get(os.getenv('DO_CONFIG') or 'default')

emails_organizations = db.Table(
    'emails_organizations', db.metadata,
    db.Column('id', db.Integer, primary_key=True),
    db.Column(
        'email_id',
        db.Integer,
        db.ForeignKey('emails.id')
    ),
    db.Column(
        'organization_id',
        db.Integer,
        db.ForeignKey('organizations.id')
    ),
    # db.UniqueConstraint('email_id', 'organization_id', name='eo_idx')
)
tags_vulnerabilities = db.Table(
    'tags_vulnerabilities', db.metadata,
    db.Column('id', db.Integer, primary_key=True),
    db.Column(
        'tag_id',
        db.Integer,
        db.ForeignKey('tags.id')
    ),
    db.Column(
        'vulnerability_id',
        db.Integer,
        db.ForeignKey('vulnerabilities.id')
    )
)


class FilteredQuery(BaseQuery):
    """
    .. todo:: Remove the deleted field and all logic associated with it.
        Audit log will record any changes
    """
    def get(self, ident):
        # override get() so that the flag is always checked in the
        # DB as opposed to pulling from the identity map. - this is optional.
        return BaseQuery.get(self.populate_existing(), ident)

    def __iter__(self):
        return BaseQuery.__iter__(self.private())

    def from_self(self, *ent):
        # override from_self() to automatically apply
        # the criterion too.   this works with count() and
        # others.
        return BaseQuery.from_self(self.private(), *ent)

    def private(self):
        mzero = self._mapper_zero()
        if mzero is not None:
            crit = mzero.class_.deleted == 0
            return self.enable_assertions(False).filter(crit)
        else:
            return self


class Model(db.Model):
    __abstract__ = True
    __public__ = ()
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated = db.Column(db.DateTime, default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow)

    #: Flask-SQLAlchemy's base model class
    #: (which is also SQLAlchemy's declarative base class) defines a
    #: constructor which takes **kwargs and stores all the arguments given,
    #: so it isn't really necessary to define a constructor.
    def __init__(self, **kwargs):
        super(Model, self).__init__(**kwargs)
        # do custom initialization here

    @classmethod
    def fromdict(cls, json):
        items = {}
        for key, val in json.items():
            if isinstance(val, (str, int, list)):
                if hasattr(cls, key):
                    items[key] = val
        return cls(**items)

    def from_json(self, json):
        for attr, value in json.items():
            if isinstance(value, (str, int, list)):
                if hasattr(self, attr):
                    setattr(self, attr, value)
        return self

    @classmethod
    def get(cls, ident):
        return cls.query.get(ident)

    def __str__(self):
        return '{} #{}'.format(self.__class__.__name__, self.id)

    def __repr__(self):
        kws = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        args_ = []
        for k, v in kws.items():
            args_.append('{!s}={!r}'.format(k, str(v)))
        return '{}({})'.format(self.__class__.__name__, ', '.join(args_))


def get_mailman_client():
    """Return a mailman client instance to be used by the model.

    .. note:: Printing the instance will print the API crendential
    """
    return Client('{0}/{1}'.format(
        current_app.config['MAILMAN_REST_API_URL'],
        current_app.config['MAILMAN_REST_API_VERSION']),
        current_app.config['MAILMAN_REST_API_USER'],
        current_app.config['MAILMAN_REST_API_PASS'])


class MailmanApiError(Exception):
    pass


class MailmanQuery:

    def __init__(self, endpoint, **kwargs):
        self.endpoint = endpoint

    def all(self):
        try:
            return getattr(get_mailman_client(), pluralize(self.endpoint))
        except AttributeError:
            raise MailmanApiError
        except MailmanConnectionError as e:
            raise MailmanApiError(e)

    def get(self, **kwargs):
        try:
            method = getattr(get_mailman_client(), 'get_' + self.endpoint)
            return method(**kwargs)
        except AttributeError as e:
            raise MailmanApiError(e)
        except HTTPError as e:
            raise
        except MailmanConnectionError as e:
            raise MailmanApiError(e)

    def get_or_404(self, **kwargs):
        try:
            return self.get(**kwargs)
        except HTTPError as e:
            raise
        except MailmanConnectionError as mce:
            raise MailmanApiError(mce)


class MailmanModel:

    def __init__(self, endpoint, **kwargs):
        self.endpoint = endpoint

    @classmethod
    def get(cls, **kwargs):
        return cls.query.get(**kwargs)

    @classmethod
    def get_or_404(cls, **kwargs):
        return cls.query.get_or_404(**kwargs)


class MailmanDomain(MailmanModel):

    query = MailmanQuery('domain')


class MailmanList(MailmanModel):

    query = MailmanQuery('list')


class MailmanUser(MailmanModel):

    query = MailmanQuery('user')


class MailmanMember(MailmanModel):

    query = MailmanQuery('member')


class User(UserMixin, Model, SerializerMixin):
    """User model"""
    __tablename__ = 'users'
    __public__ = ('name', 'email', 'api_key', 'otp_enabled')
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    name = db.Column(db.String(255), nullable=False)
    _password = db.Column('password', db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True)
    api_key = db.Column(db.String(64), nullable=True)
    is_admin = db.Column(db.Boolean(), default=False)
    deleted = db.Column(db.Integer, default=0)
    otp_secret = db.Column(db.String(16))
    otp_enabled = db.Column(db.Boolean, default=0, nullable=False)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.email in current_app.config['ADMINS']:
            self.role = Role.query.filter_by(permissions=0xff).first()
        if self.role is None:
            self.role = Role.query.filter_by(default=True).first()
        if self.id is None:
            self.otp_secret = base64.b32encode(os.urandom(10)).decode('utf-8')

    def get_totp_uri(self):
        return 'otpauth://totp/{0}?secret={1}&issuer=CERT-EU' \
            .format(self.email, self.otp_secret)

    def verify_totp(self, token):
        return onetimepass.valid_totp(token, self.otp_secret, window=1)

    @property
    def password(self):
        """User password is a read-only property.

        :raises: :class:`AttributeError`
        """
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self._password = generate_password_hash(
            password, method='pbkdf2:sha512:100001', salt_length=32
        )

    def check_password(self, password):
        return check_password_hash(self._password, password)

    @classmethod
    def authenticate(cls, email, password):
        user = cls.query.filter(cls.email == email).first()
        if user:
            authenticated = user.check_password(password)
        else:
            authenticated = False
        return user, authenticated

    def get_auth_token(self, last_totp=None):
        """Think of :class:`URLSafeTimedSerializer` `salt` parameter as
        namespace instead of salt. `The salt explained:
        <https://pythonhosted.org/itsdangerous/#the-salt>`_.
        """
        data = [self.email, self._password, str(self.id)]
        if last_totp:
            data.append(last_totp)
        s = URLSafeTimedSerializer(
            current_app.config['SECRET_KEY'],
            salt='user-auth',
            signer_kwargs=dict(
                key_derivation='hmac',
                digest_method=hashlib.sha256)
        )
        return s.dumps(data)

    def generate_reset_token(self, expiry=900):
        """Generate a JSON Web Signature that will be used to reset customer's
        password. For details see
        :meth:`itsdangerous.JSONWebSignatureSerializer.dumps`

        :param expiry: Token expiration time (seconds)
        :return:
        """
        s = TimedJSONWebSignatureSerializer(
            current_app.config['SECRET_KEY'], expiry
        )
        return s.dumps({'user_id': self.id})

    def reset_password(self, token, new_pass):
        """Reset password. Token is generated by
        :meth:`~User.generate_reset_token`

        :param token:
        :param new_pass:
        :return:
        """
        s = TimedJSONWebSignatureSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('user_id') == self.id:
            self.password = new_pass
            db.session.add(self)
            db.session.commit()
            return True
        return False

    @classmethod
    def set_password(cls, token, passwd):
        """Set the password for user

        :param token:
        :param passwd:
        :return:
        """
        s = TimedJSONWebSignatureSerializer(current_app.config['SECRET_KEY'])
        data = s.loads(token)
        user = cls.get(data.get('user_id'))
        user.password = passwd
        db.session.add(user)
        db.session.commit()

    @staticmethod
    def create_test_user():
        """Create dummy user for running tests
        """
        if current_app.config['TESTING']:
            name = 'test-{}'.format(User.random_str(8))
            email = 'test-{}@{}.com'.format(
                User.random_str(8), User.random_str(8))
            current_app.config['ADMINS'].append(email)
            Role._Role__insert_defaults()
            user = User(name=name, email=email, password='e9c9525ef737',
                        otp_enabled=True)
            user.api_key = user.generate_api_key()
            db.session.add(user)
            db.session.commit()
            return user

    def generate_api_key(self):
        rand = self.random_str()
        return hashlib.sha256(rand.encode()).hexdigest()

    @staticmethod
    def random_str(length=64):
        return binascii.hexlify(os.urandom(length)).decode()

    def can(self, permissions):
        return self.role is not None and \
            (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)


class Permission:
    """Permissions pseudo-model. Uses 8 bits to assign permissions.
    Each permission is assigned a bit possion and for each role the
    permissions that are allowed will have their bits set to 1.

    When granularity is needed use roles and permissions.
    For simple cases (users & admins) using :attr:`User.is_admin` is enough.

    Permissions:

    +---------------+-----------------+---------------------------------------+
    | Permission    | Bit (Hex)       | Description                           |
    +===============+=================+=======================================+
    | ORGADMIN      | 00000001 (0x01) | Allow editing organization details    |
    +---------------+-----------------+---------------------------------------+
    | SUBMITSAMPLE  | 00000010 (0x02) | User can submit malware samples       |
    +---------------+-----------------+---------------------------------------+
    | ADDCPACCOUNT  | 00000100 (0x04) | User can register contact emails for  |
    |               |                 | CP access.                            |
    +---------------+-----------------+---------------------------------------+
    | SLAACTIONS    | 00001000 (0x08) | User is part of an organization that  |
    |               |                 | has signed an SLA with CERT-EU.       |
    +---------------+-----------------+---------------------------------------+
    | ADMINISTER    | 10000000 (0x80) | Administrative access                 |
    +---------------+-----------------+---------------------------------------+

    Roles:

    +---------------+-----------------+---------------------------------------+
    | Role          | Bit (Hex)       | Description                           |
    +===============+=================+=======================================+
    | Anonymous     | 00000000 (0x00) | No access                             |
    +---------------+-----------------+---------------------------------------+
    | Constituent   | 00000111 (0x07) | Constituents can edit their details,  |
    |               |                 | submit malware samples and register   |
    |               |                 | other contact emails for CP access.   |
    +---------------+-----------------+---------------------------------------+
    | SLA           | 00001111 (0x0f) | All Constituent role permissions plus |
    | Constituent   |                 | SLAACCOUNT.                           |
    +---------------+-----------------+---------------------------------------+
    | Administrator | 11111111 (0x80) | Administrator rights (Full access)    |
    +---------------+-----------------+---------------------------------------+

    >>> '0x{0:02x}'.format(int('00000100', 2))
    >>> 0x04
    """
    ORGADMIN = 0x01
    SUBMITSAMPLE = 0x02
    ADDCPACCOUNT = 0x04
    SLAACTIONS = 0x08
    ADMINISTER = 0x80


class Role(Model, SerializerMixin):
    __tablename__ = 'roles'
    __public__ = ('id', 'name')
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    #: True for one role, False for all others
    #: Used as marker when creating new users
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref=db.backref('role'), lazy='dynamic')

    @staticmethod
    def __insert_defaults():
        roles = {
            'Constituent': (Permission.ORGADMIN |
                            Permission.SUBMITSAMPLE |
                            Permission.ADDCPACCOUNT, True),
            'SLA Constituent': (Permission.ORGADMIN |
                                Permission.SUBMITSAMPLE |
                                Permission.ADDCPACCOUNT |
                                Permission.SLAACTIONS, False),
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()


class Asn(Model, SerializerMixin):
    __tablename__ = 'asn'
    __public__ = ('id', 'asn', 'as_name')
    query_class = FilteredQuery
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    asn = db.Column(db.Integer)
    as_name = db.Column(db.String(255), nullable=True)
    deleted = db.Column(db.Integer, default=0)


class IpRange(Model, SerializerMixin):
    """Classless Inter-Domain Routing"""
    __tablename__ = 'ip_ranges'
    __public__ = ('id', 'ip_range')
    query_class = FilteredQuery
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    ip_range = db.Column(db.String(255))
    deleted = db.Column(db.Integer, default=0)


class ContactEmail(Model, SerializerMixin):
    """ContactEmail Association Object
    http://docs.sqlalchemy.org/en/rel_1_0/orm/basic_relationships.html#
    association-object
    http://docs.sqlalchemy.org/en/rel_1_0/orm/extensions/associationproxy.html#
    simplifying-association-objects
    """
    __tablename__ = 'contactemails_organizations'
    __public__ = ('email', 'cp', 'fmb')
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    email_id = db.Column(
        db.Integer,
        db.ForeignKey('emails.id'),
        primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('organizations.id'),
        primary_key=True
    )
    #: Mark customer portal access for this email
    cp = db.Column('cp_access', db.Boolean(), default=0, doc='CP access')
    #: Functional mailbox marker
    fmb = db.Column(db.Boolean(), default=0, doc='Functional mailbox')
    organization = db.relationship(
        'Organization',
        backref=db.backref(
            'contact_emails',
            cascade='all, delete-orphan'
        )
    )
    email_ = db.relationship('Email')
    email = association_proxy(
        'email_',
        'email',
        creator=lambda eml: Email(email=eml)
    )

    def __repr__(self):
        return '<AssociationProxy Email({0})>'.format(self.email)


class Email(Model, SerializerMixin):
    __tablename__ = 'emails'
    __public__ = ('id', 'email')
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255))
    deleted = db.Column(db.Integer, default=0)


class Fqdn(Model, SerializerMixin):
    __tablename__ = 'fqdns'
    __public__ = ('id', 'fqdn', 'typosquats')
    query_class = FilteredQuery
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    fqdn = db.Column(db.String(255))
    deleted = db.Column(db.Integer, default=0)

    typosquats = db.relationship('Typosquat', lazy='dynamic')


class Typosquat(Model, SerializerMixin):
    __tablename__ = 'fqdns_typosquats'
    __public__ = ('id', 'fqdn', 'dns_a', 'dns_ns', 'dns_mx', 'updated')
    id = db.Column(db.Integer, primary_key=True)
    fqdn_id = db.Column(db.Integer, db.ForeignKey('fqdns.id'))
    fqdn = db.Column(db.String(255))
    dns_a = db.Column(db.String(255), nullable=True)
    dns_ns = db.Column(db.String(255), nullable=True)
    dns_mx = db.Column(db.String(255), nullable=True)
    raw = db.Column(db.Text)

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self.fqdn)

    def __str__(self):
        return self.fqdn


class OrganizationGroup(Model, SerializerMixin):
    __tablename__ = 'organization_groups'
    __public__ = ('id', 'name', 'color')
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    color = db.Column(db.String(7))
    deleted = db.Column(db.Integer, default=0)

    __mapper_args__ = {
        'order_by': desc(id)
    }

    @staticmethod
    def __insert_defaults():
        """Insert sample organization groups"""
        groups = [{'name': 'Constituents', 'color': '#0033CC'},
                  {'name': 'National CERTs', 'color': '#AF2018'},
                  {'name': 'Partners', 'color': '#00FF00'}]
        for group in groups:
            g = OrganizationGroup(**group)
            db.session.add(g)
        db.session.commit()


class Organization(Model, SerializerMixin):
    """

    .. note::

        AssociationProxy on Many-to-Many will not automagically update
        relantionship model. It needs to be updated manually.

    http://docs.sqlalchemy.org/en/latest/faq/ormconfiguration.html?highlight=
    primaryjoin#i-m-using-declarative-and-setting-primaryjoin-secondaryjoin-
    using-an-and-or-or-and-i-am-getting-an-error-message-about-foreign-keys
    """
    __tablename__ = 'organizations'
    __public__ = ('id', 'abbreviation', 'full_name', 'abuse_emails',
                  'ip_ranges', 'fqdns', 'asns', 'old_ID', 'is_sla',
                  'mail_template', 'mail_times', 'group_id',
                  'group', 'contact_emails')
    query_class = FilteredQuery
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(
        'organization_group_id',
        db.Integer,
        db.ForeignKey('organization_groups.id', name='fk_org_group_id')
    )
    is_sla = db.Column(mysql.TINYINT(1), default=0)
    abbreviation = db.Column(db.String(255), index=True)
    # this is the ID field from AH wiki
    # ("{0:02d}".format(9)
    # we are keeping it for compatibility with the Excel sheets
    old_ID = db.Column(db.String(5))
    full_name = db.Column(db.String(255))
    mail_template = db.Column(db.String(50), default='EnglishReport')
    # send emails this many seconds apart
    mail_times = db.Column(db.Integer, default=3600)
    deleted = db.Column(db.Integer, default=0)

    group = db.relationship(
        'OrganizationGroup',
        uselist=False,
        foreign_keys=[group_id]
    )
    ip_ranges_ = db.relationship(
        'IpRange',
        cascade='all, delete-orphan',
        primaryjoin="and_(IpRange.organization_id == Organization.id, "
                    "IpRange.deleted == 0)",
    )
    ip_ranges = association_proxy(
        'ip_ranges_',
        'ip_range',
        creator=lambda r: IpRange(ip_range=r)
    )
    abuse_emails_ = db.relationship(
        "Email", secondary=lambda: emails_organizations,
        secondaryjoin=db.and_(
            Email.id == emails_organizations.c.email_id,
            Email.deleted == 0)
    )
    #: Abuse e-mails are read by machines
    abuse_emails = association_proxy(
        'abuse_emails_',
        'email',
        creator=lambda eml: Email(email=eml)
    )

    #: Contact e-mails are used by humans
    contact_emails = association_proxy('contact_emails', 'email')

    asns_ = db.relationship(
        'Asn',
        cascade='all, delete-orphan',
        primaryjoin="and_(Asn.organization_id == Organization.id,"
                    "Asn.deleted == 0)"
    )
    asns = association_proxy(
        'asns_',
        'asn',
        creator=lambda asn: Asn(asn=asn)
    )
    fqdns_ = db.relationship('Fqdn', cascade='all, delete-orphan')
    fqdns = association_proxy(
        'fqdns_',
        'fqdn',
        creator=lambda fqdn: Fqdn(fqdn=fqdn)
    )

    users = db.relationship(
        'User', backref=db.backref('organizations'), lazy='dynamic')

    __mapper_args__ = {
        'order_by': abbreviation
    }

    @staticmethod
    def from_collab(customer):
        """Import organization from collab

        :param customer: ``CollabCustomer``
        :return:
        :rtype:
        """
        org = Organization(abbreviation=customer.name)
        conf = customer.config
        try:
            org.full_name = conf['Full name'][0]
        except IndexError:
            current_app.log.error(
                'Organization {} is missing full name...'.format(customer[0])
            )
        try:
            org.mail_times = conf['Mail times'][0]
        except IndexError:
            current_app.log.debug('Using default mail times...')
        try:
            org.mail_template = conf['Mail template'][0]
        except IndexError:
            current_app.log.debug('Using default template...')
        try:
            org.old_ID = conf['ID'][0]
        except IndexError:
            current_app.log.debug('Missing ID...')

        _props_map = {
            'ip_ranges': 'IP range',
            'fqdns': 'FQDN',
            'asns': 'ASN',
            'abuse_emails': 'Abuse email',
            'contact_emails': 'Point of Contact'
        }

        for key, collab_key in _props_map.items():
            if key == 'contact_emails':
                for eml in conf[collab_key]:
                    org.contact_emails.append(
                        ContactEmail(email_=Email(email=eml), cp=0))
            else:
                setattr(org, key, conf[collab_key])

        org.group_id = 1
        return org

    def __repr__(self):
        return '{} #{}'.format(self.__class__.__name__, self.abbreviation)


class Tag(Model, SerializerMixin):
    __tablename__ = 'tags'
    __public__ = ('id', 'name')
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)


class Vulnerability(Model, SerializerMixin):
    __tablename__ = 'vulnerabilities'
    __public__ = ('id', 'constituent', 'do', 'check_string', 'types',
                  'updated', 'url', 'reported', 'patched', 'request_method',
                  'tested', 'request_data', 'request_response_code',
                  'incident_id', 'reporter_name', 'reporter_email',
                  'organization_id', 'notes', 'published', 'scanable',
                  'test_type')
    query_class = FilteredQuery
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    incident_id = db.Column(db.Integer, nullable=True)
    reporter_name = db.Column(db.String(255))
    reporter_email = db.Column(db.String(255))
    #: PoC
    url = db.Column(db.Text)
    request_method = db.Column(db.Enum('GET', 'POST', 'PUT'), default='GET')
    request_data = db.Column(db.Text)
    check_string = db.Column(db.Text)
    test_type = db.Column(db.Enum('request'), default='request')
    request_response_code = db.Column(db.Integer, nullable=True)
    tested = db.Column(db.DateTime, nullable=True)
    reported = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    patched = db.Column(db.DateTime, nullable=True)
    #: Publish in the Hall of Fame
    published = db.Column(db.Boolean, default=False)
    scanable = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    deleted = db.Column(db.Integer, default=0)

    organization_ = db.relationship('Organization')
    constituent = association_proxy('organization_', 'abbreviation')

    user = db.relationship('User')
    do = association_proxy('user', 'name')

    labels_ = db.relationship(
        'Tag', secondary=tags_vulnerabilities,
        backref=db.backref('vulnerabilities'))
    types = association_proxy(
        'labels_',
        'name',
        creator=lambda l: Tag(name=l)
    )
    __mapper_args__ = {
        'order_by': desc(id)
    }


class Deliverable(Model, SerializerMixin):
    """Sample deliverables: CIMBL, CITAR, etc.
    """
    __tablename__ = 'deliverables'
    __public__ = ('id', 'name')
    query_class = FilteredQuery
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    deleted = db.Column(db.Integer, default=0)


class DeliverableFile(Model, SerializerMixin):
    """The files that we upload
    """
    __tablename__ = 'deliverable_files'
    __public__ = ('id', 'name', 'created', 'type')
    query_class = FilteredQuery
    id = db.Column(db.Integer, primary_key=True)
    deliverable_id = db.Column(db.Integer, db.ForeignKey('deliverables.id'))
    name = db.Column(db.String(255), nullable=False)
    #: File will be available to SLA constituents only
    is_sla = db.Column(mysql.TINYINT(1), default=0)
    deleted = db.Column(db.Integer, default=0)

    deliverable_ = db.relationship(
        'Deliverable', uselist=False,
        foreign_keys=[deliverable_id],
        backref=db.backref('files')
    )
    type = association_proxy(
        'deliverable_',
        'name'
    )

    __mapper_args__ = {
        'order_by': desc(id)
    }


class Task(Model):
    __tablename__ = 'tasks_taskmeta'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(255), nullable=True, unique=True)
    status = db.Column(db.String(50), nullable=True)
    result = db.Column(db.BLOB, nullable=True)
    date_done = db.Column(db.DateTime, nullable=True)
    traceback = db.Column(db.Text, nullable=True)


class TaskGroup(Model):
    __tablename__ = 'tasks_groupmeta'
    id = db.Column(db.Integer, primary_key=True)
    taskset_id = db.Column(db.String(255), nullable=True, unique=True)
    result = db.Column(db.BLOB, nullable=True)
    date_done = db.Column(db.DateTime, nullable=True)


class AHBotType(Model, SerializerMixin):
    __tablename__ = 'ah_bot_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30))


class AHBot(Model, SerializerMixin):
    """Model for AbuseHelper bots.
    """
    __tablename__ = 'ah_bots'
    __public__ = ('id', 'name')
    id = db.Column(db.Integer, primary_key=True)
    bot_type_id = db.Column(
        db.Integer,
        db.ForeignKey('ah_bot_types.id'))
    name = db.Column(db.String(30))
    description = db.Column(db.String(255))

    type = db.relationship(
        'AHBotType', uselist=False,
        foreign_keys=[bot_type_id]
    )


class AHStartupConfig(Model, SerializerMixin):
    __tablename__ = 'ah_startup_configs'
    # belongsTo AbuseHelperBot
    # hasMany AbuseHelperStartupParam
    # HABTM AbuseHelperStartupTemplate
    id = db.Column(db.Integer, primary_key=True)
    ah_bot_id = db.Column(
        db.Integer,
        db.ForeignKey('ah_bots.id'))
    enabled = db.Column(db.Boolean(), default=False)
    #: python module or PATH
    module = db.Column(db.String(255))
    state = db.Column(db.Boolean(), default=False, nullable=True)
    pid = db.Column(db.Integer, nullable=True)
    started = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    stopped = db.Column(db.DateTime, nullable=True,
                        onupdate=datetime.datetime.utcnow)
    ah_bot = db.relationship(
        'AHBot',
        foreign_keys=[ah_bot_id]
    )


class AHStartupConfigParam(Model, SerializerMixin):
    __tablename__ = 'ah_startup_config_params'
    # belongsTo AbuseHelperStartupConfig
    id = db.Column(db.Integer, primary_key=True)
    ah_startup_config_id = db.Column(
        db.Integer,
        db.ForeignKey('ah_startup_configs.id'))
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(100), nullable=False)
    ah_startup_config = db.relationship(
        'AHStartupConfig',
        foreign_keys=[ah_startup_config_id],
        backref=db.backref('params')
    )


class AHRuntimeConfig(Model, SerializerMixin):
    __tablename__ = 'ah_runtime_configs'
    # belongsTo AbuseHelperBot
    # hasMany AbuseHelperRuntimeConfigParam
    id = db.Column(db.Integer, primary_key=True)
    alias = db.Column(db.String(2))
    ah_bot_id = db.Column(
        db.Integer,
        db.ForeignKey('ah_bots.id'))
    ah_bot = db.relationship(
        'AHBot',
        foreign_keys=[ah_bot_id]
    )


class AHRuntimeConfigParam(Model, SerializerMixin):
    __tablename__ = 'ah_runtime_config_params'
    # belongsTo AbuseHelperRuntimeConfig
    id = db.Column(db.Integer, primary_key=True)
    ah_runtime_config_id = db.Column(
        db.Integer,
        db.ForeignKey('ah_runtime_configs.id'))
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(100), nullable=False)
    ah_runtime_config = db.relationship(
        'AHRuntimeConfig',
        foreign_keys=[ah_runtime_config_id],
        backref=db.backref('params')
    )


class Sample(Model, SerializerMixin):
    """Model for samples that will be submitted for analysis
    """
    __tablename__ = 'samples'
    __public__ = ('id', 'created', 'filename', 'md5', 'sha1', 'sha256',
                  'sha512', 'ctph')
    query_class = FilteredQuery
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id', name='fk_sample_user_id'))
    #: For archives. All files within an archive will have the parent_id set
    #: to the archive unique ID
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey('samples.id'),
        nullable=True)
    #: Submitted filename
    filename = db.Column(db.Text, nullable=False)
    md5 = db.Column(db.String(32), nullable=False)
    sha1 = db.Column(db.String(40), nullable=False)
    #: SHA-256 sum of file contents
    sha256 = db.Column(db.String(64), nullable=False)
    sha512 = db.Column(db.String(128), nullable=False)
    #: Context triggered piecewise hash
    ctph = db.Column(
        db.Text, nullable=False,
        doc='Context triggered piecewise hash')
    infected = db.Column(db.Integer, default=0)
    deleted = db.Column(db.Integer, default=0)

    __mapper_args__ = {'order_by': desc(id)}

    reports = db.relationship('Report')
    user = db.relationship(
        'User', uselist=False,
        foreign_keys=[user_id],
        backref=db.backref('samples')
    )
    parent = db.relationship(
        'Sample', backref=db.backref('children'),
        remote_side=[id]
    )


class ReportType(Model, SerializerMixin):
    __tablename__ = 'report_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

    @staticmethod
    def __insert_defaults():
        types = ['Static analysis', 'AntiVirus scan', 'Dynamic analysis']
        for type_ in types:
            r = ReportType(name=type_)
            db.session.add(r)
        db.session.commit()


class Report(Model, SerializerMixin):
    __tablename__ = 'reports'
    __public__ = ('id', 'created', 'type', 'report')
    id = db.Column(db.Integer, primary_key=True)
    type_id = db.Column(db.Integer, db.ForeignKey('report_types.id'))
    sample_id = db.Column(db.Integer, db.ForeignKey('samples.id'))
    report = db.Column(db.Text)

    __mapper_args__ = {'order_by': desc(id)}

    type_ = db.relationship('ReportType')
    type = association_proxy(
        'type_',
        'name'
    )


class Contact(Model):
    """Not used"""
    __tablename__ = 'contacts'
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    name = db.Column(db.String(255), nullable=False)
    position = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    deleted = db.Column(db.Integer, default=0)


@login_manager.user_loader
def load_user(user_id):
    """
    Flask-Login user_loader callback.
    The user_loader function asks this function to get a User Object or return
    None based on the userid.
    The userid was stored in the session environment by Flask-Login.
    user_loader stores the returned User object in current_user during every
    flask request.
    """
    return User.query.get(int(user_id))


@login_manager.token_loader
def load_token(token):
    """
    Flask-Login token_loader callback.
    The token_loader function asks this function to take the token that was
    stored on the users computer process it to check if its valid and then
    return a User Object if its valid or None if its not valid.

    :param token: Token generated by :meth:`app.models.User.get_auth_token`
    """

    # The Token itself was generated by User.get_auth_token.  So it is up to
    # us to known the format of the token data itself.

    # The Token was encrypted using itsdangerous.URLSafeTimedSerializer which
    # allows us to have a max_age on the token itself.  When the cookie is
    # stored
    # on the users computer it also has a exipry date, but could be changed by
    # the user, so this feature allows us to enforce the exipry date of the
    # token
    # server side and not rely on the users cookie to exipre.

    max_age = current_app.config['REMEMBER_COOKIE_DURATION'].total_seconds()

    # Decrypt the Security Token, data = [username, hashpass, id]
    s = URLSafeTimedSerializer(
        current_app.config['SECRET_KEY'],
        salt='user-auth',
        signer_kwargs=dict(key_derivation='hmac',
                           digest_method=hashlib.sha256))
    try:
        data = s.loads(token, max_age=max_age)
    except (BadTimeSignature, SignatureExpired):
        return None

    # Find the User
    user = User.query.get(data[2])

    # 2FA check
    totp_endpoint = request.endpoint == 'auth.verify_totp'
    if user and user.otp_enabled and not totp_endpoint and len(data) < 4:
        return None

    # Check Password and return user or None
    if user and data[1] == user._password:
        return user
    return None


@login_manager.request_loader
def load_user_from_request(request):
    """Login users using api_key for header values
    See `<https://flask-login.readthedocs.org/en/latest/#custom-login-using-
    request-loader`>_

    :param request: Flask request
    """
    # first, try to login using the api_key url arg
    api_key = request.args.get('api_authorization')
    if api_key:
        user = User.query.filter_by(api_key=api_key).first()
        if user:
            current_app.log.warn(
                "{} logged in using URL parameter".format(user.name)
            )
            return user

    # next, try to login using an API key
    api_key = request.headers.get('API-Authorization')
    if api_key:
        user = User.query.filter_by(api_key=api_key).first()
        if user:
            return user

    # finally, return None if both methods did not login the user
    return None

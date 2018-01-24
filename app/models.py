import os
import base64
import datetime
import binascii
import hashlib
import random
import csv
import yaml
from urllib.error import HTTPError
from mailmanclient import MailmanConnectionError, Client
import onetimepass
from app import db, login_manager, config
from sqlalchemy import desc, event
# from sqlalchemy.dialects import postgres
from flask_sqlalchemy import BaseQuery
from flask import current_app, request
from sqlalchemy.ext.associationproxy import association_proxy
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from itsdangerous import BadTimeSignature, TimedJSONWebSignatureSerializer
from app.utils.mixins import SerializerMixin
from app.utils.inflect import pluralize
from validate_email import validate_email
from app.utils.mail import send_email
import phonenumbers
import time

#: we don't have an app context yet,
#: we need to load the configuration from the config module
_config = config.get(os.getenv('DO_CONFIG') or 'default')


def check_password_quality(password):
    import re
    error_text = ''
    ea = []
    if len(password) < 8:
        ea.append('password too short')
    if not re.search(r"\d", password):
        ea.append('password has to contain a number')
    if not re.search(r"[ !#$%&'()*+,-./[\\\]^_`{|}~" + r'"]', password):
        ea.append('password has to contain a special character')
    if not re.search(r"[A-Z]", password):
        ea.append('password has to contain an upper case letter')
    if not re.search(r"[a-z]", password):
        ea.append('password has to contain a lower case letter')

    error_text = '; '.join(ea)
    return error_text


emails_organizations = db.Table(
    'emails_organizations',
    db.metadata,
    db.Column('id', db.Integer, primary_key=True),
    db.Column('email_id', db.Integer, db.ForeignKey('emails.id')),
    db.Column('organization_id', db.Integer,
              db.ForeignKey('organizations.id')),
    # db.UniqueConstraint('email_id', 'organization_id', name='eo_idx')
)
tags_vulnerabilities = db.Table('tags_vulnerabilities', db.metadata,
                                db.Column('id', db.Integer, primary_key=True),
                                db.Column('tag_id', db.Integer,
                                          db.ForeignKey('tags.id')),
                                db.Column('vulnerability_id', db.Integer,
                                          db.ForeignKey('vulnerabilities.id')))


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
    updated = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow,
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
            if isinstance(value, (str, int, list)) or value is None:
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
    __public__ = ('id', 'name', 'api_key', 'otp_enabled', 'picture',
                  'birthdate', 'title', 'origin', 'email', 'picture_filename')
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    name = db.Column(db.String(255), nullable=False)
    _password = db.Column(
        'password',
        db.String(255),
        nullable=False,
        default=binascii.hexlify(os.urandom(12)).decode())
    _email = db.Column('email', db.String(255), unique=True)
    api_key = db.Column(db.String(64), nullable=True)
    is_admin = db.Column(db.Boolean(), default=False)
    deleted = db.Column(db.Integer, default=0)
    ts_deleted = db.Column(db.DateTime)
    otp_secret = db.Column(db.String(16))
    otp_enabled = db.Column(db.Boolean, default=False, nullable=False)
    picture = db.Column(db.Text)
    picture_filename = db.Column(db.String(255))
    birthdate = db.Column(db.Date)
    title = db.Column(db.String(255))
    origin = db.Column(db.String(255))

    _orgs = []
    _org_ids = []

    user_memberships = db.relationship(
        'OrganizationMembership',
        # backref='user_memberships',
        lazy='subquery',
        back_populates="user",
    )

    user_memberships_dyn = db.relationship(
        'OrganizationMembership',
        lazy='dynamic',
    )

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
        password_errors = check_password_quality(password)
        if password_errors:
            raise AttributeError(password_errors)
        self._password = generate_password_hash(
            password, method='pbkdf2:sha512:100001', salt_length=32)

    def check_password(self, password):
        return check_password_hash(self._password, password)

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, email):
        if not validate_email(email):
            raise AttributeError(email, 'seems not to be valid')
        user = User.query.filter_by(_email=email).first()
        if user:
            raise AttributeError(email, 'duplicate email')
        self._email = email

    @classmethod
    def authenticate(cls, email, password):
        user = cls.query.filter(cls._email == email).first()
        if user:
            authenticated = user.check_password(password)
            # user has to be 'OrgAdmin' for at least one organisation
            orgs = user.get_organization_memberships()
            if orgs == []:
                authenticated = False
        else:
            authenticated = False
        return user, authenticated

    @classmethod
    def reset_password_send_email(cls, email):
        user = cls.query.filter(cls._email == email).first()
        if user:
            orgs = user.get_organization_memberships()
            if orgs == []:
                return False
            password = binascii.hexlify(os.urandom(random.randint(
                6, 8))).decode('ascii') + 'aB1$'
            user.password = password
            send_email(
                'energy-cert account', [user.email],
                'auth/email/ec_reset_password',
                user=user,
                new_password=password)
            db.session.add(user)
            db.session.commit()
            return password
        return False

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
                key_derivation='hmac', digest_method=hashlib.sha256))
        return s.dumps(data)

    def generate_reset_token(self, expiry=900):
        """Generate a JSON Web Signature that will be used to reset customer's
        password. For details see
        :meth:`itsdangerous.JSONWebSignatureSerializer.dumps`

        :param expiry: Token expiration time (seconds)
        :return:
        """
        s = TimedJSONWebSignatureSerializer(current_app.config['SECRET_KEY'],
                                            expiry)
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
            user = User(
                name=name,
                email=email,
                password='e9c9525ef737',
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

    def may_handle_user(self, user):
        """checks if the user object it is called on
           (which MUST be an OrgAdmin)
            may manipulate the user of the parameter list
        """
        for um in user.user_memberships:
            if um.organization_id in self._org_ids:
                return True
        return False

    def mark_as_deleted(self):
        self.deleted = 1
        self.ts_deleted = datetime.datetime.utcnow()
        self.email = str(time.time()) + self.email
        db.session.add(self)
        for um in self.user_memberships:
            um.mark_as_deleted(delete_last_membership=True)

    def may_handle_organization(self, org):
        """checks if the user object it is called on
           (which MUST be an OrgAdmin)
            may manipulate the organization of the parameter list
        """
        self.get_organization_memberships()
        if org.id in self._org_ids:
            return True
        return False

    def _org_tree_iterator(self, org_id):
        sub_orgs = Organization.query.filter_by(parent_org_id=org_id)
        for sub_org in sub_orgs:
            # print(sub_org.full_name + str(sub_org.id))
            self._orgs.append(sub_org.organization_memberships)
            self._org_ids.append(sub_org.id)
            self._org_tree_iterator(sub_org.id)

    def get_organization_memberships(self):
        """ returns a list of OrganizationMembership records"""
        """ self MUST be a logged in admin, we find all nodes (and subnodes)
            where the user is admin an return ALL memeberships of those nodes
            in the org tree """
        # there must be a better way to write this
        admin_role = MembershipRole.query.filter_by(name='OrgAdmin').first()
        orgs_admins = OrganizationMembership.query.filter_by(
            user_id=self.id, membership_role_id=admin_role.id).all()

        if (not orgs_admins):
            return []

        self._orgs = [orgs_admins]
        self._org_ids = [org.organization.id for org in orgs_admins]

        # find all orgs where the org.id is the parent_org_id recursivly
        #  for org in orgs_admin:
        for oa in orgs_admins:
            self._org_tree_iterator(oa.organization_id)
        return OrganizationMembership.query.filter(
            OrganizationMembership.organization_id.in_(self._org_ids))

    def get_organizations(self):
        """returns a list of Organization records"""
        self.get_organization_memberships()
        if not self._org_ids:
            return []
        return Organization.query.filter(Organization.id.in_(self._org_ids))

    def get_users(self):
        """returns a list of unique User records"""
        oms = self.get_organization_memberships()
        # for om in oms:
        users = []
        ud = {}
        for om in oms:
            if om.user.id not in ud:
                if om.user.deleted != 1:
                    users.append(om.user)
                ud[om.user.id] = 1
        return users

    def get_memberships(self):
        """returns all memeberships for user"""
        return self.user_memberships


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
        db.Integer, db.ForeignKey('emails.id'), primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('organizations.id'), primary_key=True)
    #: Mark customer portal access for this email
    cp = db.Column('cp_access', db.Boolean(), default=False, doc='CP access')
    #: Functional mailbox marker
    fmb = db.Column(db.Boolean(), default=False, doc='Functional mailbox')
    organization = db.relationship(
        'Organization',
        backref=db.backref('contact_emails', cascade='all, delete-orphan'))
    email_ = db.relationship('Email')
    email = association_proxy(
        'email_', 'email', creator=lambda eml: Email(email=eml))

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

    __mapper_args__ = {'order_by': desc(id)}

    @staticmethod
    def __insert_defaults():
        """Insert sample organization groups"""
        groups = [{
            'name': 'Constituents',
            'color': '#0033CC'
        }, {
            'name': 'National CERTs',
            'color': '#AF2018'
        }, {
            'name': 'Partners',
            'color': '#00FF00'
        }]
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
                  'mail_template', 'mail_times', 'group_id', 'group',
                  'contact_emails', 'display_name', 'parent_org_id')
    query_class = FilteredQuery
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column('organization_group_id', db.Integer,
                         db.ForeignKey(
                             'organization_groups.id', name='fk_org_group_id'))
    is_sla = db.Column(db.Boolean, default=True)
    abbreviation = db.Column(db.String(255), index=True)
    # this is the ID field from AH wiki
    # ("{0:02d}".format(9)
    # we are keeping it for compatibility with the Excel sheets
    old_ID = db.Column(db.String(5))
    full_name = db.Column(db.String(255))
    display_name = db.Column(db.String(255))
    mail_template = db.Column(db.String(50), default='EnglishReport')
    # send emails this many seconds apart
    mail_times = db.Column(db.Integer, default=3600)
    ts_deleted = db.Column(db.DateTime)
    deleted = db.Column(db.Integer, default=0)

    parent_org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    child_organizations = db.relationship('Organization')
    parent_org = db.relationship('Organization', remote_side=[id])

    organization_memberships = db.relationship(
        'OrganizationMembership', backref='orgs_for_user')

    group = db.relationship(
        'OrganizationGroup', uselist=False, foreign_keys=[group_id])
    ip_ranges_ = db.relationship(
        'IpRange',
        cascade='all, delete-orphan',
        primaryjoin="and_(IpRange.organization_id == Organization.id, "
        "IpRange.deleted == 0)",
    )
    ip_ranges = association_proxy(
        'ip_ranges_', 'ip_range', creator=lambda r: IpRange(ip_range=r))
    abuse_emails_ = db.relationship(
        "Email",
        secondary=lambda: emails_organizations,
        secondaryjoin=db.and_(Email.id == emails_organizations.c.email_id,
                              Email.deleted == 0))
    #: Abuse e-mails are read by machines
    abuse_emails = association_proxy(
        'abuse_emails_', 'email', creator=lambda eml: Email(email=eml))

    #: Contact e-mails are used by humans
    contact_emails = association_proxy('contact_emails', 'email')

    asns_ = db.relationship(
        'Asn',
        cascade='all, delete-orphan',
        primaryjoin="and_(Asn.organization_id == Organization.id,"
        "Asn.deleted == 0)")
    asns = association_proxy('asns_', 'asn', creator=lambda asn: Asn(asn=asn))
    fqdns_ = db.relationship('Fqdn', cascade='all, delete-orphan')
    fqdns = association_proxy(
        'fqdns_', 'fqdn', creator=lambda fqdn: Fqdn(fqdn=fqdn))

    users = db.relationship(
        'User', backref=db.backref('organizations'), lazy='dynamic')

    __mapper_args__ = {'order_by': abbreviation}

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
                'Organization {} is missing full name...'.format(customer[0]))
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

    def mark_as_deleted(self):
        self.deleted = 1
        self.ts_deleted = datetime.datetime.utcnow()

    # STUB
    def has_child_organizations(self):
        return True

    # STUB
    def can_be_deleted(self):
        # records
        return True

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
    request_method = db.Column(
        db.Enum('GET', 'POST', 'PUT', name='httpverb'), default='GET')
    request_data = db.Column(db.Text)
    check_string = db.Column(db.Text)
    test_type = db.Column(
        db.Enum('request', name='test_type_enum'), default='request')
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
        'Tag',
        secondary=tags_vulnerabilities,
        backref=db.backref('vulnerabilities'))
    types = association_proxy('labels_', 'name', creator=lambda l: Tag(name=l))
    __mapper_args__ = {'order_by': desc(id)}


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
    is_sla = db.Column(db.Boolean, default=0)
    deleted = db.Column(db.Integer, default=0)

    deliverable_ = db.relationship(
        'Deliverable',
        uselist=False,
        foreign_keys=[deliverable_id],
        backref=db.backref('files'))
    type = association_proxy('deliverable_', 'name')

    __mapper_args__ = {'order_by': desc(id)}


class Task(Model):
    __tablename__ = 'tasks_taskmeta'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(255), nullable=True, unique=True)
    status = db.Column(db.String(50), nullable=True)
    result = db.Column(db.LargeBinary, nullable=True)
    date_done = db.Column(db.DateTime, nullable=True)
    traceback = db.Column(db.Text, nullable=True)


class TaskGroup(Model):
    __tablename__ = 'tasks_groupmeta'
    id = db.Column(db.Integer, primary_key=True)
    taskset_id = db.Column(db.String(255), nullable=True, unique=True)
    result = db.Column(db.LargeBinary, nullable=True)
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
    bot_type_id = db.Column(db.Integer, db.ForeignKey('ah_bot_types.id'))
    name = db.Column(db.String(30))
    description = db.Column(db.String(255))

    type = db.relationship(
        'AHBotType', uselist=False, foreign_keys=[bot_type_id])


class AHStartupConfig(Model, SerializerMixin):
    __tablename__ = 'ah_startup_configs'
    # belongsTo AbuseHelperBot
    # hasMany AbuseHelperStartupParam
    # HABTM AbuseHelperStartupTemplate
    id = db.Column(db.Integer, primary_key=True)
    ah_bot_id = db.Column(db.Integer, db.ForeignKey('ah_bots.id'))
    enabled = db.Column(db.Boolean(), default=False)
    #: python module or PATH
    module = db.Column(db.String(255))
    state = db.Column(db.Boolean(), default=False, nullable=True)
    pid = db.Column(db.Integer, nullable=True)
    started = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    stopped = db.Column(
        db.DateTime, nullable=True, onupdate=datetime.datetime.utcnow)
    ah_bot = db.relationship('AHBot', foreign_keys=[ah_bot_id])


class AHStartupConfigParam(Model, SerializerMixin):
    __tablename__ = 'ah_startup_config_params'
    # belongsTo AbuseHelperStartupConfig
    id = db.Column(db.Integer, primary_key=True)
    ah_startup_config_id = db.Column(db.Integer,
                                     db.ForeignKey('ah_startup_configs.id'))
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(100), nullable=False)
    ah_startup_config = db.relationship(
        'AHStartupConfig',
        foreign_keys=[ah_startup_config_id],
        backref=db.backref('params'))


class AHRuntimeConfig(Model, SerializerMixin):
    __tablename__ = 'ah_runtime_configs'
    # belongsTo AbuseHelperBot
    # hasMany AbuseHelperRuntimeConfigParam
    id = db.Column(db.Integer, primary_key=True)
    alias = db.Column(db.String(2))
    ah_bot_id = db.Column(db.Integer, db.ForeignKey('ah_bots.id'))
    ah_bot = db.relationship('AHBot', foreign_keys=[ah_bot_id])


class AHRuntimeConfigParam(Model, SerializerMixin):
    __tablename__ = 'ah_runtime_config_params'
    # belongsTo AbuseHelperRuntimeConfig
    id = db.Column(db.Integer, primary_key=True)
    ah_runtime_config_id = db.Column(db.Integer,
                                     db.ForeignKey('ah_runtime_configs.id'))
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(100), nullable=False)
    ah_runtime_config = db.relationship(
        'AHRuntimeConfig',
        foreign_keys=[ah_runtime_config_id],
        backref=db.backref('params'))


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
        db.Integer, db.ForeignKey('samples.id'), nullable=True)
    #: Submitted filename
    filename = db.Column(db.Text, nullable=False)
    md5 = db.Column(db.String(32), nullable=False)
    sha1 = db.Column(db.String(40), nullable=False)
    #: SHA-256 sum of file contents
    sha256 = db.Column(db.String(64), nullable=False)
    sha512 = db.Column(db.String(128), nullable=False)
    #: Context triggered piecewise hash
    ctph = db.Column(
        db.Text, nullable=False, doc='Context triggered piecewise hash')
    infected = db.Column(db.Integer, default=0)
    deleted = db.Column(db.Integer, default=0)

    __mapper_args__ = {'order_by': desc(id)}

    reports = db.relationship('Report')
    user = db.relationship(
        'User',
        uselist=False,
        foreign_keys=[user_id],
        backref=db.backref('samples'))
    parent = db.relationship(
        'Sample', backref=db.backref('children'), remote_side=[id])


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
    type = association_proxy('type_', 'name')


class Contact(Model):
    """Not used"""
    __tablename__ = 'contacts'
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    name = db.Column(db.String(255), nullable=False)
    position = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    deleted = db.Column(db.Integer, default=0)


class Country(Model, SerializerMixin):
    __tablename__ = 'countries'
    __public__ = ('id', 'cc', 'name')
    query_class = FilteredQuery
    cc = db.Column(db.String(255), nullable=False, unique=True)
    name = db.Column(db.String(255), nullable=False)
    id = db.Column(db.Integer, primary_key=True)
    deleted = db.Column(db.Integer, default=0)
    users_for_country = db.relationship(
        'OrganizationMembership', back_populates='country')

    @staticmethod
    def __insert_defaults():
        with open('install/iso_3166_2_countries.csv') as csvfile:
            data = csv.reader(csvfile, delimiter=',')
            data = list(data)
            for r in data[2:]:
                #    print(r[1], r[10])
                country = Country.query.filter_by(cc=r[10]).first()
                if country is None:
                    country = Country(cc=r[10], name=r[1])
                    db.session.add(country)
            db.session.commit()


class MembershipRole(Model, SerializerMixin):
    __tablename__ = 'membership_roles'
    __public__ = ('id', 'name', 'display_name')
    query_class = FilteredQuery
    name = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(255), nullable=False)
    id = db.Column(db.Integer, primary_key=True)
    deleted = db.Column(db.Integer, default=0)
    users_for_role = db.relationship(
        'OrganizationMembership', back_populates='membership_role')

    __mapper_args__ = {'order_by': name}

    @staticmethod
    def __insert_defaults():
        # this role has to exist
        roles = [['OrgAdmin', 'Administrator Organisation']]
        default_roles = [
            ['tech-c', 'Domain Technical Contact (tech-c)'],
            ['abuse-c', 'Domain Abuse Contact (abuse-c)'],
            ['billing-c', 'Domain Billing Contact (billing-c)'],
            ['admin-c', 'Domain Administrative Contact (admin-c)'],
            ['CISO', 'CISO'],
            ['private', 'Private'],
        ]

        try:
            stream = open('install/roles.yaml')
            data_loaded = yaml.load(stream)
            for role in data_loaded:
                roles.append([role['name'], role['display_name']])
        except IOError:
            for role in default_roles:
                roles.append(role)

        for r in roles:
            role = MembershipRole.query.filter_by(name=r[0]).first()

            if role is None:
                role = MembershipRole(name=r[0], display_name=r[1])
                db.session.add(role)
        db.session.commit()

        def __repr__(self):
            return '{} #{}'.format(self.__class__.__name__, self.name)


class OrganizationMembership(Model, SerializerMixin):
    __tablename__ = 'organization_memberships'
    __public__ = ('id', 'user_id', 'organization_id', 'street', 'zip', 'city',
                  'country', 'comment', 'email', 'phone', 'mobile',
                  'membership_role_id', 'pgp_key_id', 'pgp_key_fingerprint',
                  'pgp_key', 'smime', 'country_id', 'coc', 'coc_filename',
                  'smime_filename', 'sms_alerting')

    query_class = FilteredQuery
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship(
        "User", back_populates="user_memberships", lazy='subquery')
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    organization = db.relationship("Organization")
    membership_role_id = db.Column(db.Integer,
                                   db.ForeignKey('membership_roles.id'))
    membership_role = db.relationship("MembershipRole")
    street = db.Column(db.String(255))
    zip = db.Column(db.String(25))
    city = db.Column(db.String(255))
    # country = db.Column(db.String(50))  # should be a lookup table
    country_id = db.Column(db.Integer, db.ForeignKey('countries.id'))
    country = db.relationship("Country")
    comment = db.Column(db.String(255))
    _email = db.Column('email', db.String(255))
    _phone = db.Column('phone', db.String(255))
    _mobile = db.Column('mobile', db.String(255))
    deleted = db.Column(db.Integer, default=0)
    ts_deleted = db.Column(db.DateTime)
    pgp_key_id = db.Column(db.String(255))
    pgp_key_fingerprint = db.Column(db.String(255))
    pgp_key = db.Column(db.Text)
    smime = db.Column(db.Text)
    smime_filename = db.Column(db.String(255))
    coc = db.Column(db.Text)
    coc_filename = db.Column(db.String(255))
    _sms_alerting = db.Column('sms_alerting', db.Integer, default=0)

    def mark_as_deleted(self, delete_last_membership=False):
        mc = self.user.user_memberships_dyn.filter_by(deleted=0).count()
        if mc == 1 and delete_last_membership is False:
            raise AttributeError('Last membership may not be deleted')
        self.deleted = 1
        self.ts_deleted = datetime.datetime.utcnow()

    @property
    def sms_alerting(self):
        return self._sms_alerting

    @sms_alerting.setter
    def sms_alerting(self, sms_alerting):
        # if sms_alerting == 1 and not self._mobile:
        #     db.session.rollback()
        #     raise AttributeError( \
        # 'if sms_alerting is set mobile number also has to be set')
        self._sms_alerting = sms_alerting

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, email):
        if not validate_email(email):
            db.session.rollback()
            raise AttributeError(email, 'seems not to be valid')
        self._email = email

    @property
    def phone(self):
        return self._phone

    @phone.setter
    def phone(self, phone):
        try:
            if not phone:
                phone = None
            else:
                phonenumbers.parse(phone, None)
        except phonenumbers.phonenumberutil.NumberParseException as err:
            db.session.rollback()
            raise AttributeError(phone, 'seems not to be valid:', err)
        self._phone = phone

    @property
    def mobile(self):
        return self._mobile

    @mobile.setter
    def mobile(self, mobile):
        try:
            if not mobile:
                mobile = None
            else:
                phonenumbers.parse(mobile, None)
        except phonenumbers.phonenumberutil.NumberParseException as err:
            db.session.rollback()
            raise AttributeError(mobile, 'seems not to be valid:', err)
        self._mobile = mobile


""" watch for insert on Org Memberships """


def org_mem_listerner(mapper, connection, org_mem):
    if org_mem.membership_role and org_mem.membership_role.name == 'OrgAdmin':
        password = binascii.hexlify(os.urandom(random.randint(
            6, 8))).decode('ascii') + 'Ba1%'
        org_mem.user.password = password
        send_email(
            'energy-cert account', [org_mem.user.email],
            'auth/email/ec_activate_account',
            org_mem=org_mem,
            new_password=password)


event.listen(
    OrganizationMembership,
    'after_insert',
    org_mem_listerner,
    retval=True,
    propagate=True)


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
    print("*****", max_age)
    # Decrypt the Security Token, data = [username, hashpass, id]
    s = URLSafeTimedSerializer(
        current_app.config['SECRET_KEY'],
        salt='user-auth',
        signer_kwargs=dict(
            key_derivation='hmac', digest_method=hashlib.sha256))
    from pprint import pprint
    try:
        (data, timestamp) = s.loads(
            token, max_age=max_age, return_timestamp=True)
        pprint(data)
        pprint(timestamp)
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
            current_app.log.warn("{} logged in using URL parameter".format(
                user.name))
            return user

    # next, try to login using an API key
    api_key = request.headers.get('API-Authorization')
    if api_key:
        user = User.query.filter_by(api_key=api_key).first()
        if user:
            return user

    # finally, return None if both methods did not login the user
    return None

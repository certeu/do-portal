import os
# import socket
# my_ips = socket.gethostbyname_ex(socket.gethostname())
from datetime import timedelta
import jsonschema
import ipaddress
import re

basedir = os.path.abspath(os.path.dirname(__file__))


@jsonschema.FormatChecker.cls_checks('cidr')
def _validate_cidr_format(cidr):
    """Validate CIDR IP range
    :param str cidr:
    :return:
    :rtype: bool
    """
    try:
        ipaddress.ip_network(cidr, strict=False)
    except (ValueError, ipaddress.AddressValueError,
            ipaddress.NetmaskValueError):
        return False
    if '/' not in cidr:
        return False
    if re.search('\s', cidr):
        return False
    return True


@jsonschema.FormatChecker.cls_checks('gpg_pubkey')
def _validate_gpg_pubkey_format(pubkey):
    """Validate GPG public key format
    :param str pubkey: ASCII armored public key
    :return:
    :rtype: bool
    : ref:: https://stackoverflow.com/questions/24238743/flask-decorator-to-
    verify-json-and-json-schema
    """
    prefix = '-----BEGIN PGP PUBLIC KEY BLOCK-----'
    suffix = '-----END PGP PUBLIC KEY BLOCK-----'
    if not pubkey.startswith(prefix) and not pubkey.endswith(suffix):
        return False
    return True


class Config:
    """Main configuration class
    Options here are overwritten by child configuration.
    Configuration options can also be overwritten by setting the
    ``DO_LOCAL_CONFIG`` envinronment variable to a configuration file.
    """
    #: Secret key
    SECRET_KEY = os.environ.get('SECRET_KEY')
    #: CSRF secret key
    WTF_CSRF_SECRET_KEY = ''

    LOGGER_NAME = 'doportal'

    #: SQL settings
    SQLALCHEMY_DATABASE_URI = ''
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    #: Root PATH of deployment
    ROOT = os.path.dirname(os.path.abspath(__file__))
    APP_ROOT = os.path.join(ROOT, 'app')
    #: Web root
    APP_STATIC = os.path.join(APP_ROOT, 'static')
    APP_DATA = os.path.join(APP_STATIC, 'data')
    #: Uploaded files will be stored here
    APP_UPLOADS = os.path.join(APP_DATA, 'uploads')
    #: Uploaded malware samples will be store here.
    #: In production this is on a different disk mounted with noexec options
    APP_UPLOADS_SAMPLES = os.path.join(APP_DATA, 'samples')
    APP_UPLOADS_SAMPLES_TMP = os.path.join(APP_UPLOADS_SAMPLES, 'tmp')
    LOG_DIR = os.path.join(ROOT, 'logs')
    MISC_DIR = os.path.join(ROOT, 'misc')
    MIGRATIONS_DIR = os.path.join(MISC_DIR, 'migrations')
    JSONSCHEMA_DIR = os.path.join(MISC_DIR, 'json_schemas')
    JSONSCHEMA_FORMAT_CHECKER = jsonschema.FormatChecker()

    #: Analysis report files location
    #: Big report files are stored here
    REPORTS_PATH = os.path.join(APP_STATIC, 'reports')
    #: Antivirus scan reports
    REPORTS_AV_PATH = os.path.join(REPORTS_PATH, 'av')
    #: Static analysis reports
    REPORTS_STATIC_PATH = os.path.join(REPORTS_PATH, 'static')
    #: Dynamic analysis reports
    REPORTS_DYNAMIC_PATH = os.path.join(REPORTS_PATH, 'dynamic')

    ADMINS = []

    #: The number of items per page used for paginated data
    ITEMS_PER_PAGE = 20

    #: Email server
    MAIL_SERVER = '127.0.0.1'
    #: Email port
    MAIL_PORT = 25  # 465
    #: Use TLS
    MAIL_USE_TLS = False
    #: Use SSL
    MAIL_USE_SSL = False
    #: E-mail useranme
    MAIL_USERNAME = ''
    #: E-mail password
    MAIL_PASSWORD = None
    MAIL_DEFAULT_SENDER = ''

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    REMEMBER_COOKIE_DURATION = timedelta(days=2)
    REMEMBER_COOKIE_NAME = 'rm'
    #: Client sessions will be store here
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True

    #: RabbitMQ broker for Celery
    #: Can also be passed from ENV as CELERY_BROKER_URL
    BROKER_URL = ''
    #: The backend used to store task results
    CELERY_BACKEND = ''
    CELERY_RESULT_DB_TABLENAMES = {
        'task': 'tasks_taskmeta',
        'group': 'tasks_groupmeta'
    }
    #: Accepted content
    CELERY_ACCEPT_CONTENT = ['pickle', 'json']
    #: Modules that are expected to use Celery
    CELERY_IMPORTS = ['app.tasks']
    #: http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html
    #: Scheduled tasks require beat running:
    #: venv/bin/celery beat -A tasks.celery -l debug
    CELERYBEAT_SCHEDULE = {}
    CELERY_TIMEZONE = 'Europe/Brussels'

    #: Mailman API version to use (3.0 or 3.1)
    MAILMAN_REST_API_VERSION = '3.1'  # 3.0, 3.1
    #: Mailman API base URL
    MAILMAN_REST_API_URL = ''
    #: Mailman API username
    MAILMAN_REST_API_USER = ''
    #: Mailman API password
    MAILMAN_REST_API_PASS = ''

    MAILMAN_DOMAIN = ''
    MAILMAN_ADMIN = ''

    #: Syslog host
    SYSLOG_HOST = None
    #: Syslog port
    SYSLOG_PORT = None

    #: Use Lightweight Directory Access Protocol (LDAP) for authentication
    LDAP_AUTH_ENABLED = False
    #: LDAP host
    LDAP_HOST = ''
    #: LDAP base distinguished name
    LDAP_BASE_DN = ''
    #: LDAP user distinguished name
    LDAP_USER_DN = ''
    LDAP_SEARCH_FOR_GROUPS = False
    #: LDAP bind user distinguished name
    LDAP_BIND_USER_DN = ''
    #: Service account password used for bind searching
    LDAP_BIND_USER_PASSWORD = ''
    LDAP_USER_LOGIN_ATTR = ''

    #: GnuPG home directoy
    GPG_HOME = ""
    #: Full PATH of the gpg binary
    GPG_BINARY = "/usr/bin/gpg"
    #: GnuPG keyservers to use.
    #: First keyserver is considered local, second one public.
    GPG_KEYSERVERS = []
    #: Extra option to pass to the gpg binary
    GPG_OPTIONS = ['--batch', '--no-tty', '--yes', '--keyserver-options',
                   'no-honor-keyserver-url,timeout=3']
    #: Verbose output of GPG commands
    GPG_VERBOSE = True

    #: Enable BOSH connections
    BOSH_ENABLED = False
    #: Full URL of the BOSH service URL. It will be passed to clients.
    BOSH_SERVICE = ''
    CP_BOSH_SERVICE = ''
    #: Jabber ID. Account needs to be present on the AbuseHelper server.
    JID = ''  # append customer resource
    #: Jabber password
    JPASS = ''
    #: List of rooms to join
    ROOMS = []
    CP_ROOMS = []
    #: Full PATH to multi AV configuration file
    AVSCAN_CONFIG = ''

    #: VxStream Sandbox API base URL
    REST_CLIENT_VX_BASE_URL = None
    #: VxStream Sandbox API key
    REST_CLIENT_VX_API_KEY = None
    #: VxStream Sandbox API secret
    REST_CLIENT_VX_API_SECRET = None
    #: VxStream default environment
    REST_CLIENT_VX_DEFAULT_ENV = 1

    #: Nessus appscan credentials
    REST_CLIENT_NESSUS_BASE_URL = None
    REST_CLIENT_NESSUS_API_KEY = None
    REST_CLIENT_NESSUS_API_SECRET = None
    #: Nessus templates UUIDs available for customers
    REST_CLIENT_NESSUS_TEMPLATES = None

    #: FireEye AX credentials
    REST_CLIENT_FIREEYE_BASE_URL = None
    REST_CLIENT_FIREEYE_USERNAME = None
    REST_CLIENT_FIREEYE_API_SECRET = None

    #: Customer portal web root URL
    CP_WEB_ROOT = ''

    #: Password user for archiving infected files
    INFECTED_PASSWD = 'infected'

    PROXIES = {}


class DevelConfig(Config):
    DEBUG = True
    TRAP_BAD_REQUEST_ERRORS = True
    ASSETS_DEBUG = True
    WTF_CSRF_ENABLED = False
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY') or 'devkey'
    SQLALCHEMY_DATABASE_URI = ''
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class TestingConfig(Config):
    # DEBUG = True
    TESTING = True
    SERVER_NAME = 'localhost'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'do-testing'
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = \
        'postgresql://dope_test:dope_test@localhost:5432/dope_test'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BROKER_URL = ''
    CELERY_BACKEND = ''
    CELERY_ALWAYS_EAGER = True
    LDAP_AUTH_ENABLED = True
    BOSH_ENABLED = True
    MAIL_DEFAULT_SENDER = 'testing@test.at'


class ProductionConfig(Config):
    JSON_AS_ASCII = False
    JSONIFY_PRETTYPRINT_REGULAR = False
    CSRF_ENABLED = True
    FILE_LOGGING = False
    SMTP_LOGGING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False


config = {
    'devel': DevelConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelConfig
}

import os
import logging
from celery import Celery
from config import config, Config
from flask import g
from flask_gnupg import GPG
from flask_jsonschema import JsonSchema
from flask_ldap3_login import LDAP3LoginManager
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_tinyclients.nessus import Nessus
from flask_tinyclients.vxstream import VxStream
from flask_tinyclients.fireeye import FireEye
from app.core import FlaskApi, ApiException
from app.utils import JSONEncoder
from .utils.mixins import Anonymous

version_ = (1, 8, 0)
__version__ = '.'.join(map(str, version_[0:2]))
__release__ = '.'.join(map(str, version_))


db = SQLAlchemy()
mail = Mail()
login_manager = LoginManager()
celery = Celery(__name__, broker=Config.BROKER_URL)
jsonschema = JsonSchema()
gpg = GPG()
ldap3_manager = LDAP3LoginManager()
migrate = Migrate()
vxstream = VxStream()
nessus = Nessus()
fireeye = FireEye()


def create_app(config_name):
    app = FlaskApi(__name__)
    app.config.from_object(config[config_name])
    if app.config['TESTING']:
        app.config.from_envvar('DO_TESTING_CONFIG', silent=True)
    else:
        app.config.from_envvar('DO_LOCAL_CONFIG', silent=True)
    app.json_encoder = JSONEncoder
    app.log = app.logger

    _audit_log = logging.getLogger('doaudit')
    rhandler = logging.handlers.RotatingFileHandler(
        os.path.join(app.config['LOG_DIR'], 'audit.log'),
        mode="a+",
        maxBytes=10 * 1024 * 1024,
        backupCount=5)
    rhandler.setFormatter(
        logging.Formatter(
            '%(asctime)s %(name)s %(levelname)s: %(message)s',
            '%b %d %H:%M:%S'))
    rhandler.setLevel(logging.INFO)
    _audit_log.addHandler(rhandler)
    if app.config['SYSLOG_HOST']:
        shandler = logging.handlers.SysLogHandler(
            address=(app.config['SYSLOG_HOST'], app.config['SYSLOG_PORT'])
        )
        shandler.setFormatter(
            logging.Formatter('%(message)s')
        )
        shandler.setLevel(logging.INFO)
        _audit_log.addHandler(shandler)

    _audit_log.setLevel(logging.INFO)
    app.audit_log = _audit_log

    if not app.config['DEBUG'] and not app.config['TESTING']:
        # configure logging for production
        # email errors to the administrators
        if app.config.get('MAIL_ERROR_RECIPIENT') is not None:

            credentials = None
            secure = None
            if app.config.get('MAIL_USERNAME') is not None:
                credentials = (
                    app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                if app.config['MAIL_USE_TLS'] is not None:
                    secure = ()
            mail_handler = logging.handlers.SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr=app.config['MAIL_DEFAULT_SENDER'],
                toaddrs=[app.config['MAIL_ERROR_RECIPIENT']],
                subject='[DO Portal] Application Error',
                credentials=credentials,
                secure=secure)
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)

    @app.errorhandler(ApiException)
    def api_error_handler(err):
        return err.to_response()

    init_extensions(app)
    init_routes(app)

    @app.before_request
    def before_request():
        """Global ``before_request``.
        With :class:`flask.g` all requests will have access to the
        logged in user, even inside templates.

        :return:
        """
        g.user = current_user
    return app


def init_extensions(app):
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.anonymous_user = Anonymous
    celery.conf.update(app.config)
    jsonschema.init_app(app)
    gpg.init_app(app)
    ldap3_manager.init_app(app)
    migrate.init_app(app, db, directory=app.config['MIGRATIONS_DIR'])
    vxstream.init_app(app)
    nessus.init_app(app)
    fireeye.init_app(app)


def init_routes(app):
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/1.0')

    from .cp import cp as cp_blueprint
    app.register_blueprint(cp_blueprint, url_prefix='/cp/1.0')

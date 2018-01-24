# -*- coding: utf-8 -*-
"""
    For documentation on the available API endpoints please see :ref:`rest_api`
"""
import json
import datetime
from flask import Flask, Blueprint, current_app, request
from flask_login import current_user
from app.utils import _HTTP_METHOD_TO_AUDIT_MAP, addslashes
from ..api.decorators import json_response, rate_limit, crossdomain
from ldap3.core.exceptions import LDAPException
auth = Blueprint('auth', __name__)
from . import routes  # noqa
from . import errors  # noqa


@auth.before_request
@rate_limit(10, 1)
def before_auth_request():
    if 'application/json' not in request.accept_mimetypes:
        return errors.not_acceptable()


@auth.errorhandler(LDAPException)
@json_response
def ldap_error(e):
    return {'message': str(e)}, 500

app = Flask(__name__)
app.config.from_envvar('DO_LOCAL_CONFIG')
if 'CP_SERVER' in app.config:
    cp_server = app.config['CP_SERVER']
else:
    cp_server = 'http://127.0.0.1:5002'

@auth.after_request
@crossdomain(origin=cp_server,
             headers='Content-Type, Accept, Authorization, Origin, '
                     'CP-TOTP-Required')
def auth_audit_log(response):
    """On deployment remove the ``crossdomain`` decorator"""
    try:
        jdata = json.loads(request.data.decode())
        if 'password' in jdata:
            jdata['password'] = '*********'
        jdata_str = json.dumps(jdata)
    except ValueError:
        jdata_str = ''
    kwargs = {
        'module': auth.name,
        'user': current_user.name,
        'email': current_user.email,
        'action': _HTTP_METHOD_TO_AUDIT_MAP[request.method.lower()],
        'data': addslashes(jdata_str),
        'url': request.url,
        'endpoint': request.endpoint,
        'ip': request.remote_addr,
        'status': response.status,
        'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }
    entry = []
    for k, v in kwargs.items():
        entry.append('{0!s}="{1!s}"'.format(k, v))
    entry = ' '.join(entry)
    current_app.audit_log.info('{0!s}'.format(entry))
    return response

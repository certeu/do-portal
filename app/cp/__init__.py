"""
    Customer Portal endpoints package
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This package holds all endpoints that will be exposed to customers
"""
import json
import datetime
from flask import Flask, Blueprint
from flask import current_app, request, g
from flask_login import login_required, decode_cookie
from app.utils import addslashes, _HTTP_METHOD_TO_AUDIT_MAP
from app.api.decorators import rate_limit, crossdomain

version_ = (0, 6, 5)
__version__ = '.'.join(map(str, version_[0:2]))
__release__ = '.'.join(map(str, version_))

cp = Blueprint('cp', __name__)
from . import routes  # noqa
from . import organizations, vulnerabilities, deliverable_files, fqdns  # noqa
from . import membership_roles, countries, organization_memberships, users  # noqa
from .analysis import av, static, vxstream, fireeye  # noqa
from . import errors  # noqa


app = Flask(__name__)
app.config.from_envvar('DO_LOCAL_CONFIG')
if 'CP_SERVER' in app.config:
    cp_server = app.config['CP_SERVER']
else:
    cp_server = 'http://127.0.0.1:5002'

@cp.before_request
@rate_limit(30, 1)
@login_required
def before_api_request():
    if 'application/json' not in request.accept_mimetypes:
        return errors.not_acceptable()


@cp.after_request
@crossdomain(origin=cp_server)
def cp_audit_log(response):
    """Saves information about the request in the ``audit_log``

    :param response: Server :class:`~flask.Response`
    :return: :class:`~flask.Response`
    """
    try:
        jdata = json.loads(request.data.decode())
        if 'password' in jdata:
            jdata['password'] = '*********'
        jdata_str = json.dumps(jdata)
    except ValueError:
        jdata_str = ''

    kwargs = {
        'module': cp.name,
        'user': g.user.name,
        'email': g.user.email,
        'action': _HTTP_METHOD_TO_AUDIT_MAP[request.method.lower()],
        'data': addslashes(jdata_str),
        'url': request.url,
        'endpoint': request.endpoint,
        'ip': request.remote_addr,
        'status': response.status,
        'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }
    if not request.view_args and request.method.lower() == 'put':
        kwargs['action'] = _HTTP_METHOD_TO_AUDIT_MAP['post']
    entry = []
    for k, v in kwargs.items():
        entry.append('{0!s}="{1!s}"'.format(k, v))
    entry = ' '.join(entry)
    current_app.audit_log.info('{0!s}'.format(entry))
    return response

"""
    https://en.wikipedia.org/wiki/Representational_state_transfer
"""
import datetime

from flask import Blueprint, request, current_app
from flask_login import login_required, current_user

api = Blueprint('api', __name__)
from . import routes  # noqa
from . import organizations, organization_groups, ip_ranges, lists  # noqa
from . import asns, emails, fqdns, gnupg_keys, samples  # noqa
from . import deliverables, deliverable_files, reports, tags  # noqa
from . import vulnerabilities  # noqa
from .analysis import av, static, vxstream, nessus, fireeye  # noqa
from . import errors
from .decorators import rate_limit, admin_required
from app.utils import addslashes, _HTTP_METHOD_TO_AUDIT_MAP


@api.before_request
@rate_limit(100, 1)
@login_required
@admin_required
def before_api_request():
    if 'application/json' not in request.accept_mimetypes:
        return errors.not_acceptable()


@api.after_request
def api_audit_log(response):
    """Saves information about the request in the ``audit_log``

    :param response: Server :class:`~flask.Response`
    :return: :class:`~flask.Response`
    """
    kwargs = {
        'module': api.name,
        'user': current_user.name,
        'email': current_user.email,
        'action': _HTTP_METHOD_TO_AUDIT_MAP[request.method.lower()],
        'data': addslashes(request.data.decode()),
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

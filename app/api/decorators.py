"""
Copyright (c) 2014 Miguel Grinberg
Copyright (c) 2015 Alexandru Ciobanu
"""
from datetime import timedelta
import functools
from time import time
from threading import Thread
from werkzeug.wrappers import Response
from flask import jsonify, url_for, request, make_response, current_app
from flask import g, abort
from flask_login import current_user
from app.models import Permission


def json_response(f):
    """A decorator without arguments

    :param func f:
    :return:
    :rtype: func
    """

    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        current_app.log.warn('Using the json_response decorator is deprecated.'
                             'Please use app.core.ApiResponse.')
        # invoke the wrapped function
        rv = f(*args, **kwargs)
        # wrapped function is a redirect
        # return it without doing anything
        if isinstance(rv, Response):
            return rv

        # the wrapped function can return the dictionary alone,
        # or can also include a status code and/or headers.
        # here we separate all these items
        status_or_headers = None
        headers = None
        if isinstance(rv, tuple):
            rv, status_or_headers, headers = rv + (None, ) * (3 - len(rv))
        if isinstance(status_or_headers, (dict, list)):
            headers, status_or_headers = status_or_headers, None

        # if the response was a database model, then convert it to a
        # dictionary
        if not isinstance(rv, dict):
            rv = rv.serialize()

        # generate the JSON response
        rv = jsonify(rv)
        if status_or_headers is not None:
            rv.status_code = status_or_headers
        if headers is not None:
            rv.headers.extend(headers)
        return rv

    return wrapped


def paginate(f=None, *, max_per_page=20, headers_prefix='DO-'):
    """Pagination decorator.
    Generate a paginated response for a resource collection.
    Routes that use this decorator must return a SQLAlchemy query as a
    response.

    :param f: function to be decorated
    :param max_per_page: Items per page
    :param headers_prefix: Prefix for custom headers
    :return: tuple as (response, headers)
    """
    if f is None:
        return functools.partial(
            paginate, max_per_page=max_per_page, headers_prefix=headers_prefix)

    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        page = request.args.get('page', 1, type=int)
        per_page = min(
            request.args.get('per_page', max_per_page, type=int), max_per_page)
        query = f(*args, **kwargs)
        p = query.paginate(page, per_page)
        rv = {'page': page, 'per_page': per_page, 'count': p.total}
        if p.has_prev:
            rv['prev'] = url_for(
                request.endpoint,
                page=p.prev_num,
                per_page=per_page,
                _external=True,
                **kwargs)
        else:
            rv['prev'] = None
        if p.has_next:
            rv['next'] = url_for(
                request.endpoint,
                page=p.next_num,
                per_page=per_page,
                _external=True,
                **kwargs)
        else:
            rv['next'] = None
        rv['first'] = url_for(
            request.endpoint,
            page=1,
            per_page=per_page,
            _external=True,
            **kwargs)
        rv['last'] = url_for(
            request.endpoint,
            page=p.pages,
            per_page=per_page,
            _external=True,
            **kwargs)
        rv['items'] = [item.serialize() for item in p.items]
        headers = {
            headers_prefix + 'Page-Current': page,
            headers_prefix + 'Page-Prev': rv['prev'],
            headers_prefix + 'Page-Next': rv['next'],
            headers_prefix + 'Page-Item-Count': rv['count']
        }
        return rv, headers

    return wrapped


def async(f):
    def wrapper(*args, **kwargs):
        t = Thread(target=f, args=args, kwargs=kwargs)
        t.start()

    return wrapper


_limiter = None


class MemRateLimit(object):
    """Rate limiter that uses a Python dictionary as storage."""

    def __init__(self):
        self.counters = {}

    def is_allowed(self, key, limit, period):
        """Check if the client's request should be allowed, based on the
        hit counter. Returns a 3-element tuple with a True/False result,
        the number of remaining hits in the period, and the time the
        counter resets for the next period.

        :param period:
        :param limit:
        :param key:
        """
        now = int(time())
        begin_period = now // period * period
        end_period = begin_period + period

        self.cleanup(now)
        if key in self.counters:
            self.counters[key]['hits'] += 1
        else:
            self.counters[key] = {'hits': 1, 'reset': end_period}
        allow = True
        remaining = limit - self.counters[key]['hits']
        if remaining < 0:
            remaining = 0
            allow = False
        return allow, remaining, self.counters[key]['reset']

    def cleanup(self, now):
        """Eliminate expired keys."""
        for key, value in list(self.counters.items()):
            if value['reset'] < now:
                del self.counters[key]


def rate_limit(limit, period):
    """Limits the rate at which clients can send requests to 'limit' requests
    per 'period' seconds. Once a client goes over the limit all requests are
    answered with a status code 429 Too Many Requests for the remaining of
    that period.

    :param period:
    :param limit:
    """

    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            # initialize the rate limiter the first time here
            global _limiter
            if _limiter is None:
                _limiter = MemRateLimit()

            # generate a unique key to represent the decorated function and
            # the IP address of the client. Rate limiting counters are
            # maintained on each unique key.
            key = '{0}/{1}'.format(f.__name__, request.remote_addr)
            allowed, remaining, reset = _limiter.is_allowed(key, limit, period)

            # set the rate limit headers in g, so that they are picked up
            # by the after_request handler and attached to the response
            g.headers = {
                'DO-RateLimit-Remaining': str(remaining),
                'DO-RateLimit-Limit': str(limit),
                'DO-RateLimit-Reset': str(reset)
            }

            # if the client went over the limit respond with a 429 status
            # code, else invoke the wrapped function
            if not allowed:
                response = jsonify({
                    'status':
                    429,
                    'error':
                    'too many requests',
                    'message':
                    'You have exceeded your request rate'
                })
                response.status_code = 429
                return response

            # else we let the request through
            return f(*args, **kwargs)

        return wrapped

    return decorator


def api_deprecated(new_endpoint, message='This endpoint is deprecated.'):
    """Decorator that adds a deprecation message for and endpoint.
    Decorated function will not be executed.

    :param new_endpoint: New endpoint to use
    :param message: Warning message
    :return:
    :rtype: func
    """

    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            response = jsonify({
                'message':
                message,
                'endpoint':
                url_for(new_endpoint, _external=True)
            })
            # response = jsonify(rv)
            response.status_code = 301
            response.headers['DO-New-Endpoint'] = \
                url_for(new_endpoint, _external=True)
            return response

        return wrapped

    return decorator


def permission_required(permission):
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)
            return f(*args, **kwargs)

        return wrapped

    return decorator


def admin_required(f):
    return permission_required(Permission.ADMINISTER)(f)


def needs_admin(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        admin_id = g.user.is_admin
        if not admin_id:
            abort(403)
        return f(*args, **kwargs)

    return wrapped


def crossdomain(origin=None,
                methods=None,
                headers=None,
                max_age=21600,
                attach_to_all=True,
                automatic_options=True):
    """Add CORS headers to response. Courtesy of Armin Ronacher.

    .. note::

        This is used only for localhost development. In production we use a
        reverse proxy.

    :param origin:
    :param methods:
    :param headers:
    :param max_age:
    :param attach_to_all:
    :param automatic_options:
    :return:
    """
    if headers is None:
        headers = 'Content-Type, Accept, Authorization, Origin'
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, str):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, str):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            h['Access-Control-Allow-Credentials'] = 'true'
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
                h['Access-Control-Expose-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return functools.update_wrapper(wrapped_function, f)

    return decorator

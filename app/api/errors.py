"""
Copyright (c) 2014 Miguel Grinberg
Copyright (c) 2015 Alexandru Ciobanu
"""
from werkzeug.exceptions import HTTPException
from itsdangerous import BadTimeSignature, SignatureExpired
from requests.exceptions import RequestException, ConnectionError
from urllib.error import HTTPError
from smtplib import SMTPException
from flask import jsonify
from flask_jsonschema import ValidationError
from . import api
from ..models import MailmanApiError
from .decorators import json_response
from sqlalchemy.exc import IntegrityError


class ServerProcessingError(HTTPException):
    code = 500
    description = 'The server was unable to process your request'


def not_modified():
    response = jsonify({'status': 304, 'error': 'not modified'})
    response.status_code = 304
    return response


def bad_request(message):
    response = jsonify({'status': 'bad request', 'message': message})
    response.status_code = 400
    return response


def unauthorized(message):
    response = jsonify({'status': 'unauthorized', 'message': message})
    response.status_code = 401
    return response


def forbidden(message):
    response = jsonify({'status': 'forbidden', 'message': message})
    response.status_code = 403
    return response


def not_found(message="Resource not found"):
    response = jsonify({'status': 'not found', 'message': message})
    response.status_code = 404
    return response


def entity_too_large(message=None):
    if message is None:
        message = "Request Entity Too Large"
    response = jsonify({'status': 'too large', 'message': message})
    response.status_code = 413
    return response


def not_allowed(message):
    response = jsonify({'status': 'not allowed', 'message': message})
    response.status_code = 405
    return response


def not_acceptable():
    response = jsonify({
        'status':
        'not acceptable',
        'message':
        'The resource identified by the request is only capable of '
        'generating response entities which have content '
        'characteristics not acceptable according to the accept '
        'headers sent in the request.'
    })
    response.status_code = 406
    return response


def precondition_failed():
    response = jsonify({'status': 412, 'error': 'precondition failed'})
    response.status_code = 412
    return response


def too_many_requests(message, limit=None):
    response = jsonify({
        'status': 429,
        'error': 'too many requests',
        'message': message
    })
    response.status_code = 429
    return response


_STATUS_CODES_ = {404: not_found}


@api.errorhandler(ValueError)
@json_response
def on_value_error(e):
    return {'message': e.args[0]}, 400


@api.errorhandler(BadTimeSignature)
@json_response
def on_bad_signature(e):
    return {'message': e.args[0], 'validator': 'signature'}, 410


@api.errorhandler(SignatureExpired)
@json_response
def on_expired_signature(e):
    return {'message': e.args[0], 'validator': 'signature'}, 410


@api.errorhandler(ValidationError)
@json_response
def on_validation_error(e):
    return {'message': e.message, 'validator': e.validator}, 422


@api.errorhandler(401)
def unauthorized_handler(e):
    return unauthorized('Unauthorized')


@api.errorhandler(403)
def forbidden_handler(e):
    return forbidden('You don\'t have the permission to access the requested'
                     ' resource. It is either read-protected or not readable '
                     'by the server.')


@api.errorhandler(404)
def not_found_handler(e):
    return not_found('Resource not found')


@api.errorhandler(405)
def too_large_handler(e):
    return entity_too_large()


@api.errorhandler(413)
def not_allowed_handler(e):
    return not_allowed('Method not allowed')


@api.errorhandler(IntegrityError)
@json_response
def server_error(e):
    return {'message': e.args[0]}, 500


@api.errorhandler(HTTPError)
@json_response
def urllib_error(e):
    return {'message': e.msg.decode()}, e.code


@api.errorhandler(MailmanApiError)
@json_response
def mailman_error(e):
    return {'message': str(e)}, 500


@api.errorhandler(SMTPException)
@json_response
def smtp_errpr(e):
    return {'message': e.args[0]}, 500


@api.errorhandler(RequestException)
@json_response
def requests_exception(e):
    if isinstance(e, ConnectionError):
        return {'message': str(e.args[0].reason)}, 500
    else:
        if e.response.status_code in _STATUS_CODES_:
            return _STATUS_CODES_[e.response.status_code]()
        return {'message': str(e.args[0])}, 500

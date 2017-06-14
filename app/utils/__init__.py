from json import JSONEncoder as BaseJSONEncoder
import decimal
import re
import binascii
import os
import hashlib
from datetime import datetime, date
from collections import namedtuple
import ssdeep
from app.utils.mixins import SerializerMixin

_HTTP_METHOD_TO_AUDIT_MAP = {
    'post': 'add',
    'put': 'edit',
    'get': 'view',
    'delete': 'delete',
    'options': 'options'
}


class JSONEncoder(BaseJSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        elif isinstance(o, datetime) or isinstance(o, date):
            return str(o)
        elif isinstance(o, SerializerMixin):
            return o.serialize()
        return super(JSONEncoder, self).default(o)


def is_valid_email(email):
    """Check if email is valid

    :param email: E-mail address
    :return: True if email is valid
    """
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))


def addslashes(s, chars=None):
    """Add slashes by replacing the keys from ``chars`` with the values

    :param s:
    :param chars: Character map
    :return:
    """
    if chars is None:
        chars = {'"': '\\"', "'": "\\'", "\0": "\\\0", "\\": "\\\\"}
    return ''.join(chars.get(c, c) for c in s)


def random_ascii(length=8):
    return binascii.hexlify(os.urandom(length)).decode('ascii')


def get_hashes(buf):
    hexdigests = namedtuple('Digests', 'md5 sha1 sha256 sha512 ctph')
    if isinstance(buf, str):
        buf = open(buf, 'rb').read()
    md5 = hashlib.md5(buf).hexdigest()
    sha1 = hashlib.sha1(buf).hexdigest()
    sha256 = hashlib.sha256(buf).hexdigest()
    sha512 = hashlib.sha512(buf).hexdigest()
    ctph = ssdeep.hash(buf)
    return hexdigests._make((md5, sha1, sha256, sha512, ctph))

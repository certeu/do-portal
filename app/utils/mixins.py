from flask import current_app
from flask_login import AnonymousUserMixin
from datetime import datetime, date
from decimal import Decimal


class SerializerMixin(object):
    __public__ = None
    """Must be implemented by implementors"""

    def _get_fields(self):
        for f in self.__mapper__.iterate_properties:
            yield f.key

    def serialize(self, exclude=(), extra=()):
        """Returns model's public data for jsonify
        :param set exclude: Exclude these items from serialization
        :param set extra: Include these items for serialization
        :return: dictionary to be passed to jsonify
        :rtype: dict
        """
        data = {}
        keys = self._sa_instance_state.attrs.items()
        public = self.__public__ + extra if self.__public__ else extra
        for k, field in keys:
            if public and k not in public:
                continue
            if exclude and k in exclude:
                continue
            value = self._serialize(field.value)
            if value:
                data[k] = value
        extras = list(
            set(public).difference(self._sa_instance_state.attrs.keys()))
        for e in extras:
            try:
                data[e] = self._serialize(getattr(self, e))
            except AttributeError as ae:  # noqa
                current_app.log.error(ae)

        return data

    @classmethod
    def _serialize(cls, value):
        """Serialize value based its type
        :param value:
        :type value:
        :return:
        :rtype:
        """
        if type(value) in (datetime, date):
            ret = value.isoformat()
        elif type(value) is Decimal:
            ret = str(value)
        elif hasattr(value, '__iter__') and not isinstance(value, str):
            ret = []
            for v in value:
                ret.append(cls._serialize(v))
        elif SerializerMixin in value.__class__.__bases__:
            ret = value.serialize()
        else:
            ret = value

        return ret


class Anonymous(AnonymousUserMixin):
    def __init__(self):
        self.name = 'Anonymous'
        self.email = 'anonymous@domain.tld'
        self.organization_id = 0

    def can(self, permissions):
        return False

    def is_admin(self):
        return False

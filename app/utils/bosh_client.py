"""
Copyright (c) 2013 Brendon Crawford, Nathan Fritz, Jack Moffit
"""

import logging
import sys
import uuid
import random
import base64
from urllib.parse import urlparse
from xml.dom import minidom

import requests

TLS_XMLNS = 'urn:ietf:params:xml:ns:xmpp-tls'
SASL_XMLNS = 'urn:ietf:params:xml:ns:xmpp-sasl'
BIND_XMLNS = 'urn:ietf:params:xml:ns:xmpp-bind'
SESSION_XMLNS = 'urn:ietf:params:xml:ns:xmpp-session'
XMPP_XMLNS = 'urn:xmpp:xbosh'


class JID(object):
    """
    JID Class

    Note: This was taken from SleekXMPP
    See: sleekxmpp.basexmpp.set_jid
    """

    fulljid = None
    resource = None
    jid = None
    user = None
    host = None

    def __init__(self, jid):
        self.fulljid = jid
        self.resource = self.getjidresource()
        self.jid = self.getjidbare()
        self.user = jid.split('@', 1)[0]
        self.host = jid.split('@', 1)[-1].split('/', 1)[0]
        return

    def getjidresource(self):
        if '/' in self.fulljid:
            return self.fulljid.split('/', 1)[-1]
        return ''

    def getjidbare(self):
        return self.fulljid.split('/', 1)[0]


class BOSHClient(object):
    rid = None
    jid = None
    jabberid = None
    password = None
    authid = None
    sid = None
    logged_in = False
    headers = None
    bosh_service = None
    request_session = None

    def __init__(self,
                 jabberid,
                 password,
                 bosh_service,
                 hold=1,
                 wait=60,
                 logger=None):
        """

        :param jabberid:
        :param password:
        :param bosh_service:
        :param hold:
        :param wait:
        :param logger:
        :return:
        """
        if logger is None:
            logger = logging.getLogger('bosh_client')
            logger.addHandler(logging.NullHandler())
        logger.debug("BOSHClient jabberid:%s; password:%s; bosh_service:%s",
                     jabberid, password, bosh_service)
        self.rid = random.randint(0, 10000000)
        self.jabberid = JID(jabberid)
        self.password = password
        self.authid = None
        self.sid = None
        self.logged_in = False
        self.headers = {
            "User-Agent": "do-portal-bosh-client/0.1",
            "Content-type": "text/xml",
            "Accept": "text/xml"
        }
        self.bosh_service = urlparse(bosh_service)
        self.request_session = requests.Session()
        self.request_session.headers.update(self.headers)
        self.logged_in = self.start_session_and_auth(hold, wait)
        # Close it
        self.request_session.close()
        logger.debug("BOSH Logged In: %s", self.logged_in)
        return

    def build_element(self, name, child=None, attrs=None):
        """Build XML element

        :param name:
        :param child:
        :param attrs:
        :return: :class:`~xml.dom.minidom.Element`
        """
        if attrs is None:
            attrs = {}
        xdoc = minidom.Document()
        e = xdoc.createElement(name)
        for attr_k, attr_v in attrs.items():
            e.setAttribute(attr_k, attr_v)
        if child is not None:
            e.appendChild(child)
        return e

    def build_text(self, data):
        """Builds XML text element

        :param data:
        :return: :class:`~xml.dom.minidom.Text`
        """
        t = minidom.Text()
        t.data = data
        return t

    def build_body(self, child=None, attrs=None):
        """Build BOSH body

        :param child:
        :param attrs:
        :return: :class:`~xml.dom.minidom.Element`
        """
        if attrs is None:
            attrs = {}
        self.rid += 1
        body = {}
        body['xmlns'] = 'http://jabber.org/protocol/httpbind'
        body['content'] = 'text/xml; charset=utf-8'
        body['rid'] = str(self.rid)
        body['xml:lang'] = 'en'
        if self.sid is not None:
            body['sid'] = str(self.sid)
        for attr_k, attr_v in attrs.items():
            body[attr_k] = attr_v
        elm = self.build_element('body', child=child, attrs=body)
        return elm

    def send_body(self, body):
        """Send the body

        :param body:
        :return: A  tuple in the form
          ``(:class:`~xml.dom.minidom.Element`, String)``
        """
        out = body.toxml()
        response = \
            self.request_session.post(
                self.bosh_service.geturl(),
                data=out)
        if response.status_code == 200:
            data = response.text
        else:
            data = ''
        doc = minidom.parseString(data)
        return (doc.documentElement, data)

    def build_auth_string_plain(self):
        """Builds auth string
        """
        auth_str = b"\x00"
        auth_str += self.jabberid.user.encode('utf-8')
        auth_str += b"\x00"
        try:
            auth_str += self.password.encode('utf-8').strip()
        except UnicodeDecodeError:
            auth_str += self.password.decode('latin1').encode('UTF-8').strip()
        enc_str = base64.b64encode(auth_str)
        return enc_str.decode('utf-8')

    def unique_id(self):
        """Returns a Unique ID
        """
        ret = uuid.uuid4().hex
        return ret

    def start_session_and_auth(self, hold=1, wait=2):
        """Starts session and authenticates

        :param hold:
        :param wait:
        :return: boolean
        """
        # Create a session
        # create body
        body = {}
        body['hold'] = str(hold)
        body['to'] = self.jabberid.host
        body['wait'] = str(wait)
        body['window'] = '5'
        body['ver'] = '1.6'
        body['xmpp:version'] = '1.0'
        body['xmlns:xmpp'] = XMPP_XMLNS
        body_elm = self.build_body(attrs=body)
        retb, _ = self.send_body(body_elm)
        if retb.hasAttribute('authid') and retb.hasAttribute('sid'):
            self.authid = retb.getAttribute('authid')
            self.sid = retb.getAttribute('sid')
            auth = {}
            auth['xmlns'] = SASL_XMLNS
            auth['mechanism'] = 'PLAIN'
            if auth['mechanism'] == 'PLAIN':
                auth_str = self.build_auth_string_plain()
                auth_text_elm = self.build_text(auth_str)
                auth_elm = self.build_element(
                    'auth', child=auth_text_elm, attrs=auth)
                body_auth = self.build_body(child=auth_elm)
                retb, _ = self.send_body(body_auth)
                sucs = retb.getElementsByTagName('success')
                if len(sucs) > 0:
                    body_binder = {}
                    body_binder['xmpp:restart'] = 'true'
                    body_binder['xmlns:xmpp'] = XMPP_XMLNS
                    body_binder_elm = self.build_body(attrs=body_binder)
                    retb, _ = self.send_body(body_binder_elm)
                    bind_elms = retb.getElementsByTagName('bind')
                    # Bind element was found
                    if len(bind_elms) > 0:
                        bind = {}
                        bind['xmlns'] = BIND_XMLNS
                        bind_elm = self.build_element('bind', attrs=bind)
                        if self.jabberid.resource:
                            resource_text = \
                                self.build_text(self.jabberid.resource)
                            resource = self.build_element(
                                'resource', child=resource_text)
                            bind_elm.appendChild(resource)
                        iq = {}
                        iq['xmlns'] = 'jabber:client'
                        iq['type'] = 'set'
                        iq['id'] = self.unique_id()
                        iq_elm = self.build_element('iq', bind_elm, iq)
                        iq_body = self.build_body(child=iq_elm)
                        retb, _ = self.send_body(iq_body)
                        jids = retb.getElementsByTagName('jid')
                        # Jid was found
                        if len(jids) > 0:
                            self.jid = jids[0].childNodes[0].nodeValue
                            # send session
                            iq = {}
                            iq['xmlns'] = 'jabber:client'
                            iq['type'] = 'set'
                            iq['id'] = self.unique_id()
                            session = {}
                            session['xmlns'] = SESSION_XMLNS
                            sess_elm = \
                                self.build_element('session', attrs=session)
                            sess_iq_elm = \
                                self.build_element('iq', sess_elm, attrs=iq)
                            sess_body_elm = \
                                self.build_body(sess_iq_elm)
                            retb, _ = self.send_body(sess_body_elm)
                            sess_res = retb.getElementsByTagName('session')
                            # Session returned ok
                            if len(sess_res) > 0:
                                self.rid += 1
                                return True
        return False


if __name__ == '__main__':
    root_logger = logging.getLogger()
    root_logger.addHandler(logging.StreamHandler())
    root_logger.setLevel(logging.DEBUG)
    USERNAME = sys.argv[1]
    PASSWORD = sys.argv[2]
    SERVICE = sys.argv[3]
    c = BOSHClient(USERNAME, PASSWORD, SERVICE)
    root_logger.info("Logged In: %s", c.logged_in)
    root_logger.info("SID: %s", c.sid)
    root_logger.info("JID: %s", c.jid)
    root_logger.info("RID: %s", c.rid)

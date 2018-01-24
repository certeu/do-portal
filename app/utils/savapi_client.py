#!/usr/bin/env python3
"""
    SAVAPI client
    ~~~~~~~~~~~~~


"""
import argparse
import socket
import sys
from collections import namedtuple
from contextlib import closing
from mimetypes import MimeTypes
import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())

try:
    import magic
except ImportError:
    magic = False
    logging.warn('No magic. Will guess filetype from extension')

SAVAPIResponse = namedtuple('SAVAPIResponse', ['code', 'definition', 'data'])


class SAVAPIClient(object):
    sock = None
    _codes = {
        100: 'Information (response)',
        199: '"Pong" response with optional ping-text',
        200: 'File was not an archive, no alert found',
        210: 'File was an archive, no alert found',
        220: 'A connection timeout occurred',
        310: 'Alert found',
        319: 'Scan finished, alert found',
        350: 'Error occurred',
        401: 'Low-level alert information',
        420: 'Repairable alert found (the alert itself will follow)',
        421: 'Office document found',
        422: 'Office document with macros found',
        430: 'Alert URL',
        440: 'IFRAME',
        450: 'Plugin response',
        499: 'Information'
    }

    def __init__(self, host, port):
        self._host = host
        self._port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self._host, self._port))

    def __repr__(self):
        """ If at all possible, this should look like a valid
        Python expression that could be used to recreate an object with the
        same value (given an appropriate environment)
        """
        return '%s("%s", %d)' % (self.__class__.__qualname__, self._host,
                                 self._port)

    def __enter__(self):
        banner = self.sock.recv(20).decode('utf-8')
        logging.debug(self.parse_response(banner.strip()))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sock.close()

    def scan(self, file_path):
        cmd = 'SCAN {}\n'.format(file_path)
        self.sock.send(cmd.encode('utf-8'))
        with closing(self.sock.makefile()) as f:
            for line in f:
                rv = self.parse_response(line.strip())
                yield rv

    def command(self, command, key=None, val=None):
        if val is None:
            val = ''
        if key is None:
            key = ''
        cmd = '{} {} {}\n'.format(command.upper(), key, val)
        self.sock.send(cmd.encode('utf-8'))
        with closing(self.sock.makefile()) as f:
            for line in f:
                return self.parse_response(line.strip())

    def parse_response(self, response):
        """Parse the response line. Add any processing here.
        Reponse line format: <status-code> <data>\n

        :param response:
        :return:
        """
        code, data = response.split(' ', 1)
        return SAVAPIResponse(code, self._codes[int(code)], data)


def main(argv=None):
    if argv is None:
        argv = sys.argv
    p = argparse.ArgumentParser(
        description='SAVAPI Client',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument(
        '--savapi-host',
        dest='host',
        help='SAVAPI service host',
        default='127.0.0.1')
    p.add_argument(
        '--savapi-port',
        dest='port',
        help='SAVAPI service port',
        default=9999,
        type=int)
    p.add_argument('file', help='Absolute path of file')

    try:
        args = p.parse_args(argv[1:])
    except SystemExit:
        return 2

    log = logging.getLogger()
    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.DEBUG)

    archive_mimes = ('application/zip', 'application/x-tar', 'application/rar')
    if magic:
        mime = magic.Magic(mime=True)
        mimetype = mime.from_file(args.file)
    else:
        mimes = MimeTypes()
        mimetype, _ = mimes.guess_type(args.file)

    with SAVAPIClient(args.host, args.port) as savapi:
        r = savapi.command('SET', 'PRODUCT', '10776')
        log.info(r)
        if mimetype in archive_mimes:
            r = savapi.command('SET', 'ARCHIVE_SCAN', '1')
            log.info(r)
        for r in savapi.scan(args.file):
            print('{} {} <<< {}'.format(r.code, r.definition, r.data))
            if int(r.code) in [319, 350]:
                savapi.command('QUIT')


if __name__ == '__main__':
    sys.exit(main())

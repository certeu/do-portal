"""
    File analysis tasks
    ~~~~~~~~~~~~~~~~~~~

    Report types:
        1. Static analysis
        2. AntiVirus scan
        3. Sandbox report

    .. todo::

        See mastiff for more static analysis.
        https://git.korelogic.com/mastiff.git/
        See https://remnux.org/docs/distro/tools/
        https://github.com/guelfoweb/peframe
        https://github.com/erocarrera/pefile

"""
import os
import re
import json
from app.tasks import popen
from collections import namedtuple
from flask import current_app
from app import db, celery
from app.models import Sample, Report
from app.utils.avscanlib import Scanner
from app.utils import get_hashes
import magic
import zipfile

TRID = namedtuple('TRID', ['probability', 'extension', 'description'])

#: don't attempt to unarchive the following mime types
skip_mimes = [
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # noqa
    'application/vnd.openxmlformats-officedocument.presentationml.slideshow',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.template',
]


@celery.task
def preprocess(sample):
    """Preprocess files after upload.

    :param sample: :class:`~app.models.Sample`
    :return:
    """
    hash_path = os.path.join(current_app.config['APP_UPLOADS_SAMPLES'],
                             sample.sha256)
    if zipfile.is_zipfile(hash_path):
        mt = magic.from_file(hash_path, mime=True)
        if mt in skip_mimes:
            return None
        current_app.log.debug('Extracting {}'.format(hash_path))
        zfile = zipfile.ZipFile(hash_path)
        for zipfo in zfile.namelist():
            cfg = current_app.config
            if zfile.getinfo(zipfo).compress_type == 99:  # PK compat. v5.1
                pwd = '-p{}'.format(cfg['INFECTED_PASSWD'])
                with popen('7z', 'e', '-so', pwd, hash_path) as zproc:
                    buf, stderr = zproc.communicate()
            else:
                buf = zfile.read(
                    zipfo, pwd=bytes(cfg['INFECTED_PASSWD'], 'utf-8'))
            digests = get_hashes(buf)
            hash_path = os.path.join(cfg['APP_UPLOADS_SAMPLES'],
                                     digests.sha256)
            if not os.path.isfile(hash_path):
                with open(hash_path, 'wb') as wf:
                    wf.write(buf)
            s = Sample(
                user_id=sample.user_id,
                filename=zipfo,
                parent_id=sample.id,
                md5=digests.md5,
                sha1=digests.sha1,
                sha256=digests.sha256,
                sha512=digests.sha512,
                ctph=digests.ctph)
            db.session.add(s)
            db.session.commit()


@celery.task
def static(sha256):
    """Task to run static analysis of file identified by :param:`sha256`.

    .. todo::
        Add MacroRaptor for OLE files: http://decalage.info/python/oletools
        Each analysis its own function
        Don't assume the supporting binaries are in my PATH
        Run static analysis based on file type.
        E.g. for ELF executables list dynamic object deps,
        for PDF run PDFiD tools

    :param sha256: File hash
    """
    analyzed = Sample.query.filter_by(sha256=sha256).first()
    file = os.path.join(current_app.config['APP_UPLOADS_SAMPLES'], sha256)
    current_app.log.debug('Analyzing {}'.format(file))
    static_report = {
        'magic': {
            'type': magic.from_file(file),
            'mimetype': magic.from_file(file, mime=True)
        }
    }
    with popen('exiftool', '-a', '-j', file) as exif_proc:
        stdout, stderr = exif_proc.communicate()
        static_report['exif'] = json.loads(stdout.decode('utf-8').strip())
        if exif_proc.returncode != 0:
            current_app.log.error(stderr)

    with popen('hexdump', '-C', '-n', '1024', file) as hexdump_proc:
        stdout, stderr = hexdump_proc.communicate()
        static_report['hex'] = stdout.decode('utf-8')

    with popen('trid', file) as trid_proc:
        stdout, stderr = trid_proc.communicate()
        tr_raw = stdout.decode('utf-8')
        results = re.findall('(.+%) \(([A-Z\.]+)\) (.+)', tr_raw)
        static_report['trID'] = list(
            map(lambda n: dict(TRID._make(n)._asdict()), results))

    # current_app.log.debug('Raw report: {}'.format(static_report))

    # do we need these?
    # with popen('strings', '-a', file) as as_proc:
    #     stdout, stderr = as_proc.communicate()
    #     static_report['strings_ascii'] = stdout.decode('utf-8')
    #
    # with popen('strings', '-a', '-el', file) as us_proc:
    #     stdout, stderr = us_proc.communicate()
    #     static_report['strings_unicode'] = stdout.decode('utf-8')

    # with popen('ldd', file) as ldd_proc:
    #     stdout, stderr = ldd_proc.communicate()
    #: do something with ldd

    # report_fn = '{}_{}.json'.format(sha256, random_ascii(10))
    # report_path = os.path.join(
    #     current_app.config['REPORTS_STATIC_PATH'], report_fn
    # )
    #
    # with open(report_path, 'w') as report:
    #     report.write(json.dumps(static_report))
    #     analyzed.reports.append(Report(type_id=1, report=report_fn))
    #     db.session.add(analyzed)
    #     db.session.commit()

    analyzed.reports.append(
        Report(type_id=1, report=json.dumps(static_report)))
    db.session.add(analyzed)
    db.session.commit()


@celery.task
def multiavscan(sha256):
    """Task to run the AV scanners

    :param sha256: File hash
    """
    scanned = Sample.query.filter_by(sha256=sha256).first()
    file_path = os.path.join(current_app.config['APP_UPLOADS_SAMPLES'], sha256)
    av = Scanner(current_app.config['AVSCAN_CONFIG'])
    av_report = av.scan(file_path)

    scanned.reports.append(Report(type_id=2, report=json.dumps(av_report)))
    db.session.add(scanned)
    db.session.commit()

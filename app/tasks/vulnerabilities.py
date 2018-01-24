import requests
import datetime
from flask import current_app
from app import celery, db
from app.models import Vulnerability


@celery.task
def checkall(checked_patched=False):
    if checked_patched:
        vulns = Vulnerability.query.all()
    else:
        vulns = Vulnerability.query.filter_by(patched=None).all()

    for vuln in vulns:
        if vuln.scanable:
            vuln.tested = datetime.datetime.now()
            rc, status_code = check_patched(vuln.request_method, vuln.url,
                                            vuln.request_data,
                                            vuln.check_string)

            if rc == 1:
                vuln.patched = datetime.datetime.now()
            elif rc == 0:
                vuln.patched = None

            vuln.request_response_code = status_code
            vuln.updated = datetime.datetime.now()

            db.session.add(vuln)
    db.session.commit()


def check_patched(method, url, data, check_string):
    page = requests.request(
        method,
        url,
        data=data,
        stream=False,
        verify=False,
        proxies=current_app.config['PROXIES'])
    if page.status_code != 403:
        if check_string in page.text:
            return 0, page.status_code
        else:
            return 1, page.status_code
    else:
        return 2, page.status_code

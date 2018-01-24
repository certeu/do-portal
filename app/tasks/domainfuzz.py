"""
    Typosquats discovery tasks
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import json
from urllib.parse import urlparse
from app import db, celery  # noqa
from app.models import Fqdn, Typosquat
from domainfuzzer.domain import DomainFuzz
from domainfuzzer.augment import Augmenter


@celery.task
def fuzz_all():
    Typosquat.query.delete()
    db.session.commit()
    fqdns = Fqdn.query.all()
    for fqdn in fqdns:
        fuzz_one.delay(fqdn.fqdn)


@celery.task
def fuzz_one(fqdn):
    original = Fqdn.query.filter_by(fqdn=fqdn).first()
    _url = original.fqdn
    # no scheme, assuming HTTP
    if '://' not in _url:
        _url = 'http://' + _url
    url = urlparse(_url)

    fuzzed = DomainFuzz(url.netloc)
    fuzzed.generate()
    checks = {
        'banners': True,
        'geoip': True,
        'whois': True,
        'ssdeep': True,
        'mxcheck': False
    }

    for domain in fuzzed.domains:
        augment.delay(domain, url, original.id, checks)


@celery.task
def augment(domain, url, parent_fqdn_id, checks):
    augmenter = Augmenter(domain, url, **checks)
    result = augmenter.augment()
    if result.any(['dns_a', 'dns_ns']) and domain.fuzzer != 'Original*':
        d = Typosquat(
            fqdn_id=parent_fqdn_id,
            fqdn=domain.name,
            dns_a=domain.dns_a,
            dns_ns=domain.dns_ns,
            dns_mx=domain.dns_mx,
            raw=json.dumps(domain.__dict__))
        db.session.add(d)
        db.session.commit()

import gzip
from io import BytesIO
from unittest.mock import MagicMock
from flask import url_for
from flask_sqlalchemy import BaseQuery
from flask_tinyclients.vxstream import VxAPIClient, VxStream
from app.api.analysis.vxstream import _state_to_name, SUCCESS
from .conftest import assert_msg
import pytest


@pytest.fixture
def cp_organization(client):
    rv = client.get(url_for('cp.get_cp_organization'))
    assert_msg(rv, key='abbreviation')
    return rv.json


def test_update_cp_organization(client, cp_organization):
    rv = client.put(
        url_for('cp.update_cp_organization', org_id=cp_organization['id']),
        json=cp_organization
    )
    assert_msg(rv, value='Organization saved')


def test_get_cp_samples(client):
    rv = client.get(url_for('cp.get_samples'))
    assert rv.status_code == 200


def test_get_cp_sample(client):
    rv = client.get(url_for('cp.get_sample', sha256=1))
    assert rv.status_code == 404


def test_add_cp_sample(client, malware_sample):
    rv = client.post(
        url_for('cp.add_cp_sample'),
        data=dict(file=(BytesIO(), malware_sample.filename)),
        content_type='multipart/form-data'
    )
    assert rv.status_code == 201


def test_read_cp_av_engines(client):
    rv = client.get(url_for('cp.get_cp_av_engines'))
    assert_msg(rv, key='engines')


def test_add_cp_av_scan(client, monkeypatch):
    monkeypatch.setattr(BaseQuery, 'first_or_404', lambda x: True)
    rv = client.post(
        url_for('cp.add_cp_av_scan'),
        json=dict(files=[{'sha256': '1eedab2b09a4bf6c'}])
    )
    assert_msg(rv, key='message',
               value='Your files have been submitted for AV scanning',
               response_code=202)


def test_get_cp_av_scan(client):
    rv = client.get(url_for('cp.get_cp_av_scan', sha256=1))
    assert rv.status_code == 404


def test_get_cp_vxstream_json_summary(client, monkeypatch, malware_sample):
    vxstream = MagicMock()
    state_resp = MagicMock(
        return_value={
            'response': {'state': _state_to_name[SUCCESS]},
            'response_code': 0
        }
    )
    summary_resp = MagicMock(
        return_value={
            'response': {
                "analysis_start_time": "2016-05-11 21:50:33",
                "domains": [],
                "environmentDescription": "Windows 7 x64 (Stealth)",
                "environmentId": "6",
                "hosts": [],
                "isinteresting": False,
                "isurlanalysis": False,
                "md5": malware_sample.md5,
                "sha1": malware_sample.sha1,
                "sha256": malware_sample.sha256,
                "size": 26616,
                "targeturl": "",
                "threatlevel": 0,
                "threatscore": 0,
                "type": "PE32 executable (native) Intel 80386"
            },
            'response_code': 0
        }
    )
    vxstream.side_effect = [
        state_resp(),
        summary_resp()
    ]
    monkeypatch.setattr(BaseQuery, 'first_or_404', lambda x: True)
    monkeypatch.setattr(VxAPIClient, 'get', lambda *args, **kw: vxstream())
    rv = client.get(
        url_for('cp.get_cp_vxstream_analysis',
                sha256=1, envid=1))

    assert rv.status_code == 200


def test_cp_start_static_analysis(client):
    rv = client.post(
        url_for('cp.add_cp_analysis'),
        json=dict(files=[{'sha256': '1eedab2b09a4bf6c'}])
    )
    assert_msg(rv, response_code=202,
               value='Your files have been submitted for static analysis')


def test_get_cp_static_analysis(client):
    rv = client.get(
        url_for('cp.get_cp_analysis', sha256='1eeb2b09a4bf6c87b273305c09')
    )
    assert rv.status_code == 404


def test_get_cp_vxstream_environments(client, monkeypatch):
    envs = MagicMock(return_value={
        'response_code': 0,
        'response': {
            'environmentList': {
                1: 'Windows 7 64 bit',
                5: 'Windows 7 32 bit (KERNELMODE)',
                6: 'Windows 7 64 bit (KERNELMODE)'
            }
        }
    })
    monkeypatch.setattr(VxStream, 'state', lambda kw: envs())
    rv = client.get(url_for('cp.get_cp_vxstream_environments'))
    assert_msg(rv, key='environments')


def test_cp_vxstream_submit(client, monkeypatch):
    submit = MagicMock(return_value={
        'response_code': 0,
        'response': 'Fake response'
    })
    monkeypatch.setattr(VxStream, 'submit', lambda data, **kw: submit())
    rv = client.post(
        url_for('cp.add_cp_vxstream_analysis'),
        json=dict(files=[], dyn_analysis=dict(vxstream=[5, 6]))
    )
    assert_msg(
        rv,
        value='Your files have been submitted for dynamic analysis',
        response_code=202)


def test_download_cp_html_report(client, monkeypatch):
    fgz = BytesIO()
    with gzip.GzipFile('report.gz', mode='wb', fileobj=fgz) as gzipobj:
        gzipobj.write(b'<html><head></head></html>')
    monkeypatch.setattr(VxAPIClient, 'get', lambda *args, **kw: bytes(fgz))
    monkeypatch.setattr(BaseQuery, 'first_or_404', lambda x: True)

    rv = client.get(
        url_for('cp.get_cp_vxstream_download',
                sha256='sss', eid=1, ftype='html')
    )
    assert rv.status_code == 200


def test_get_cp_html_report(client, monkeypatch):
    fgz = BytesIO()
    with gzip.GzipFile('report.gz', mode='wb', fileobj=fgz) as gzipobj:
        gzipobj.write(b'<html><head></head></html>')
    monkeypatch.setattr(VxAPIClient, 'get', lambda *args, **kw: bytes(fgz))
    monkeypatch.setattr(BaseQuery, 'first_or_404', lambda x: True)

    rv = client.get(
        url_for('cp.get_cp_vxstream_report',
                sha256='sss', envid=1, type_='html')
    )
    assert rv.status_code == 200


@pytest.mark.parametrize('urls, status_code',
                         [(list(), 422), (['http://cert.europa.eu'], 202)])
def test_cp_vxstream_submit_url(client, monkeypatch, urls, status_code):
    submit = MagicMock(return_value={
        'response_code': 0,
        'response': {'sha256': 'b291588f2d2b3'}
    })
    monkeypatch.setattr(VxStream, 'submiturl', lambda data, k, **kw: submit())
    rv = client.post(
        url_for('cp.add_cp_vxstream_url_analysis'),
        json=dict(urls=urls, dyn_analysis=dict(vxstream=[5, 6]))
    )
    assert rv.status_code == status_code


@pytest.fixture
def test_create_fqdn(client):
    rv = client.post(
        url_for('cp.add_fqdn'),
        json=dict(fqdn='cert.europa.eu')
    )
    assert_msg(rv, value='Fqdn added', response_code=201)
    return rv.json


def test_update_fqdn(client, test_create_fqdn):
    rv = client.put(
        url_for('cp.update_fqdn', fqdn_id=test_create_fqdn['fqdn']['id']),
        json=dict(fqdn='cert.europa.eu')
    )
    assert rv.status_code == 200


def test_read_fqdns(client, test_create_fqdn):
    rv = client.get(url_for('cp.get_fqdns'))
    assert_msg(rv, key='fqdns')


def test_read_fqdn(client, test_create_fqdn):
    rv = client.get(
        url_for('cp.get_fqdn', fqdn_id=test_create_fqdn['fqdn']['id']))
    assert_msg(rv, key='fqdn')


def test_delete_fqdn(client, test_create_fqdn):
    rv = client.delete(
        url_for('cp.delete_fqdn', fqdn_id=test_create_fqdn['fqdn']['id']))
    assert rv.status_code == 200

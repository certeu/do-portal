#!venv/bin/python
import os
import sys
import json
from collections import namedtuple
import requests
import datetime
import click

from app import create_app
from flask import current_app
from flask.cli import FlaskGroup
from flask_gnupg import fetch_gpg_key
from app import db
from app.models import User, Organization, IpRange, Fqdn, Asn, Email
from app.models import OrganizationGroup, Vulnerability, Tag
from app.models import ContactEmail, emails_organizations, tags_vulnerabilities
from app.models import Role, ReportType


def create_cli_app(info):
    return create_app(os.getenv('DO_CONFIG') or 'default')


def abort_if_false(ctx, param, value):
    if not value:
        ctx.abort()


@click.group(cls=FlaskGroup, create_app=create_cli_app)
def cli():
    """DO portal management script"""


@cli.command('shell', short_help='Start shell in app context')
def shell_command():
    ctx = current_app.make_shell_context()

    try:
        from IPython import start_ipython
        start_ipython(argv=(), user_ns=ctx)
    except ImportError:
        from code import interact
        interact(local=ctx)


CollabCustomer = namedtuple('CollabCustomer', ['name', 'config'])


@cli.command()
@click.option('--collab-url', help='AbuseHelper collab URL',
              default='https://abusehelper.cert.europa.eu/collab/customers/'
                      'FrontPage?action=getMetaJSON&args='
                      'CategoryAbuseContact,%27%20%27%20||Full%20name||'
                      'IP%20range||FQDN||ASN||Abuse%20email%27%20%27||'
                      'Mail%20template||Mail%20times||ID||'
                      '%27%20%27Point%20of%20Contact||')
@click.option('-u', '--username', help='Collab username')
@click.option('-p', '--password', help='Collab password', prompt=True,
              hide_input=True)
def import_orgs(collab_url, username, password):
    """Import customers from AbuseHelper collab wiki."""
    group_count = OrganizationGroup.query.count()
    if group_count < 1:
        sys.exit("No groups defined. "
                 "Run create_groups to create default groups.")
    if click.confirm("This command will drop all exiting organizations"
                     " and all their details (IPs, Emails, ASNs, etc.). "
                     "Are you sure you want to continue?", abort=True):
        ah_resp = requests.get(collab_url, auth=(username, password),
                               verify=False)
        if ah_resp.status_code != 201:
            current_app.log.error(ah_resp.reason)
            raise click.Abort

        click.echo("Deleting old data...")
        db.session.execute(emails_organizations.delete())
        db.session.execute(tags_vulnerabilities.delete())

        ContactEmail.query.delete()
        IpRange.query.delete()
        Fqdn.query.delete()
        Asn.query.delete()
        Email.query.delete()
        Vulnerability.query.delete()
        Organization.query.filter(Organization.group_id == 1).delete()
        click.echo("Old data deleted!")

        data = json.loads(ah_resp.text)
        for name, config in data.items():
            org = Organization.from_collab(CollabCustomer(name, config))
            click.echo("Adding {}...".format(org.abbreviation))
            db.session.add(org)
        db.session.commit()
        click.echo('Done')


@cli.command()
@click.option('--collab-url', help='AH collab URL',
              default='https://abusehelper.cert.europa.eu/collab/'
                      'national_certs/FrontPage?action=getMetaJSON&args'
                      '=CategoryNationalCert,%20||Rule||Description||'
                      'Abuse%20email||Mail%20template||Mail%20times||'
                      'Disabled||')
@click.option('-u', '--username', help='Collab username')
@click.option('-p', '--password', help='Collab password', prompt=True,
              hide_input=True)
def import_certs(collab_url, username, password):
    """Import national CERTs information from AbuseHelper collab wiki."""
    if click.confirm("This command should be run only once, on install",
                     abort=True):
        ah_resp = requests.get(collab_url, auth=(username, password),
                               verify=False)
        if ah_resp.status_code != 200:
            current_app.log.error(ah_resp.reason)
            raise click.Abort

        data = json.loads(ah_resp.text)
        for country, details in data.items():
            org = Organization(
                abbreviation=country,
                group_id=2,
                full_name='National CERT of ' + country
            )

            try:
                org.mail_times = details['Mail times'][0]
            except IndexError:
                current_app.log.debug('Using default mail times...')
            try:
                org.mail_template = details['Mail template'][0]
            except IndexError:
                current_app.log.debug('Using default template...')
            org.abuse_emails = details['Abuse email']
            click.echo("Adding {}...".format(country))
            db.session.add(org)
        db.session.commit()
        click.echo('Done')


@cli.command()
def addsampledata():
    """Add sample data"""
    OrganizationGroup._OrganizationGroup__insert_defaults()
    ReportType._ReportType__insert_defaults()
    Role._Role__insert_defaults()
    adm = Role.query.filter_by(permissions=0xff).first()

    o = Organization(
        abbreviation="CERT-EU",
        full_name="Computer Emergency Response Team for EU "
                  "Institutions Agencies and Bodies",
        ip_ranges=['212.8.189.16/28'],
        abuse_emails=['cert-eu@ec.europa.eu'],
        contact_emails=[ContactEmail(email='cert-eu@ec.europa.eu')],
        asns=[5400],
        fqdns=['cert.europa.eu']
    )
    db.session.add(o)
    db.session.commit()

    user = User(name='testadmin', email='testadmin@domain.tld',
                password='changeme', role=adm)
    db.session.add(user)
    db.session.commit()
    click.echo('Done')


@cli.command()
@click.argument('oid')
@click.option('--yes', is_flag=True, callback=abort_if_false,
              expose_value=False,
              prompt='Are you sure you want to delete this organization?')
def delorg(oid):
    o = Organization.get(oid)
    o.fqdns = o.ip_ranges = o.asns = o.abuse_emails = o.contact_emails = []
    Organization.query.filter_by(id=oid).delete()
    db.session.commit()


@cli.command()
@click.argument('filename', required=True)
def import_hof(filename):
    """Import Hall of Fame records from initial PoC"""
    dos = {}
    staff = User.query.filter_by(role_id=1).all()
    for do in staff:
        name = ''.join([n[0] for n in do.name.split()])
        if name == 'VRR':
            dos['VR'] = do.id
        dos[name] = do.id

    constituents = {}
    orgs = Organization.query.filter_by(group_id=1).all()
    for org in orgs:
        constituents[org.abbreviation] = org.id

    with open(filename) as f:
        hof = json.loads(f.read())
        for entry in hof:
            vuln_exist = Vulnerability.query.\
                filter_by(url=entry['url']).\
                count()
            if vuln_exist != 0:
                print('Entry already exist')
            else:
                print('Adding')
                print(entry['url'])
                if entry['published'] == 'yes':
                    published = True
                else:
                    published = False
                if entry['scanable'] == 'yes':
                    scanable = True
                else:
                    scanable = False
                user_id = dos.get(entry['DO'], 1)
                org_id = constituents.get(entry['constituent'], 1)
                list_types = []
                vtype = entry['type']
                if Tag.query.filter_by(name=vtype).first():
                    list_types.append(Tag.query.filter_by(name=vtype).first())
                else:
                    list_types.append(Tag(name=vtype))
                vuln = Vulnerability(
                    user_id=user_id,
                    check_string=entry['check_string'],
                    updated=datetime.datetime.now(),
                    reporter_name=entry['reporter'],
                    url=entry['url'],
                    request_data=json.dumps(entry['data']),
                    request_method=entry['method'],
                    test_type='request',
                    request_response_code=entry['test_status'],
                    tested=entry['last_test'],
                    reported=entry['report_date'],
                    patched=entry['patched_date'],
                    published=published,
                    scanable=scanable,
                    incident_id=entry['Incident'],
                    organization_id=org_id,
                    labels_=list_types
                )
                db.session.add(vuln)
            db.session.commit()
        print('Done')


@cli.command()
@click.argument('emails', required=True)
def fetchkeys(emails):
    """Download GPG keys from remote keyserver"""
    for e in emails:
        fetch_gpg_key(e, current_app.config['GPG_KEYSERVERS'][0])


@cli.command()
@click.password_option()
@click.argument('name', required=True)
@click.argument('email', required=True)
def adduser(password, name, email):
    """Create new local account"""
    user = User(name=name, email=email, password=password)
    db.session.add(user)
    db.session.commit()
    click.echo('User {0} was registered successfully.'.format(email))


if __name__ == '__main__':
    cli()

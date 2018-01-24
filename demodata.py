#!venv/bin/python

# flake8: noqa

import os
import sys
import json
from collections import namedtuple
import requests
import datetime
import click
import yaml

from app import create_app
from flask import current_app
from flask.cli import FlaskGroup
from flask_gnupg import fetch_gpg_key
from app import db
from app.models import User, Organization, IpRange, Fqdn, Asn, Email
from app.models import OrganizationGroup, Vulnerability, Tag
from app.models import ContactEmail, emails_organizations, tags_vulnerabilities
from app.models import Role, ReportType, OrganizationMembership, MembershipRole
from app.fixtures import testfixture


def create_cli_app(info):
    return create_app(os.getenv('DO_CONFIG') or 'default')


def abort_if_false(ctx, param, value):
    if not value:
        ctx.abort()


@click.group(cls=FlaskGroup, create_app=create_cli_app)
def cli():
    """DO portal management script"""


@cli.command()
def addyaml():
    """Add sample data from yaml file"""
    testfixture.testdata.addyaml()
    db.session.commit()


@cli.command()
def addcountries():
    testfixture.testdata.addcountries()


@cli.command()
def add():
    """Add sample data"""

    cert = Organization(
        abbreviation="CERT",
        full_name="CERT Master User",
    )
    db.session.add(cert)

    cert_user = User(name="cert master user", )
    cert_user.password = 'iAasdas588'
    db.session.add(cert_user)

    cert_user4cert = OrganizationMembership(
        email='certifant@cert.at',
        zip='1234',
        organization=cert,
        user=cert_user)

    db.session.commit()

    click.echo('Done Org id: ' + str(cert.id))
    click.echo('Done User id: ' + str(cert_user.id))
    click.echo('adding sub org')

    eorg = Organization(
        abbreviation="E-Org", full_name="E-Org Dach", parent_org=cert)
    # db.session.add(eorg)

    eorg_user = User(name="eorg master user")
    eorg_user.password = 'iAasdas588'

    OrganizationMembership(
        email='master@eorg.at', zip='5678', organization=eorg, user=eorg_user)

    eorg_electricity = Organization(
        abbreviation="E-Org Strom", full_name="E-Org Strom", parent_org=eorg)
    db.session.add(eorg_electricity)

    eorg_electricity_user = User(name="eorg electricity user", )
    eorg_electricity_user.password = 'iAasdas588'
    db.session.add(eorg_electricity_user)

    eorgelectricity_orguser = OrganizationMembership(
        email='electricity@eorg.at',
        zip='5678',
        organization=eorg_electricity,
        user=eorg_electricity_user)
    db.session.commit()


@cli.command()
def delete():
    """delete sample data"""
    OrganizationMembership.query.delete()
    #contactemails_organizations.delete()
    emails_organizations.delete()
    User.query.filter(User.name != 'testadmin').delete()
    Organization.query.filter(Organization.abbreviation != "CERT-EU").delete()
    db.session.commit()


@cli.command()
def print():
    """output sample data"""
    u = User.query.filter_by(name="certmaster").first()
    click.echo(u.name + str(u.id))
    for uo in u.user_memberships:
        click.echo(uo.email)
        click.echo(uo)
        click.echo(uo.organization.full_name)
        for co in uo.organization.child_organizations:
            click.echo(co.full_name)

    click.echo('**** organization_memberships ******')
    for oxu in u.get_organization_memberships():

        click.echo('%s %s' % (oxu.email, oxu.organization.full_name))

    #click.echo(u.org_ids)

    click.echo('**** organization_memberships ******')
    oms = User.query.filter_by(
        name='EnergyOrg Admin').first().get_organization_memberships()
    if (oms):
        for oxu in oms:
            click.echo('%s %s %s' % (oxu.email, oxu.membership_role.name,
                                     oxu.organization.full_name))

    click.echo('**** organizations ******')
    orgs = u.get_organizations()
    i = 0
    for org in orgs:
        click.echo(u.id)
        click.echo('%d %s %s' % (i, org.full_name, org.abbreviation))
        i += 1

    click.echo('**** permission checks ******')
    eorg_user = User.query.filter_by(name='E-Org User').first()
    eorgmaster = User.query.filter_by(name='eorgmaster').first()
    click.echo("eorgmaster for E-Org %s \nE-Org for eorgmaster %s" %
               (eorgmaster.may_handle_user(eorg_user),
                eorg_user.may_handle_user(eorgmaster)))
    click.echo("cert for E-Org %s \nE-Org for cert %s" %
               (u.may_handle_user(eorg_user), eorg_user.may_handle_user(u)))
    click.echo("cert for eorgmaster %s \neorgmaster for cert %s" %
               (u.may_handle_user(eorgmaster), eorgmaster.may_handle_user(u)))

    click.echo('**** user.get_userss ******')
    users = u.get_users()
    for user in users:
        click.echo("%s" % (user.name))

    click.echo('**** user.get_users(eorgmaster) ******')
    users = eorgmaster.get_users()
    for user in users:
        click.echo("%s" % (user.name))


if __name__ == '__main__':
    cli()

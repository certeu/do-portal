import os
import sys
import json
from collections import namedtuple
import requests
import datetime
import yaml
import csv

from app import create_app
from flask import current_app
from flask.cli import FlaskGroup
from flask_gnupg import fetch_gpg_key
from app import db
from app.models import User, Organization, IpRange, Fqdn, Asn, Email
from app.models import OrganizationGroup, Vulnerability, Tag
from app.models import ContactEmail, emails_organizations, tags_vulnerabilities
from app.models import Role, ReportType, OrganizationMembership, MembershipRole
from app.models import Country

class testdata:
   def addcountries():
      """Add country list from csv file"""
      with open('install/iso_3166_2_countries.csv') as csvfile:
          data = csv.reader(csvfile, delimiter = ',')
          data = list(data)
          for r in data[2:]:
          #    print(r[1], r[10])
              country = Country.query.filter_by(cc=r[10]).first()
              if country is None:
                  country = Country(cc=r[10], name=r[1] )
                  db.session.add(country)
          db.session.commit()


   def addyaml(yamlfile = "install/testdata.yaml"):
      """Add sample data from yaml file"""
      with open(yamlfile, 'r') as stream:
           data_loaded = yaml.load(stream)

      for org in data_loaded['org']:
         if 'full_name' not in org:
            org['full_name'] = org['abbreviation']
         if 'display_name' not in org:
            org['display_name'] = org['abbreviation']
         o = Organization(
            abbreviation=org['abbreviation'],
            full_name=org['full_name'],
            display_name=org['display_name'],
         )
         if ('parent_org' in org):
            po = Organization.query.filter_by(abbreviation=org['parent_org']).first()
            o.parent_org = po
         db.session.add(o)
         db.session.commit()

      for user in data_loaded['user']:
         u = User.query.filter_by(name = user['name']).first()
         if (not u):
            u = User(
               name = user['name']
            )
            u.email = user['email']
            u.api_key = u.generate_api_key()
            if 'password' in user:
                u.password = user['password']
            else:
                u.password = 'Bla12345%'
            db.session.add(u)

         role = MembershipRole.query.filter_by(name=user['role']).first()
         org = Organization.query.filter_by(abbreviation=user['org']).first()
         if 'email' not in user:
             user['email'] = 'na@email.at'
         if 'street' not in user:
             user['street'] = 'no street'
         if 'zip' not in user:
             user['zip'] = '1234'
         if 'city' not in user:
             user['city'] = 'n/a'
         if 'country' not in user:
             country_o = Country.query.filter_by(cc='AT').first()
         else:
             country_o = Country.query.filter_by(cc=user['country']).first()
         if 'comment' not in user:
             user['comment'] = 'no comment'
         if 'phone' not in user:
             user['phone'] = '+12345678'
         if 'mobile' not in user:
             user['mobile'] = '+33456788'
         if 'sms_alerting' not in user:
             user['sms_alerting'] = 0

         oxu = OrganizationMembership(
            email =  user['email'],
            street = user['street'],
            city = user['city'],
            zip  = user['zip'],
            country = country_o,
            comment = user['comment'],
            phone =user['phone'],
            mobile =user['mobile'],
            organization = org,
            user = u,
            membership_role = role,
            sms_alerting = user['sms_alerting'],
         )
         db.session.commit()

   def print():
      """output sample data"""
      u = User.query.filter_by(name="certmaster").first()
      echo(u.name + str(u.id))
      for uo in u.user_memberships:
          print(uo.email)
          print(uo)
          print(uo.organization.full_name)
          for co in uo.organization.child_organizations:
             print(co.full_name)

      print('**** organization_memberships ******')
      for oxu in u.get_organization_memberships():

          print('%s %s %s' %
              (oxu.email, oxu.membership_role.name,  oxu.organization.full_name))

      #print(u.org_ids)

      print('**** organization_memberships ******')
      oms = User.query.filter_by(name = 'EnergyOrg Admin').first().get_organization_memberships()
      if (oms):
        for oxu in oms:
          print('%s %s %s' %
             (oxu.email, oxu.membership_role.name,  oxu.organization.full_name))

      print('**** organizations ******')
      orgs = u.get_organizations()
      i = 0
      for org in orgs:
          print('%d %s %s' %
              (i, org.full_name, org.abbreviation))
          i += 1

      print('**** permission checks ******')
      eorg_user = User.query.filter_by(name = 'E-Org User').first()
      eorgmaster = User.query.filter_by(name = 'eorgmaster').first()
      print("eorgmaster for E-Org %s \nE-Org for eorgmaster %s" %
           (eorgmaster.may_handle_user(eorg_user), eorg_user.may_handle_user(eorgmaster)))
      print("cert for E-Org %s \nE-Org for cert %s" %
           (u.may_handle_user(eorg_user), eorg_user.may_handle_user(u)))
      print("cert for eorgmaster %s \neorgmaster for cert %s" %
           (u.may_handle_user(eorgmaster), eorgmaster.may_handle_user(u)))


      print('**** user.get_userss ******')
      users = u.get_users()
      for user in users:
         print("%s" % (user.name))

      print('**** user.get_users(eorgmaster) ******')
      users = eorgmaster.get_users()
      for user in users:
         print("%s" % (user.name))


   if __name__ == '__main__':
       cli()

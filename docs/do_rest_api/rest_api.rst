.. _rest_api:

DO REST API
===========

`REST <https://en.wikipedia.org/wiki/Representational_state_transfer>`_ API


.. toctree::
    :maxdepth: 2

    auth
    asns
    bots
    deliverables
    emails
    fqdns
    ip_ranges
    organizations
    reports
    samples
    vulnerabilities
    analysis


.. autoflask:: app:create_app('default')
    :undoc-static:
    :blueprints: api
    :modules: app.api.routes

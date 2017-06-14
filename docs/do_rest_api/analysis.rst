.. _analysis:

Analysis
========

AV
--

.. autoflask:: app:create_app('default')
    :undoc-static:
    :blueprints: api
    :modules: app.api.analysis.av

FireEye
-------

.. autoflask:: app:create_app('default')
    :undoc-static:
    :blueprints: api
    :modules: app.api.analysis.fireeye

Nessus
------

.. autoflask:: app:create_app('default')
    :undoc-static:
    :blueprints: api
    :modules: app.api.analysis.nessus

Static
------

.. autoflask:: app:create_app('default')
    :undoc-static:
    :blueprints: api
    :modules: app.api.analysis.static

VxStream
--------

.. autoflask:: app:create_app('default')
    :undoc-static:
    :blueprints: api
    :modules: app.api.analysis.vxstream

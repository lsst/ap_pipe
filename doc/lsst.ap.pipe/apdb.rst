.. py:currentmodule:: lsst.ap.pipe

.. program:: make_apdb.py

.. _ap-pipe-apdb:

###################################################
Setting up the Prompt Products Database for ap_pipe
###################################################

.. Centralized markup for program names

.. |make_apdb| replace:: :doc:`make_apdb.py <scripts/make_apdb.py>`

.. |ap_pipe| replace:: :command:`ap_pipe.py`

|ap_pipe| needs an existing Prompt Products Database (APDB) in which to store its results.
Such a database will be provided externally during operations, but developers can run |make_apdb| to set up their own database for testing.
This page provides an overview of how to use |make_apdb|.

.. _section-ap-pipe-apdb-config:

Configuring the database
========================

|ap_pipe| includes information about the database location and schema in its `ApPipeConfig`, and most users pass this information to the script through the :option:`--config <ap_pipe.py --config>` and :option:`--configfile <ap_pipe.py --configfile>` command-line options.

|make_apdb| also uses `ApPipeConfig` and the :option:`--config` and :option:`--configfile` options, so users can pass exactly the same arguments to |make_apdb| and |ap_pipe|.
Supporting identical command line arguments for both scripts makes it easy to keep the database settings in sync.

For more information on the configuration options themselves, see `lsst.dax.apdb.ApdbConfig`.
``apdb.db_url`` has no default and must be set to create a valid config.

.. _section-ap-pipe-apdb-examples:

Examples
========

Databases can be configured using direct config overrides:

.. prompt:: bash

   make_apdb.py -c apdb.isolation_level=READ_UNCOMMITTED apdb.db_url="sqlite:///databases/apdb.db" differencer.coaddName=dcr
   ap_pipe.py -c apdb.isolation_level=READ_UNCOMMITTED apdb.db_url="sqlite:///databases/apdb.db" differencer.coaddName=dcr repo --calib repo/calibs --rerun myrun --id

|make_apdb| ignores any `ApPipeConfig` fields not related to the APDB (in the example, ``differencer.coaddName``), so there is no need to filter them out.

Databases can also be set up using config files:

.. prompt:: bash

   make_apdb.py -C myApPipeConfig.py
   ap_pipe.py repo --calib repo/calibs --rerun myrun -C myApPipeConfig.py --id

.. _section-ap-pipe-apdb-seealso:

Further reading
===============

- :doc:`pipeline-tutorial`

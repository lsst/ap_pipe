.. py:currentmodule:: lsst.ap.pipe

.. program:: make_ppdb.py

.. _ap-pipe-ppdb:

###################################################
Setting up the Prompt Products Database for ap_pipe
###################################################

:command:`ap_pipe.py` needs an existing Prompt Products Database (PPDB) in which to store its results.
Such a database will be provided externally during operations, but developers can run :command:`make_ppdb.py` to set up their own database for testing.
This page provides an overview of how to use :command:`make_ppdb.py`.

.. _section-ap-pipe-ppdb-config:

Configuring the database
========================

:command:`ap_pipe.py` includes information about the database location and schema in its `ApPipeConfig`, and most users pass this information to the script through the :option:`--config <ap_pipe.py --config>` and :option:`--configfile <ap_pipe.py --configfile>` command-line options.

:command:`make_ppdb.py` also uses `ApPipeConfig` and the :option:`--config` and :option:`--configfile` options, so users can pass exactly the same arguments to :command:`make_ppdb.py` and :command:`ap_pipe.py`.
Supporting identical command line arguments for both scripts makes it easy to keep the database settings in sync.

For more information on the configuration options themselves, see `lsst.dax.ppdb.PpdbConfig`.
``ppdb.db_url`` has no default and must be set to create a valid config.

.. _section-ap-pipe-ppdb-examples:

Examples
========

Databases can be configured using direct config overrides:

.. prompt:: bash

   make_ppdb.py -c ppdb.isolation_level=READ_UNCOMMITTED ppdb.db_url="sqlite:///databases/ppdb.db" differencer.coaddName=dcr
   ap_pipe.py -c ppdb.isolation_level=READ_UNCOMMITTED ppdb.db_url="sqlite:///databases/ppdb.db" differencer.coaddName=dcr repo --calib repo/calibs --rerun myrun --id

:command:`make_ppdb.py` ignores any `ApPipeConfig` fields not related to the PPDB (in the example, ``differencer.coaddName``), so there is no need to filter them out.

Databases can also be set up using config files:

.. prompt:: bash

   make_ppdb.py -C myApPipeConfig.py
   ap_pipe.py repo --calib repo/calibs --rerun myrun -C myApPipeConfig.py --id

.. _section-ap-pipe-ppdb-seealso:

Further reading
===============

- :doc:`pipeline-tutorial`

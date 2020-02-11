.. py:currentmodule:: lsst.ap.pipe

.. program:: make_apdb.py

.. _ap-pipe-apdb:

####################################################
Setting up the Alert Production Database for ap_pipe
####################################################

.. Centralized markup for program names

.. |make_apdb| replace:: :doc:`make_apdb.py <scripts/make_apdb.py>`

.. |ap_pipe| replace:: :command:`ap_pipe.py`

The Alert Production Pipeline, as represented by :lsst-task:`lsst.ap.pipe.ApPipeTask` and executed by |ap_pipe|, delegates saving and loading DIASources and DIAObjects to its ``diaPipe`` subtask.
In principle, different implementations of ``diaPipe`` can be selected in defined in `ApPipeTask`'s configuration (by setting :lsst-config-field:`lsst.ap.pipe.ap_pipe.ApPipeConfig.diaPipe`), but the default choice --- :lsst-task:`lsst.ap.association.DiaPipelineTask` --- is expected to be appropriate for most uses.
`~lsst.ap.association.DiaPipelineTask` uses a database --- known as the Alert Production Database, or APDB --- to store its results.
Such a database will be provided externally during operations, but developers can run |make_apdb| to set up their own database for testing.
This page provides an overview of how to use |make_apdb|.

.. _section-ap-pipe-apdb-config:

Configuring the database
========================

The database is configured using an instance of `~lsst.dax.apdb.ApdbConfig`, which is made accessible through `ApPipeConfig`'s ``diaPipe.apdb`` option.
|ap_pipe| command line users can pass configuration information to the script through the :option:`--config <ap_pipe.py --config>` and :option:`--configfile <ap_pipe.py --configfile>` command-line options.

|make_apdb| also uses `ApPipeConfig` and the :option:`--config` and :option:`--configfile` options, so users can pass exactly the same arguments to |make_apdb| and |ap_pipe|.
Supporting identical command line arguments for both scripts makes it easy to keep the database settings in sync.

Note that ``apdb.db_url`` has no default; a value *must* be provided by the user.

.. _section-ap-pipe-apdb-examples:

Examples
========

Databases can be configured using direct config overrides:

.. prompt:: bash

   make_apdb.py -c diaPipe.apdb.isolation_level=READ_UNCOMMITTED diaPipe.apdb.db_url="sqlite:///databases/apdb.db" differencer.coaddName=dcr
   ap_pipe.py -c diaPipe.apdb.isolation_level=READ_UNCOMMITTED diaPipe.apdb.db_url="sqlite:///databases/apdb.db" differencer.coaddName=dcr repo --calib repo/calibs --rerun myrun --id

|make_apdb| ignores any `ApPipeConfig` fields not related to the APDB (in the example, ``differencer.coaddName``), so there is no need to filter them out.

Databases can also be set up using config files:

.. prompt:: bash

   make_apdb.py -C myApPipeConfig.py
   ap_pipe.py repo --calib repo/calibs --rerun myrun -C myApPipeConfig.py --id

.. _section-ap-pipe-apdb-seealso:

Further reading
===============

- :doc:`pipeline-tutorial`

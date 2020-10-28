.. py:currentmodule:: lsst.ap.pipe

.. program:: make_apdb.py

.. _ap-pipe-apdb:

####################################################
Setting up the Alert Production Database for ap_pipe
####################################################

.. Centralized markup for program names

.. |make_apdb| replace:: :doc:`make_apdb.py <scripts/make_apdb.py>`

.. |ap_pipe| replace:: :command:`ap_pipe.py`

.. |pipetask| replace:: :command:`pipetask`


In its default configuration, the Alert Production Pipeline, as represented by :lsst-task:`lsst.ap.pipe.ApPipeTask` (Gen 2) or :file:`pipelines/ApPipe.yaml` (Gen 3), relies on a database to save and load DIASources and DIAObjects.
When running as part of the operational system, this database will be provided externally.
However, during testing and development, developers can run |make_apdb| to set up their own database.
This page provides an overview of how to use |make_apdb|.

.. _section-ap-pipe-apdb-config:

Configuring the database
========================

The database is configured using `~lsst.dax.apdb.ApdbConfig`.
|ap_pipe| command line users can pass configuration information to the script through the :option:`--config <ap_pipe.py --config>` and :option:`--configfile <ap_pipe.py --configfile>` command-line options, using the prefix ``diaPipe.apdb.`` to distinguish APDB information from other pipeline configuration.
|make_apdb| configures the database directly through :option:`--config` and :option:`--config-file` (different spelling, for consistency with |pipetask|), with no prefix.

For |pipetask| users, the APDB is configured with the :option:`--config <pipetask run --config>` and :option:`--config-file <pipetask run --config-file>` options.
APDB configuration info uses the prefix ``diaPipe:apdb.``, with a colon, but is otherwise the same.

Note that the `~lsst.dax.apdb.ApdbConfig.db_url` field has no default; a value *must* be provided by the user.

.. _section-ap-pipe-apdb-examples:

Examples
========

Databases can be configured using direct config overrides (see :ref:`ap-pipe-pipeline-tutorial-gen2` for an explanation of the |ap_pipe| command line):

.. prompt:: bash

   make_apdb.py -c isolation_level=READ_UNCOMMITTED db_url="sqlite:///databases/apdb.db"
   ap_pipe.py -c diaPipe.apdb.isolation_level=READ_UNCOMMITTED diaPipe.apdb.db_url="sqlite:///databases/apdb.db" differencer.coaddName=dcr repo --calib repo/calibs --rerun myrun --id [optional IDs to process]

The user is responsible for making sure the two APDB configurations are consistent.

In Gen 3, this becomes (see :ref:`ap-pipe-pipeline-tutorial` for an explanation of |pipetask|):

.. prompt:: bash

   make_apdb.py -c isolation_level=READ_UNCOMMITTED db_url="sqlite:///databases/apdb.db"
   pipetask run -p ApPipe.yaml -c diaPipe:apdb.isolation_level=READ_UNCOMMITTED diaPipe:apdb.db_url="sqlite:///databases/apdb.db" differencer:coaddName=dcr -b repo -o myrun

.. warning::

   As in Gen 2, make sure the APDB is created with a configuration consistent with the one used by the pipeline.
   Note that the pipeline file given by ``-p`` may include APDB config overrides of its own.
   You can double-check what configuration is being run by calling :command:`pipetask run` with the ``--show config="apdb*"`` argument, though this lists *all* configuration options, including those left at their defaults.

Databases can also be set up using :ref:`config files <command-line-task-config-howto-configfile>`:

.. code-block:: py
   :caption: myApdbConfig.py

   config.db_url = "sqlite:///databases/apdb.db"
   config.isolation_level = "READ_UNCOMMITTED"

.. prompt:: bash

   make_apdb.py -C myApdbConfig.py
   ap_pipe.py repo --calib repo/calibs --rerun myrun -C myApPipeConfig.py --id [optional ID to process]

.. _section-ap-pipe-apdb-seealso:

Further reading
===============

- :doc:`pipeline-tutorial-gen2`
- :doc:`pipeline-tutorial`

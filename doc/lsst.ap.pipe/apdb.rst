.. py:currentmodule:: lsst.ap.pipe

.. _ap-pipe-apdb:

####################################################
Setting up the Alert Production Database for ap_pipe
####################################################

.. Centralized markup for program names

.. |apdb-cli| replace:: :command:`apdb-cli`

.. |pipetask| replace:: :command:`pipetask`


In its default configuration, the Alert Production Pipeline, as represented by :file:`pipelines/ApPipe.yaml`, relies on a database to save and load DIASources and DIAObjects.
When running as part of the operational system, this database will be provided externally.
However, during testing and development, developers can run |apdb-cli| to set up their own database.
This page provides an overview of how to use |apdb-cli|.
Note that this document applies to APDB implementation backed by SQL database (SQLite or PostgreSQL), Cassandra-based implementation will use different set of options.

.. _section-ap-pipe-apdb-config:

Configuring the database
========================

The database is configured using `~lsst.dax.apdb.ApdbConfig`.

For |pipetask| users, the APDB is configured with the :option:`--config <pipetask run --config>` and :option:`--config-file <pipetask run --config-file>` options.
APDB configuration info uses the prefix ``diaPipe:apdb.``, with a colon, but is otherwise the same.

Note that the `~lsst.dax.apdb.ApdbConfig.db_url` field has no default; a value *must* be provided by the user.

Additionally, the default set of observed bands allowed to be used in the pipeline are set by the columns available in the Apdb schema specified by `~lsst.dax.ApdbConfig.schema_file`.
Should the user wish to use the pipeline on data containing bands not in the ``ugrizy`` system, they must add the appropriate columns to the Apdb schema and add the bands to the ``validBands`` config in `~lsst.ap.association.DiaPipelineConig`.

.. _section-ap-pipe-apdb-examples:

Examples
========

In Gen 3, this becomes (see :ref:`ap-pipe-pipeline-tutorial` for an explanation of |pipetask|):

.. prompt:: bash

   apdb-cli create-sql sqlite:///databases/apdb.db apdb_config.py
   pipetask run -p ApPipe.yaml -c diaPipe:apdb.db_url="sqlite:///databases/apdb.db" differencer:coaddName=dcr -b repo -o myrun

.. warning::

   Make sure the APDB is created with a configuration consistent with the one used by the pipeline.
   Note that the pipeline file given by ``-p`` may include APDB config overrides of its own.
   You can double-check what configuration is being run by calling :command:`pipetask run` with the ``--show config="apdb*"`` argument, though this lists *all* configuration options, including those left at their defaults.

The ``apdb_config.py`` argument to |apdb-cli| specifies the name of the created configuration file that will contain serialized `~lsst.dax.apdb.ApdbConfig` for the new database.
This file is not used yet by the ``pipetask`` options, but it will be used in the future.

A Postgres database can be set up and used with the following:

.. prompt:: bash
    
   apdb-cli create-sql --namespace='my_apdb_name' 'postgresql://rubin@usdf-prompt-processing-dev.slac.stanford.edu/lsst-devl' apdb_config.py
   pipetask run -p ApPipe.yaml -c diaPipe:apdb.db_url='postgresql://rubin@usdf-prompt-processing-dev.slac.stanford.edu/lsst-devl' -c diaPipe:apdb.namespace='my_apdb_name' -d "my_data_query" -b repo -i my/input/collection -o my/output/collection

A Postgres database can be set up and used within :ref:`bps yaml files <creating-a-yaml-file>` by adding this to a submit yaml:

.. code-block:: yaml

  extraQgraphOptions: "-c diaPipe:apdb.db_url='postgresql://rubin@usdf-prompt-processing-dev.slac.stanford.edu/lsst-devl' -c diaPipe:apdb.namespace='my_apdb_name'"

.. prompt:: bash

   apdb-cli create-sql --namespace='my_apdb_name' 'postgresql://rubin@usdf-prompt-processing-dev.slac.stanford.edu/lsst-devl' apdb_config.py
  
Note that |apdb-cli| must be run with the same `namespace` prior to submitting this bps yaml.
  
.. _section-ap-pipe-apdb-seealso:

Further reading
===============

- :doc:`pipeline-tutorial`

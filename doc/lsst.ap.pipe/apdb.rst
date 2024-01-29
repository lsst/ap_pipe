.. py:currentmodule:: lsst.ap.pipe

.. program:: make_apdb.py

.. _ap-pipe-apdb:

####################################################
Setting up the Alert Production Database for ap_pipe
####################################################

.. Centralized markup for program names

.. |make_apdb| replace:: :doc:`make_apdb.py <scripts/make_apdb.py>`

.. |pipetask| replace:: :command:`pipetask`


In its default configuration, the Alert Production Pipeline, as represented by :file:`pipelines/ApPipe.yaml`, relies on a database to save and load DIASources and DIAObjects.
When running as part of the operational system, this database will be provided externally.
However, during testing and development, developers can run |make_apdb| to set up their own database.
This page provides an overview of how to use |make_apdb|.

.. _section-ap-pipe-apdb-config:

Configuring the database
========================

The database is configured using `~lsst.dax.apdb.ApdbConfig`.

For |pipetask| users, the APDB is configured with the :option:`--config <pipetask run --config>` and :option:`--config-file <pipetask run --config-file>` options.
APDB configuration info uses the prefix ``diaPipe:apdb.``, with a colon, but is otherwise the same.

Note that the `~lsst.dax.apdb.ApdbConfig.db_url` field has no default; a value *must* be provided by the user.

Additionally, the default set of observed bands allowed to be used in the pipeline are set by the columns available in the Apdb schema specified by `~lsst.dax.ApdbConfig.schema_file` and `~lsst.dax.ApdbConfig.extra_schema_file`.
Should the user wish to use the pipeline on data containing bands not in the ``ugrizy`` system, they must add the appropriate columns to the Apdb schema and add the bands to the ``validBands`` config in `~lsst.ap.association.DiaPipelineConig`.

.. _section-ap-pipe-apdb-examples:

Examples
========

In Gen 3, this becomes (see :ref:`ap-pipe-pipeline-tutorial` for an explanation of |pipetask|):

.. prompt:: bash

   make_apdb.py -c db_url="sqlite:///databases/apdb.db"
   pipetask run -p ApPipe.yaml -c diaPipe:apdb.db_url="sqlite:///databases/apdb.db" differencer:coaddName=dcr -b repo -o myrun

.. warning::

   Make sure the APDB is created with a configuration consistent with the one used by the pipeline.
   Note that the pipeline file given by ``-p`` may include APDB config overrides of its own.
   You can double-check what configuration is being run by calling :command:`pipetask run` with the ``--show config="apdb*"`` argument, though this lists *all* configuration options, including those left at their defaults.
   
A Postgres database can be set up and used with the following:

.. prompt:: bash
    
   make_apdb.py -c db_url='postgresql://rubin@usdf-prompt-processing-dev.slac.stanford.edu/lsst-devl' -c namespace='my_apdb_name'
   pipetask run -p ApPipe.yaml -c diaPipe:apdb.db_url='postgresql://rubin@usdf-prompt-processing-dev.slac.stanford.edu/lsst-devl' -c diaPipe:apdb.namespace='my_apdb_name' -d "my_data_query" -b repo -i my/input/collection -o my/output/collection

Databases can also be set up using :ref:`config files <command-line-config-howto-configfile>`:

.. code-block:: py
   :caption: myApdbConfig.py

   config.db_url = "sqlite:///databases/apdb.db"

.. prompt:: bash

   make_apdb.py -C myApdbConfig.py
   pipetask run -p ApPipe.yaml -C myApPipeConfig.py  -b repo -o myrun
   
A Postgres database can be set up and used within :ref:`bps yaml files <creating-a-yaml-file>` by adding this to a submit yaml:

.. code-block:: yaml

  extraQgraphOptions: "-c diaPipe:apdb.db_url='postgresql://rubin@usdf-prompt-processing-dev.slac.stanford.edu/lsst-devl' -c diaPipe:apdb.namespace='my_apdb_name'"

.. prompt:: bash

   make_apdb.py -c db_url='postgresql://rubin@usdf-prompt-processing-dev.slac.stanford.edu/lsst-devl' -c namespace='my_apdb_name'
  
Note that `make_apdb.py` must be run with the same `namespace` prior to submitting this bps yaml.
  
.. _section-ap-pipe-apdb-seealso:

Further reading
===============

- :doc:`pipeline-tutorial`

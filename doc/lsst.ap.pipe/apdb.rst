.. py:currentmodule:: lsst.ap.pipe

.. _ap-pipe-apdb:

####################################################
Setting up the Alert Production Database for ap_pipe
####################################################

.. Centralized markup for program names

.. |apdb-cli| replace:: :command:`apdb-cli`

.. |pipetask| replace:: :command:`pipetask`


In its default configuration, the Alert Production Pipeline, as represented by :file:`pipelines/_ingredients/ApPipe.yaml`, relies on a database to save and load DIASources and DIAObjects.
When running as part of the operational system, this database will be provided externally.
However, during testing and development, developers can run |apdb-cli| to set up their own database.
This page provides an overview of how to integrate the AP pipeline with |apdb-cli|.

.. _section-ap-pipe-apdb-config:

Configuring the database
========================

The database is configured using |apdb-cli|, as described in the :ref:`dax_apdb documentation <lsst.dax.apdb-scripts>`.
If you are creating your own database, |apdb-cli| outputs a config file encoding the database settings.
If you are using a database set up by someone else, they should have provided you with a config file or its label in the APDB index (see :py:meth:`lsst.dax.apdb.Apdb.from_uri` for details).

Once you have a config file or label, you must pass it to the pipeline as the ``parameters:apdb_config`` config field (see :option:`--config <pipetask run --config>`).
Note that this parameter has no default; a value *must* be provided by the user.

Additionally, the default set of observed bands allowed to be used in the pipeline are set by the columns available in the Apdb schema specified by `~lsst.dax.apdb.ApdbConfig.schema_file`.
Should the user wish to use the pipeline on data containing bands not in the ``ugrizy`` system, they must add the appropriate columns to the Apdb schema and add the bands to the ``validBands`` config in `~lsst.ap.association.DiaPipelineConfig`.

.. _section-ap-pipe-apdb-examples:

Examples
========

To create an SQLite database from scratch, run the following (see the :ref:`dax_apdb documentation <lsst.dax.apdb-scripts>` for an explanation of |apdb-cli|, and :ref:`ap-pipe-pipeline-tutorial` for an explanation of |pipetask|):

.. prompt:: bash

   apdb-cli create-sql sqlite:///databases/apdb.db apdb_config.py
   apdb-cli metadata set apdb_config.py instrument MY_INSTRUMENT
   pipetask run -p ApPipe.yaml -c parameters:apdb_config=apdb_config.py differencer:coaddName=dcr -b repo -o myrun

The ``apdb_config.yaml`` argument to |apdb-cli| specifies the name of the created configuration file that will contain a serialized `~lsst.dax.apdb.ApdbConfig` for the new database.
Note that ``MY_INSTRUMENT`` should be the short name of the instrument whose data will populate this APDB instance (e.g. ``DECam`` or ``HSC``).

A Postgres database can be set up and used with the following.

.. prompt:: bash
    
   apdb-cli create-sql --namespace='my_apdb_name' 'postgresql://rubin@usdf-prompt-processing-dev.slac.stanford.edu/lsst-devl' apdb_config.py
   apdb-cli metadata set apdb_config.py instrument MY_INSTRUMENT
   pipetask run -p ApPipe.yaml -c parameters:apdb_config=apdb_config.py -d "my_data_query" -b repo -i my/input/collection -o my/output/collection

If a pre-existing database is registered in the ``dax_apdb`` index, this becomes:

.. prompt:: bash

   pipetask run -p ApPipe.yaml -c parameters:apdb_config=label:db_name -d "my_data_query" -b repo -i my/input/collection -o my/output/collection

A Postgres database can be set up and used within :ref:`bps yaml files <creating-a-yaml-file>` by adding this to a submit yaml:

.. code-block:: yaml

  extraQgraphOptions: "-c parameters:apdb_config=/path/to/apdb_config.py"
  
Note that |apdb-cli| must be run prior to submitting this bps yaml, and the path to the resulting config file (``apdb_config.py`` in this example) passed in ``extraQgraphOptions``.
  
.. _section-ap-pipe-apdb-seealso:

Further reading
===============

- :doc:`pipeline-tutorial`

.. py:currentmodule:: lsst.ap.pipe

.. _ap-pipe-pipeline-tutorial-gen2:

###############################
Running the AP pipeline (Gen 2)
###############################

Setup
=====

Pick up where you left off in :doc:`Getting Started <getting-started-gen2>`.
This means you already have a repository of ingested DECam data and have setup
the LSST Science Pipelines stack as well as ``ap_pipe`` and ``ap_association``.

Your directory structure should look something like

.. code-block:: none

   repo/   <-- where you will be running ap_pipe
      registry.sqlite3   <--- created during image ingestion
      2000-01-31/
          g/
              image1.fits   <--- linked here by default during image ingestion
              image2.fits
              ...
      ...
      ref_cats/   <--- copied or linked here manually by you
         gaia/
            shard1
            shard2
            ...
         pan-starrs/
            shard1
            shard2
            ...
      calibs/
         calibRegistry.sqlite3   <--- created/updated during calib ingestion
         cpBIAS/
            bias1.fits   <--- linked here by default during calib ingestion
            bias2.fits
            ...
         cpFLAT/
            flat1.fits   <--- linked here by default during calib ingestion
            flat2.fits
            ...
         defects/   <--- put here during curated calib ingestion
         crosstalk/   <--- put here during curated calib ingestion
      templates/   <--- does not need to be here, but needs to exist somewhere
         repositoryCfg.yaml
         deepCoadd/
            g/
               0/
                  0,0.fits
                  0,1.fits
                  ...

.. _section-ap-pipe-command-line-gen2:

AP pipeline on the command line
===============================

The executable to run for the AP Pipeline (`ApPipeTask`) is in ``ap_pipe/bin/ap_pipe.py``.

To process your ingested data, run

.. prompt:: bash

   mkdir apdb/
   make_apdb.py -c isolation_level=READ_UNCOMMITTED -c db_url="sqlite:///apdb/association.db"
   ap_pipe.py repo --calib repo/calibs --rerun processed -c diaPipe.apdb.isolation_level=READ_UNCOMMITTED -c diaPipe.apdb.db_url="sqlite:///apdb/association.db" --id visit=123456^123457 ccdnum=42 filter=g --template templates

In this case, a ``processed`` directory will be created within ``repo/rerun`` and the results will be written there.
See :doc:`apdb` for more information on :command:`make_apdb.py`.

This example command only processes observations that have a
:ref:`dataId<subsection-ap-pipe-previewing-dataIds-gen2>`
corresponding to visits 123456 and 123457, with ccdnum 42 and the g filter.

:doc:`lsst.ap.pipe <index>` supports ``dataId`` parsing, e.g., ``ccdnum=3^6..12`` will process
``ccdnums`` 3, 6, 7, 8, 9, 10, 11, and 12.

.. note::

   Until a resolution for `DM-12672 <https://jira.lsstcorp.org/browse/DM-12672>`_
   is found, you should include a filter in the ``dataId`` string for
   ``ap_pipe`` to run successfully.

If you prefer to have a standalone output repository, you may instead run

.. prompt:: bash

   ap_pipe.py repo --calib repo/calibs --output path/to/put/processed/data/in -c diaPipe.apdb.isolation_level=READ_UNCOMMITTED -c diaPipe.apdb.db_url="sqlite:///apdb/association.db" --id visit=123456^123457 ccdnum=42 filter=g --template path/to/templates

In this case, the output directory will be created if it does not already exist.
If you omit the ``--template`` flag, ``ap_pipe`` will assume the templates are
somewhere in ``repo``.

.. note::

   If you are using the default (SQLite) association database, you must :doc:`configure </modules/lsst.pipe.base/command-line-task-config-howto>` the database location, or ``ap_pipe`` will not run.
   The location is a path to a new or existing database file to be used for source associations (including associations with previously known objects, if the database already exists).
   In the examples above, it is configured with the ``-c`` option, but a personal config file may be more convenient if you intend to run ``ap_pipe`` many times.

.. _section-ap-pipe-expected-outputs-gen2:

Expected outputs
================

If you used the rerun option above, most of the output from ``ap_pipe`` should be written out in the repo/rerun/processed directory,.
The exception is the source association database, which will be written to the location you configure.
The result from running ``ap_pipe`` on DECam data should look something like

.. code-block:: none

   apdb/
      association.db   <--- the Alert Production Database with DIAObjects
   repo/
      rerun/
         processed/
            repositoryCfg.yaml
            deepDiff/
               v123456/   <--- difference images and DIASource tables are in here
               v123457/
            123456/   <--- all other processed data products are in here (calexps etc.)
            123457/

This is one example, and your rerun or output directory structure may differ.
Of course, to inspect this data with the Butler, you don't need to know
where it lives on disk. You should instead instantiate a Butler within python
in the ``processed`` directory and access the data products that way.

For example, in python

.. code-block:: python

   import lsst.daf.persistence as dafPersist
   butler = dafPersist.Butler('repo/rerun/processed')
   dataId = {'visit': 123456, 'ccdnum': 42, 'filter': 'g'}
   calexp = butler.get('calexp', dataId=dataId)
   diffim = butler.get('deepDiff_differenceExp', dataId=dataId)
   diaSourceTable = butler.get('deepDiff_diaSrc', dataId=dataId)


.. _section-ap-pipe-calexp-templates-gen2:

Calexp template mode
====================

By default, ``ap_pipe`` assumes you would like to use PSF-matched coadd images
as templates for difference imaging. However, the pipeline also supports
using calibrated exposures (``calexps``) as templates instead. A configuration file
``config/calexpTemplates.py`` is included witha ``ap_pipe`` to enable this.

.. note::

   This functionality is available in the Gen 2 alert production pipeline, but is not tested as thoroughly as coadd templates.
   For technical reasons, use of calexp templates will not be supported in the Gen 3 pipeline.

To use ap_pipe in calexp template mode, point to the config file with the
``--configfile`` (``-C``) flag and additionally specify the ``dataId`` of the template
with the ``--templateId`` flag, e.g.,

.. code-block:: none

   -C $AP_PIPE_DIR/config/calexpTemplates.py --templateId visit=234567

Be sure to also specify the location of the repo containing the calexp templates
with the ``--template`` flag if they are not in the main repo.
A full command looks like

.. prompt:: bash

   ap_pipe.py repo --calib repo/calibs --rerun processed -C $AP_PIPE_DIR/config/calexpTemplates.py -c diaPipe.apdb.isolation_level=READ_UNCOMMITTED -c diaPipe.apdb.db_url="sqlite:///apdb/association.db" --id visit=123456 ccdnum=42 filter=g --template /path/to/calexp/templates --templateId visit=234567


.. _section-ap-pipe-supplemental-info-gen2:

Supplemental information
========================

.. _subsection-ap-pipe-previewing-dataIds-gen2:

Previewing dataIds
------------------

So far, we have implicitly assumed that you know reasonable values to choose for the
dataId values (i.e., visit, ccdnum, and filter for DECam). While it is your
responsibility to ensure the data you want to process and your templates
do indeed overlap with each other, ap_pipe supports the ``--show data`` flag.

To get a list of all the g-band dataIds available in ``repo`` in lieu of actually
running ap_pipe, try

.. prompt:: bash
   
   ap_pipe.py repo --calib repo/calibs --rerun processed --id filter=g --show data


Running on other cameras
------------------------

Running ap_pipe on cameras other than DECam works much the same way: you need to provide a raw repo and either a rerun or an output repo, and you may need to provide calib or template repos.
The :ref:`calexp configuration file <section-ap-pipe-calexp-templates-gen2>` will work with any camera.

You will need to use a dataId formatted appropriately for the camera; check the camera's obs package documentation or consult the :ref:`--show data<subsection-ap-pipe-previewing-dataIds-gen2>` flag.

Common errors
-------------

* 'No locations for get': This means you are trying to access a data product
  which the Butler cannot find. It is common to encounter this if you do not
  have all of the calibration products in the right spot or a template image
  cannot be accessed.

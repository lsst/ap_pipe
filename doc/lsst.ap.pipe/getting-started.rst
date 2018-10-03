.. _getting-started:

####################################
Getting started with the AP Pipeline
####################################


.. _section-ap-pipe-installation:

Installation
============

`lsst.ap.pipe` is available from the `LSST Science Pipelines <https://pipelines.lsst.io/>`_.
It is installed as part of the ``lsst_apps`` and ``lsst_distrib`` metapackages.


.. _section-ap-pipe-ingesting-data-files:

Ingesting data files
====================

LSST-style image processing typically operates on Butler repositories and does not
directly interface with data files. `lsst.ap.pipe` is no exception.
The process of turning a set of raw data files and corresponding calibration
products into a format the Butler understands is called ingestion. Ingestion
can be somewhat camera-specific, and is outside the scope of the AP Pipeline.

.. TODO: Cut or condense above paragraph and link to ingestion-related docs.

A utility to ingest data before running `lsst.ap.pipe` 
is available in :ref:`ap-verify-run-ingest`. However, this works
only on datasets which adhere to the :ref:`ap-verify-datasets` format.
Alternately, you may use a pre-
ingested dataset or manually ingest files yourself following the directions
for a given ``obs_`` package, e.g.,
step 4 of `the obs_decam README <https://github.com/lsst/obs_decam/blob/master/README.md>`_.

A standard ingestion workflow for DECam looks something like

.. prompt:: bash

   ingestImagesDecam.py input_loc --filetype raw path/to/raw/files
   ingestCalibs.py input_loc --calib calib_loc path/to/flats/and/biases --validity 999
   ingestCalibs.py input_loc --calib calib_loc --calibType defect --mode=skip path/to/defects --validity 0

.. note::

   Defect ingestion is a step unique to DECam. It presently requires 
   ``--mode=skip``, this mode interprets paths as relative to ``calib_loc``,
   and the validity value is not used (but must be included). This interface
   may change when `DM-5467 <https://jira.lsstcorp.org/browse/DM-5467>`_ is completed.


.. _section-ap-pipe-required-data-products:

Required data products
======================

For the AP Pipeline to successfully process data, the following is required:

- **Raw science images** and `reference catalogs 
  <https://community.lsst.org/t/creating-and-using-new-style-reference-catalogs/1523>`_
  ingested into a main Butler repository

  - The reference catalogs must be in a directory called `ref_cats` with subdirectories
    for each catalog containing the appropriate catalog shards.
    We recommend using Pan-STARRS for photometry and gaia for astrometry.
    An example :ref:`config file <command-line-task-config-howto-configfile>` for using these two catalogs can be found in the `ap_verify_hits2015`_ repository.
    
- **Calibration products** (biases, flats, and defects, if applicable)
  ingested into a Butler repository you must specify with the ``--calib`` flag on
  the command line at runtime
  
  - To check if this requirement has been satisfied, you can inspect the
    `calibRegistry.sqlite3` created in this repository and ensure the information
    in the flat, bias, and defect tables is accurate
    
- **Template images** (of type ``deepCoadd`` by default) for difference imaging
  must be either in the main Butler repository or in another location you may
  specify with the ``--template`` flag on the command line at runtime

.. TODO: update default for DM-14601

.. _ap_verify_hits2015: https://github.com/lsst/ap_verify_hits2015/

A sample dataset from the `DECam HiTS survey <http://iopscience.iop.org/article/10.3847/0004-637X/832/2/155/meta>`_ 
that works with ``ap_pipe`` in the :ref:`ap-verify-datasets` format
is available as `ap_verify_hits2015`_. However, this dataset must be
ingested as described in :ref:`section-ap-pipe-ingesting-data-files`, and the reference
catalog and defect files must be decompressed and extracted.

Please continue to :doc:`Pipeline Tutorial <pipeline-tutorial>` for more
details about running the AP Pipeline and interpreting the results.

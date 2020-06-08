.. py:currentmodule:: lsst.ap.pipe

.. _ap-pipe-getting-started:

.. _ap-pipe-getting-started-gen3:

############################################
Getting started with the AP pipeline (Gen 3)
############################################


.. _section-ap-pipe-installation:

Installation
============

:doc:`lsst.ap.pipe <index>` is available from the `LSST Science Pipelines <https://pipelines.lsst.io/>`_.
It is installed as part of the ``lsst_distrib`` metapackage, which also includes infrastructure for running the pipeline from the command line.


.. _section-ap-pipe-ingesting-data-files:

Ingesting data files
====================

Vera Rubin Observatory-style image processing typically operates on Butler repositories and does not directly interface with data files.
:doc:`lsst.ap.pipe <index>` is no exception.
The process of turning a set of raw data files and corresponding calibration products into a format the Butler understands is called ingestion.
Ingestion for the Generation 3 Butler is still being developed, and is outside the scope of the AP Pipeline.

.. TODO: fill in details once we know what happens with image-like calibs


.. _section-ap-pipe-required-data-products:

Required data products
======================

For the AP Pipeline to successfully process data, the following must be present in a Butler repository:

- **Raw science images** to be processed.

- **Reference catalogs** covering at least the area of the raw images.
  We recommend using Pan-STARRS for photometry and Gaia for astrometry.

- **Calibration products** (biases, flats, and possibly others, depending on the instrument)

- **Template images** for difference imaging.
  These are of type ``deepCoadd`` by default, but the AP pipeline can be configured to use other types.

.. TODO: update default for DM-14601

.. _ap_verify_hits2015: https://github.com/lsst/ap_verify_hits2015/

A sample dataset from the `DECam HiTS survey <http://iopscience.iop.org/article/10.3847/0004-637X/832/2/155/meta>`_ that works with ``ap_pipe`` in the :doc:`/modules/lsst.ap.verify/datasets` format is available as `ap_verify_hits2015`_.
However, raw images from this dataset must be ingested.

Please continue to :doc:`the Pipeline Tutorial <pipeline-tutorial>` for more details about running the AP Pipeline and interpreting the results.

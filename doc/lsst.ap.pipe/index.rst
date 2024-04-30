.. py:currentmodule:: lsst.ap.pipe

.. _lsst.ap.pipe:

############
lsst.ap.pipe
############

.. Paragraph that describes what this Python module does and links to related modules and frameworks.

The ``lsst.ap.pipe`` module links together a set of common image processing tasks so that a user may run one command on a dataset of raw, ingested images rather than several.
The Alert Production (AP) pipeline includes the following key data processing Tasks for LSST Prompt Data Products: `~lsst.ip.isr.IsrTask`, `~lsst.pipe.tasks.characterizeImage.CharacterizeImageTask`, `~lsst.pipe.tasks.calibrate.CalibrateTask`, `~lsst.ip.diffim.subtractImages.AlardLuptonSubtractTask`, `~lsst.ip.diffim.detectAndMeasure.DetectAndMeasureTask`, and `~lsst.ap.association.DiaPipelineTask`.

At present, the alert production pipeline is implemented using the Gen 3 framework:

- ``ApPipe`` is an `lsst.pipe.base.Pipeline` that reads and writes data using the :ref:`lsst.daf.butler` package.

.. TODO: add links to Gen 3 docs as they become available

Overview
========

.. toctree::
   :maxdepth: 1

   pipeline-overview

.. _lsst.ap.pipe-using:

.. _lsst.ap.pipe-using-gen3:

Using lsst.ap.pipe in Gen 3
===========================

.. toctree::
   :maxdepth: 1

   getting-started
   pipeline-tutorial
   apdb
   pipeline-bps

.. _lsst.ap.pipe-contributing:

Contributing
============

``lsst.ap.pipe`` is developed at https://github.com/lsst/ap_pipe.
You can find Jira issues for this module under the `ap_pipe <https://rubinobs.atlassian.net/issues/?jql=project%20%3D%20DM%20AND%20component%20%3D%20ap_pipe>`_ component.

.. If there are topics related to developing this module (rather than using it), link to this from a toctree placed here.

Script reference
================

.. toctree::
   :maxdepth: 1

   scripts/make_apdb.py

.. _lsst.ap.pipe-pyapi:

Python API reference
====================

.. automodapi:: lsst.ap.pipe
   :no-main-docstr:
   :no-inheritance-diagram:

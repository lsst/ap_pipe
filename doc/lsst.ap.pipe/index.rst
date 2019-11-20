.. py:currentmodule:: lsst.ap.pipe

.. _lsst.ap.pipe:

############
lsst.ap.pipe
############

.. Paragraph that describes what this Python module does and links to related modules and frameworks.

The ``lsst.ap.pipe`` module links together a set of common image processing tasks so that a user may run one Command-Line Task on a dataset of raw, ingested images rather than several.
The Alert Production (AP) pipeline includes three key data processing Tasks for LSST Prompt Data Products: `~lsst.pipe.tasks.ProcessCcdTask` (which includes `~lsst.ip.isr.IsrTask`),  `~lsst.ip.diffim.ImageDifferenceTask`, and `~lsst.ap.associate.AssociationTask`.

Overview
========

.. toctree::
   :maxdepth: 1
   
   pipeline-overview

.. .. _lsst.ap.pipe-using:

Using lsst.ap.pipe
==================

.. toctree::
   :maxdepth: 1
   
   getting-started
   pipeline-tutorial
   apdb

.. _lsst.ap.pipe-contributing:

Contributing
============

``lsst.ap.pipe`` is developed at https://github.com/lsst/ap_pipe.
You can find Jira issues for this module under the `ap_pipe <https://jira.lsstcorp.org/issues/?jql=project%20%3D%20DM%20AND%20component%20%3D%20ap_pipe>`_ component.

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

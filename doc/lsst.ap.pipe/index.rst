.. _lsst.ap.pipe:

############
lsst.ap.pipe
############

.. Paragraph that describes what this Python module does and links to related modules and frameworks.

The ``lsst.ap.pipe`` module links together a set of common image processing
tasks so that a user may run one Command-Line Task on a dataset of raw,
ingested images rather than several. The Alert Production (AP) pipeline
includes three key data processing Tasks for LSST Prompt Data Products:
`~lsst.pipe.tasks.ProcessCcdTask` (which includes `~lsst.ip.isr.IsrTask`), 
`~lsst.ip.diffim.ImageDifferenceTask`, and
`~lsst.ap.associate.AssociationTask`.

.. Add subsections with toctree to individual topic pages.

Overview
========

.. toctree::
   :maxdepth: 1
   
   pipeline-overview.rst
   

Running the AP Pipeline
=======================

.. toctree::
   :maxdepth: 1
   
   getting-started.rst
   pipeline-tutorial.rst


Python API reference
====================

.. automodapi:: lsst.ap.pipe

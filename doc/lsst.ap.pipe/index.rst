.. py:currentmodule:: lsst.ap.pipe

.. _lsst.ap.pipe:

############
lsst.ap.pipe
############

.. Paragraph that describes what this Python module does and links to related modules and frameworks.

The ``lsst.ap.pipe`` module links together a set of common image processing tasks so that a user may run one command on a dataset of raw, ingested images rather than several.
The Alert Production (AP) pipeline includes the following key data processing Tasks for LSST Prompt Data Products: `~lsst.ip.isr.IsrTask`, `~lsst.pipe.tasks.characterizeImage.CharacterizeImageTask`, `~lsst.pipe.tasks.calibrate.CalibrateTask`, `~lsst.pipe.tasks.imageDifference.ImageDifferenceTask`, and `~lsst.ap.association.DiaPipelineTask`.

At present, the alert production pipeline is implemented using two separate frameworks that store and retrieve data from "Butler" repositories in incompatible ways:

- `ApPipeTask` is an `lsst.pipe.base.CmdLineTask` that reads and writes data using the :ref:`lsst.daf.persistence` package.
  This is the established "Gen 2" framework.
- ``ApPipe`` is an `lsst.pipe.base.Pipeline` that reads and writes data using the :ref:`lsst.daf.butler` package.
  This "Gen 3" framework is expected to be the only implementation in the future.

.. TODO: add links to Gen 3 docs as they become available

Overview
========

.. toctree::
   :maxdepth: 1

   pipeline-overview

.. _lsst.ap.pipe-using-gen2:

Using lsst.ap.pipe in Gen 2
===========================

.. toctree::
   :maxdepth: 1

   getting-started-gen2
   pipeline-tutorial-gen2
   apdb

.. _lsst.ap.pipe-using:

.. _lsst.ap.pipe-using-gen3:

Using lsst.ap.pipe in Gen 3
===========================

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

Task reference
==============

.. _lsst.ap.pipe-command-line-tasks:

Command-line tasks
------------------

.. lsst-cmdlinetasks::
   :root: lsst.ap.pipe
   :toctree: tasks

.. _lsst.ap.pipe-pyapi:

Python API reference
====================

.. automodapi:: lsst.ap.pipe
   :no-main-docstr:
   :no-inheritance-diagram:

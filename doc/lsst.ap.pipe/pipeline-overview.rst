.. py:currentmodule:: lsst.ap.pipe

.. _pipeline-overview:

###########################
Overview of the AP pipeline
###########################

:doc:`lsst.ap.pipe <index>` is a data processing pipeline for Prompt Data Products.
It is a Command-Line Task which operates on ingested raw data in a Butler repository.
It also requires appropriate calibration products and templates. As it runs,
`ApPipeTask` generates calibrated exposures, difference images,
difference image source catalogs, and a source association database.

The initial motivation for :doc:`lsst.ap.pipe <index>`, information about one of the original test datasets,
and an outdated tutorial are available in `DMTN-039 <https://dmtn-039.lsst.io>`_.

The AP Pipeline calls three main tasks and their associated subtasks:

1. `~lsst.pipe.tasks.ProcessCcdTask`, which in turn calls `lsst.ip.isr.IsrTask`,
   `lsst.pipe.tasks.CharacterizeImageTask`, and `lsst.pipe.tasks.CalibrateTask`
   to perform image reduction as well as photometric and astrometric calibration;
2. `~lsst.pipe.tasks.ImageDifferenceTask`, which uses many utilities from
   :doc:`lsst.ip.diffim </modules/lsst.ip.diffim/index>`; and
3. `~lsst.ap.associate.AssociationTask`, which makes a catalog of
   Difference Image Analysis (DIA) Objects from the DIASources created
   during image differencing.

In practice, :doc:`lsst.ap.pipe <index>` is often discussed in the context of :doc:`lsst.ap.verify </modules/lsst.ap.verify/index>`.
The former is responsible for running the AP Pipeline. The latter uses :doc:`lsst.ap.pipe <index>`
to verify the output.

:doc:`ap_pipe <index>` is entirely written in Python. Key contents include:

- `ApPipeTask`: a `~lsst.pipe.base.CmdLineTask` for running the entire AP Pipeline
- `ApPipeConfig`: a config for customizing ``ApPipeTask`` for a particular dataset's needs.
  Supported observatory packages should provide a :ref:`config override file <command-line-task-config-howto-obs>` that does most of the work.


.. py:currentmodule:: lsst.ap.pipe

.. _pipeline-overview:

###########################
Overview of the AP pipeline
###########################

:doc:`lsst.ap.pipe <index>` is a data processing pipeline for Prompt Data Products.
It operates on ingested raw data in a Butler repository.
It also requires appropriate calibration products and templates. As it runs,
the pipeline generates calibrated exposures, difference images,
difference image source catalogs, and a source association database.

The initial motivation for :doc:`lsst.ap.pipe <index>`, information about one of the original test datasets,
and an outdated tutorial are available in `DMTN-039 <https://dmtn-039.lsst.io>`_.

The AP Pipeline calls several main tasks and their associated subtasks:

#. `~lsst.ip.isr.IsrTask`, which performs image reduction;
#. `~lsst.pipe.tasks.characterizeImage.CharacterizeImageTask`, which estimates the background and point-spread function of an image;
#. `~lsst.pipe.tasks.calibrate.CalibrateTask`, which performs photometric and astrometric calibration;
#. `~lsst.pipe.tasks.imageDifference.ImageDifferenceTask`, which uses many utilities from
   :doc:`lsst.ip.diffim </modules/lsst.ip.diffim/index>`; and
#. `~lsst.ap.association.DiaPipelineTask`, which makes a catalog of
   Difference Image Analysis (DIA) Objects from the DIASources created
   during image differencing.

In practice, :doc:`lsst.ap.pipe <index>` is often discussed in the context of :doc:`lsst.ap.verify </modules/lsst.ap.verify/index>`.
The former is responsible for running the AP Pipeline. The latter uses :doc:`lsst.ap.pipe <index>`
to verify the output.

:doc:`ap_pipe <index>` is entirely written in Python. Key contents include:

- `ApPipeTask`: a `~lsst.pipe.base.CmdLineTask` for running the entire AP Pipeline in the older, "Gen 2" data processing framework
- `ApPipeConfig`: a config for customizing ``ApPipeTask`` for a particular dataset's needs.
  Supported observatory packages should provide a :ref:`config override file <command-line-task-config-howto-obs>` that does most of the work.
- :file:`ApPipe.yaml`: a `~lsst.pipe.base.Pipeline` configuration for running the entire AP Pipeline in the newer, "Gen 3" framework

By default the pipeline is limited to running on data taken in filter bands whose names match those used by the Rubin Observatory LSST Camera (that is `ugrizy`).
In order to run on bands outside of these filters, one must add the associated columns to the `~lsst.dax.apdb.Apdb` schema and add the band names to the config of `~lsst.ap.association.DiaPipelineTask`.

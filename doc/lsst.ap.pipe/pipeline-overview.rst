.. py:currentmodule:: lsst.ap.pipe

.. _pipeline-overview:

###########################
Overview of the AP pipeline
###########################

:doc:`lsst.ap.pipe <index>` is a data processing pipeline for Prompt Data Products.
It operates on ingested raw data in a Butler repository.
It also requires appropriate calibration products and templates. As it runs,
the pipeline generates calibrated images, difference images,
difference image source catalogs, and a source association database.

The initial motivation for :doc:`lsst.ap.pipe <index>`, information about one of the original test datasets,
and an outdated tutorial are available in `DMTN-039 <https://dmtn-039.lsst.io>`_.

The AP Pipeline calls several main tasks and their associated subtasks:

#. `~lsst.ip.isr.IsrTask`, which performs image reduction;
#. `~lsst.pipe.tasks.characterizeImage.CharacterizeImageTask`, which estimates the background and point-spread function of an image;
#. `~lsst.pipe.tasks.calibrate.CalibrateTask`, which performs photometric and astrometric calibration;
#. `~lsst.ip.diffim.subtractImages.AlardLuptonSubtractTask`, which subtracts a warped template from an image;
#. `~lsst.ip.diffim.detectAndMeasure.DetectAndMeasureTask`, which detects and measures diaSources on an image difference and
#. `~lsst.ap.association.DiaPipelineTask`, which makes a catalog of
   Difference Image Analysis (DIA) Objects from the DIASources created
   during image differencing.

In practice, :doc:`lsst.ap.pipe <index>` is often discussed in the context of :doc:`lsst.ap.verify </modules/lsst.ap.verify/index>`.
The former is responsible for running the AP Pipeline. The latter uses :doc:`lsst.ap.pipe <index>`
to verify the output.

:doc:`ap_pipe <index>` is entirely written in Python. Key contents include:

- :file:`ApPipe.yaml`: a `~lsst.pipe.base.Pipeline` configuration for running the entire AP Pipeline.
- :file:`LSSTCam/ApPipeDaytime.yaml`: the variant used for daytime (non-real-time) LSSTCam processing.
  It drops ``loadDiaCatalogs`` and has `~lsst.ap.association.DiaPipelineTask` read the DIAObject and
  DIASource history from the APDB during association, so that the duplicate DIASource check sees rows
  written by any earlier pass over the same image.
  Prompt Processing must not use it; the preload is what keeps the APDB out of its latency-critical path.
- :file:`ApPipe-legacy.yaml` and :file:`ApPipeWithPreconvolution-legacy.yaml`: variants that write legacy afw images.
  See :ref:`pipeline-overview-image-types`.

By default the pipeline is limited to running on data taken in filter bands whose names match those used by the Rubin Observatory LSST Camera (that is `ugrizy`).
In order to run on bands outside of these filters, one must add the associated columns to the `~lsst.dax.apdb.Apdb` schema and add the band names to the config of `~lsst.ap.association.DiaPipelineTask`.

.. _pipeline-overview-image-types:

Image types
===========

The ``image_type`` pipeline parameter, declared in :file:`_ingredients/ApPipe.yaml`, selects the storage classes of the image datasets.
The default, ``future``, writes ``lsst.images`` types: ``VisitImage`` for ``preliminary_visit_image``, and ``DifferenceImage`` for the template and difference images.
The value ``legacy`` writes afw ``ExposureF`` datasets.
The parameter also applies to the imported ``analysis_tools`` pipeline, and overrides the value that pipeline declares.

Two connections name a component of an image dataset.
The component names differ between the two types, so the parameter cannot switch them:

- ``buildTemplate:connections.wcs``: ``preliminary_visit_image.sky_projection`` (future) or ``preliminary_visit_image.wcs`` (legacy).
- ``filterDiaSource:connections.diffImVisitInfo``: ``difference_image.obs_info`` (future) or ``difference_image.visitInfo`` (legacy).

The instrument directories provide :file:`ApPipe-legacy.yaml` and, where the base pipeline exists, :file:`ApPipeWithPreconvolution-legacy.yaml`.
These set ``image_type: legacy`` and override both connections.
:file:`LSSTComCamSim/ApPipe.yaml` and :file:`LSSTCam/ApPipeDaytime.yaml` have no legacy variant; :ref:`section-ap-pipe-legacy-images` shows how to run them in legacy mode.
The :file:`SingleFrame.yaml` pipelines contain neither connection, so ``-c parameters:image_type=legacy`` alone switches them.
The ``ApPipeWithFakes`` pipelines always write legacy images; see :doc:`ap-pipe-pipeline-with-fakes`.

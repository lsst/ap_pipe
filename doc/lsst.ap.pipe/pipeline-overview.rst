.. _pipeline-overview:

###########################
Overview of the AP Pipeline
###########################

:doc:`lsst.ap.pipe <index>` is a data processing pipeline for Prompt Data Products.
It is a Command-Line Task which operates on ingested raw data in a Butler repository.
It also requires appropriate calibration products and templates. As it runs,
`lsst.ap.pipe.ApPipeTask` generates calibrated exposures, difference images,
difference image source catalogs, and a source association database.

The initial motivation for `lsst.ap.pipe`, information about one of the original test datasets,
and an outdated tutorial are available in `DMTN-039 <https://dmtn-039.lsst.io>`_.

The AP Pipeline calls three main tasks and their associated subtasks:

1. `~lsst.pipe.tasks.ProcessCcdTask`, which in turn calls `lsst.ip.isr.IsrTask`,
   `lsst.pipe.tasks.CharacterizeImageTask`, and `lsst.pipe.tasks.CalibrateTask`
   to perform image reduction as well as photometric and astrometric calibration;
2. `~lsst.pipe.tasks.ImageDifferenceTask`, which uses many utilities from
   `lsst.ip.diffim`; and
3. `~lsst.ap.associate.AssociationTask`, which makes a catalog of
   Difference Image Analysis (DIA) Objects from the DIASources created
   during image differencing.

In practice, `lsst.ap.pipe` is often discussed in the context of `lsst.ap.verify`.
The former is responsible for running the AP Pipeline. The latter uses `lsst.ap.pipe`
to verify the output.

`ap_pipe` is entirely written in Python. Key contents include:

- `~lsst.ap.pipe.ApPipeTask`: a `~lsst.pipe.base.CmdLineTask` for running the entire AP Pipeline


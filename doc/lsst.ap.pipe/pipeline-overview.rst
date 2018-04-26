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

In practice, `lsst.ap.pipe` is often discussed in the context of `lsst.ap.verify`.
The former is responsible for running the AP Pipeline. The latter uses `lsst.ap.pipe`
to verify the output.

`ap_pipe` is entirely written in Python. Key contents include:

- `~lsst.ap.pipe.ApPipeTask`: a `~lsst.pipe.base.CmdLineTask` for running the entire AP Pipeline
- `~lsst.ap.pipe.MaxPsfWcsSelectImagesTask`: a `~lsst.pipe.tasks.selectImages.WcsSelectImagesTask` 
    for selecting images with good PSFs to create a coadd template

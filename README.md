# ap_pipe

This package contains the LSST Data Management Alert Production Pipeline.

For up-to-date documentation, including a tutorial, see the `doc` directory.

ap_pipe processes raw images that have been ingested into a Butler repository
with corresponding calibration products and templates. It produces calexps,
difference images and source catalogs, and an association database.

The user must specify the main repository with ingested images (and the
location of the calibration products and templates if they reside elsewhere),
the name of the association database (may be either created from scratch or
connected to for continued associating), and a Butler data ID.

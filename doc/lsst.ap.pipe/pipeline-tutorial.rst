.. _pipeline-tutorial:

####################
AP Pipeline Tutorial
####################

.. note::

   Coming soon!

This section will provide a brief tutorial for processing a dataset with ``ap_pipe``.

It will begin assuming the user has ingested data and the appropriate stack
packages already setup (see :doc:`Getting Started <getting-started>`).
It will end with making some plots using the association database that is created
as the final step of `lsst.ap.pipe`.

- Include notes about DECam peculiarities
- Discuss where to put templates since that is super non-obvious
- Describe all the new data products created and what they're good for
- Catch common pitfalls (NO LOCATIONS FOR GET, what else?)
- Explain briefly what each step does (processCcd: ISR, image characterization, 
  calibration; diffim; and association) but also include links to those
  tasks' future amazing numpydoc pages
- 
.. _getting-started:

####################################
Getting started with the AP Pipeline
####################################

`lsst.ap.pipe` is not yet included with the LSST Science Pipelines stack.
You will need to clone and set it up by following the directions
`here <https://pipelines.lsst.io/install/package-development.html>`_.

.. note::

   `lsst.ap.association` is a prerequisite for `lsst.ap.pipe`.
   You must clone ``ap_association`` and set it up first.

The Command-Line Task you will need to run for the AP Pipeline is
``ap_pipe/bin/ap_pipe.py``.

For example, to process ingested data in ``input_loc`` with calibration products
(including an appropriate template) residing in ``calib_loc``, one may run

.. code-block:: none
   
   ap_pipe.py input_loc --calib calib_loc --output output_loc --id visit=123456 ccdnum=12

This command only processes observations that have a ``dataId`` corresponding to
visit 123456 and ccdnum 12. The user must specify a ``dataId`` string or
no data will be processed.

`lsst.ap.pipe` has only been used on DECam (and, correspondingly, with `lsst.obs.decam`)
so far, and does not yet support data from other cameras.

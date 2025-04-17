.. py:currentmodule:: lsst.ap.pipe

.. _ap-pipe-pipeline-tutorial:

.. _ap-pipe-pipeline-tutorial-gen3:

#######################
Running the AP pipeline
#######################

Setup
=====

Pick up where you left off in :doc:`Getting Started <getting-started>`.
This means you already have a repository of ingested DECam data and have set up the LSST Science Pipelines stack.

Your repository should have the following collections, which can be checked using ``butler query-collections <repo>``:

- **DECam/calib**: biases, flats, defects, camera specs, etc.
- **DECam/raw/all**: images to be processesd
- **refcats**: reference catalogs for calibration
- **skymaps**: index for the templates
- **templates/deep**: ``deepCoadd`` templates for difference imaging


.. _section-ap-pipe-command-line:

AP pipeline on the command line
===============================

Like most Vera Rubin Observatory pipelines, the AP Pipeline is run with an external runner called ``pipetask``.
This can be found in the ``ctrl_mpexec`` package, which is included as part of ``lsst_distrib``.

The pipeline itself is configured in `ap_pipe/pipelines/DECam/ApPipe.yaml <https://github.com/lsst/ap_pipe/blob/master/pipelines/DECam/ApPipe.yaml>`_.

To process your ingested data, run

.. prompt:: bash

   apdb-cli create-sql "sqlite:///apdb.db" apdb_config.yaml
   apdb-cli metadata set apdb_config.yaml instrument DECam
   pipetask run -p ${AP_PIPE_DIR}/pipelines/DECam/ApPipe.yaml \
       --register-dataset-types -c parameters:coaddName=deep \
       -c isr:connections.bias=cpBias -c isr:connections.flat=cpFlat \
       -c parameters:apdb_config=apdb_config.yaml -b repo/ \
       -i "DECam/defaults,DECam/raw/all" -o processed \
       -d "visit in (411420, 419802) and detector=10"

In this case, a ``processed/<timestamp>`` collection will be created within ``repo`` and the results will be written there.
The ``apdb_config.yaml`` file will be created by ``apdb-cli`` and passed to ``pipetask``.
See :doc:`apdb` for more information on :command:`apdb-cli`.

This example command only processes observations corresponding to visits 411420 and 419802, both with only detector 10.

The example creates a "chained" output collection that can refer back to its inputs.
If you prefer to have a standalone output collection, you may instead run

.. prompt:: bash

   pipetask run -p ${AP_PIPE_DIR}/pipelines/DECam/ApPipe.yaml \
       --register-dataset-types -c parameters:coaddName=deep \
       -c isr:connections.bias=cpBias -c isr:connections.flat=cpFlat \
       -c parameters:apdb_config=apdb_config.yaml -b repo/ \
       -i "DECam/defaults,DECam/raw/all" --output-run processed \
       -d "visit in (411420, 419802) and detector=10"

.. note::

   You must :doc:`configure </modules/lsst.ctrl.mpexec/configuring-pipetask-tasks>` the pipeline to use the APDB config file, or ``ap_pipe`` will not run.
   In the examples above, it is configured with the ``-c`` option.

.. note::

   Both examples above are only valid when running the pipeline for the first time.
   When rerunning with an existing chained collection using ``-o``, you should omit the ``-i`` argument.
   When rerunning with an existing standalone collection using ``--output-run``, you must pass ``--extend-run``.

.. _section-ap-pipe-expected-outputs:

Expected outputs
================

If you used the chained option above, most of the output from ``ap_pipe`` should be written to a timestamped collection (e.g., ``processed/20200131T00h00m00s``) in the repository.
The exception is the source association database, which will be written to the location you configure.
The result from running ``ap_pipe`` should look something like

.. code-block:: none

   apdb.db   <--- the Alert Production Database with DIAObjects
   repo/
      contains_no_user_servicable_files/

To inspect this data with the Butler, you should instantiate a Butler within python and access the data products that way.

For example, in python

.. code-block:: python

   import lsst.daf.butler as dafButler
   butler = dafButler.Butler('repo', collections="processed")  # collections keyword is optional
   dataId = {'instrument': 'DECam', 'visit': 123456, 'detector': 42}
   calexp = butler.get('calexp', dataId=dataId)
   diffim = butler.get('deepDiff_differenceExp', dataId=dataId)
   diaSourceTable = butler.get('deepDiff_diaSrc', dataId=dataId)


.. _section-ap-pipe-supplemental-info:

Supplemental information
========================

Running on other cameras
------------------------

Running ap_pipe on cameras other than DECam works much the same way.
You need to provide a repository containing raws, calibs, and templates appropriate for the camera.
There are versions of the AP pipeline for DECam, HSC, LATISS, and ImSim.

Common errors
-------------

.. TODO: update (or remove!) after DM-25013

* 'KeyError: DatasetType <type> could not be found': This usually means you left out the ``--register-dataset-types`` argument.
* 'Expected exactly one instance of input <arbitrary dataset>': This may mean an invalid pipeline, but can also mean that you did not provide an ``-i`` or ``--input`` argument when it was required.
  This is especially likely if the data ID is not one of the expected values.

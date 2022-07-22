.. py:currentmodule:: lsst.ap.pipe

.. _ap-pipe-pipeline-bps:

############################################################
Running the AP pipeline in the Batch Production System (bps)
############################################################

.. _section-ap-pipe-pipeline-bps-setup:

Setup
=====

Pick up where you left off in :doc:`Pipeline Tutorial <pipeline-tutorial>`. 
While our examples here are with HSC data, the basic principles are the same for working with data from any telescope supported by the LSST pipelines, such as DECam.
You of course have to set the instrument, visit(s), and detector(s) appropriately.
Assuming you are on one of the lsst-devl machines (paths may differ if you are not) you would do run the following commands:

.. prompt:: bash

  . /software/lsstsw/stack/loadLSST.bash
  setup lsst_distrib -t your_favorite_weekly

As of March 2022 there is a need to do one more thing after the usual setups in order to pick up the appropriate HTCondor libraries:

.. prompt:: bash

  export PYTHONPATH=$PYTHONPATH:/usr/lib64/python3.6/site-packages

It is not known how long it will continue to be necessary, but since the new directory is appended to PYTHONPATH, any newer packages would be picked up first.

.. _section-ap-pipe-pipeline-bps-yaml:

Creating a yaml file
====================

Next we need to create a yaml file for submission. 
Typically it will contain info about the processing campaign, desired input and output collections, resource requests for the various job types, and can include other yaml files (as we will do this this example).

Here's an example .yaml file governing what gets passed to pipetask.
It is simply a slightly modified version of the example in `ap_pipe/bps/bps_ApPipe.yaml <https://github.com/lsst/ap_pipe/blob/main/bps/bps_ApPipe.yaml>`_.
Again, as of March 2022 this assumes you are running on one of the lsst-devl machines at NCSA.

.. code-block:: yaml


  # Path to the pipeline to run

  pipelineYaml: '/path/to/my/pipeline.yaml'
  # Format for job names and job output filenames
  templateDataId: '{tract}_{patch}_{band}_{visit}_{exposure}_{detector}'
  project: ApPipe
  campaign: my_example
  
  # Directory where files associated with your submission, such as logs, will go.
  submitPath: ${PWD}/bps/{outputRun}
  computeSite: ncsapool
  site:
    ncsapool:
      profile:
        condor:
          +Walltime: 28800
  # Memory allocated for each quantum, in MBs
  requestMemory: 2048
  # CPUs to use per quantum; 1 is default.
  requestCpus: 1
  
  # Arguments you would pass to pipetask run if running from the command line instead of in a bps job.
  # Further arguments are given in the calls to 'runQuantumCommand' (see below).
  payload:
    # Specifies whether to run --init-only on each pipetask run before doing the real pipetask run.
    runInit: true
    # This will set the output collection name.
    payloadName: my_example_name
    # Same as -b on the command line.
    butlerConfig: /datasets/hsc/gen3repo/rc2w50_ssw02/butler.yaml
    # Same as -i on the command line; actual input collections may differ from what is shown here.
    inCollection: HSC/calib,HSC/raw/all,refcats,u/diffim_sprint/templates_bestThirdSeeing
    # Same as -o on the command line. Note: must specify outCollection with timestamp so you don't get innumerable sub-runs.
    output : 'u/${USER}/{payloadName}'
    # Same as -d on the command line. Here is an example of a small data query just for testing.
    dataQuery: 'exposure IN (11690, 11692) AND detector in (49, 50)'
  
  # Various things for bps to customize about each pipeline task.
  pipetask:
    # Here you can set options to various pipeline tasks if they should run with something other than the defaults you specified above.
    subtractImages:
      requestMemory: 4096

Notes on the yaml file
----------------------
* A good example of a complete pipeline yaml is `ap_pipe/pipelines/ApPipe.yaml <https://github.com/lsst/ap_pipe/blob/main/pipelines/ApPipe.yaml>`_.

  * You can simply import that, or you may want to make other changes.
* The `computeSite` option determines where your jobs will run; as of now (March 2022) the typical choice will be `ncsapool`.

  * Other options may be possible in the future; see the `ctrl_bps <https://pipelines.lsst.io/modules/lsst.ctrl.bps/index.html>`_ documentation.
  * One can also ask the bps experts about that, for example on the #dm-middleware-support Slack channel.
* The `outputRun` variable is automatically set for you based on the value of `output` and a timestamp.
* The default wall time for jobs is around 72 hours; you can override that value by setting `+Walltime` as shown (time should be given in seconds).
* In general don't ask for more resources (CPUs, memory, disk space, wall time, etc.) than you know you need.
* Note that you must use the long option names in a yaml file for the corresponding pipetask options, e.g. `butlerConfig` instead of `-i`, `dataQuery` instead of `-d`, etc.
* You can request default resource requirements such as memory or run time at the top level of the yaml (see the `requestMemory` line above), but you can give other values for specific task types if you want (for example see the higher requestMemory value in the subtractImages section under `pipetask`).
* Don't forget to set your butler, input and output collections, and any other absolute paths according to your own work area.

.. _section-ap-pipe-pipeline-bps-submit:

Submit and Monitor
==================

Now we should be able to run a `bps submit` command with our appropriately-modified yaml file (assuming it's named bps_ApPipe.yaml):

.. prompt:: bash

   bps submit yaml/bps_ApPipe.yaml

To see the status of our submission we can run

.. prompt:: bash

   bps report

Which will look something like::

  X     STATE  %S       ID OPERATOR   PRJ      CMPGN                     PAYLOAD                        RUN                                               
  -----------------------------------------------------------------------------------------------------------------------
  F    RUNNING  83    25639 kherner    ApPipe kh_default_bestSeeing_FULL ApPipe_default_bestSeeing_FULL u_kherner_ApPipe_default_bestSeeing_FULL_20210329T

You can get additional information about the status of your run by passing the ``--id IDNUM`` option to ``bps report``. For example: 

.. prompt:: bash

  bps report --id 25639

And the result will be something of the form::

    X      STATE  %S       ID OPERATOR   PRJ   CMPGN    PAYLOAD    RUN                                               
  -----------------------------------------------------------------------------------------------------------------------
  F    RUNNING  83    25639 kherner    ApPipe kh_default_bestSeeing_FULL ApPipe_default_bestSeeing_FULL u_kherner_ApPipe_default_bestSeeing_FULL_20210329T

  Path: /project/kherner/diffim_sprint_2021-02/bps_testing/bps/u/kherner/ApPipe_default_bestSeeing_FULL/20210329T230709Z

                                    UNKNO | MISFI | UNREA | READY | PENDI | RUNNI | DELET | HELD  | SUCCE | FAILE
  Total                                   0 |     0 |  3731 |  4766 |     0 |     0 |     0 |     0 | 69607 |  4267
  ----------------------------------------------------------------------------------------------------------------------
  imageDifference                         0 |     0 | 15073 |     0 |     0 |     0 |     0 |     2 |  1448 |   165
  diaPipe                                 0 |     0 |  7234 |     0 |  1007 |    60 |     0 |     0 |  6585 |  1802
  isr                                     0 |     0 | 16688 |     0 |     0 |     0 |     0 |     0 |     0 |     0
  characterizeImage                       0 |     0 | 16688 |     0 |     0 |     0 |     0 |     0 |     0 |     0
  calibrate                               0 |     0 | 16688 |     0 |     0 |     0 |     0 |     0 |     0 |     0

When your run is finished, the STATE will change from RUNNING to COMPLETED (or FAILED, if any quanta were unsuccessful).

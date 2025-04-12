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

.. _section-ap-pipe-pipeline-bps-yaml:

Creating a yaml file
====================

Next we need to create a yaml file for submission. 
Typically it will contain info about the processing campaign, desired input and output collections, resource requests for the various job types, and can include other yaml files (as we will do this this example).

Here's an example .yaml file governing what gets passed to pipetask.
It is simply a slightly modified version of the example in `ap_pipe/bps/bps_ApPipe.yaml <https://github.com/lsst/ap_pipe/blob/main/bps/bps_ApPipe.yaml>`_.
Again, as of September 2023 this assumes you are running on one of the lsst-devl machines at USDF.

.. code-block:: yaml

  # Path to the pipeline to run
  pipelineYaml: '/path/to/my/pipeline.yaml'
  
  # Names to help organize runs
  project: ApPipe
  campaign: my_example
  
  # Directory where files associated with your submission, such as logs, will go.
  # Default is shown.
  submitPath: ${PWD}/bps/{outputRun}
  
  # Specify WMS plugin (HTCondor, Parsl, Slurm, triple Slurm, etc.); HTCondor is default.
  wmsServiceClass: lsst.ctrl.bps.htcondor.HTCondorService
  
  # Specify compute site and specific site settings.
  computeSite: s3df
  site:
    s3df:
      profile:
        condor:
          +Walltime: 7200
          
  # Memory allocated for each quantum, in MBs; 2048 is default.
  requestMemory: 2048
  
  # CPUs to use per quantum; 1 is default.
  requestCpus: 1
  
  # The submit yaml must specify the following arguments:
  # Default arguments provided by bps (not included here) are listed in the ctrl_bps documentation (see below).
  payload:
    # This will set the output collection name.
    payloadName: my_example_name
    # Same as -b on the command line.
    butlerConfig: /sdf/group/rubin/repo/main/butler.yaml
    # Same as -i on the command line; actual input collections may differ from what is shown here.
    inCollection: HSC/calib,HSC/raw/all,refcats,u/elhoward/DM-38242/templates
    # Same as -d on the command line. Here is an example of a small data query just for testing.
    dataQuery: 'exposure IN (11690, 11692) AND detector in (49, 50)'
  
  # Various things for bps to customize about each pipeline task.
  pipetask:
    # Here you can set options to various pipeline tasks if they should run with something other than the defaults you specified above.
    subtractImages:
      requestMemory: 4096

Notes on the yaml file
----------------------
* A good example of a complete pipeline yaml is `ap_pipe/pipelines/_ingredients/ApPipe.yaml <https://github.com/lsst/ap_pipe/blob/main/pipelines/_ingredients/ApPipe.yaml>`_.

  * You can simply import that, or you may want to make other changes.
* The `computeSite` option determines where your jobs will run; as of now (September 2023) the typical choice will be `s3df`.

  * Other options may be possible in the future; see the `ctrl_bps <https://pipelines.lsst.io/modules/lsst.ctrl.bps/index.html>`_ documentation.
  * One can also ask the bps experts about that, for example on the #dm-middleware-support Slack channel.
* The `outputRun` variable is automatically set for you based on the value of `output` and a timestamp.
* The default wall time for jobs is around 72 hours; you can override that value by setting `+Walltime` as shown (time should be given in seconds).
* In general don't ask for more resources (CPUs, memory, disk space, wall time, etc.) than you know you need.
* Note that you must use the long option names in a yaml file for the corresponding pipetask options, e.g. `butlerConfig` instead of `-i`, `dataQuery` instead of `-d`, etc.
* You can request default resource requirements such as memory or run time at the top level of the yaml (see the `requestMemory` line above), but you can give other values for specific task types if you want (for example see the higher requestMemory value in the subtractImages section under `pipetask`).
* Don't forget to set your butler, input and output collections, and any other absolute paths according to your own work area.

.. _section-ap-pipe-pipeline-bps-allocate:

Allocating Nodes
================

If using the default WMS service class, HTCondor, we need to allocate nodes in order for a job to run. Here is a typical example for `s3df`:

.. prompt:: bash

   allocateNodes.py -v --dynamic -n 20 -c 32 -m 1-00:00:00 -q roma,milano -g 900 s3df

The number of nodes and cores per node are given by `-n` and `-c, respectively, where 120 is the maximum number of cores per node as of September 2023. The maximum possible time the nodes will run before automatically shutting down is given with `-m`, so adjust it according to your run size. The glide-in inactivity shutdown time in seconds is given by `-g`. Be sure to modify this if your run takes a while to generate a quantum graph. Also note that in order to run `allocateNodes.py` you will need a `condor-info.py` configuration. See the `ctrl_bps_htcondor <https://developer.lsst.io/usdf/batch.html#ctrl-bps-htcondor>`_ section of `Batch Resources <https://developer.lsst.io/usdf/batch.html>`_ for instructions.
   
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
  subtractImages                          0 |     0 | 15073 |     0 |     0 |     0 |     0 |     2 |  1448 |   165
  associateApdb                           0 |     0 |  7234 |     0 |  1007 |    60 |     0 |     0 |  6585 |  1802
  isr                                     0 |     0 | 16688 |     0 |     0 |     0 |     0 |     0 |     0 |     0
  calibrateImage                          0 |     0 | 16688 |     0 |     0 |     0 |     0 |     0 |     0 |     0

When your run is finished, the STATE will change from RUNNING to COMPLETED (or FAILED, if any quanta were unsuccessful).

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
Assuming you are on one of the rubin-devl machines (paths may differ if you are not) you would do run the following commands:

.. prompt:: bash

  source /sdf/group/rubin/sw/loadLSST.bash
  setup lsst_distrib -t your_favorite_weekly

.. _section-ap-pipe-pipeline-bps-apdb

Setting Up an APDB
==================

In order to run the AP Pipeline, you need a database to store the results of difference imaging.
You can make an Alert Production Database (APDB) by following the `Setting up the Alert Production Database for ap_pipe guide <https://pipelines.lsst.io/modules/lsst.ap.pipe/apdb.html>`_.

.. note::

  It is recommended that you use a PostgreSQL database for batch processing jobs.
  You need to include the full filepath to this file in the ``extraQgraphOptions`` in your submit yaml.

.. _section-ap-pipe-pipeline-bps-yaml:

Creating a yaml file
====================

Next we need to create a yaml file for submission. 
Typically it will contain info about the processing campaign, desired input and output collections, resource requests for the various job types, and can include other yaml files (as we will do this this example).

Here's an example .yaml file governing what gets passed to pipetask.
It is simply a slightly modified version of the example in `ap_pipe/bps/bps_ApPipe.yaml <https://github.com/lsst/ap_pipe/blob/main/bps/bps_ApPipe.yaml>`_.
Again, as of May 2025 this assumes you are running on one of the rubin-devl machines at USDF.

.. code-block:: yaml

  # Path to the pipeline to run
  pipelineYaml: '/path/to/my/pipeline.yaml'
  
  # Names to help organize runs
  project: ApPipe
  campaign: my_example
  
  # The submit yaml must specify the following arguments:
  # Default arguments provided by bps (not included here) are listed in the ctrl_bps documentation (see below).
  payload:
    # This will set the output collection name.
    payloadName: my_example_name
    # Same as -b on the command line.
    butlerConfig: /sdf/group/rubin/repo/main/butler.yaml
    # Same as -i on the command line; actual input collections may differ from what is shown here.
    inCollection: u/elhoward/DM-38243/templates,DECam/defaults
    # Same as -d on the command line. Here is an example of a small data query just for testing.
    dataQuery: "instrument='DECam' AND skymap='decam_rings_v1' AND tract=8122"

  # Add extra quantum graph options, such as specifying parameters.
  extraQgraphOptions: "-c parameters:apdb_config=path/to/your/apdb_config.yaml"

  # An example on how to add more configurations, such as clustering.
  includeConfigs:
    - ${AP_PIPE_DIR}/bps/clustering/clustering_ApPipe.yaml

  # An example on how to customize a pipeline task.
  pipetask:
    # Here you can set options to various pipeline tasks if they should run with something other than the defaults you specified above.
    subtractImages:
      requestMemory: 4096

  # Directory where files associated with your submission, such as logs, will go; default is shown.
  submitPath: ${PWD}/bps/{outputRun}

  # Specify WMS plugin (HTCondor, Parsl, Slurm, triple Slurm, etc.); HTCondor is default.
  wmsServiceClass: lsst.ctrl.bps.htcondor.HTCondorService
  
  # Specify compute site and specific site settings; s3df is default.
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

Notes on the yaml file
----------------------

* A good example of a complete pipeline yaml is `ap_pipe/pipelines/_ingredients/ApPipe.yaml <https://github.com/lsst/ap_pipe/blob/main/pipelines/_ingredients/ApPipe.yaml>`_.

  * You can simply import that, or you may want to make other changes.
* The ``computeSite`` option determines where your jobs will run; as of now (May 2025) the typical choice will be ``s3df``.

  * Other options may be possible in the future; see the `ctrl_bps <https://pipelines.lsst.io/modules/lsst.ctrl.bps/index.html>`_ documentation.
  * One can also ask the bps experts about that, for example on the #dm-middleware-support Slack channel.
* The ``outputRun`` variable is automatically set for you based on the value of ``output`` and a timestamp.
* The default wall time for jobs is around 72 hours; you can override that value by setting ``+Walltime`` as shown (time should be given in seconds).
* In general don't ask for more resources (CPUs, memory, disk space, wall time, etc.) than you know you need.
* Note that you must use the long option names in a yaml file for the corresponding pipetask options, e.g. ``butlerConfig`` instead of ``-i``, ``dataQuery`` instead of ``-d``, etc.
* You can request default resource requirements such as memory or run time at the top level of the yaml (see the ``requestMemory`` line above), but you can give other values for specific task types if you want (for example see the higher requestMemory value in the subtractImages section under ``pipetask``).
* Don't forget to set your butler, input and output collections, and any other absolute paths according to your own work area.

.. _section-ap-pipe-pipeline-bps-allocate:

Allocating Nodes
================

If using the default WMS service class, HTCondor, we need to allocate nodes in order for a job to run. Here is a typical example for ``s3df``:

.. prompt:: bash

   allocateNodes.py -v -n 20 -c 32 -m 4-00:00:00 -q milano -g 240 s3df

The number of nodes and cores per node are given by ``-n`` and ``-c``, respectively, where 120 is the maximum number of cores per node as of September 2023. The maximum possible time the nodes will run before automatically shutting down is given with ``-m``, so adjust it according to your run size. The glide-in inactivity shutdown time in seconds is given by ``-g``. Be sure to modify this if your run takes a while to generate a quantum graph. Also note that in order to run ``allocateNodes.py`` you will need a `condor-info.py` configuration. See the `ctrl_bps_htcondor <https://developer.lsst.io/usdf/batch.html#ctrl-bps-htcondor>`_ section of `Batch Resources <https://developer.lsst.io/usdf/batch.html>`_ for instructions.

.. note::

    If you want your nodes to scale with your run automatically, consider adding ``provisionResources: true`` to your submit yaml.
    You can find more information about this feature in the `ctrl_bps HTCondor Overview <https://pipelines.lsst.io/modules/lsst.ctrl.bps.htcondor/userguide.html#provisioning-resources-automatically>`_.

.. _section-ap-pipe-pipeline-bps-ordering:

Visit Ordering
==============

When processes run in batch mode, catalogs are read for multiple visits before the preceding visits have written to the APDB, resulting in missing history.
To combat this, we can add visit ordering to our submit yaml:

.. code-block:: yaml

  ordering:
    ordered_ap:
      labels: getRegionTimeFromVisit,loadDiaCatalogs,associateApdb
      dimensions: visit,detector
      equalDimensions: visit:group
      findDependencyMethod: sink

You can find more information about this feature in the `ctrl_bps Quickstart Guide <https://github.com/lsst/ctrl_bps/blob/main/doc/lsst.ctrl.bps/quickstart.rst#job-ordering>`_.

.. note::

    If you run with clustering, make sure that these three tasks are not in the clustering file.
   
.. _section-ap-pipe-pipeline-bps-submit:

Submit and Monitor
==================

Now we should be able to run a ``bps submit`` command with our appropriately-modified yaml file (assuming it's named bps_ApPipe.yaml):

.. prompt:: bash

  bps submit yaml/bps_ApPipe.yaml

After your ``bps submit`` is complete, you will see helpful details about your run at the end of the log::

  Submit dir: /sdf/home/e/elhoward/u/repo-main-logs/DM-49903/submit/u/elhoward/DM-49903/HiTS_sample/20250530T063908Z
  Run Id: 15828852.0
  Run Name: u_elhoward_DM-49903_HiTS_sample_20250530T063908Z

To see the status of our submission we can run

.. prompt:: bash

  bps report --user ${USER}

Which will look something like::

    X   STATE   %S     ID     OPERATOR   PROJECT   CAMPAIGN       PAYLOAD                              RUN
    --- ------- --- ---------- -------- ----------- -------- -------------------- ------------------------------------------------
    F RUNNING   8 15828856.0 elhoward ApPipe-HiTS DM-49903 DM-49903/HiTS_sample u_elhoward_DM-49903_HiTS_sample_20250530T063908Z

You can get additional information about the status of your run by passing ``--id submit_dir`` (from the end of your ``bps submit`` log) or ``--id run_id`` option to ``bps report``. For example: 

.. prompt:: bash

  bps report --id /sdf/home/e/elhoward/u/repo-main-logs/DM-49903/submit/u/elhoward/DM-49903/HiTS_sample/20250530T063908Z

And the result will be something of the form::

     X   STATE   %S     ID     OPERATOR   PROJECT   CAMPAIGN       PAYLOAD                              RUN
    --- ------- --- ---------- -------- ----------- -------- -------------------- ------------------------------------------------
      F RUNNING   7 15828856.0 elhoward ApPipe-HiTS DM-49903 DM-49903/HiTS_sample u_elhoward_DM-49903_HiTS_sample_20250530T063908Z
    
    Path: /sdf/data/rubin/user/elhoward/repo-main-logs/DM-49903/submit/u/elhoward/DM-49903/HiTS_sample/20250530T063908Z
    Global job id: sdfiana014.sdf.slac.stanford.edu#15828856.0#1748588023
    Status of provisioningJob: RUNNING
    
                           UNKNOWN MISFIT UNREADY READY PENDING RUNNING DELETED HELD SUCCEEDED FAILED PRUNED EXPECTED
    ---------------------- ------- ------ ------- ----- ------- ------- ------- ---- --------- ------ ------ --------
    TOTAL                        0      0     205     0     219      32       0    0       144     26   1350     1976
    ---------------------- ------- ------ ------- ----- ------- ------- ------- ---- --------- ------ ------ --------
    pipetaskInit                 0      0       0     0       0       0       0    0         1      0      0        1
    singleFrame                  0      0       0     0      81      32       0    0       143     26      0      282
    diffim                       0      0     124     0     138       0       0    0         0      0     20      282
    getRegionTimeFromVisit       0      0      16     0       0       0       0    0         0      0    266      282
    loadDiaCatalogs              0      0      16     0       0       0       0    0         0      0    266      282
    associateApdb                0      0      16     0       0       0       0    0         0      0    266      282
    associationMetrics           0      0      16     0       0       0       0    0         0      0    266      282
    diaSrcDetectorAnalysis       0      0      16     0       0       0       0    0         0      0    266      282
    finalJob                     0      0       1     0       0       0       0    0         0      0      0        1

When your run is finished, the STATE will change from RUNNING to COMPLETED (or FAILED, if any quanta were unsuccessful).

.. note::

    Using run ID for ``bps report`` only works if you are on the same interactive node as when you submitted the run, and it is by default limited to the default ``--hist`` if left unchanged.
    However, using the submit directory will always get you the ``bps report`` without any additional modifications to the incantation.
.. py:currentmodule:: lsst.ap.pipe

.. _ap-pipe-pipeline-with-fakes:

########################
ApPipeWithFakes pipeline
########################

This document provides an overview of the ``ApPipeWithFakes`` pipeline, which extends the standard Alert Production (AP) pipeline to include the capability of injecting synthetic (fake) sources into images for testing and validation purposes.

.. note::

    The ``ApPipeWithFakes.yaml`` ingredients file is **not** a standard static file in the codebase.
    Instead, it is **automatically generated at compilation time** by the build script ``SConstruct``.
    This ensures the fakes pipeline always reflects the latest base pipeline and injection tasks.
    Do **not** attempt to manually edit or add this file; any changes will be overwritten during the next build.


Pipeline Structure
==================

The ``ApPipeWithFakes`` pipeline is built upon the standard AP pipeline but includes additional tasks for:

1. **Source injection**: Using :lsst-task:`lsst.source.injection.VisitInjectTask` to add synthetic point sources (stars) into images prior to difference imaging
2. **Fake source matching**: Matching of detected sources in difference images to the true injected sources using ``lsst.pipe.tasks.matchDiffimSourceInjected`` tasks
3. **Performance analysis**: Evaluating recovery rates and measurement accuracy, including detailed analysis of fake source recovery across various magnitude and SNR ranges using ``analysis_tools`` tasks.


Build-Time Pipeline Generation
==============================

The ``_ingredients/ApPipeWithFakes.yaml`` file is **automatically generated** during package compilation, not manually maintained. This process is controlled by the ``SConstruct`` file at the package root.

The ``SConstruct`` file defines the build process for generating the ``ApPipeWithFakes`` pipeline, where the base ``_ingredients/ApPipe.yaml`` is taken as input and by using the  ``source_injection`` `~lsst.source.injection.bin.make_injection_pipeline` command to automatically add injection tasks as well as including the post injection specific tasks from ``_ingredients/injection/PostInjectedTasksApPipe.yaml``.

The generated ``ApPipeWithFakes.yaml`` file should **not** be manually edited, instead, modifications should be made to:

* The base ``_ingredients/ApPipe.yaml`` pipeline
* The ``_ingredients/injection/PostInjectedTasksApPipe.yaml`` injection-specific and metrics tasks
* The ``SConstruct`` build configuration

Running the Pipeline
====================

Prerequisites
-------------
Running ``ApPipeWithFakes`` requires the same prerequisites as the standard ``ApPipe`` pipeline, and in addition an **injection catalog**, that should be ingested into the input collection to use.

Check documentation on how to run this pipeline and create a fake catalog:

* :doc:`pipeline-tutorial`: Tutorial for running AP pipelines
* :ref:`source_injection <lsst.source.injection-ref-generate>`: Creating an injection catalog

Output Products
---------------

The ``ApPipeWithFakes`` pipeline produces all standard AP pipeline outputs  (with ``fakes_`` prefix) plus additional fake-specific datasets.

The key additional outputs include:

* ``fakes_preliminary_visit_image_catalog``: Catalog of injected source properties
* ``fakes_goodSeeingDiff_matchDiaSrc``: Matches between injected and detected sources
* ``fakes_goodSeeingDiff_matchAssocDiaSrc``: Matches for successfully associated sources


Creating an Injection Catalog
-----------------------------
To create an injection catalog for use with ``ApPipeWithFakes``, use the ``createInjectionCatalog`` command from the ``lsst.source.injection`` package * :ref:`source_injection <lsst.source.injection-ref-generate>`. This command generates a catalog of synthetic sources based on specified parameters such as magnitude distribution, spatial distribution, and source types.
Alternatively, you can use the ``createApFakes`` task from the ``lsst.ap.pipe`` package, which is specifically designed to create injection catalogs tailored for the AP pipeline.
We also provide a pipeline yaml file that is able to create an injection catalog with the same configuration as the one used in the ``ApPipeWithFakes`` pipeline, which can be found at ``pipelines/CreateInjectionCatalogs.yaml``. This pipeline can be run using the same command as for running the AP pipelines, but with the above yaml file as input and specifying an output collection to ingest the generated injection catalog into.

.. code-block:: bash

    pipetask run  \
        -i u/user/input_collection \
        -b /path/to/repo/butler.yaml \
        -o fake_catalogs_collection \
        -p $AP_PIPE_DIR/pipelines/CreateInjectionCatalogs.yaml \
        -d "instrument='LSSTComCam' AND skymap='lsst_cells_v2' AND visit=2024111100094 AND detector IN (0,3)"


Sharding an Injection Catalog for ApPipeWithFakes
-------------------------------------------------

When an injection catalog has already been ingested in unsharded form, use
``scripts/fakes/shard_fake_catalogs.py`` to split and ingest sharded catalogs
into an output collection before running ``ApPipeWithFakes``.

The command supports Butler ``where`` expressions through ``-d/--dataquery``
using the same syntax style as ``pipetask -d``.

Example:

.. code-block:: bash

    python ${AP_PIPE_DIR}/scripts/fakes/shard_fake_catalogs.py \
        -b /path/to/repo/butler.yaml \
        -i u/user/input_collection \
        -o u/user/output_collection \
        -t VisitDetectorFakeSourceCat \
        -d "instrument='LSSTComCam' AND skymap='lsst_cells_v2' AND visit=2024111100094 AND detector IN (0,3)"

Arguments:

* ``-b/--butler-config``: Butler config file path.
* ``-i/--input-collection``: Collection containing unsharded injection catalogs.
* ``-o/--output-collection``: Output collection for sharded catalogs.
* ``-t/--dataset-type-name``: Dataset type to query (default: ``injection_catalog``).
* ``-d/--dataquery``: Optional Butler ``where`` expression for dataset selection.

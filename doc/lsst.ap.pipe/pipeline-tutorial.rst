.. _pipeline-tutorial:

####################
AP Pipeline Tutorial
####################

Setup
=====

Pick up where you left off in :doc:`Getting Started <getting-started>`.
This means you already have a repository of ingested DECam data and have setup
the LSST Science Pipelines stack as well as ``ap_pipe`` and ``ap_association``.

Your directory structure should look something like 

.. code-block:: none

   repo/   <-- where you will be running ap_pipe
      registry.sqlite3   <--- created during image ingestion
      image1.fits   <--- linked here by default during image ingestion
      image2.fits
      ...
      ref_cats/   <--- copied or linked here manually by you
         gaia/
            shard1
            shard2
            ...
         pan-starrs/
            shard1
            shard2
            ...
      calibs/
         calibRegistry.sqlite3   <--- created/updated during calib/defect ingestion
         cpBIAS/
            bias1.fits   <--- linked here by default during calib ingestion
            bias2.fits
            ...
         cpFLAT/
            flat1.fits   <--- linked here by default during calib ingestion
            flat2.fits
            ...
         defects/   <--- put here manually by you prior to defect ingestion
            defect1.fits
            defect2.fits
            ...
      templates/   <--- copied or linked here manually by you
         repositoryCfg.yaml
         deepCoadd/
            g/
               0/
                  psfMatched-0,0.fits
                  psfMatched-0,1.fits
                  ...

.. _section-ap-pipe-command-line:

AP Pipeline on the command line
===============================

The executable to run for the AP Pipeline (`lsst.ap.pipe.ApPipeTask`) is
in ``ap_pipe/bin/ap_pipe.py``.

To process your ingested data, run

.. prompt:: bash
   
   ap_pipe.py repo --calib repo/calibs --rerun processed --id visit=123456 ccdnum=42 filter=g --template templates

In this case, a ``processed`` directory will be created within
``repo/rerun`` and the results will be written there.

This example command only processes observations that have a
:ref:`dataId<subsection-ap-pipe-previewing-dataIds>`
corresponding to visit 123456 and ccdnum 42 in with a filter called g.

`lsst.ap.pipe` supports ``dataId`` parsing, e.g., ``ccdnum=3^6..12`` will process
``ccdnums`` 3, 6, 7, 8, 9, 10, 11, and 12.

.. note::

   Until a resolution for `DM-12672 <https://jira.lsstcorp.org/browse/DM-12672>`_
   is found, you should include a filter in the ``dataId`` string for
   ``ap_pipe`` to run successfully.

If you prefer to have a standalone output repository, you may instead run

.. prompt:: bash

   ap_pipe.py repo --calib repo/calibs --output path/to/put/processed/data/in --id visit=123456 ccdnum=42 filter=g --template path/to/templates

In this case, the output directory will be created if it does not already exist.
If you omit the ``--template`` flag, ``ap_pipe`` will assume the templates are
somewhere in ``repo``.


.. _section-ap-pipe-expected-outputs:

Expected outputs
================

If you used the rerun option above, the output from ``ap_pipe`` should be
written out in the repo/rerun/processed directory. It should look
something like

.. code-block:: none

   repo/
      rerun/
         processed/
            repositoryCfg.yaml
            association.db   <--- the Prompt Products Database with DIAObjects
            deepDiff/
               v123456/   <--- difference images and DIASource tables are in here
            123456/   <--- all other processed data products are in here (calexps etc.)

This is one example, and your rerun or output directory structure may differ.
Of course, to inspect this data with the Butler, you don't need to know
where it lives on disk. You should instead instantiate a Butler within python
in the ``processed`` directory and access the data products that way.

For example, in python

.. code-block:: python
   
   import lsst.daf.persistence as dafPersist
   butler = dafPersist.Butler('repo/rerun/processed')
   dataId = {'visit': 123456, 'ccdnum': 42, 'filter': 'g'}
   calexp = butler.get('calexp', dataId=dataId)
   diffim = butler.get('deepDiff_differenceExp', dataId=dataId)
   diaSourceTable = butler.get('deepDiff_diaSrc', dataId=dataId)


.. _section-ap-pipe-calexp-templates:

Calexp template mode
====================

By default, ``ap_pipe`` assumes you would like to use PSF-matched coadd images
as templates for difference imaging. However, the pipeline also supports
using calibrated exposures (``calexps``) as templates instead. A configuration file
``config/calexpTemplates.py`` is included witha ``ap_pipe`` to enable this.

To use ap_pipe in calexp template mode, point to the config file with the 
``--configfile`` (``-C``) flag and additionally specify the ``dataId`` of the template
with the ``--templateId`` flag, e.g.,

.. code-block:: none

   -C $AP_PIPE_DIR/config/calexpTemplates.py --templateId visit=234567

Be sure to also specify the location of the repo containing the calexp templates
with the ``--template`` flag if they are not in the main repo.
A full command looks like

.. prompt:: bash
   
   ap_pipe.py repo --calib repo/calibs --rerun processed -C $AP_PIPE_DIR/config/calexpTemplates.py --id visit=123456 ccdnum=42 filter=g --template /path/to/calexp/templates --templateId visit=234567


.. _section-ap-pipe-supplemental-info:

Supplemental information
======================

.. _subsection-ap-pipe-previewing-dataIds:

Previewing dataIds
------------------

So far, we have implicitly assumed that you know reasonable values to choose for the
dataId values (i.e., visit, ccdnum, and filter for DECam). While it is your
responsibility to ensure the data you want to process and your templates
do indeed overlap with each other, ap_pipe supports the ``--show data`` flag.

To get a list of all the dataIds available in ``repo`` in lieu of actually
running ap_pipe, try

.. prompt:: bash
   
   ap_pipe.py repo --calib repo/calibs --rerun processed --id visit=123456 ccdnum=42 filter=g --show data


Running on other cameras
------------------------

Only DECam data is supported for now. Please stay tuned!


Common errors
-------------

* 'No locations for get': This means you are trying to access a data product
  which the Butler cannot find. It is common to encounter this if you do not
  have all of the calibration products in the right spot or a template image
  cannot be accessed.


.. _section-ap-pipe-interpreting-results:

Interpreting the results
========================

.. warning:: 
   
   The format of the ``ap_association`` Prompt Product Database is rapidly evolving. For
   the latest information on how to interface with it, see `lsst.ap.associate`.

Try these python commands to make some initial plots of your
newly processed data. You can also use the Butler to display
calibrated exposures, difference images, inspect DIAObjects and/or DIASources, etc.

.. code-block:: python

   import os
   from copy import deepcopy
   import numpy as np
   import matplotlib.pyplot as plt
   import pandas as pd
   import sqlite3
   import lsst.daf.persistence as dafPersist

   workingDir = 'repo/rerun/processed'
   butler = dafPersist.Butler(os.path.join(workingDir))

   # Open and read all data from the association database
   sqliteFile = 'association.db'
   connection = sqlite3.connect(os.path.join(workingDir, sqliteFile))
   tables = {'obj': 'dia_objects', 'src': 'dia_sources', 'con': 'dia_objects_to_dia_sources'}
   conTable = pd.read_sql_query('select * from {0};'.format(tables['con']), connection)
   objTable = pd.read_sql_query('select * from {0};'.format(tables['obj']), connection)
   srcTable = pd.read_sql_query('select * from {0};'.format(tables['src']), connection)
   connection.close()
   
   # Plot how many sourceIDs are attached to any given objectID
   obj_id = objTable['id'].values  # object ids from the objTable
   con_obj_id = conTable['obj_id'].values  # object ids from the conTable
   con_obj_id.sort()
   lowerIndex = np.searchsorted(con_obj_id, obj_id, side='left')
   upperIndex = np.searchsorted(con_obj_id, obj_id, side='right')
   count = upperIndex - lowerIndex
   plt.hist(count, bins=50)
   plt.yscale('log')
   plt.xlabel('Number of DIASources per DIAObject')
   plt.ylabel('DIAObject Count')
   plt.show()

   # Plot all the DIAObjects on the sky
   plt.hexbin(objTable['coord_ra'], objTable['coord_dec'], 
                   cmap='cubehelix', bins='log', gridsize=500, mincnt=1)
   plt.title('DIA Objects', loc='right')
   plt.xlabel('RA')
   plt.ylabel('Dec')
   plt.show()


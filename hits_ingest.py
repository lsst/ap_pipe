from __future__ import print_function
# import numpy as np
# import matplotlib.pyplot as plt
# from astropy.io import fits
# from lsst.utils import getPackageDir
from lsst.obs.decam import ingest, ingestCalibs
from lsst.pipe.tasks.ingest import IngestConfig
from glob import glob
import sys
from lsst.obs.decam.ingest import DecamParseTask
'''
Little script to ingest some raw decam images

You have to specify two directory names:
1. repo, an empty directory the nicely organized and ingested images will go
2. data, a directory where some '*.fits.fz' images currently live

Usage: $ python hits_ingest.py 'path/to/datadir/'

Result: repo populated with *links* to files in datadir, organized by date

The command line equivalent with doIngest = True given the variables below is:
$ ingestImagesDecam.py repo --filetype raw --mode link datafiles

And with doIngestCalibs = True, it is (should be?):
$ ingestCalibs.py repo --calib calibrepo --calibType defect 
                       --validity 999 datafiles
'''
doIngest = True
doIngestCalibs = False  # doesn't work yet, see below

# ~~ edit directory names for ingested data repos here ~~ #
# repo = '../ingested/'  # on lsst-dev
# calibrepo = '../calibingested/' # on lsst-dev
repo = 'ingested/'  # on laptop
calibrepo = 'calibingested/'  # on laptop

datadir = sys.argv[1]  # '/lsst7/mrawls/HiTS/Blind15A_38/' on lsst-dev
                       # 'data/' on laptop
datafiles = glob(datadir + '*.fits.fz')

# make a text file that handles the mapper, per the obs_decam github README
f = open(repo+'_mapper', 'w')
print('lsst.obs.decam.DecamMapper', file=f)
f.close()

if doIngest:
    print('Ingesting raw images...')
    # save arguments you'd put on the command line after 'ingestImagesDecam.py'
    # (extend the list with all the filenames as the last set of arguments)
    args = [repo, '--filetype', 'raw', '--mode', 'link']
    args.extend(datafiles)

    # set up the decam ingest task so it can take arguments
    # ('name' says which file in obs_decam/config to use)
    argumentParser = ingest.DecamIngestArgumentParser(name='ingest')

    # create an instance of ingest configuration
    # the retarget command is from line 2 of obs_decam/config/ingest.py
    config = IngestConfig()
    config.parse.retarget(DecamParseTask)  

    # create an instance of the decam ingest task
    ingestTask = ingest.DecamIngestTask(config=config)

    # feed everything to the argument parser
    parsedCmd = argumentParser.parse_args(config=config, args=args)

    # finally, run the ingestTask
    ingestTask.run(parsedCmd)

    print('Images from {0} are now ingested in {1}'.format(datadir, repo))

# follow a similar process to ingest calibrations for doIngestCalibs = True
# ~ WORK IN PROGRESS!!! ~
# TODO:
# - get the command-line task to work on its own
# - get this script to work in the same way
# - find a way to ingest all calibration products (bias, flat, defect, etc.)
if doIngestCalibs:
    print('Ingesting calibration products...')
    args = [repo, '--calib', calibrepo, '--calibType', 'defect', 
            '--validity', '999']
    args.extend(datafiles)
    argumentParser = ingest.DecamIngestArgumentParser(name='ingestCalibs')
    config = IngestConfig()
    config.parse.retarget(ingestCalibs.DecamCalibsParseTask)
    # ingestTask = ingest.DecamIngestTask(config=config)
    ingestTask = ingestCalibs.DecamCalibsParseTask(config=config, 
                                                   name='ingestCalibs')
    parsedCmd = argumentParser.parse_args(config=config, args=args)
    # ^^ FAIL lsst.pipe.tasks.ingest.RegisterConfig has no attribute detector ?
    ingestTask.run(parsedCmd)
    print('Calibrations from {0} for {1} are now ingested in {2}'
                                    .format(datadir, repo, calibrepo))

from __future__ import print_function
# import numpy as np
# import matplotlib.pyplot as plt
# from astropy.io import fits
# from lsst.utils import getPackageDir
from lsst.obs.decam import ingest
from lsst.obs.decam import ingestCalibs
from lsst.pipe.tasks.ingest import IngestConfig
from lsst.pipe.tasks.ingestCalibs import IngestCalibsConfig, IngestCalibsTask
from lsst.pipe.tasks.ingestCalibs import IngestCalibsArgumentParser
from glob import glob
import sys
import sqlite3
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

And with doIngestCalibs = True, it is:
$ ingestCalibs.py repo --calib calibrepo --validity 999 datafiles
'''
doIngest = False
doIngestCalibs = True

# ~~ edit directory names for ingested data repos here ~~ #
repo = 'ingested/'
calibrepo = 'calibingested/'

datadir = sys.argv[1]  # '/lsst7/mrawls/HiTS/Blind15A_38/' on lsst-dev
                       # 'data/' on laptop
                       # or, if doIngestCalibs, needs to be the dir of calibs
                       # e.g., '/lsst7/mrawls/HiTS/MasterCals/c4d*.fits.fz'
                       # PUTTING REGEXPS IN QUOTES MATTERS !!
if '*' or '?' in datadir:
    datafiles = glob(datadir)
else:
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

    print('Images are now ingested in {0}'.format(repo))

# follow a similar process to ingest calibrations for doIngestCalibs = True
# catch the common sqlite3.IntegrityError and print some useful information
if doIngestCalibs:
    print('Ingesting calibration products...')
    args = [repo, '--calib', calibrepo, '--validity', '999']
    args.extend(datafiles)
    argumentParser = IngestCalibsArgumentParser(name='ingestCalibs')
    config = IngestCalibsConfig()
    config.parse.retarget(ingestCalibs.DecamCalibsParseTask)
    ingestTask = IngestCalibsTask(config=config, name='ingestCalibs')
    parsedCmd = argumentParser.parse_args(config=config, args=args)
    try:
        ingestTask.run(parsedCmd)
    except sqlite3.IntegrityError as detail:
        print('~~~ !!! ~~~')
        print('sqlite3.IntegrityError: ', detail)
        print('(sqlite3 doesn\'t think all the calibration files are unique)')
        print('If this isn\'t your first time ingesting these calibration')
        print('  files, move or delete the existing database and try again.')
        print('If this is your first time ingesting these calibration files,')
        print('  make sure you only use image or wtmap MasterCals, not both.')
        print('~~~ !!! ~~~')
    else:
        print('Success!')
        print('Calibrations corresponding to {0} are now ingested in {1}' \
                                                    .format(repo, calibrepo))

from __future__ import print_function
from lsst.obs.decam import ingest
from lsst.obs.decam import ingestCalibs
from lsst.obs.decam.ingest import DecamParseTask
from lsst.pipe.tasks.ingest import IngestConfig
from lsst.pipe.tasks.ingestCalibs import IngestCalibsConfig, IngestCalibsTask
from lsst.pipe.tasks.ingestCalibs import IngestCalibsArgumentParser
from lsst.pipe.tasks.processCcd import ProcessCcdTask
from lsst.pipe.base import ArgumentParser
from lsst.utils import getPackageDir
from glob import glob
import sys
import sqlite3
import os
'''
Little script to ingest some raw decam images

PREPARATION
Make the following empty directories and name them as desired below
1. repo, where the ingested images and registry will go
2. calibrepo, where the calibration product registry will go

USAGE
$ python hits_ingest.py 'path/to/datadir/'
or
$ python hits_ingest.py 'path/to/datadir/justsomefiles*.fits.fz'
(the quotes around the datadir string are important!)
or
$ python hits_ingest.py
(if you don't want to give it an argument because you're running processCcd)

OUTPUT
if doIngest: repo populated with *links* to files in datadir, organized by date
             sqlite3 database registry of ingested images also created in repo
if doIngestCalibs: sqlite3 database registry of ingested calibration products
                   created in calibrepo
if doProcessCcd: outputrepo/visit populated with subdirectories containing the
                 usual post-ISR data (bkgd, calexp, icExp, icSrc, postISR)

BASH EQUIVALENT
if doIngest:
    $ ingestImagesDecam.py repo --filetype raw --mode link datafiles
if doIngestCalibs:
    $ ingestCalibs.py repo --calib calibrepo --validity 999 datafiles
if doProcessCcd:
    $ cd calibrepo
    $ processCcd.py ../repo --id visit=visit ccdnum=ccdnum 
            --output ../outputrepo -C $OBS_DECAM_DIR/config/processCcdCpIsr.py
            --config calibrate.doAstrometry=False calibrate.doPhotoCal=False
            --no-versions
'''
# edit values below as desired
doIngest = False
doIngestCalibs = False
doProcessCcd = True
visit = '410877' # used for ProcessCcd only
ccdnum = '25'    # used for ProcessCcd only
repo = 'ingested/'
calibrepo = 'calibingested/'
outputrepo = 'processed/'
# edit values above as desired

if ((doIngest and doIngestCalibs) or (doIngest and doProcessCcd) or 
    (doIngestCalibs and doProcessCcd)):
    raise RuntimeError('You can only have one task True at a time')
elif not doIngest and not doIngestCalibs and not doProcessCcd:
    raise RuntimeError('Nothing to do, every task is set to False')

if len(sys.argv) < 2:
    datadir = None
    datafiles = None
    print('WARNING: no data directory specified.')
    print('(This is OK if you are just running ProcessCcd.)')
else:
    datadir = sys.argv[1]  # '/lsst7/mrawls/HiTS/<dirname>' on lsst-dev
                       # 'data/' or 'MasterCals/' on laptop
                       # (if doIngestCalibs, datadir must be the dir of calibs)
                       # can also use a regex, e.g., 'data/c4d_15*.fz'   
    if os.path.isdir(datadir):
        datafiles = glob(datadir + '*.fits.fz')
    else:
        datafiles = glob(datadir)

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
# NOTE: I chose to ingest the 'defect' calibration products separately on
#       the command line by specifying a different directory and adding the
#       argument --calibType defect. In the future, this should be done
#       here alongside ingesting the biases and flats.
if doIngestCalibs:
    print('Ingesting calibration products...')  # just biases and flats for now
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

# the final step is to run processCcd to do ISR by combining the ingested
# images and calibration products
if doProcessCcd:
    print('Running ProcessCcd...')
    OBS_DECAM_DIR = getPackageDir('obs_decam')  # os.getenv('OBS_DECAM_DIR')
    # TODO: once DM-5466 is complete, the chdir should be removed and the
    #       relative '../' path nonsense in args should be removed too
    os.chdir(calibrepo)
    args = ['../' + repo, '--id', 'visit=' + visit, 'ccdnum=' + ccdnum, 
            '--output', '../' + outputrepo, 
            '-C', OBS_DECAM_DIR + '/config/processCcdCpIsr.py',
            '--config', 'calibrate.doAstrometry=False',
            'calibrate.doPhotoCal=False',
            '--no-versions']
    # This is SO MUCH EASIER than parsing the args in the above two cases!!
    ProcessCcdTask.parseAndRun(args=args, doReturnResults=True)

    

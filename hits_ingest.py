from __future__ import print_function
from lsst.obs.decam import ingest
from lsst.obs.decam import ingestCalibs
from lsst.obs.decam.ingest import DecamParseTask
from lsst.pipe.tasks.ingest import IngestConfig
from lsst.pipe.tasks.ingestCalibs import IngestCalibsConfig, IngestCalibsTask
from lsst.pipe.tasks.ingestCalibs import IngestCalibsArgumentParser
from lsst.pipe.tasks.processCcd import ProcessCcdTask
from lsst.utils import getPackageDir
from glob import glob
import sqlite3
import os
import argparse
'''
Little script to ingest some raw decam images

USAGE
$ python hits_ingest.py ingest -f path/to/rawimages/
(will use all files in the directory named *.fz if no files are specified)
or
$ python hits_ingest.py ingestCalibs -f path/to/calibrations/somefiles*.fits.fz
or
$ python hits_ingest.py processCcd

OUTPUT
ingest: repo populated with *links* to files in datadir, organized by date
        sqlite3 database registry of ingested images also created in repo
ingestCalibs: calibrepo populated with *links* to files in datadir, 
              organized by date (bias/zero and flat images only)
              sqlite3 database registry of ingested calibration products
              created in calibrepo
        **NOTE: this does not ingest any defects or fringes!**
        You must do this manually... e.g.,
        $ cd calibrepo
        $ ingestCalibs.py ../repo --calib . --calibType defect --validity 999 
          ../HiTS/MasterCals/defects/2014-12-05/*fits
processCcd: outputrepo/visit populated with subdirectories containing the
            usual post-ISR data (bkgd, calexp, icExp, icSrc, postISR)

BASH EQUIVALENTS
ingest:
    $ ingestImagesDecam.py repo --filetype raw --mode link datafiles
ingestCalibs:
    $ ingestCalibs.py repo --calib calibrepo --mode=link --validity 999 datafiles
processCcd:
    $ cd calibrepo
    $ processCcd.py repo --id visit=visit ccdnum=ccdnum 
            --output outputrepo --calib calibrepo
            -C $OBS_DECAM_DIR/config/processCcdCpIsr.py
            --config calibrate.doAstrometry=False calibrate.doPhotoCal=False
            --no-versions --clobber-config
'''
# edit values below as desired
#visit = '421604' #15A40
#visit = '412263' #15A39
visit = '410877' #15A38  # visit is used for ProcessCcd only
ccdnum = '5..8'         # ccdnum is used for ProcessCcd only; 1-62 exist
repo = 'test_ingested/'
calibrepo = 'test_calibingested/'
outputrepo = 'test_processed/'
# edit values above as desired

# parse command line arguments with argparse
parser = argparse.ArgumentParser()
parser.add_argument('task', help='Which task you would like to run', 
    choices=['ingest', 'ingestCalibs', 'processCcd'])
parser.add_argument('-f', '--files', help='Input files or directory')
args = parser.parse_args()
if (args.task == 'ingest' or args.task == 'ingestCalibs') and not args.files:
    raise ArgumentError('-f is required to ingest images or calibrations.')
if args.files == None:
    datadir = None
    datafiles = None
else:
    datadir = args.files
    # ingest: 'HiTS/Blind15A_XX/' on lsstdev:/project/mrawls/prototype_ap
    # ingestCalibs: 'HiTS/MasterCals/' on lsstdev:/project/mrawls/prototype_ap
    if os.path.isdir(datadir):
        datafiles = glob(datadir + '*.fz')
    else:
        datafiles = glob(datadir)

if args.task == 'ingest':
    if not os.path.isdir(repo):
        os.mkdir(repo)
    # make a text file that handles the mapper, per the obs_decam github README
    f = open(repo+'_mapper', 'w')
    print('lsst.obs.decam.DecamMapper', file=f)
    f.close()
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
elif args.task == 'ingestCalibs':
    if not os.path.isdir(calibrepo):
        os.mkdir(calibrepo)
    print('Ingesting calibration products...')  # just biases and flats for now
    args = [repo, '--calib', calibrepo, '--mode', 'link', '--validity', '999']
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
        print('Calibrations corresponding to {0} are now ingested in {1}'.format(repo, calibrepo))

# the final step is to run processCcd to do ISR by combining the ingested
# images and calibration products
elif args.task == 'processCcd':
    if not os.path.isdir(processed):
        os.mkdir(processed)
    print('Running ProcessCcd...')
    OBS_DECAM_DIR = getPackageDir('obs_decam')  # os.getenv('OBS_DECAM_DIR')
    args = [repo, '--id', 'visit=' + visit, 'ccdnum=' + ccdnum,
            '--output', outputrepo,
            '--calib', calibrepo,
            '-C', OBS_DECAM_DIR + '/config/processCcdCpIsr.py',
            '--config', 'calibrate.doAstrometry=False',
            'calibrate.doPhotoCal=False',
            '--no-versions', '--clobber-config']
    ProcessCcdTask.parseAndRun(args=args, doReturnResults=True)

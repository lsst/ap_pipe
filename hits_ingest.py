from __future__ import print_function
from lsst.obs.decam import ingest
from lsst.obs.decam import ingestCalibs
from lsst.obs.decam.ingest import DecamParseTask
from lsst.pipe.tasks.ingest import IngestConfig
from lsst.pipe.tasks.ingestCalibs import IngestCalibsConfig, IngestCalibsTask
from lsst.pipe.tasks.ingestCalibs import IngestCalibsArgumentParser
from lsst.pipe.tasks.processCcd import ProcessCcdTask, ProcessCcdConfig
from lsst.meas.algorithms import LoadIndexedReferenceObjectsTask
from lsst.utils import getPackageDir
from lsst.ip.diffim.getTemplate import GetCalexpAsTemplateTask
from lsst.pipe.tasks.imageDifference import ImageDifferenceConfig, ImageDifferenceTask
from glob import glob
import sqlite3
import os
import argparse
'''
This script processes raw decam images from ingestion --> difference imaging!

USAGE
$ python hits_ingest.py ingest -f path/to/rawimages/
(will use all files in the directory named *.fz if no files are specified)
or
$ python hits_ingest.py ingestCalibs -f path/to/calibrations/somefiles*.fits.fz
or
$ python hits_ingest.py processCcd
or
$ python hits_ingest.py diffIm

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
processCcd: processedrepo/visit populated with subdirectories containing the
            usual post-ISR data (bkgd, calexp, icExp, icSrc, postISR)

BASH EQUIVALENTS
ingest:
    $ ingestImagesDecam.py repo --filetype raw --mode link datafiles
ingestCalibs:
    $ ingestCalibs.py repo --calib calibrepo --mode=link --validity 999 datafiles
processCcd:
    $ cd calibrepo
    $ processCcd.py repo --id visit=visit ccdnum=ccdnum
            --output processedrepo --calib calibrepo
            -C $OBS_DECAM_DIR/config/processCcdCpIsr.py
            -C processccd_config.py
            --config calibrate.doAstrometry=True calibrate.doPhotoCal=True
    ** note that to run from bash, 'processccd_config.py' must exist
diffIm:
    $ imageDifference.py processedrepo --id visit=diffimvisit ccdnum=ccdnum
            --templateId visit=templatevisit --output diffimrepo
            -C diffim_config.py
    ** note that to run from bash, 'diffim_config.py' must exist
'''
# ~~  edit values below as desired  ~~ #
visit = '410927^411033'#^411067^411267^411317^411367^411418^411468^411669^ \
#         411719^411770^411820^411870^412072^412262^412319^412516^412566^ \
#         412616^412666^412716^413647^413692^415326^415376^419800^421602'  # 15A38 g filter
templatevisit = '410927'  # only used for diffIm
diffimvisit = visit[7::]  # exclude templatevisit from the visit string
ccdnum = '1..62'  # note visit and ccdnum info are not used during ingestion
repo = 'ingested_15A38/'
calibrepo = 'calibingested_15A38/'
processedrepo = 'processed_15A38/'
diffimrepo = 'diffim_15A38_g/'
# ~~ edit values above as desired  ~~ #

# parse command line arguments with argparse
parser = argparse.ArgumentParser()
parser.add_argument('task', help='Which task you would like to run',
                    choices=['ingest', 'ingestCalibs', 'processCcd', 'diffIm'])
parser.add_argument('-f', '--files', help='Input files or directory')
args = parser.parse_args()
if (args.task == 'ingest' or args.task == 'ingestCalibs') and not args.files:
    raise IOError('-f is required to ingest images or calibrations.')
if args.files is None:
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

# the next step is to run processCcd to do ISR by combining the ingested
# images and calibration products
# astrometry and photometric calibration is also done by processCcd
elif args.task == 'processCcd':
    if not os.path.isdir(processedrepo):
        os.mkdir(processedrepo)
    print('Running ProcessCcd...')
    OBS_DECAM_DIR = getPackageDir('obs_decam')  # os.getenv('OBS_DECAM_DIR')
    config = ProcessCcdConfig()
    # Astrometry retarget party
    for refObjLoader in (config.calibrate.astromRefObjLoader,
                         config.calibrate.photoRefObjLoader,
                         config.charImage.refObjLoader,):
        refObjLoader.retarget(LoadIndexedReferenceObjectsTask)
        refObjLoader.ref_dataset_name = 'pan-starrs'  # options are gaia, pan-starrs, sdss
        refObjLoader.filterMap = {"g": "g",  # 'phot_g_mean_mag' is gaia-specific
                                  "r": "r",  # all of 'g,r,i,z,y' are options for pan-starrs
                                  "VR": "g"}
    args = [repo, '--id', 'visit=' + visit, 'ccdnum=' + ccdnum,
            '--output', processedrepo,
            '--calib', calibrepo,
            '-C', OBS_DECAM_DIR + '/config/processCcdCpIsr.py',
            '--config', 'calibrate.doAstrometry=True',
            'calibrate.doPhotoCal=True']
    ProcessCcdTask.parseAndRun(args=args, config=config, doReturnResults=True)

# finally, we do difference imaging with a template
elif args.task == 'diffIm':
    if not os.path.isdir(diffimrepo):
        os.mkdir(diffimrepo)
    print('Running ImageDifference...')
    config = ImageDifferenceConfig()
    config.getTemplate.retarget(GetCalexpAsTemplateTask)
    # config.doMeasurement = True
    # config.doPreConvolve = False
    config.detection.thresholdValue = 5.0
    config.doDecorrelation = True
    args = [processedrepo, '--id', 'visit=' + diffimvisit, 'ccdnum=' + ccdnum,
            '--templateId', 'visit=' + templatevisit, '--output', diffimrepo]
    ImageDifferenceTask.parseAndRun(args=args, config=config, doReturnResults=True)

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
Process raw decam images with MasterCals from ingestion --> difference imaging

USAGE:
$ python hits_ingest.py ingest -f path/to/rawimages/
$ python hits_ingest.py ingestCalibs -f path/to/calibrations/somefiles*.fits.fz
$ python hits_ingest.py processCcd
$ python hits_ingest.py diffIm

A typical workflow will run these four tasks in order. More details about the
required arguments, bash command equivalents, and result of each task is given
in each function defined below.
'''


def main():
    '''
    Set input parameters (repos, visits, ccdnums) and run the requested task
    '''

    # ~~  edit values below as desired  ~~ #
    repo = 'ingested_15A38/'  # used by ingest, ingestCalibs, processCcd
    calibrepo = 'calibingested_15A38/'  # used by ingestCalibs, processCcd
    processedrepo = 'processed_15A38/'  # used by processCcd, diffIm
    diffimrepo = 'diffim_15A38_g/'  # used by diffIm
    visits = [410927, 411033]  # used by processCcd, diffIm
    # NOTE: visits assumes the first element is template and the rest are science
    ccdnum = '1..62'  # used by processCcd, diffIm
    # NOTE: the default '1..62' value includes all of the DECam CCDs
    # ~~ edit values above as desired  ~~ #

    # Parse visits into strings for command-line arguments
    visit = '^'.join(str(v) for v in visits)
    templatevisit = str(visits[0])
    sciencevisit = '^'.join(str(v) for v in visits[1:])

    # Run whichever task has been requested
    if args.task == 'ingest':
        doIngest(repo, datafiles)
    elif args.task == 'ingestCalibs':
        doIngestCalibs(repo, calibrepo, datafiles)
    elif args.task == 'processCcd':
        doProcessCcd(repo, calibrepo, processedrepo, visit, ccdnum)
    elif args.task == 'diffIm':
        doDiffIm(processedrepo, sciencevisit, ccdnum, templatevisit, diffimrepo)

    return


def doIngest(repo, datafiles):
    '''
    Ingest raw DECam images into a repository with a corresponding registry

    USAGE:
    $ python hits_ingest.py ingest -f path/to/rawimages/
    (will use all files in the directory named *.fz if no files are specified)

    BASH EQUIVALENT:
    $ ingestImagesDecam.py repo --filetype raw --mode link datafiles

    RESULT:
    repo populated with *links* to files in datadir, organized by date
    sqlite3 database registry of ingested images also created in repo
    '''
    if not os.path.isdir(repo):
        os.mkdir(repo)
    # make a text file that handles the mapper, per the obs_decam github README
    with open(os.path.join(repo, '_mapper'), 'w') as f:
        print('lsst.obs.decam.DecamMapper', file=f)
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
    return


def doIngestCalibs(repo, calibrepo, datafiles):
    '''
    Ingest DECam MasterCal biases and flats into a calibration repository with a corresponding registry

    USAGE:
    $ python hits_ingest.py ingestCalibs -f path/to/calibrations/somefiles*.fits.fz

    BASH EQUIVALENT:
    $ ingestCalibs.py repo --calib calibrepo --mode=link --validity 999 datafiles

    RESULT:
    calibrepo populated with *links* to files in datadir,
    organized by date (bias/zero and flat images only)
    sqlite3 database registry of ingested calibration products
    created in calibrepo

    Darks (and fringes, if applicable) must be ingested manually! e.g.,
    $ cd calibrepo
    $ ingestCalibs.py ../repo --calib . --calibType defect --validity 999
          ../HiTS/MasterCals/defects/2014-12-05/*fits

    This function also catches a common sqlite3 error and prints useful info
    '''
    if not os.path.isdir(calibrepo):
        os.mkdir(calibrepo)
    print('Ingesting calibration products...')  # NOTE: just biases and flats
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
    return


def doProcessCcd(repo, calibrepo, processedrepo, visit, ccdnum):
    '''
    Perform ISR with ingested images and calibrations via processCcd

    For successful difference imaging in the next step, astrometry and
    photometric calibration must also be done by processCcd.

    USAGE:
    $ python hits_ingest.py processCcd

    BASH EQUIVALENT:
    $ processCcd.py repo --id visit=visit ccdnum=ccdnum
            --output processedrepo --calib calibrepo
            -C $OBS_DECAM_DIR/config/processCcdCpIsr.py
            -C processccd_config.py
            --config calibrate.doAstrometry=True calibrate.doPhotoCal=True
    ** to run from bash, 'processccd_config.py' must exist and contain, e.g.,
        from lsst.meas.algorithms import LoadIndexedReferenceObjectsTask
        for refObjLoader in (config.calibrate.astromRefObjLoader,
                            config.calibrate.photoRefObjLoader,
                            config.charImage.refObjLoader,
                            ):
        refObjLoader.retarget(LoadIndexedReferenceObjectsTask)
        refObjLoader.ref_dataset_name = 'pan-starrs'
        refObjLoader.filterMap = {"g": "g",
                                  "r": "r",
                                  "VR": "g"}

    RESULT:
    processedrepo/visit populated with subdirectories containing the
    usual post-ISR data (bkgd, calexp, icExp, icSrc, postISR).
    '''
    if not os.path.isdir(processedrepo):
        os.mkdir(processedrepo)
    print('Running ProcessCcd...')
    OBS_DECAM_DIR = getPackageDir('obs_decam')
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
    ProcessCcdTask.parseAndRun(args=args, config=config)
    return


def doDiffIm(processedrepo, sciencevisit, ccdnum, templatevisit, diffimrepo):
    '''
    Do difference imaging with a visit as a template and one or more as science

    USAGE:
    $ python hits_ingest.py diffIm

    BASH EQUIVALENT:
    $ imageDifference.py processedrepo --id visit=sciencevisit ccdnum=ccdnum
            --templateId visit=templatevisit --output diffimrepo
            -C diffim_config.py
    ** to run from bash, 'diffim_config.py' must exist and contain, e.g.,
        from lsst.ip.diffim.getTemplate import GetCalexpAsTemplateTask
        config.getTemplate.retarget(GetCalexpAsTemplateTask)
        config.detection.thresholdValue=5.0
        config.doDecorrelation=True

    RESULT:
    diffimrepo/deepDiff/v+sciencevisit populated with difference images
    and catalogs of detected sources (diaSrc, diffexp, and metadata files)
    '''
    if not os.path.isdir(diffimrepo):
        os.mkdir(diffimrepo)
    print('Running ImageDifference...')
    config = ImageDifferenceConfig()
    config.getTemplate.retarget(GetCalexpAsTemplateTask)
    config.detection.thresholdValue = 5.0
    config.doDecorrelation = True
    args = [processedrepo, '--id', 'visit=' + sciencevisit, 'ccdnum=' + ccdnum,
            '--templateId', 'visit=' + templatevisit, '--output', diffimrepo]
    ImageDifferenceTask.parseAndRun(args=args, config=config)
    return


if __name__ == '__main__':
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
        if os.path.isdir(datadir):
            datafiles = glob(os.path.join(datadir, '*.fz'))
        else:
            datafiles = glob(datadir)
    main()

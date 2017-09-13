#
# LSST Data Management System
# Copyright 2017 LSST Corporation.
#
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.
#

'''
Process raw decam images with MasterCals from ingestion --> difference imaging

TODO: Update DMTN-039 to reflect the new user interface.
      I'm postponing this until DM-11422 and/or DM-11390 are complete.
'''

from __future__ import absolute_import, division, print_function

__all__ = ['runPipelineAlone', 'doIngest', 'doIngestCalibs', 'doProcessCcd', 'doDiffIm']

import os
import argparse
import textwrap
import tarfile
from glob import glob
import sqlite3

import lsst.log
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

# IN PROGRESS: figure out which of these ALL-CAPS VARIABLES are already known by
# ap_verify and which need to be explicitly provided in a function here in ap_pipe

# Names of directories containing data products in dataset_root
RAW_DIR = 'raw'
MASTERCAL_DIR = 'calib'
DEFECT_DIR = 'calib'
REFCATS_DIR = 'refcats'
TEMPLATES_DIR = 'templates'

# Name of defects tarball residing in DEFECT_DIR
DEFECT_TARBALL = 'defects_2014-12-05.tar.gz'

# Names of directories to be created in specified output location
INGESTED_DIR = 'ingested'
CALIBINGESTED_DIR = 'calibingested'
PROCESSED_DIR = 'processed'
DIFFIM_DIR = 'diffim'


def get_datafiles(dataset_root):
    '''
    Retrieve a list of the raw DECam images for use during ingestion.

    Parameters
    ----------
    dataset_root: `str`
        The top-level directory containing all pieces of an ap_verify-style dataset.

    Returns
    -------
    datafiles: `list`
        A list of the filenames of each raw image file.
    '''
    types = ('*.fits', '*.fz')
    datafiles = []
    for files in types:
        datafiles.extend(glob(os.path.join(dataset_root, RAW_DIR, files)))
    return datafiles


def get_calibdatafiles(dataset_root):
    '''
    Retrieve a list of the DECam MasterCal flat and bias files for use during ingestion.

    Parameters
    ----------
    dataset_root: `str`
        The top-level directory containing all pieces of an ap_verify-style dataset.

    Returns
    -------
    calibdatafiles: `list`
        A list of the filenames of each flat and bias image file.
    '''
    types = ('*.fits', '*.fz')
    allcalibdatafiles = []
    for files in types:
        allcalibdatafiles.extend(glob(os.path.join(dataset_root, MASTERCAL_DIR, files)))
    # Ignore wtmaps and illumcors
    calibdatafiles = []
    filestoignore = ['fcw', 'zcw', 'ici']
    for file in allcalibdatafiles:
        if all(string not in file for string in filestoignore):
            calibdatafiles.append(file)
    return calibdatafiles


def get_defectfiles(dataset_root):
    '''
    Retrieve a list of the DECam defect files for use during ingestion.

    Parameters
    ----------
    dataset_root: `str`
        The top-level directory containing all pieces of an ap_verify-style dataset.

    Returns
    -------
    defectfiles: `list`
        A list of the filenames of each defect image file.
        The first element in this list will be the name of a .tar.gz file
        which contains all the compressed defect images.
    '''
    # Retrieve defect filenames from tarball
    defectloc = os.path.join(dataset_root, DEFECT_DIR)
    defect_tarfile_path = glob(os.path.join(defectloc, DEFECT_TARBALL))[0]
    defectfiles = tarfile.open(defect_tarfile_path).getnames()
    defectfiles = [os.path.join(defectloc, file) for file in defectfiles]
    return defectfiles


def get_output_repos(outputpath):
    '''
    Define locations on disk for all of the output repositories used by ap_pipe.

    Parameters
    ----------
    dataset_root: `str`
        The top-level directory containing all pieces of an ap_verify-style dataset.

    Returns
    -------
    repo: `str`
        Repository (directory on disk) where raw images will be ingested.
    calib_repo: `str`
        Repository (directory on disk) where calibration products will be ingested.
    processed_repo: `str`
        Repository (directory on disk) where calexps from processCcd will live.
    diffim_repo: `str`
        Repository (directory on disk) where difference images will live.
    '''
    if not os.path.isdir(args.output):
        os.mkdir(args.output)
    repo = os.path.join(args.output, INGESTED_DIR)
    calib_repo = os.path.join(args.output, CALIBINGESTED_DIR)
    processed_repo = os.path.join(args.output, PROCESSED_DIR)
    diffim_repo = os.path.join(args.output, DIFFIM_DIR)
    return repo, calib_repo, processed_repo, diffim_repo


def parsePipelineArgs():
    '''
    Parse command-line arguments to run the pipeline. NOT used by ap_verify.

    TODO (DM-11422): Implement the arguments that specify dataid info instead
    of having hardwired values for visits and ccdnum.

    Returns
    -------
    repos_and_files: `dict`
        Includes the names of new repos that will be written to disk
        following ingestion, calib ingestion, processing, and difference imaging
        (repo, calib_repo, processed_repo, diffim_repo)
        Includes the files in dataset_root for raw images, flats and biases, 
        and defects (datafiles, calibdatafiles, defectfiles)
    idlist: `list` containing two `str`
        Data ID and template info needed for processing and difference imaging
        [dataId, template]
        TODO: allow 'template' to be either a visit ID or a repo name (DM-11422)
    refcats: `str`
        Path on disk of the reference catalogs
    '''

    # Parse command line arguments with argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description=textwrap.dedent('''
    Process raw decam images with MasterCals from ingestion --> difference imaging

    USAGE:
    $ python ap_pipe.py -d dataset_root -o output_location -i "visit=12345 ccdnum=5"
                                     '''))
    parser.add_argument('-d', '--dataset_root',
                        help="Location on disk of dataset_root, which contains subdirectories of raw data, calibs, etc.")
    parser.add_argument('-o', '--output',
                        help="Location on disk where output repos will live.")
    # TODO: implement this argument. Part of DM-11422.
    # parser.add_argument('-i', '--id',
    #                    help="String containing visit and ccd information. Typically set as 'visit=12345, ccd=5'.")
    args = parser.parse_args()

    # Retrieve lists of input files for raw images and calibration products
    datafiles = get_datafiles(args.dataset_root)
    calibdatafiles = get_calibdatafiles(args.dataset_root)
    defectfiles = get_defectfiles(args.dataset_root)

    # Define output repo locations on disk
    repo, calib_repo, processed_repo, diffim_repo = get_output_repos(args.output)

    # Retrieve location of refcats directory containing gaia and pan-starrs tarballs
    refcats = os.path.join(args.dataset_root, REFCATS_DIR)

    # TEMPORARY HARDWIRED THINGS ARE TEMPORARY
    # TODO (DM-11422):
    # - use a coadd as a template instead of a visit
    # - implement the --id argument and pull visit and ccdnum from there (default = all CCDs)
    visit = '410985'  # one arbitrary g-band visit in Blind15A40
    templatevisit = '410929'  # another arbitrary g-band visit in Blind15A40
    ccdnum = '25'  # arbitrary single CCD for testing
    sciencevisit = visit  # for doDiffIm, for now

    repos_and_files = {'repo': repo, 'calib_repo': calib_repo, 
                       'processed_repo': processed_repo, 
                       'diffim_repo': diffim_repo, 'datafiles': datafiles, 
                       'calibdatafiles', calibdatafiles, 'defectfiles': defectfiles}
    idlist = [visit, sciencevisit, templatevisit, ccdnum]

    return repos_and_files, idlist, refcats


def doIngest(repo, refcats, datafiles):
    '''
    Ingest raw DECam images into a repository with a corresponding registry

    Parameters
    ----------
    repo: `str`
        The output repository location on disk where ingested raw images live.
    refcats: `str`
        A directory containing two .tar.gz files with LSST-formatted astrometric
        and photometric reference catalog information. The filenames are set below.
    datafiles: `list`
        A list of the filenames of each raw image file.

    BASH EQUIVALENT:
    $ ingestImagesDecam.py repo --filetype raw --mode link datafiles
    ** If run from bash, refcats must also be manually copied or symlinked to repo

    Returns
    -------
    ingest_metadata: `PropertySet` or None
        Metadata from the IngestTask for use by ap_verify

    RESULT:
    repo populated with *links* to datafiles, organized by date
    sqlite3 database registry of ingested images also created in repo

    NOTE:
    This functions ingests *all* the images, not just the ones for the
    specified visits and/or filters. We may want to revisit this in the future.
    '''
    # Names of tarballs containing astrometric and photometric reference catalog files
    ASTROM_REFCAT_TAR = 'gaia_HiTS_2015.tar.gz'
    PHOTOM_REFCAT_TAR = 'ps1_HiTS_2015.tar.gz'

    # Names of reference catalog directories processCcd expects to find in repo
    ASTROM_REFCAT_DIR = 'refcats/gaia'
    PHOTOM_REFCAT_DIR = 'refcats/pan-starrs'

    lsst.log.configure()
    log = lsst.log.Log.getLogger('ap.pipe.doIngest')
    if os.path.exists(os.path.join(repo, 'registry.sqlite3')):
        log.warn('Raw images were previously ingested, skipping...')
        return None
    if not os.path.isdir(repo):
        os.mkdir(repo)
    # make a text file that handles the mapper, per the obs_decam github README
    with open(os.path.join(repo, '_mapper'), 'w') as f:
        print('lsst.obs.decam.DecamMapper', file=f)
    log.info('Ingesting raw images...')
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
    # create an *instance* of the decam ingest task
    ingestTask = ingest.DecamIngestTask(config=config)
    # feed everything to the argument parser
    parsedCmd = argumentParser.parse_args(config=config, args=args)
    # finally, run the ingestTask
    ingestTask.run(parsedCmd)
    # Copy refcats files to repo (needed for doProcessCcd)
    astrom_tarball = os.path.join(refcats, ASTROM_REFCAT_TAR)
    photom_tarball = os.path.join(refcats, PHOTOM_REFCAT_TAR)
    tarfile.open(astrom_tarball, 'r').extractall(os.path.join(repo, ASTROM_REFCAT_DIR))
    tarfile.open(photom_tarball, 'r').extractall(os.path.join(repo, PHOTOM_REFCAT_DIR))
    log.info('Images are now ingested in {0}'.format(repo))
    ingest_metadata = ingestTask.getFullMetadata()
    return ingest_metadata


def flatBiasIngest(repo, calib_repo, calibdatafiles):
    '''
    Ingest DECam flats and biases (called by doIngestCalibs)

    Parameters
    ----------
    repo: `str`
        The output repository location on disk where ingested raw images live.
    calib_repo: `str`
        The output repository location on disk where ingested calibration images live.
    calibdatafiles: `list`
        A list of the filenames of each flat and bias image file.

    Returns
    -------
    flatBias_metadata: `PropertySet` or None
        Metadata from the IngestCalibTask (flats and biases) for use by ap_verify

    BASH EQUIVALENT:
    $ ingestCalibs.py repo --calib calib_repo --mode=link --validity 999 calibdatafiles
    '''
    lsst.log.configure()
    log = lsst.log.Log.getLogger('ap.pipe.flatBiasIngest')
    log.info('Ingesting flats and biases...')
    args = [repo, '--calib', calib_repo, '--mode', 'link', '--validity', '999']
    args.extend(calibdatafiles)
    argumentParser = IngestCalibsArgumentParser(name='ingestCalibs')
    config = IngestCalibsConfig()
    config.parse.retarget(ingestCalibs.DecamCalibsParseTask)
    calibIngestTask = IngestCalibsTask(config=config, name='ingestCalibs')
    parsedCmd = argumentParser.parse_args(config=config, args=args)
    try:
        calibIngestTask.run(parsedCmd)
    except sqlite3.IntegrityError as detail:
        log.error('sqlite3.IntegrityError: ', detail)
        log.error('(sqlite3 doesn\'t think all the calibration files are unique)')
        flatBias_metadata = None
    else:
        log.info('Success!')
        log.info('Calibrations corresponding to {0} are now ingested in {1}'.format(repo, calib_repo))
        flatBias_metadata = calibIngestTask.getFullMetadata()
    return flatBias_metadata


def defectIngest(repo, calib_repo, defectfiles):
    '''
    Ingest DECam defect images (called by doIngestCalibs)

    Parameters
    ----------
    repo: `str`
        The output repository location on disk where ingested raw images live.
    calib_repo: `str`
        The output repository location on disk where ingested calibration images live.
    defectfiles: `list`
        A list of the filenames of each defect image file.
        The first element in this list must be the name of a .tar.gz file
        which contains all the compressed defect images.

    Returns
    -------
    defect_metadata: `PropertySet` or None
        Metadata from the IngestCalibTask (defects) for use by ap_verify

    BASH EQUIVALENT:
    $ cd calib_repo
    $ ingestCalibs.py ../../repo --calib . --mode=skip --calibType defect --validity 999 defectfiles
    $ cd ..

    This function assumes very particular things about defect ingestion:
    - They must live in a .tar.gz file in the same location on disk as the other calibs
    - They will be ingested using ingestCalibs.py run from the calib_repo directory
    - They will be manually uncompressed and saved in calib_repo/defects/<tarballname>/.
    - They will be added to the calib registry, but not linked like the flats and biases
    '''
    lsst.log.configure()
    log = lsst.log.Log.getLogger('ap.pipe.defectIngest')
    os.chdir(calib_repo)
    try:
        os.mkdir('defects')
    except OSError:
        # most likely the defects directory already exists
        if os.path.isdir('defects'):
            log.warn('Defects were previously ingested, skipping...')
        else:
            log.error('Defect ingestion failed because \'defects\' dir could not be created')
        defect_metadata = None
    else:
        log.info('Ingesting defects...')
        defectargs = ['../../' + repo, '--calib', '.', '--calibType', 'defect',
                      '--mode', 'skip', '--validity', '999']
        defect_tarball = defectfiles[0] + '.tar.gz'
        tarfile.open(os.path.join('../../', defect_tarball), 'r').extractall('defects')
        defectfiles = glob(os.path.join('defects', os.path.basename(defectfiles[0]), '*.fits'))
        defectargs.extend(defectfiles)
        defectArgumentParser = IngestCalibsArgumentParser(name='ingestCalibs')
        defectConfig = IngestCalibsConfig()
        defectConfig.parse.retarget(ingestCalibs.DecamCalibsParseTask)
        DefectIngestTask = IngestCalibsTask(config=defectConfig, name='ingestCalibs')
        defectParsedCmd = defectArgumentParser.parse_args(config=defectConfig, args=defectargs)
        DefectIngestTask.run(defectParsedCmd)
        defect_metadata = DefectIngestTask.getFullMetadata()
    finally:
        os.chdir('../..')
    return defect_metadata


def doIngestCalibs(repo, calib_repo, calibdatafiles, defectfiles):
    '''
    Ingest DECam MasterCal biases and flats into a calibration repository with a corresponding registry.
    Also ingest DECam defects into the calib registry.

    Parameters
    ----------
    repo: `str`
        The output repository location on disk where ingested raw images live.
    calib_repo: `str`
        The output repository location on disk where ingested calibration images live.
    calibdatafiles: `list`
        A list of the filenames of each flat and bias image file.
    defectfiles: `list`
            A list of the filenames of each defect image file.
            The first element in this list must be the name of a .tar.gz file
            which contains all the compressed defect images.

    Returns
    -------
    calibingest_metadata: `PropertySet` or None
        Metadata from the IngestCalibTask (flats and biases) and from the
        IngestCalibTask (defects) for use by ap_verify

    RESULT:
    calib_repo populated with *links* to calibdatafiles,
    organized by date (bias and flat images only)
    sqlite3 database registry of ingested calibration products (bias, flat,
    and defect images) created in calib_repo

    NOTE:
    calib ingestion ingests *all* the calibs, not just the ones needed
    for certain visits. We may want to ...revisit... this in the future.
    '''
    lsst.log.configure()
    log = lsst.log.Log.getLogger('ap.pipe.doIngestCalibs')
    if not os.path.isdir(calib_repo):
        os.mkdir(calib_repo)
        flatBias_metadata = flatBiasIngest(repo, calib_repo, calibdatafiles)
        defect_metadata = defectIngest(repo, calib_repo, defectfiles)
    elif os.path.exists(os.path.join(calib_repo, 'cpBIAS')):
        log.warn('Flats and biases were previously ingested, skipping...')
        flatBias_metadata = None
        defect_metadata = defectIngest(repo, calib_repo, defectfiles)
    else:
        flatBias_metadata = flatBiasIngest(repo, calib_repo, calibdatafiles)
        defect_metadata = defectIngest(repo, calib_repo, defectfiles)
    calibingest_metadata = flatBias_metadata
    calibingest_metadata.combine(defect_metadata)
    return calibingest_metadata


def doProcessCcd(repo, calib_repo, processed_repo, visit, ccdnum):
    '''
    Perform ISR with ingested images and calibrations via processCcd

    Parameters
    ----------
    repo: `str`
        The output repository location on disk where ingested raw images live.
    calib_repo: `str`
        The output repository location on disk where ingested calibration images live.
    processed_repo: `str`
        The output repository location on disk where processed raw images live.
    dataId: `str`
        Butler identifier naming the data to be processed (e.g., visit and ccdnum)
        formatted in the usual way (e.g., 'visit=54321 ccdnum=7').

    Returns
    -------
    process_metadata: `PropertySet` or None
        Metadata from the ProcessCcdTask for use by ap_verify

    BASH EQUIVALENT:
    $ processCcd.py repo --id dataId
            --output processed_repo --calib calib_repo
            -C $OBS_DECAM_DIR/config/processCcdCpIsr.py
            -C processccd_config.py
            --config calibrate.doAstrometry=True calibrate.doPhotoCal=True
    ** to run from bash, 'processccd_config.py' must exist and contain
       all of the refObjLoader information in the code below. repo must also
       already contain the refcats (this is done during doIngest).

    RESULT:
    processed_repo/visit populated with subdirectories containing the
    usual post-ISR data (bkgd, calexp, icExp, icSrc, postISR).
    By default, the configuration for astrometric reference catalogs uses Gaia
    and the configuration for photometry reference catalogs uses Pan-STARRS.
    '''
    lsst.log.configure()
    log = lsst.log.Log.getLogger('ap.pipe.doProcessCcd')
    if os.path.isdir(os.path.join(processed_repo, '0'+visit)):
        log.warn('ProcessCcd has already been run for visit {0}, skipping...'.format(visit))
        return None
    if not os.path.isdir(processed_repo):
        os.mkdir(processed_repo)
    log.info('Running ProcessCcd...')
    OBS_DECAM_DIR = getPackageDir('obs_decam')
    config = ProcessCcdConfig()
    # Use gaia for astrometry (phot_g_mean_mag is only available DR1 filter)
    # Use pan-starrs for photometry (grizy filters)
    for refObjLoader in (config.calibrate.astromRefObjLoader,
                         config.calibrate.photoRefObjLoader,
                         config.charImage.refObjLoader,):
        refObjLoader.retarget(LoadIndexedReferenceObjectsTask)
    config.calibrate.astromRefObjLoader.ref_dataset_name = 'gaia'
    config.calibrate.astromRefObjLoader.filterMap = {'u': 'phot_g_mean_mag',
                                                     'g': 'phot_g_mean_mag',
                                                     'r': 'phot_g_mean_mag',
                                                     'i': 'phot_g_mean_mag',
                                                     'z': 'phot_g_mean_mag',
                                                     'y': 'phot_g_mean_mag',
                                                     'VR': 'phot_g_mean_mag'}
    config.calibrate.photoRefObjLoader.ref_dataset_name = 'pan-starrs'
    config.calibrate.photoRefObjLoader.filterMap = {'u': 'g',
                                                    'g': 'g',
                                                    'r': 'r',
                                                    'i': 'i',
                                                    'z': 'z',
                                                    'y': 'y',
                                                    'VR': 'g'}
    args = [repo, '--id', 'visit=' + visit, 'ccdnum=' + ccdnum,
            '--output', processed_repo,
            '--calib', calib_repo,
            '-C', OBS_DECAM_DIR + '/config/processCcdCpIsr.py',
            '--config', 'calibrate.doAstrometry=True',
            'calibrate.doPhotoCal=True']
    process_result = ProcessCcdTask.parseAndRun(args=args, config=config, doReturnResults=True)
    process_metadata = process_result.resultList[0].metadata
    return process_metadata


def doDiffIm(processed_repo, sciencevisit, ccdnum, templatevisit, diffim_repo):
    '''
    Do difference imaging with a visit as a template and one or more as science

    Parameters
    ----------
    processed_repo: `str`
        The output repository location on disk where processed raw images live.
    dataId: `str`
        Butler identifier naming the data to be processed (e.g., visit and ccdnum)
        formatted in the usual way (e.g., 'visit=54321 ccdnum=7').
    template: `str`
        The single DECam visit number which will be used as a template for
        difference imaging.
        TODO: allow 'template' to be either a visit ID or a repo name (DM-11422)
    diffim_repo: `str`
        The output repository location on disk where difference images live.

    Returns
    -------
    diffim_metadata: `PropertySet` or None
        Metadata from the ImageDifferenceTask for use by ap_verify

    BASH EQUIVALENT:
    $ imageDifference.py processed_repo --id dataId
            --templateId visit=template --output diffim_repo
            -C diffim_config.py
    ** to run from bash, 'diffim_config.py' must exist and contain, e.g.,
        from lsst.ip.diffim.getTemplate import GetCalexpAsTemplateTask
        config.getTemplate.retarget(GetCalexpAsTemplateTask)
        config.detection.thresholdValue = 5.0
        config.doDecorrelation = True

    TODO: use coadds as templates by default, not another visit (DM-11422).
    Some of the comments in this function are placeholders for DM-11422 work.

    RESULT:
    diffim_repo/deepDiff/v+visit populated with difference images
    and catalogs of detected sources (diaSrc, diffexp, and metadata files)
    '''
    lsst.log.configure()
    log = lsst.log.Log.getLogger('ap.pipe.doDiffIm')
    if os.path.exists(os.path.join(diffim_repo, 'deepDiff', 'v' + sciencevisit)):
        log.warn('DiffIm has already been run for visit {0}, skipping...'.format(sciencevisit))
        return None
    if not os.path.isdir(diffim_repo):
        os.mkdir(diffim_repo)
    log.info('Running ImageDifference...')
    config = ImageDifferenceConfig()
    config.getTemplate.retarget(GetCalexpAsTemplateTask)  # not for use with coadds
    #config.doSelectSources = False  # for use with coadds only
    config.detection.thresholdValue = 5.0
    config.doDecorrelation = True
    args = [processed_repo, '--id', 'visit=' + sciencevisit, 'ccdnum=' + ccdnum,
            '--templateId', 'visit=' + templatevisit, '--output', diffim_repo]  # visit option
    # args = [processed_repo, '--id', 'visit=' + sciencevisit, 'ccdnum=' + ccdnum,
    #         '--output', diffim_repo]  # coadd option
    # IMPORTANT: diffim_repo must have the coadd templates in it
    diffim_result = ImageDifferenceTask.parseAndRun(args=args, config=config, doReturnResults=True)
    diffim_metadata = diffim_result.resultList[0].metadata
    return diffim_metadata


def runPipelineAlone():
    '''
    Run each step of the pipeline. NOT used by ap_verify.

    This function is solely for the purpose of running ap_pipe alone,
    from the command line, on a dataset intended for ap_verify. It is useful
    for testing or standalone image processing independently from verification.
    '''
    lsst.log.configure()
    log = lsst.log.Log.getLogger('ap.pipe.runPipelineAlone')
    repos_and_files, idlist, refcats = parsePipelineArgs()
    
    repo = repos_and_files['repo']
    calib_repo = repos_and_files['calib_repo']
    processed_repo = repos_and_files['processed_repo']
    diffim_repo = repos_and_files['diffim_repo']

    datafiles = repos_and_files['datafiles']
    calibdatafiles = repos_and_files['calibdatafiles']
    defectfiles = repos_and_files['defectfiles']

    visit = idlist[0]
    sciencevisit = idlist[1]
    templatevisit = idlist[2]
    ccdnum = idlist[3]

    # Run all the tasks in order
    doIngest(repo, refcats, datafiles)
    doIngestCalibs(repo, calib_repo, calibdatafiles, defectfiles)
    doProcessCcd(repo, calib_repo, processed_repo, visit, ccdnum)
    doProcessCcd(repo, calib_repo, processed_repo, templatevisit, ccdnum)  # temporary
    doDiffIm(processed_repo, sciencevisit, ccdnum, templatevisit, diffim_repo)
    log.info('Prototype AP Pipeline run complete.')

    return
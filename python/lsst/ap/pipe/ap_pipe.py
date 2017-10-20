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
Process raw DECam images with MasterCals from ingestion --> difference imaging.

A tutorial for using ap_pipe is available in DMTN-039 (http://dmtn-039.lsst.io).

ap_pipe is designed to be used as the main processing portion of ap_verify, but
it can also be run alone from the command line, e.g.:
$ python ap_pipe/bin.src/ap_pipe.py -d ap_verify_hits2015/ -o output_dir
         -i "visit=410985 ccdnum=25"
'''

from __future__ import absolute_import, division, print_function

__all__ = ['get_datafiles', 'get_calib_datafiles', 'get_defectfiles', 'get_output_repo',
           'doIngest', 'doIngestCalibs', 'doProcessCcd', 'doDiffIm', 'doAssociation',
           'runPipelineAlone']

import os
import argparse
import textwrap
import tarfile
from glob import glob
import sqlite3
import re

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
from lsst.ap.association import AssociationDBSqliteTask, AssociationConfig, AssociationTask
import lsst.daf.persistence as dafPersist

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
DB_DIR = 'l1db'


def get_datafiles(raw_location):
    '''
    Retrieve a list of the raw DECam images for use during ingestion.

    Parameters
    ----------
    raw_location: `str`
        The path on disk to where the raw files live.

    Returns
    -------
    datafiles: `list`
        A list of the filenames of each raw image file.
    '''
    types = ('*.fits', '*.fz')
    datafiles = []
    for files in types:
        datafiles.extend(glob(os.path.join(raw_location, files)))
    return datafiles


def get_calib_datafiles(calib_location):
    '''
    Retrieve a list of the DECam MasterCal flat and bias files for use during ingestion.

    Parameters
    ----------
    calib_location: `str`
        The path on disk to where the calibration files live.

    Returns
    -------
    calib_datafiles: `list`
        A list of the filenames of each flat and bias image file.
    '''
    types = ('*.fits', '*.fz')
    all_calib_datafiles = []
    for files in types:
        all_calib_datafiles.extend(glob(os.path.join(calib_location, files)))
    # Ignore wtmaps and illumcors
    calib_datafiles = []
    files_to_ignore = ['fcw', 'zcw', 'ici']
    for file in all_calib_datafiles:
        if all(string not in file for string in files_to_ignore):
            calib_datafiles.append(file)
    return calib_datafiles


def get_defectfiles(defect_location, defect_tarball=DEFECT_TARBALL):
    '''
    Retrieve a list of the DECam defect files for use during ingestion.

    Parameters
    ----------
    defect_location: `str`
        The path on disk to where the defect tarball lives.
    defect_tarball: `str`
        The filename of the tarball containing the defect files.

    Returns
    -------
    defectfiles: `list`
        A list of the filenames of each defect image file.
        The first element in this list will be the name of a .tar.gz file
        which contains all the compressed defect images.
    '''
    # Retrieve defect filenames from tarball
    defect_tarfile_path = os.path.join(defect_location, defect_tarball)
    defectfiles = tarfile.open(defect_tarfile_path).getnames()
    defectfiles = [os.path.join(defect_location, file) for file in defectfiles]
    return defectfiles


def get_output_repo(output_root, output_dir):
    '''
    Return location on disk for one output repository used by ap_pipe.

    Parameters
    ----------
    output_root: `str`
        The top-level directory where the output will live.
    output_dir: `str`
        Name of the subdirectory to be created in output_root.

    Returns
    -------
    output_path: `str`
        Repository (directory on disk) where desired output product will live.
    '''
    if not os.path.isdir(output_root):
        os.mkdir(output_root)
    output_path = os.path.join(output_root, output_dir)
    return output_path


def parsePipelineArgs():
    '''
    Parse command-line arguments to run the pipeline. NOT used by ap_verify.

    Returns
    -------
    repos_and_files: `dict`
        Includes the names of new repos that will be written to disk
        following ingestion, calib ingestion, processing, and difference imaging
        ('repo', 'calib_repo', 'processed_repo', 'diffim_repo')
        Includes the files in dataset_root for raw images, flats and biases,
        and defects ('datafiles', 'calib_datafiles', 'defectfiles')
        Finally includes the path on disk of the reference catalogs ('refcats')
    idlist: `list` containing two `str`
        Data ID and template info needed for processing and difference imaging
        [dataId, template]
        TODO: allow 'template' to be either a visit ID or a repo name (DM-11422)
    '''

    # Parse command line arguments with argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description=textwrap.dedent('''
    Process raw decam images with MasterCals from ingestion --> difference imaging

    USAGE:
    $ python ap_pipe.py -d dataset_root -o output_location -i "visit=12345 ccdnum=5"
                                     '''))
    parser.add_argument('-d', '--dataset_root',
                        help="Location on disk of dataset_root, which contains subdirectories of \
                              raw data, calibs, etc.")
    parser.add_argument('-o', '--output',
                        help="Location on disk where output repos will live.")
    parser.add_argument('-i', '--dataId',
                        help="Butler identifier naming the data to be processed (e.g., visit and ccdnum) \
                              formatted in the usual way (e.g., 'visit=54321 ccdnum=7').")
    args = parser.parse_args()

    # Retrieve lists of input files for raw images and calibration products
    datafiles = get_datafiles(os.path.join(args.dataset_root, RAW_DIR))
    calib_datafiles = get_calib_datafiles(os.path.join(args.dataset_root, MASTERCAL_DIR))
    defectfiles = get_defectfiles(os.path.join(args.dataset_root, DEFECT_DIR))

    # Define output repo locations on disk
    repo = get_output_repo(args.output, INGESTED_DIR)
    calib_repo = get_output_repo(args.output, CALIBINGESTED_DIR)
    processed_repo = get_output_repo(args.output, PROCESSED_DIR)
    diffim_repo = get_output_repo(args.output, DIFFIM_DIR)
    db_repo = get_output_repo(args.output, DB_DIR)

    # Retrieve location of refcats directory containing gaia and pan-starrs tarballs
    refcats = os.path.join(args.dataset_root, REFCATS_DIR)

    # TEMPORARY HARDWIRED THINGS ARE TEMPORARY
    # TODO (DM-11422):
    # - use a coadd as a template instead of a visit
    # dataId = 'visit=410985 ccdnum=25'  # one g-band visit in Blind15A40 and one CCD for testing
    template = '410929'  # one g-band visit in Blind15A40, temporarily hard-wired

    repos_and_files = {'repo': repo, 'calib_repo': calib_repo,
                       'processed_repo': processed_repo,
                       'diffim_repo': diffim_repo, 'db_repo': db_repo,
                       'datafiles': datafiles,
                       'calib_datafiles': calib_datafiles, 'defectfiles': defectfiles,
                       'refcats': refcats}
    idlist = [args.dataId, template]

    return repos_and_files, idlist


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
    ASTROM_REFCAT_DIR = 'ref_cats/gaia'
    PHOTOM_REFCAT_DIR = 'ref_cats/pan-starrs'

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


def flatBiasIngest(repo, calib_repo, calib_datafiles):
    '''
    Ingest DECam flats and biases (called by doIngestCalibs)

    Parameters
    ----------
    repo: `str`
        The output repository location on disk where ingested raw images live.
    calib_repo: `str`
        The output repository location on disk where ingested calibration images live.
    calib_datafiles: `list`
        A list of the filenames of each flat and bias image file.

    Returns
    -------
    flatBias_metadata: `PropertySet` or None
        Metadata from the IngestCalibTask (flats and biases) for use by ap_verify

    BASH EQUIVALENT:
    $ ingestCalibs.py repo --calib calib_repo --mode=link --validity 999 calib_datafiles
    '''
    log = lsst.log.Log.getLogger('ap.pipe.flatBiasIngest')
    log.info('Ingesting flats and biases...')
    args = [repo, '--calib', calib_repo, '--mode', 'link', '--validity', '999']
    args.extend(calib_datafiles)
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
        raise
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
    log = lsst.log.Log.getLogger('ap.pipe.defectIngest')
    os.chdir(calib_repo)
    try:
        os.mkdir('defects')
    except OSError:
        # most likely the defects directory already exists
        if os.path.isdir('defects'):
            log.warn('Defects were previously ingested, skipping...')
            defect_metadata = None
        else:
            log.error('Defect ingestion failed because \'defects\' dir could not be created')
            raise
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


def doIngestCalibs(repo, calib_repo, calib_datafiles, defectfiles):
    '''
    Ingest DECam MasterCal biases and flats into a calibration repository with a corresponding registry.
    Also ingest DECam defects into the calib registry.

    Parameters
    ----------
    repo: `str`
        The output repository location on disk where ingested raw images live.
    calib_repo: `str`
        The output repository location on disk where ingested calibration images live.
    calib_datafiles: `list`
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
    calib_repo populated with *links* to calib_datafiles,
    organized by date (bias and flat images only)
    sqlite3 database registry of ingested calibration products (bias, flat,
    and defect images) created in calib_repo

    NOTE:
    calib ingestion ingests *all* the calibs, not just the ones needed
    for certain visits. We may want to ...revisit... this in the future.
    '''
    log = lsst.log.Log.getLogger('ap.pipe.doIngestCalibs')
    if not os.path.isdir(calib_repo):
        os.mkdir(calib_repo)
        flatBias_metadata = flatBiasIngest(repo, calib_repo, calib_datafiles)
        defect_metadata = defectIngest(repo, calib_repo, defectfiles)
    elif os.path.exists(os.path.join(calib_repo, 'cpBIAS')):
        log.warn('Flats and biases were previously ingested, skipping...')
        flatBias_metadata = None
        defect_metadata = defectIngest(repo, calib_repo, defectfiles)
    else:
        flatBias_metadata = flatBiasIngest(repo, calib_repo, calib_datafiles)
        defect_metadata = defectIngest(repo, calib_repo, defectfiles)
    # Handle the case where one or both of the calib metadatas may be None
    if flatBias_metadata is not None:
        calibingest_metadata = flatBias_metadata
        if defect_metadata is not None:
            calibingest_metadata.combine(defect_metadata)
    else:
        calibingest_metadata = defect_metadata
    return calibingest_metadata


def doProcessCcd(repo, calib_repo, processed_repo, dataId):
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
    log = lsst.log.Log.getLogger('ap.pipe.doProcessCcd')
    dataId_items = re.split('[ +=]', dataId)
    dataId_dict = dict(zip(dataId_items[::2], dataId_items[1::2]))
    if 'visit' not in dataId_dict.keys():
        raise RuntimeError('The dataId string is missing \'visit\'')
    else:  # save the visit number from the dataId
        visit = dataId_dict['visit']
    if os.path.isdir(os.path.join(processed_repo, '0'+visit)):
        log.warn('ProcessCcd has already been run for visit {0}, skipping...'.format(visit))
        return None
    if not os.path.isdir(processed_repo):
        os.mkdir(processed_repo)
    log.info('Running ProcessCcd...')
    OBS_DECAM_DIR = getPackageDir('obs_decam')
    calib_repo = os.path.abspath(calib_repo)
    butler = dafPersist.Butler(inputs={'root': repo, 'mapperArgs': {'calibRoot': calib_repo}},
                               outputs=processed_repo)
    config = ProcessCcdConfig()
    config.load(os.path.join(OBS_DECAM_DIR, 'config/processCcd.py'))
    config.load(os.path.join(OBS_DECAM_DIR, 'config/processCcdCpIsr.py'))
    config.calibrate.doAstrometry = True
    config.calibrate.doPhotoCal = True
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
    processCcdTask = ProcessCcdTask(butler=butler, config=config)
    processCcdTask.run(butler.dataRef('raw', dataId=dataId_dict))
    process_metadata = processCcdTask.metadata
    return process_metadata


def doDiffIm(processed_repo, dataId, template, diffim_repo):
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

    RESULT:
    diffim_repo/deepDiff/v+visit populated with difference images
    and catalogs of detected sources (diaSrc, diffexp, and metadata files)
    '''
    log = lsst.log.Log.getLogger('ap.pipe.doDiffIm')
    dataId_items = re.split('[ +=]', dataId)
    dataId_dict = dict(zip(dataId_items[::2], dataId_items[1::2]))
    if 'visit' not in dataId_dict.keys():
        raise RuntimeError('The dataId string is missing \'visit\'')
    else:  # save the visit number from the dataId
        visit = dataId_dict['visit']
    if os.path.exists(os.path.join(diffim_repo, 'deepDiff', 'v' + visit)):
        log.warn('DiffIm has already been run for visit {0}, skipping...'.format(visit))
        return None
    if not os.path.isdir(diffim_repo):
        os.mkdir(diffim_repo)
    log.info('Running ImageDifference...')
    config = ImageDifferenceConfig()
    config.getTemplate.retarget(GetCalexpAsTemplateTask)  # visit template config
    # config.doSelectSources = False  # coadd template config
    config.detection.thresholdValue = 5.0
    config.doDecorrelation = True
    dataId = dataId.split(' ')
    args = [processed_repo, '--id']
    args.extend(dataId)
    args.extend(['--templateId', 'visit=' + template, '--output', diffim_repo])  # visit option
    # args.extend(['--template', template, '--output', diffim_repo])  # coadd option (DM-11422)
    diffim_result = ImageDifferenceTask.parseAndRun(args=args, config=config, doReturnResults=True)
    diffim_metadata = diffim_result.resultList[0].metadata
    return diffim_metadata


def _setupDatabase(configurable):
    '''
    Set up a database according to a configuration.

    Takes no action if the database already exists.

    Parameters
    ----------
    configurable: `lsst.pex.config.ConfigurableInstance`
        A ConfigurableInstance with a database-managing class in its `target`
        field. The API of `target` must expose a `create_tables` method taking
        no arguments.
    '''
    db = configurable.apply()
    try:
        db.create_tables()
    finally:
        db.close()


# TODO: duplication of ArgumentParser's internal functionality; remove this in DM-11372
def _deStringDataId(dataId):
    '''
    Replace a dataId's values with numbers, where appropriate.

    Parameters
    ----------
    dataId: `dict`
        The dataId to be cleaned up.
    '''
    integer = re.compile('^\s*[+-]?\d+\s*$')
    for key, value in dataId.items():
        if isinstance(value, basestring) and integer.match(value) is not None:
            dataId[key] = int(value)


def doAssociation(diffim_repo, dataId, db_repo):
    '''
    Do source association.

    Parameters
    ----------
    diffim_repo: `str`
        The output repository location on disk where difference images live.
    dataId: `str`
        Butler identifier naming the data to be processed (e.g., visit and ccdnum)
        formatted in the usual way (e.g., 'visit=54321 ccdnum=7').
    db_repo: `str`
        The output repository location on disk where the source database lives.

    Returns
    -------
    assoc_metadata: `PropertySet` or None
        Metadata from the AssociationTask for use by ap_verify
    '''
    log = lsst.log.Log.getLogger('ap.pipe.doAssociation')
    dataId_items = re.split('[ +=]', dataId)
    dataId_dict = dict(zip(dataId_items[::2], dataId_items[1::2]))
    if 'visit' not in dataId_dict.keys():
        raise RuntimeError('The dataId string is missing \'visit\'')
    _deStringDataId(dataId_dict)

    # No reasonable way to check if Association finished successfully
    if not os.path.isdir(db_repo):
        os.mkdir(db_repo)

    log.info('Running Association...')
    config = AssociationConfig()
    config.level1_db.retarget(AssociationDBSqliteTask)
    config.level1_db.db_name = os.path.join(db_repo, 'association.db')

    butler = dafPersist.Butler(inputs=diffim_repo)

    _setupDatabase(config.level1_db)

    associationTask = AssociationTask(config=config)
    try:
        catalog = butler.get('deepDiff_diaSrc', dataId=dataId_dict)
        exposure = butler.get('deepDiff_differenceExp', dataId=dataId_dict)
        associationTask.run(catalog, exposure)
    finally:
        associationTask.level1_db.close()

    return associationTask.getFullMetadata()


def runPipelineAlone():
    '''
    Run each step of the pipeline. NOT used by ap_verify.

    This function is solely for the purpose of running ap_pipe alone,
    from the command line, on a dataset intended for ap_verify. It is useful
    for testing or standalone image processing independently from verification.
    '''
    lsst.log.configure()
    log = lsst.log.Log.getLogger('ap.pipe.runPipelineAlone')
    repos_and_files, idlist = parsePipelineArgs()

    repo = repos_and_files['repo']
    calib_repo = repos_and_files['calib_repo']
    processed_repo = repos_and_files['processed_repo']
    diffim_repo = repos_and_files['diffim_repo']
    db_repo = repos_and_files['db_repo']

    datafiles = repos_and_files['datafiles']
    calib_datafiles = repos_and_files['calib_datafiles']
    defectfiles = repos_and_files['defectfiles']

    refcats = repos_and_files['refcats']

    dataId = idlist[0]
    template = idlist[1]

    dataId_template = 'visit=410929 ccdnum=25'  # temporary

    # Run all the tasks in order
    doIngest(repo, refcats, datafiles)
    doIngestCalibs(repo, calib_repo, calib_datafiles, defectfiles)
    doProcessCcd(repo, calib_repo, processed_repo, dataId)
    doProcessCcd(repo, calib_repo, processed_repo, dataId_template)  # temporary
    doDiffIm(processed_repo, dataId, template, diffim_repo)
    doAssociation(diffim_repo, dataId, db_repo)
    log.info('Prototype AP Pipeline run complete.')

    return

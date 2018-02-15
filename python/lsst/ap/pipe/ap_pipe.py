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
Process raw DECam images with MasterCals from basic processing --> source association.

A tutorial for using ap_pipe is available in DMTN-039 (http://dmtn-039.lsst.io).

ap_pipe is designed to be used as the main processing portion of ap_verify, but
it can also be run alone from the command line, e.g.:
$ python ap_pipe/bin.src/ap_pipe.py input_dir -o output_dir
         -i "visit=410985 ccdnum=25"
'''

from __future__ import absolute_import, division, print_function

__all__ = ['get_output_repo',
           'doIngestTemplates', 'doProcessCcd', 'doDiffIm', 'doAssociation',
           'runPipelineAlone']

import os
import argparse
import re

import lsst.log
from lsst.pipe.tasks.processCcd import ProcessCcdTask, ProcessCcdConfig
from lsst.meas.algorithms import LoadIndexedReferenceObjectsTask
from lsst.utils import getPackageDir
from lsst.ip.diffim.getTemplate import GetCalexpAsTemplateTask
from lsst.pipe.tasks.imageDifference import ImageDifferenceConfig, ImageDifferenceTask
from lsst.ap.association import AssociationDBSqliteTask, AssociationConfig, AssociationTask
import lsst.daf.persistence as dafPersist

# Names of directories to be created in specified output location
INGESTED_DIR = 'ingested'
CALIBINGESTED_DIR = 'calibingested'
PROCESSED_DIR = 'processed'
DIFFIM_DIR = 'diffim'
DB_DIR = 'l1db'


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
    `dict`
        Includes the names of new repos that will be written to disk
        following ingestion, calib ingestion, processing, and difference imaging
        ('repo', 'calib_repo', 'processed_repo', 'diffim_repo')
        Includes the data ID of the data to process ('dataID')
        Includes the type of template ('templateType', can be 'coadd' or 'visit'),
        and the repository or dataId of the template, respectively ('template')
    '''

    # Parse command line arguments with argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description='Process raw decam images with MasterCals from basic processing --> source association')
    parser.add_argument('input',
                        help="Location on disk of input data repository.")
    parser.add_argument('--calib',
                        help="Location on disk of input calib repository. Defaults to input.")
    parser.add_argument('-o', '--output',
                        help="Location on disk where output repos will live. May be the same as input.")
    parser.add_argument('-i', '--dataId',
                        help="Butler identifier naming the data to be processed (e.g., visit and ccdnum) "
                             "formatted in the usual way (e.g., 'visit=54321 ccdnum=7').")
    parser.add_argument('--no-skip', dest='skip', action='store_false',
                        help="Do not skip pipeline steps that have already been started. Necessary for "
                             "processing multiple data IDs in the same repository.")
    templateFlags = parser.add_mutually_exclusive_group()
    templateFlags.add_argument('--templateId',
                               help="A Butler identifier naming a visit to use as the template "
                                    "(e.g., 'visit=101').")
    templateFlags.add_argument('-t', '--templateRepo',
                               help="A URI to a Butler repository that will be searched for coadd "
                                    "templates. Defaults to input if neither --templateId "
                                    "nor --templateRepo provided.")
    args = parser.parse_args()

    # Define input repo locations on disk
    repo = args.input

    if args.calib is not None:
        calib_repo = args.calib
    else:
        calib_repo = repo

    # Stringly typed code, but I don't see a safer way to do this in Python
    if args.templateRepo is not None:
        templateType = 'coadd'
        template = args.templateRepo
    elif args.templateId is not None:
        templateType = 'visit'
        template = args.templateId
    else:
        templateType = 'coadd'
        template = repo

    # Define output repo locations on disk
    processed_repo = get_output_repo(args.output, PROCESSED_DIR)
    diffim_repo = get_output_repo(args.output, DIFFIM_DIR)
    db_repo = get_output_repo(args.output, DB_DIR)

    skip = args.skip

    repos_and_files = {'repo': repo, 'calib_repo': calib_repo,
                       'processed_repo': processed_repo,
                       'diffim_repo': diffim_repo, 'db_repo': db_repo,
                       'dataId': args.dataId,
                       'template_type': templateType, 'template': template,
                       'skip': skip}

    return repos_and_files


# TODO: move doIngestTemplates to ap_verify once DM-11865 resolved
def doIngestTemplates(repo, templateRepo, inputTemplates):
    '''Ingest templates into the input repository, so that
    GetCoaddAsTemplateTask can find them.

    After this method returns, butler queries against `templateRepo` can find the
    templates in `inputTemplates`.

    Parameters
    ----------
    repo: `str`
        The output repository location on disk where ingested raw images live.
    templateRepo: `str`
        The output repository location on disk where ingested templates live.
    inputTemplates: `str`
        The input repository location where templates have been previously computed.

    Returns
    -------
    calibingest_metadata: `PropertySet` or None
        Metadata from any tasks run by this method
    '''
    log = lsst.log.Log.getLogger('ap.pipe.doIngestTemplates')
    # TODO: this check will need to be rewritten when Butler directories change, ticket TBD
    if os.path.exists(os.path.join(templateRepo, 'deepCoadd')):
        log.warn('Templates were previously ingested, skipping...')
        return None
    else:
        # TODO: chain inputTemplates to templateRepo once DM-12662 resolved
        if not os.path.isdir(templateRepo):
            os.mkdir(templateRepo)
        for baseName in os.listdir(inputTemplates):
            oldDir = os.path.abspath(os.path.join(inputTemplates, baseName))
            if os.path.isdir(oldDir):
                os.symlink(oldDir, os.path.join(templateRepo, baseName))
        return None


def doProcessCcd(base_repo, dataId):
    '''
    Perform ISR with ingested images and calibrations via processCcd

    By default, the configuration for astrometric reference catalogs uses Gaia
    and the configuration for photometry reference catalogs uses Pan-STARRS.

    Parameters
    ----------
    base_repo: `str`
        The output repository location on disk.
    dataId: `str`
        Butler identifier naming the data to be processed (e.g., visit and ccdnum)
        formatted in the usual way (e.g., 'visit=54321 ccdnum=7').

    Returns
    -------
    process_metadata: `PropertySet` or None
        Metadata from the ProcessCcdTask for use by ap_verify
    '''
    raw_repo = get_output_repo(base_repo, INGESTED_DIR)
    calib_repo = get_output_repo(base_repo, CALIBINGESTED_DIR)
    processed_repo = get_output_repo(base_repo, PROCESSED_DIR)
    return _doProcessCcd(raw_repo, calib_repo, processed_repo, dataId, skip=False)


def _doProcessCcd(repo, calib_repo, processed_repo, dataId, skip=True):
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
    skip: `bool`
        If set, _doProcessCcd will skip processing if data have already been processed.

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
       already contain the refcats.

    RESULT:
    processed_repo/visit populated with subdirectories containing the
    usual post-ISR data (bkgd, calexp, icExp, icSrc, postISR).
    By default, the configuration for astrometric reference catalogs uses Gaia
    and the configuration for photometry reference catalogs uses Pan-STARRS.
    '''
    log = lsst.log.Log.getLogger('ap.pipe._doProcessCcd')
    dataId_items = re.split('[ +=]', dataId)
    dataId_dict = dict(zip(dataId_items[::2], dataId_items[1::2]))
    if 'visit' not in dataId_dict.keys():
        raise RuntimeError('The dataId string is missing \'visit\'')
    else:  # save the visit number from the dataId
        visit = dataId_dict['visit']
    if skip and os.path.isdir(os.path.join(processed_repo, '0'+visit)):
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
    process_metadata = processCcdTask.getFullMetadata()
    return process_metadata


def doDiffIm(base_repo, dataId):
    '''
    Do difference imaging with an automatically selected template.

    Parameters
    ----------
    base_repo: `str`
        The output repository location on disk.
    dataId: `str`
        Butler identifier naming the data to be processed (e.g., visit and ccdnum)
        formatted in the usual way (e.g., 'visit=54321 ccdnum=7').

    Returns
    -------
    diffim_metadata: `PropertySet` or None
        Metadata from the ImageDifferenceTask for use by ap_verify
    '''
    repo = get_output_repo(base_repo, INGESTED_DIR)
    processed_repo = get_output_repo(base_repo, PROCESSED_DIR)
    diffim_repo = get_output_repo(base_repo, DIFFIM_DIR)
    return _doDiffIm(processed_repo, dataId, 'coadd', repo, diffim_repo, skip=False)


def _doDiffIm(processed_repo, dataId, templateType, template, diffim_repo, skip=True):
    '''
    Do difference imaging with a template and one or more visits as science

    Parameters
    ----------
    processed_repo: `str`
        The output repository location on disk where processed raw images live.
    dataId: `str`
        Butler identifier naming the data to be processed (e.g., visit and ccdnum)
        formatted in the usual way (e.g., 'visit=54321 ccdnum=7').
    templateType: 'coadd' | 'visit'
        The type of template to use for difference imaging.
    template: `str`
        If `templateType` is 'coadd', the input repository containing the
        template coadds.
        If `templateType` is 'visit', the DECam data ID which will be used as a
        template for difference imaging.
    diffim_repo: `str`
        The output repository location on disk where difference images live.
    skip: `bool`
        If set, _doDiffIm will skip processing if data have already been processed.

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

    RESULT:
    diffim_repo/deepDiff/v+visit populated with difference images
    and catalogs of detected sources (diaSrc, diffexp, and metadata files)
    '''
    log = lsst.log.Log.getLogger('ap.pipe._doDiffIm')
    dataId_items = re.split('[ +=]', dataId)
    dataId_dict = dict(zip(dataId_items[::2], dataId_items[1::2]))
    if 'visit' not in dataId_dict.keys():
        raise RuntimeError('The dataId string is missing \'visit\'')
    else:  # save the visit number from the dataId
        visit = dataId_dict['visit']
    _deStringDataId(dataId_dict)

    if skip and os.path.exists(os.path.join(diffim_repo, 'deepDiff', 'v' + visit)):
        log.warn('DiffIm has already been run for visit {0}, skipping...'.format(visit))
        return None

    dataId = dataId.split(' ')
    args = [processed_repo, '--id'] + dataId
    args.extend(['--output', diffim_repo])

    config = ImageDifferenceConfig()
    config.detection.thresholdValue = 5.0
    config.doDecorrelation = True

    if templateType == 'coadd':
        # TODO: Add argument for input templates once DM-11865 resolved
        config.coaddName = 'deep'  # TODO: generalize in DM-12315
        config.getTemplate.warpType = 'psfMatched'
        config.doSelectSources = False
    elif templateType == 'visit':
        args.extend(['--templateId', template])
        config.getTemplate.retarget(GetCalexpAsTemplateTask)
    else:
        raise ValueError('templateType must be "coadd" or "visit", gave "%s" instead' % templateType)

    log.info('Running ImageDifference...')
    if not os.path.isdir(diffim_repo):
        os.mkdir(diffim_repo)
    ImageDifferenceTask.parseAndRun(args=args, config=config)
    butler = dafPersist.Butler(inputs=diffim_repo)
    metadataType = ImageDifferenceTask()._getMetadataName()
    diffim_metadata = butler.get(metadataType, dataId_dict)
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
    try:
        basestring
    except NameError:
        basestring = str
    integer = re.compile('^\s*[+-]?\d+\s*$')
    for key, value in dataId.items():
        if isinstance(value, basestring) and integer.match(value) is not None:
            dataId[key] = int(value)


def doAssociation(base_repo, dataId):
    '''
    Do source association.

    Parameters
    ----------
    base_repo: `str`
        The output repository location on disk.
    dataId: `str`
        Butler identifier naming the data to be processed (e.g., visit and ccdnum)
        formatted in the usual way (e.g., 'visit=54321 ccdnum=7').

    Returns
    -------
    assoc_metadata: `PropertySet` or None
        Metadata from the AssociationTask for use by ap_verify
    '''
    diffim_repo = get_output_repo(base_repo, DIFFIM_DIR)
    db_repo = get_output_repo(base_repo, DB_DIR)
    return _doAssociation(diffim_repo, dataId, db_repo, skip=False)


def _doAssociation(diffim_repo, dataId, db_repo, skip=True):
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
    skip: `bool`
        If set, _doAssociation will skip processing if data have already been processed.

    Returns
    -------
    assoc_metadata: `PropertySet` or None
        Metadata from the AssociationTask for use by ap_verify
    '''
    log = lsst.log.Log.getLogger('ap.pipe._doAssociation')
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
    parsed = parsePipelineArgs()

    repo = parsed['repo']
    calib_repo = parsed['calib_repo']
    processed_repo = parsed['processed_repo']
    diffim_repo = parsed['diffim_repo']
    db_repo = parsed['db_repo']

    skip = parsed['skip']

    dataId = parsed['dataId']
    templateType = parsed['template_type']
    template = parsed['template']

    # Run all the tasks in order
    _doProcessCcd(repo, calib_repo, processed_repo, dataId, skip=skip)
    if templateType == 'coadd':
        if not os.path.samefile(template, repo):
            # TODO: should be unneccessary once DM-11865 is resolved
            doIngestTemplates(repo, repo, template)
    elif templateType == 'visit':
        dataId_items = re.split('[ +=]', dataId)
        dataId_dict = dict(zip(dataId_items[::2], dataId_items[1::2]))
        if 'ccdnum' not in dataId_dict.keys():
            raise RuntimeError('The dataId string is missing \'ccdnum\'')
        ccdTemplate = template + (' ccdnum=%s' % dataId_dict['ccdnum'])
        _doProcessCcd(repo, calib_repo, processed_repo, ccdTemplate, skip=skip)
    else:
        raise ValueError('templateType must be "coadd" or "visit", gave "%s" instead' % templateType)
    _doDiffIm(processed_repo, dataId, templateType, template, diffim_repo, skip=skip)
    _doAssociation(diffim_repo, dataId, db_repo, skip=skip)
    log.info('Prototype AP Pipeline run complete.')

    return

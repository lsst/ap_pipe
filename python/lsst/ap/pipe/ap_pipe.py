#
# This file is part of ap_pipe.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (http://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
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
# You should have received a copy of the GNU General Public License
# salong with this program.  If not, see <http://www.gnu.org/licenses/>.
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

__all__ = ['ApPipeConfig',
           'doProcessCcd', 'doDiffIm', 'doAssociation',
           'runPipelineAlone']

import os
import argparse
import re

import lsst.log
import lsst.pex.config as pexConfig
from lsst.pipe.tasks.processCcd import ProcessCcdTask
from lsst.meas.algorithms import LoadIndexedReferenceObjectsTask
from lsst.utils import getPackageDir
from lsst.ip.diffim.getTemplate import GetCalexpAsTemplateTask
from lsst.pipe.tasks.imageDifference import ImageDifferenceTask
from lsst.ap.association import AssociationDBSqliteTask, AssociationTask
import lsst.daf.persistence as dafPersist


class ApPipeConfig(pexConfig.Config):
    """Settings and defaults for ApPipeTask.
    """

    ccdProcessor = pexConfig.ConfigurableField(
        target=ProcessCcdTask,
        doc="Task used to perform basic image reduction and characterization.",
    )
    differencer = pexConfig.ConfigurableField(
        target=ImageDifferenceTask,
        doc="Task used to do image subtraction and DiaSource detection.",
    )
    associator = pexConfig.ConfigurableField(
        target=AssociationTask,
        doc="Task used to associate DiaSources with DiaObjects.",
    )

    def setDefaults(self):
        """Settings assumed in baseline ap_pipe runs.
        """
        # TODO: remove explicit DECam reference in DM-12315
        obsDecamDir = getPackageDir('obs_decam')
        self.ccdProcessor.load(os.path.join(obsDecamDir, 'config/processCcd.py'))
        self.ccdProcessor.load(os.path.join(obsDecamDir, 'config/processCcdCpIsr.py'))

        self.ccdProcessor.calibrate.doAstrometry = True
        self.ccdProcessor.calibrate.doPhotoCal = True

        # Use gaia for astrometry (phot_g_mean_mag is only available DR1 filter)
        # Use pan-starrs for photometry (grizy filters)
        for refObjLoader in (self.ccdProcessor.calibrate.astromRefObjLoader,
                             self.ccdProcessor.calibrate.photoRefObjLoader,
                             self.ccdProcessor.charImage.refObjLoader,):
            refObjLoader.retarget(LoadIndexedReferenceObjectsTask)
        self.ccdProcessor.calibrate.astromRefObjLoader.ref_dataset_name = 'gaia'
        self.ccdProcessor.calibrate.astromRefObjLoader.filterMap = {
            'u': 'phot_g_mean_mag',
            'g': 'phot_g_mean_mag',
            'r': 'phot_g_mean_mag',
            'i': 'phot_g_mean_mag',
            'z': 'phot_g_mean_mag',
            'y': 'phot_g_mean_mag',
            'VR': 'phot_g_mean_mag'}
        self.ccdProcessor.calibrate.photoRefObjLoader.ref_dataset_name = 'pan-starrs'
        self.ccdProcessor.calibrate.photoRefObjLoader.filterMap = {
            'u': 'g',
            'g': 'g',
            'r': 'r',
            'i': 'i',
            'z': 'z',
            'y': 'y',
            'VR': 'g'}

        # TODO: single-template support now done by retargeting self.differencer.getTemplate
        # Document how to do this in DM-13164
        self.differencer.detection.thresholdValue = 5.0
        self.differencer.doDecorrelation = True
        self.differencer.coaddName = 'deep'  # TODO: generalize in DM-12315
        self.differencer.getTemplate.warpType = 'psfMatched'
        self.differencer.doSelectSources = False

        self.associator.level1_db.retarget(AssociationDBSqliteTask)

    def validate(self):
        pexConfig.Config.validate(self)


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
    processed_repo = args.output

    skip = args.skip

    repos_and_files = {'repo': repo, 'calib_repo': calib_repo,
                       'processed_repo': processed_repo,
                       'dataId': args.dataId,
                       'template_type': templateType, 'template': template,
                       'skip': skip}

    return repos_and_files


def doProcessCcd(sensorRef):
    '''
    Perform ISR with ingested images and calibrations via processCcd

    The output repository associated with ``sensorRef`` will be populated with subdirectories containing the
    usual post-ISR data (bkgd, calexp, icExp, icSrc, postISR).

    Parameters
    ----------
    sensorRef: `lsst.daf.persistence.ButlerDataRef`
        Data reference for raw data.

    Returns
    -------
    process_metadata: `PropertySet` or None
        Metadata from the ProcessCcdTask for use by ap_verify

    Notes
    -----
    The input repository corresponding to ``sensorRef`` must already contain the refcats.
    '''
    log = lsst.log.Log.getLogger('ap.pipe.doProcessCcd')
    log.info('Running ProcessCcd...')
    config = ApPipeConfig().ccdProcessor.value
    processCcdTask = ProcessCcdTask(butler=sensorRef.getButler(), config=config)
    processCcdTask.run(sensorRef)
    process_metadata = processCcdTask.getFullMetadata()
    return process_metadata


def doDiffIm(sensorRef, templateType, template):
    '''
    Do difference imaging with a template and one or more visits as science

    The output repository associated with ``sensorRef`` will be populated with difference images
    and catalogs of detected sources (diaSrc, diffexp, and metadata files)

    Parameters
    ----------
    sensorRef: `lsst.daf.persistence.ButlerDataRef`
        Data reference for multiple dataset types, both input and output.
    templateType: 'coadd' | 'visit'
        The type of template to use for difference imaging.
    template: `str`
        Ignored if `templateType` is 'coadd'.
        If `templateType` is 'visit', the DECam data ID which will be used as a
        template for difference imaging.

    Returns
    -------
    diffim_metadata: `PropertySet` or None
        Metadata from the ImageDifferenceTask for use by ap_verify
    '''
    log = lsst.log.Log.getLogger('ap.pipe.doDiffIm')
    config = ApPipeConfig().differencer.value

    if templateType == 'coadd':
        templateIdList = None
        pass  # This mode is assumed by ApPipeConfig
    elif templateType == 'visit':
        templateIdList = [_parseDataId(template)]
        config.getTemplate.retarget(GetCalexpAsTemplateTask)
        config.doSelectSources = True
    else:
        raise ValueError('templateType must be "coadd" or "visit", gave "%s" instead' % templateType)

    log.info('Running ImageDifference...')
    imageDifferenceTask = ImageDifferenceTask(butler=sensorRef.getButler(), config=config)
    imageDifferenceTask.run(sensorRef, templateIdList=templateIdList)
    diffim_metadata = imageDifferenceTask.getFullMetadata()
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


# TODO: dbFile is a workaround for DM-11767
def doAssociation(sensorRef, dbFile):
    '''
    Do source association.

    Parameters
    ----------
    sensorRef: `lsst.daf.persistence.ButlerDataRef`
        Data reference for multiple input dataset types.
    dbFile: `str`
        The filename where the source database lives.

    Returns
    -------
    assoc_metadata: `PropertySet` or None
        Metadata from the AssociationTask for use by ap_verify
    '''
    log = lsst.log.Log.getLogger('ap.pipe.doAssociation')
    log.info('Running Association...')
    config = ApPipeConfig().associator.value
    # TODO: workaround for DM-13602
    config.level1_db.db_name = dbFile

    _setupDatabase(config.level1_db)

    associationTask = AssociationTask(config=config)
    try:
        catalog = sensorRef.get('deepDiff_diaSrc')
        exposure = sensorRef.get('deepDiff_differenceExp')
        associationTask.run(catalog, exposure)
    finally:
        associationTask.level1_db.close()

    return associationTask.getFullMetadata()


def _parseDataId(rawDataId):
    """Convert a dataId from a command-line string to a dict.

    Parameters
    ----------
    rawDataId: `str`
        A string in a format like "visit=54321 ccdnum=7".

    Returns
    -------
    dataId: `dict` from `str` to any type
        A dataId ready for passing to Stack operations.
    """
    dataIdItems = re.split('[ +=]', rawDataId)
    dataId = dict(zip(dataIdItems[::2], dataIdItems[1::2]))
    _deStringDataId(dataId)
    return dataId


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

    repo = os.path.abspath(parsed['repo'])
    calib_repo = os.path.abspath(parsed['calib_repo'])
    output_repo = os.path.abspath(parsed['processed_repo'])

    skip = parsed['skip']

    dataId = parsed['dataId']
    templateType = parsed['template_type']
    template = parsed['template']

    # Set up repos
    dataId_dict = _parseDataId(dataId)

    mapperArgs = {'calibRoot': calib_repo}
    inputs = [{'root': repo, 'mapperArgs': mapperArgs}]
    if templateType == 'coadd':
        # samefile is a workaround for DM-13626, blocks DM-11482
        if not os.path.samefile(template, repo):
            inputs.append({'root': template, 'mode': 'r', 'mapperArgs': mapperArgs})

    butler = dafPersist.Butler(inputs=inputs,
                               outputs={'root': output_repo, 'mode': 'rw', 'mapperArgs': mapperArgs})

    rawRef = butler.dataRef('raw', dataId=dataId_dict)
    processedRef = butler.dataRef('calexp', dataId=dataId_dict)
    # TODO: workaround for DM-11767
    database = os.path.join(output_repo, 'association.db')

    if templateType == 'visit':
        template_dict = rawRef.dataId.copy()
        template_dict.update(_parseDataId(template))
        templateRaw = rawRef.getButler().dataRef('raw', dataId=template_dict)
        templateProcessed = processedRef.getButler().dataRef('calexp', dataId=template_dict)
        if not skip or not templateProcessed.datasetExists('calexp', write=True):
            doProcessCcd(templateRaw)
    elif templateType != 'coadd':
        raise ValueError('templateType must be "coadd" or "visit", gave "%s" instead' % templateType)

    # Run all the tasks in order
    if skip and processedRef.datasetExists('calexp', write=True):
        log.info('ProcessCcd has already been run for {0}, skipping...'.format(rawRef.dataId))
    else:
        doProcessCcd(rawRef)

    if skip and processedRef.datasetExists('deepDiff_diaSrc', write=True):
        log.info('DiffIm has already been run for {0}, skipping...'.format(processedRef.dataId))
    else:
        doDiffIm(processedRef, templateType, template)

    # No reasonable way to check if Association finished successfully
    doAssociation(processedRef, database)

    log.info('Prototype AP Pipeline run complete.')

    return

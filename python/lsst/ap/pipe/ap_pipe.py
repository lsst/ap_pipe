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

from __future__ import absolute_import, division, print_function

__all__ = ['ApPipeConfig', 'ApPipeTask',
           'runPipelineAlone']

import os
import argparse
import re

import lsst.log
import lsst.pex.config as pexConfig
import lsst.daf.persistence as dafPersist
import lsst.pipe.base as pipeBase

from lsst.pipe.tasks.processCcd import ProcessCcdTask
from lsst.meas.algorithms import LoadIndexedReferenceObjectsTask
from lsst.utils import getPackageDir
from lsst.ip.diffim.getTemplate import GetCalexpAsTemplateTask
from lsst.pipe.tasks.imageDifference import ImageDifferenceTask
from lsst.ap.association import AssociationDBSqliteTask, AssociationTask


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


class ApPipeTask(pipeBase.CmdLineTask):
    """Command-line task representing the entire AP pipeline.

    ``ApPipeTask`` processes raw DECam images from basic processing through
    source association. Other observatories will be supported in the future.

    A tutorial for using ``ApPipeTask`` is available in
    [DMTN-039](http://dmtn-039.lsst.io).

    ``ApPipeTask`` can be run from the command line, but it can also be called
    from other pipeline code. It provides public methods for executing each
    major step of the pipeline by itself.

    Parameters
    ----------
    butler : `lsst.daf.persistence.Butler`
        A Butler providing access to the science, calibration, and (unless
        ``config.differencer.getTemplate`` is overridden) template data to
        be processed. Its output repository must be both readable
        and writable.
    dbFile : `str`
        The filename where the source association database lives. Will be
        created if it does not yet exist.
    config : `ApPipeConfig`, optional
        A configuration for this task.
    """

    ConfigClass = ApPipeConfig
    RunnerClass = pipeBase.ButlerInitializedTaskRunner
    _DefaultName = "apPipe"

    # TODO: dbFile is a workaround for DM-11767
    def __init__(self, butler, dbFile, config=None, *args, **kwargs):
        # TODO: hacky workaround for DM-13602
        modConfig = ApPipeTask._copyConfig(config) if config is not None else ApPipeTask.ConfigClass()
        modConfig.associator.level1_db.db_name = dbFile
        modConfig.freeze()
        pipeBase.CmdLineTask.__init__(self, *args, config=modConfig, **kwargs)

        self.makeSubtask("ccdProcessor", butler=butler)
        self.makeSubtask("differencer", butler=butler)
        # Must be called before AssociationTask.__init__
        _setupDatabase(self.config.associator.level1_db)
        self.makeSubtask("associator")

    # TODO: hack for modifying frozen configs; delete once DM-13602 resolved
    @staticmethod
    def _copyConfig(config):
        configClass = type(config)
        contents = {key: value for (key, value) in config.items()}  # Force non-recursive conversion
        return configClass(**contents)

    @pipeBase.timeMethod
    def run(self, rawRef, calexpRef, templateIds=None, skip=False):
        """Execute the ap_pipe pipeline on a single image.

        Parameters
        ----------
        rawRef : `lsst.daf.persistence.ButlerDataRef`
            A reference to the raw data to process.
        calexpRef : `lsst.daf.persistence.ButlerDataRef`
            A reference to the calibrated data corresponding to ``rawRef``.
        templateIds : `list` of `dict`, optional
            A list of parsed data IDs for templates to use. Only used if
            ``config.differencer`` is configured to do so. ``differencer`` or
            its subtasks may restrict the allowed IDs.
        skip : `bool`, optional
            If set, the pipeline will attempt to determine if the products for
            a particular step are already provided in the output repository,
            and if so skip that step. If unset (the default), calls will
            attempt to re-run the entire pipeline.

        Returns
        -------
        result : `lsst.pipe.base.Struct`
            Result struct with components:

            - fullMetadata : metadata produced by the run. Intended as a transitional API
                for ap_verify, and may be removed later (`lsst.daf.base.PropertySet`).
            - l1Database : handle for accessing the final association database, conforming to
                `ap_association`'s DB access API
            - ccdProcessor : output of `config.ccdProcessor.run` (`lsst.pipe.base.Struct` or `None`).
            - differencer : output of `config.differencer.run` (`lsst.pipe.base.Struct` or `None`).
            - associator : output of `config.associator.run` (`lsst.pipe.base.Struct` or `None`).
        """
        # Ensure that templateIds make it through basic data reduction
        # TODO: treat as independent jobs (may need SuperTask framework?)
        if templateIds is not None:
            for templateId in templateIds:
                rawTemplateRef = rawRef.getButler().dataRef(
                    'raw', dataId=rawRef.dataId, **templateId)
                calexpTemplateRef = calexpRef.getButler().dataRef(
                    'calexp', dataId=calexpRef.dataId, **templateId)
                if not skip or not calexpTemplateRef.datasetExists('calexp', write=True):
                    self.runProcessCcd(rawTemplateRef)

        if skip and calexpRef.datasetExists('calexp', write=True):
            self.log.info('ProcessCcd has already been run for {0}, skipping...'.format(rawRef.dataId))
            processResults = None
        else:
            processResults = self.runProcessCcd(rawRef)

        if skip and calexpRef.datasetExists('deepDiff_diaSrc', write=True):
            self.log.info('DiffIm has already been run for {0}, skipping...'.format(calexpRef.dataId))
            diffImResults = None
        else:
            diffImResults = self.runDiffIm(calexpRef, templateIds)

        # No reasonable way to check if Association can be skipped
        associationResults = self.runAssociation(calexpRef)

        return pipeBase.Struct(
            fullMetadata = self.getFullMetadata(),
            l1Database = associationResults.l1Database,
            ccdProcessor = processResults.taskResults if processResults else None,
            differencer = diffImResults.taskResults if diffImResults else None,
            associator = associationResults.taskResults if associationResults else None
        )

    @pipeBase.timeMethod
    def runProcessCcd(self, sensorRef):
        """Perform ISR with ingested images and calibrations via processCcd.

        The output repository associated with ``sensorRef`` will be populated with the
        usual post-ISR data (bkgd, calexp, icExp, icSrc, postISR).

        Parameters
        ----------
        sensorRef : `lsst.daf.persistence.ButlerDataRef`
            Data reference for raw data.

        Returns
        -------
        result : `lsst.pipe.base.Struct`
            Result struct with components:

            - fullMetadata : metadata produced by the Task. Intended as a transitional API
                for ap_verify, and may be removed later (`lsst.daf.base.PropertySet`).
            - taskResults : output of `config.ccdProcessor.run` (`lsst.pipe.base.Struct`).

        Notes
        -----
        The input repository corresponding to ``sensorRef`` must already contain the refcats.
        """
        self.log.info('Running ProcessCcd...')
        result = self.ccdProcessor.run(sensorRef)
        return pipeBase.Struct(
            fullMetadata = self.ccdProcessor.getFullMetadata(),
            taskResults = result
        )

    @pipeBase.timeMethod
    def runDiffIm(self, sensorRef, templateIds=None):
        """Do difference imaging with a template and a science image

        The output repository associated with ``sensorRef`` will be populated with difference images
        and catalogs of detected sources (diaSrc, diffexp, and metadata files)

        Parameters
        ----------
        sensorRef: `lsst.daf.persistence.ButlerDataRef`
            Data reference for multiple dataset types, both input and output.
        templateIds : `list` of `dict`, optional
            A list of parsed data IDs for templates to use. Only used if
            ``config.differencer`` is configured to do so. ``differencer`` or
            its subtasks may restrict the allowed IDs.

        Returns
        -------
        result : `lsst.pipe.base.Struct`
            Result struct with components:

            - fullMetadata : metadata produced by the run. Intended as a transitional API
                for ap_verify, and may be removed later (`lsst.daf.base.PropertySet`).
            - taskResults : output of `config.differencer.run` (`lsst.pipe.base.Struct`).
        """
        self.log.info('Running ImageDifference...')
        result = self.differencer.run(sensorRef, templateIdList=templateIds)
        return pipeBase.Struct(
            fullMetadata = self.differencer.getFullMetadata(),
            taskResults = result
        )

    @pipeBase.timeMethod
    def runAssociation(self, sensorRef):
        """Do source association.

        Parameters
        ----------
        sensorRef : `lsst.daf.persistence.ButlerDataRef`
            Data reference for multiple input dataset types.

        Returns
        -------
        result : `lsst.pipe.base.Struct`
            Result struct with components:

            - fullMetadata : metadata produced by the run. Intended as a transitional API
                for ap_verify, and may be removed later (`lsst.daf.base.PropertySet`).
            - l1Database : handle for accessing the final association database, conforming to
                `ap_association`'s DB access API
            - taskResults : output of `config.associator.run` (`lsst.pipe.base.Struct`).
        """
        self.log.info('Running Association...')

        try:
            catalog = sensorRef.get('deepDiff_diaSrc')
            exposure = sensorRef.get('deepDiff_differenceExp')
            result = self.associator.run(catalog, exposure)
        finally:
            # Stateful AssociationTask will work for now because TaskRunner
            # uses task-oriented parallelism. Will not be necessary after DM-13672
            self.associator.level1_db.close()

        return pipeBase.Struct(
            fullMetadata = self.associator.getFullMetadata(),
            l1Database = self.associator.level1_db,
            taskResults = result
        )


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


def _parseDataId(rawDataId):
    """Convert a dataId from a command-line string to a dict.

    Parameters
    ----------
    rawDataId : `str`
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

    config = ApPipeConfig()

    if templateType == 'visit':
        templateIds = [_parseDataId(template)]
        config.differencer.getTemplate.retarget(GetCalexpAsTemplateTask)
        config.differencer.doSelectSources = True
    elif templateType == 'coadd':
        templateIds = None
        # Default assumed by ApPipeConfig, no changes needed
    else:
        raise ValueError('templateType must be "coadd" or "visit", gave "%s" instead' % templateType)
    config.freeze()

    # Run all the tasks in order
    task = ApPipeTask(butler=butler, config=config, dbFile=database)
    task.run(rawRef, processedRef, templateIds, skip=skip)

    log.info('Prototype AP Pipeline run complete.')

    return

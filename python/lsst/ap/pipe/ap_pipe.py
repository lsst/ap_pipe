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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import absolute_import, division, print_function

__all__ = ["ApPipeConfig", "ApPipeTask"]

import os

import lsst.pex.config as pexConfig
import lsst.pipe.base as pipeBase

from lsst.pipe.tasks.processCcd import ProcessCcdTask
from lsst.meas.algorithms import LoadIndexedReferenceObjectsTask
from lsst.utils import getPackageDir
from lsst.pipe.tasks.imageDifference import ImageDifferenceTask
from lsst.ap.association import AssociationDBSqliteTask, AssociationTask
from lsst.ap.pipe.apPipeParser import ApPipeParser
from lsst.ap.pipe.apPipeTaskRunner import ApPipeTaskRunner


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
        obsDecamDir = getPackageDir("obs_decam")
        self.ccdProcessor.load(os.path.join(obsDecamDir, "config/processCcd.py"))
        self.ccdProcessor.load(os.path.join(obsDecamDir, "config/processCcdCpIsr.py"))

        self.ccdProcessor.calibrate.doAstrometry = True
        self.ccdProcessor.calibrate.doPhotoCal = True

        # Use gaia for astrometry (phot_g_mean_mag is only available DR1 filter)
        # Use pan-starrs for photometry (grizy filters)
        for refObjLoader in (self.ccdProcessor.calibrate.astromRefObjLoader,
                             self.ccdProcessor.calibrate.photoRefObjLoader,
                             self.ccdProcessor.charImage.refObjLoader,):
            refObjLoader.retarget(LoadIndexedReferenceObjectsTask)
        self.ccdProcessor.calibrate.astromRefObjLoader.ref_dataset_name = "gaia"
        self.ccdProcessor.calibrate.astromRefObjLoader.filterMap = {
            "u": "phot_g_mean_mag",
            "g": "phot_g_mean_mag",
            "r": "phot_g_mean_mag",
            "i": "phot_g_mean_mag",
            "z": "phot_g_mean_mag",
            "y": "phot_g_mean_mag",
            "VR": "phot_g_mean_mag"}
        self.ccdProcessor.calibrate.photoRefObjLoader.ref_dataset_name = "pan-starrs"
        self.ccdProcessor.calibrate.photoRefObjLoader.filterMap = {
            "u": "g",
            "g": "g",
            "r": "r",
            "i": "i",
            "z": "z",
            "y": "y",
            "VR": "g"}

        # TODO: single-template support now done by retargeting self.differencer.getTemplate
        # Document how to do this in DM-13164
        self.differencer.detection.thresholdValue = 5.0
        self.differencer.doDecorrelation = True
        self.differencer.coaddName = "deep"  # TODO: generalize in DM-12315
        self.differencer.getTemplate.warpType = "psfMatched"
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
    RunnerClass = ApPipeTaskRunner
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
    def run(self, rawRef, templateIds=None, reuse=None):
        """Execute the ap_pipe pipeline on a single image.

        Parameters
        ----------
        rawRef : `lsst.daf.persistence.ButlerDataRef`
            A reference to the raw data to process.
        templateIds : `list` of `dict`, optional
            A list of parsed data IDs for templates to use. Only used if
            ``config.differencer`` is configured to do so. ``differencer`` or
            its subtasks may restrict the allowed IDs.
        reuse : `list` of `str`, optional
            The names of all subtasks that may be skipped if their output is
            present. Defaults to skipping nothing.

        Returns
        -------
        result : `lsst.pipe.base.Struct`
            Result struct with components:

            - l1Database : handle for accessing the final association database, conforming to
                `ap_association`'s DB access API
            - ccdProcessor : output of `config.ccdProcessor.run` (`lsst.pipe.base.Struct` or `None`).
            - differencer : output of `config.differencer.run` (`lsst.pipe.base.Struct` or `None`).
            - associator : output of `config.associator.run` (`lsst.pipe.base.Struct` or `None`).
        """
        if reuse is None:
            reuse = []
        # Work around mismatched HDU lists for raw and processed data
        calexpId = rawRef.dataId.copy()
        if 'hdu' in calexpId:
            del calexpId['hdu']
        calexpRef = rawRef.getButler().dataRef("calexp", dataId=calexpId)

        # Ensure that templateIds make it through basic data reduction
        # TODO: treat as independent jobs (may need SuperTask framework?)
        if templateIds is not None:
            for templateId in templateIds:
                # templateId is typically visit-only; consider only the same raft/CCD/etc. as rawRef
                rawTemplateRef = _siblingRef(rawRef, "raw", templateId)
                calexpTemplateRef = _siblingRef(calexpRef, "calexp", templateId)
                if "ccdProcessor" not in reuse or not calexpTemplateRef.datasetExists("calexp", write=True):
                    self.runProcessCcd(rawTemplateRef)

        if "ccdProcessor" in reuse and calexpRef.datasetExists("calexp", write=True):
            self.log.info("ProcessCcd has already been run for {0}, skipping...".format(rawRef.dataId))
            processResults = None
        else:
            processResults = self.runProcessCcd(rawRef)

        diffType = self.config.differencer.coaddName
        if "differencer" in reuse and calexpRef.datasetExists(diffType + "Diff_diaSrc", write=True):
            self.log.info("DiffIm has already been run for {0}, skipping...".format(calexpRef.dataId))
            diffImResults = None
        else:
            diffImResults = self.runDiffIm(calexpRef, templateIds)

        # No reasonable way to check if Association can be skipped
        associationResults = self.runAssociation(calexpRef)

        return pipeBase.Struct(
            l1Database=associationResults.l1Database,
            ccdProcessor=processResults if processResults else None,
            differencer=diffImResults if diffImResults else None,
            associator=associationResults.taskResults if associationResults else None
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
            Output of `config.ccdProcessor.run`.

        Notes
        -----
        The input repository corresponding to ``sensorRef`` must already contain the refcats.
        """
        self.log.info("Running ProcessCcd...")
        return self.ccdProcessor.run(sensorRef)

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
            Output of `config.differencer.run`.
        """
        self.log.info("Running ImageDifference...")
        return self.differencer.run(sensorRef, templateIdList=templateIds)

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

            - l1Database : handle for accessing the final association database, conforming to
                `ap_association`'s DB access API
            - taskResults : output of `config.associator.run` (`lsst.pipe.base.Struct`).
        """
        self.log.info("Running Association...")

        diffType = self.config.differencer.coaddName
        try:
            catalog = sensorRef.get(diffType + "Diff_diaSrc")
            exposure = sensorRef.get(diffType + "Diff_differenceExp")
            result = self.associator.run(catalog, exposure)
        finally:
            # Stateful AssociationTask will work for now because TaskRunner
            # uses task-oriented parallelism. Will not be necessary after DM-13672
            self.associator.level1_db.close()

        return pipeBase.Struct(
            l1Database=self.associator.level1_db,
            taskResults=result
        )

    @classmethod
    def _makeArgumentParser(cls):
        """A parser that can handle extra arguments for ap_pipe.
        """
        return ApPipeParser(name=cls._DefaultName)


def _setupDatabase(configurable):
    """
    Set up a database according to a configuration.

    Takes no action if the database already exists.

    Parameters
    ----------
    configurable: `lsst.pex.config.ConfigurableInstance`
        A ConfigurableInstance with a database-managing class in its ``target``
        field. The API of ``target`` must expose a ``create_tables`` method
        taking no arguments.
    """
    db = configurable.apply()
    try:
        db.create_tables()
    finally:
        db.close()


def _siblingRef(original, datasetType, dataId):
    """Construct a new dataRef using an existing dataRef as a template.

    The typical application is to construct a data ID that differs from an
    existing ID in one or two keys, but is more specific than expanding a
    partial data ID would be.

    Parameters
    ----------
    original : `lsst.daf.persistence.ButlerDataRef`
        A dataRef related to the desired one. Assumed to represent a unique dataset.
    datasetType : `str`
        The desired type of the new dataRef. Must be compatible
        with ``original``.
    dataId : `dict` from `str` to any
        A possibly partial data ID for the new dataRef. Any properties left
        unspecified shall be copied from ``original``.

    Returns
    -------
    dataRef : `lsst.daf.persistence.ButlerDataRef`
        A dataRef to the same butler as ``original``, but of type
        ``datasetType`` and with data ID equivalent to
        ``original.dataId.update(dataId)``.
    """
    butler = original.getButler()
    return butler.dataRef(datasetType, dataId=original.dataId, **dataId)

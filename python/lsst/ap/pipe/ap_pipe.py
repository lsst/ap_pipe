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

__all__ = ["ApPipeConfig", "ApPipeTask"]

import os

import lsst.dax.ppdb as daxPpdb
import lsst.pex.config as pexConfig
import lsst.pipe.base as pipeBase

from lsst.pipe.tasks.processCcd import ProcessCcdTask
from lsst.pipe.tasks.imageDifference import ImageDifferenceTask
from lsst.ap.association import (
    AssociationTask,
    DiaForcedSourceTask,
    MapDiaSourceTask,
    make_dia_object_schema,
    make_dia_source_schema)
from lsst.ap.pipe.apPipeParser import ApPipeParser
from lsst.ap.pipe.apPipeTaskRunner import ApPipeTaskRunner
from lsst.utils import getPackageDir


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
    ppdb = pexConfig.ConfigurableField(
        target=daxPpdb.Ppdb,
        ConfigClass=daxPpdb.PpdbConfig,
        doc="Database connection for storing associated DiaSources and "
            "DiaObjects.",
    )
    diaSourceDpddifier = pexConfig.ConfigurableField(
        target=MapDiaSourceTask,
        doc="Task for assigning columns from the raw output of ip_diffim into "
            "a schema that more closely resembles the DPDD.",
    )
    associator = pexConfig.ConfigurableField(
        target=AssociationTask,
        doc="Task used to associate DiaSources with DiaObjects.",
    )
    diaForcedSource = pexConfig.ConfigurableField(
        target=DiaForcedSourceTask,
        doc="Task used for force photometer DiaObject locations in direct and "
            "difference images.",
    )

    def setDefaults(self):
        """Settings appropriate for most or all ap_pipe runs.
        """
        # Always prefer decorrelation; may eventually become ImageDifferenceTask default
        self.differencer.doDecorrelation = True
        self.differencer.detection.thresholdValue = 5.0  # needed with doDecorrelation

        # Don't have source catalogs for templates
        self.differencer.doSelectSources = False

        # make sure the db schema and config is set up for ap_association.
        self.ppdb.dia_object_index = "baseline"
        self.ppdb.dia_object_columns = []
        self.ppdb.extra_schema_file = os.path.join(
            getPackageDir("ap_association"),
            "data",
            "ppdb-ap-pipe-schema-extra.yaml")

    def validate(self):
        pexConfig.Config.validate(self)
        if not self.differencer.doMeasurement:
            raise ValueError("Source association needs diaSource fluxes [differencer.doMeasurement].")
        if not self.differencer.doWriteSources:
            raise ValueError("Source association needs diaSource catalogs [differencer.doWriteSources].")
        if not self.differencer.doWriteSubtractedExp:
            raise ValueError("Source association needs difference exposures "
                             "[differencer.doWriteSubtractedExp].")


class ApPipeTask(pipeBase.CmdLineTask):
    """Command-line task representing the entire AP pipeline.

    ``ApPipeTask`` processes raw DECam images from basic processing through
    source association. Other observatories will be supported in the future.

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
    """

    ConfigClass = ApPipeConfig
    RunnerClass = ApPipeTaskRunner
    _DefaultName = "apPipe"

    def __init__(self, butler, *args, **kwargs):
        pipeBase.CmdLineTask.__init__(self, *args, **kwargs)

        self.makeSubtask("ccdProcessor", butler=butler)
        self.makeSubtask("differencer", butler=butler)
        # Must be called before AssociationTask.__init__
        self.ppdb = self.config.ppdb.apply(
            afw_schemas=dict(DiaObject=make_dia_object_schema(),
                             DiaSource=make_dia_source_schema()))
        self.ppdb.makeSchema()
        self.makeSubtask("diaSourceDpddifier",
                         inputSchema=self.differencer.schema)
        self.makeSubtask("associator")

    @pipeBase.timeMethod
    def runDataRef(self, rawRef, templateIds=None, reuse=None):
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
            - ccdProcessor : output of `config.ccdProcessor.runDataRef` (`lsst.pipe.base.Struct` or `None`).
            - differencer : output of `config.differencer.runDataRef` (`lsst.pipe.base.Struct` or `None`).
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

        if "associator" in reuse and \
                daxPpdb.isVisitProcessed(self.ppdb, calexpRef.get("calexp_visitInfo")):
            self.log.info("Association has already been run for {0}, skipping...".format(calexpRef.dataId))
            associationResults = None
        else:
            associationResults = self.runAssociation(calexpRef)

        return pipeBase.Struct(
            l1Database=self.ppdb,
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
            Output of `config.ccdProcessor.runDataRef`.

        Notes
        -----
        The input repository corresponding to ``sensorRef`` must already contain the refcats.
        """
        self.log.info("Running ProcessCcd...")
        return self.ccdProcessor.runDataRef(sensorRef)

    @pipeBase.timeMethod
    def runDiffIm(self, sensorRef, templateIds=None):
        """Do difference imaging with a template and a science image

        The output repository associated with ``sensorRef`` will be populated with difference images
        and catalogs of detected sources (diaSrc, diffexp, and metadata files)

        Parameters
        ----------
        sensorRef : `lsst.daf.persistence.ButlerDataRef`
            Data reference for multiple dataset types, both input and output.
        templateIds : `list` of `dict`, optional
            A list of parsed data IDs for templates to use. Only used if
            ``config.differencer`` is configured to do so. ``differencer`` or
            its subtasks may restrict the allowed IDs.

        Returns
        -------
        result : `lsst.pipe.base.Struct`
            Output of `config.differencer.runDataRef`.
        """
        self.log.info("Running ImageDifference...")
        return self.differencer.runDataRef(sensorRef, templateIdList=templateIds)

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

            - ppdb : `lsst.dax.ppdb.Ppdb` Initialized association database containing final association
                results.
            - taskResults : output of `config.associator.run` (`lsst.pipe.base.Struct`).
        """
        self.log.info("Running Association...")

        diffType = self.config.differencer.coaddName

        catalog = sensorRef.get(diffType + "Diff_diaSrc")
        diffim = sensorRef.get(diffType + "Diff_differenceExp")

        dia_sources = self.diaSourceDpddifier.run(catalog, diffim)
        result = self.associator.run(dia_sources, diffim, self.ppdb)
        self.diaForcedSource(result.dia_objects,
                             sensorRef.get("ccdExposureId_bits"),
                             sensorRef.get("calexp"),
                             diffim)

        return pipeBase.Struct(
            l1Database=self.ppdb,
            taskResults=result
        )

    @classmethod
    def _makeArgumentParser(cls):
        """A parser that can handle extra arguments for ap_pipe.
        """
        return ApPipeParser(name=cls._DefaultName)


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

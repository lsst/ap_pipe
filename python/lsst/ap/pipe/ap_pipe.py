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

import warnings

import lsst.pex.config as pexConfig
import lsst.pipe.base as pipeBase

from lsst.pipe.tasks.processCcd import ProcessCcdTask
from lsst.pipe.tasks.imageDifference import ImageDifferenceTask
from lsst.ap.association import DiaPipelineTask
from lsst.ap.association.transformDiaSourceCatalog import TransformDiaSourceCatalogTask
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
    transformDiaSrcCat = pexConfig.ConfigurableField(
        target=TransformDiaSourceCatalogTask,
        doc="Task for converting and calibrating the afw SourceCatalog of "
            "DiaSources to Pandas DataFrame for use in Association."
    )
    diaPipe = pexConfig.ConfigurableField(
        target=DiaPipelineTask,
        doc="Pipeline task for loading/store DiaSources and DiaObjects and "
            "spatially associating them.",
    )

    def setDefaults(self):
        """Settings appropriate for most or all ap_pipe runs.
        """

        # Write the WarpedExposure to disk for use in Alert Packet creation.
        self.differencer.doWriteWarpedExp = True

    def validate(self):
        pexConfig.Config.validate(self)
        if not self.ccdProcessor.calibrate.doWrite or not self.ccdProcessor.calibrate.doWriteExposure:
            raise ValueError("Differencing needs calexps [ccdProcessor.calibrate.doWrite, doWriteExposure]")
        if not self.differencer.doMeasurement:
            raise ValueError("Source association needs diaSource fluxes [differencer.doMeasurement].")
        if not self.differencer.doWriteWarpedExp:
            raise ValueError("Alert generation needs warped exposures [differencer.doWriteWarpedExp].")
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
        self.makeSubtask("transformDiaSrcCat", initInputs={"diaSourceSchema": self.differencer.outputSchema})
        self.makeSubtask("diaPipe")

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
            - diaPipe : output of `config.diaPipe.run` (`lsst.pipe.base.Struct` or `None`).
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
                if "ccdProcessor" not in reuse or not calexpTemplateRef.datasetExists("calexp"):
                    self.runProcessCcd(rawTemplateRef)

        if "ccdProcessor" in reuse and calexpRef.datasetExists("calexp"):
            self.log.info("ProcessCcd has already been run for {0}, skipping...".format(rawRef.dataId))
            processResults = None
        else:
            processResults = self.runProcessCcd(rawRef)

        diffType = self.config.differencer.coaddName
        if "differencer" in reuse and calexpRef.datasetExists(diffType + "Diff_diaSrc"):
            self.log.info("DiffIm has already been run for {0}, skipping...".format(calexpRef.dataId))
            diffImResults = None
        else:
            diffImResults = self.runDiffIm(calexpRef, templateIds)

        if "diaPipe" in reuse:
            warnings.warn(
                "Reusing association results for some images while rerunning "
                "others may change the associations. If exact reproducibility "
                "matters, please clear the association database and run "
                "ap_pipe.py with --reuse-output-from=differencer to redo all "
                "association results consistently.")
        if "diaPipe" in reuse and calexpRef.datasetExists("apdb_marker"):
            message = "DiaPipeline has already been run for {0}, skipping...".format(calexpRef.dataId)
            self.log.info(message)
            diaPipeResults = None
        else:
            diaPipeResults = self.runAssociation(calexpRef)

        return pipeBase.Struct(
            l1Database=self.diaPipe.apdb,
            ccdProcessor=processResults if processResults else None,
            differencer=diffImResults if diffImResults else None,
            diaPipe=diaPipeResults.taskResults if diaPipeResults else None
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

        This method writes an ``apdb_marker`` dataset once all changes related
        to the current exposure have been committed.

        Parameters
        ----------
        sensorRef : `lsst.daf.persistence.ButlerDataRef`
            Data reference for multiple input dataset types.

        Returns
        -------
        result : `lsst.pipe.base.Struct`
            Result struct with components:

            - apdb : `lsst.dax.apdb.Apdb` Initialized association database containing final association
                results.
            - taskResults : output of `config.diaPipe.run` (`lsst.pipe.base.Struct`).
        """
        diffType = self.config.differencer.coaddName
        diffIm = sensorRef.get(diffType + "Diff_differenceExp")

        transformResult = self.transformDiaSrcCat.run(
            diaSourceCat=sensorRef.get(diffType + "Diff_diaSrc"),
            diffIm=diffIm,
            band=diffIm.getFilterLabel().bandLabel,
            ccdVisitId=diffIm.getInfo().getVisitInfo().getExposureId())

        results = self.diaPipe.run(
            diaSourceTable=transformResult.diaSourceTable,
            diffIm=sensorRef.get(diffType + "Diff_differenceExp"),
            exposure=sensorRef.get("calexp"),
            warpedExposure=sensorRef.get(diffType + "Diff_warpedExp"),
            ccdExposureIdBits=sensorRef.get("ccdExposureId_bits"),
            band=diffIm.getFilterLabel().bandLabel,
        )

        # apdb_marker triggers metrics processing; let them try to read
        # something even if association failed
        sensorRef.put(results.apdbMarker, "apdb_marker")

        return pipeBase.Struct(
            l1Database=self.diaPipe.apdb,
            taskResults=results
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

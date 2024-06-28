# This file is part of ap_pipe.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import numpy as np
import pandas as pd
import uuid

import lsst.pex.config as pexConfig
from lsst.pipe.base import PipelineTask, PipelineTaskConnections, Struct
import lsst.pipe.base.connectionTypes as connTypes
from lsst.pipe.tasks.insertFakes import InsertFakesConfig
from lsst.skymap import BaseSkyMap

from lsst.source.injection import generate_injection_catalog


__all__ = ["CreateRandomApFakesTask",
           "CreateRandomApFakesConfig",
           "CreateRandomApFakesConnections"]


class CreateRandomApFakesConnections(PipelineTaskConnections,
                                     defaultTemplates={"fakesType": "fakes_"},
                                     dimensions=("tract", "skymap")):
    skyMap = connTypes.Input(
        doc="Input definition of geometry/bbox and projection/wcs for "
        "template exposures",
        name=BaseSkyMap.SKYMAP_DATASET_TYPE_NAME,
        dimensions=("skymap",),
        storageClass="SkyMap",
    )
    fakeCat = connTypes.Output(
        doc="Catalog of fake sources to draw inputs from.",
        name="{fakesType}fakeSourceCat",
        storageClass="DataFrame",
        dimensions=("tract", "skymap")
    )


class CreateRandomApFakesConfig(
        InsertFakesConfig,
        pipelineConnections=CreateRandomApFakesConnections):
    """Config for CreateRandomApFakesTask. Copy from the InsertFakesConfig to
    assert that columns created with in this task match that those expected in
    the InsertFakes and related tasks.
    """
    fakeDensity = pexConfig.RangeField(
        doc="Goal density of random fake sources per square degree. Default "
            "value is roughly the density per square degree for ~10k sources "
            "visit.",
        dtype=float,
        default=1000,
        min=0,
    )
    filterSet = pexConfig.ListField(
        doc="Set of Abstract filter names to produce magnitude columns for.",
        dtype=str,
        default=["u", "g", "r", "i", "z", "y"],
    )
    fraction = pexConfig.RangeField(
        doc="Fraction of the created source that should be inserted into both "
            "the visit and template images. Values less than 1 will result in "
            "(1 - fraction) / 2 inserted into only visit or the template.",
        dtype=float,
        default=1/3,
        min=0,
        max=1,
    )
    magMin = pexConfig.RangeField(
        doc="Minimum magnitude the mag distribution. All magnitudes requested "
            "are set to the same value.",
        dtype=float,
        default=20,
        min=1,
        max=40,
    )
    magMax = pexConfig.RangeField(
        doc="Maximum magnitude the mag distribution. All magnitudes requested "
            "are set to the same value.",
        dtype=float,
        default=30,
        min=1,
        max=40,
    )
    visitSourceFlagCol = pexConfig.Field(
        doc="Name of the column flagging objects for insertion into the visit "
            "image.",
        dtype=str,
        default="isVisitSource"
    )
    templateSourceFlagCol = pexConfig.Field(
        doc="Name of the column flagging objects for insertion into the "
            "template image.",
        dtype=str,
        default="isTemplateSource"
    )


class CreateRandomApFakesTask(PipelineTask):
    """Create and store a set of spatially uniform star fakes over the sphere
    for use in AP processing. Additionally assign random magnitudes to said
    fakes and assign them to be inserted into either a visit exposure or
    template exposure.
    """

    _DefaultName = "createApFakes"
    ConfigClass = CreateRandomApFakesConfig

    def runQuantum(self, butlerQC, inputRefs, outputRefs):
        inputs = butlerQC.get(inputRefs)
        inputs["tractId"] = butlerQC.quantum.dataId["tract"]

        outputs = self.run(**inputs)
        butlerQC.put(outputs, outputRefs)

    def run(self, tractId, skyMap):
        """Create a set of uniform random points that covers a tract.

        Parameters
        ----------
        tractId : `int`
            Tract id to produce randoms over.
        skyMap : `lsst.skymap.SkyMap`
            Skymap to produce randoms over.

        Returns
        -------
        randoms : `pandas.DataFrame`
            Catalog of random points covering the given tract. Follows the
            columns and format expected in `lsst.pipe.tasks.InsertFakes`.
        """
        # Use the tractId as the random seed.
        rng = np.random.default_rng(tractId)

        tract = skyMap.generateTract(tractId)
        tractWcs = tract.getWcs()
        vertexList = tract.getVertexList()
        vertexRas = [vertex.getRa().asDegrees() for vertex in vertexList]
        vertexDecs = [vertex.getDec().asDegrees() for vertex in vertexList]

        catalog = generate_injection_catalog(
            ra_lim=sorted([np.min(vertexRas), np.max(vertexRas)]),
            dec_lim=sorted([np.min(vertexDecs), np.max(vertexDecs)]),
            density=self.config.fakeDensity,
            source_type="Star",
            seed=str(tractId),
            wcs=tractWcs
        )

        nFakes = len(catalog)

        self.log.info(
            f"Creating {nFakes} star fakes over tractId={tractId} with "
            f"magnitude range: [{self.config.magMin, self.config.magMax}]")

        onesColumn = np.ones(nFakes, dtype="float")
        zerosColumn = np.zeros(nFakes, dtype="float")
        # Concatenate the data and add dummy values for the unused variables.
        # Set all data to PSF like objects.
        randData = {
            "fakeId": [uuid.uuid4().int & (1 << 64) - 1 for n in range(nFakes)],
            self.config.ra_col: catalog['ra'].value,
            self.config.dec_col: catalog['dec'].value,
            **self.createVisitCoaddSubdivision(nFakes),
            **self.createRandomMagnitudes(nFakes, rng),
            self.config.disk_semimajor_col: onesColumn,
            self.config.bulge_semimajor_col: onesColumn,
            self.config.disk_n_col: onesColumn,
            self.config.bulge_n_col: onesColumn,
            self.config.disk_axis_ratio_col: onesColumn,
            self.config.bulge_axis_ratio_col: onesColumn,
            self.config.disk_pa_col: zerosColumn,
            self.config.bulge_pa_col: onesColumn,
            self.config.sourceType: catalog['source_type'].value,
            "source_type": catalog['source_type'].value,
            "injection_id": catalog['injection_id'].value
        }

        return Struct(fakeCat=pd.DataFrame(data=randData))

    def createVisitCoaddSubdivision(self, nFakes):
        """Assign a given fake either a visit image or coadd or both based on
        the ``faction`` config value.

        Parameters
        ----------
        nFakes : `int`
            Number of fakes to create.

        Returns
        -------
        output : `dict`[`str`, `numpy.ndarray`]
            Dictionary of boolean arrays specifying which image to put a
            given fake into.
        """
        nBoth = int(self.config.fraction * nFakes)
        nOnly = int((1 - self.config.fraction) / 2 * nFakes)
        isVisitSource = np.zeros(nFakes, dtype=bool)
        isTemplateSource = np.zeros(nFakes, dtype=bool)
        if nBoth > 0:
            isVisitSource[:nBoth] = True
            isTemplateSource[:nBoth] = True
        if nOnly > 0:
            isVisitSource[nBoth:(nBoth + nOnly)] = True
            isTemplateSource[(nBoth + nOnly):] = True

        return {self.config.visitSourceFlagCol: isVisitSource,
                self.config.templateSourceFlagCol: isTemplateSource}

    def createRandomMagnitudes(self, nFakes, rng):
        """Create a random distribution of magnitudes for out fakes.

        Parameters
        ----------
        nFakes : `int`
            Number of fakes to create.
        rng : `numpy.random.Generator`
            Initialized random number generator.

        Returns
        -------
        randMags : `dict`[`str`, `numpy.ndarray`]
            Dictionary of magnitudes in the bands set by the ``filterSet``
            config option.
        """
        mags = rng.uniform(self.config.magMin,
                           self.config.magMax,
                           size=nFakes)
        randMags = {}
        for fil in self.config.filterSet:
            randMags[self.config.mag_col % fil] = mags
        # adding a non-filter column for magnitudes
        randMags["mag"] = mags
        return randMags

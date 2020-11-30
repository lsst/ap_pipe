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

__all__ = ["CreateRandomApFakesTask",
           "CreateRandomApFakesConfig",
           "CreateRandomApFakesConnections"]


class CreateRandomApFakesConnections(PipelineTaskConnections,
                                     defaultTemplates={"CoaddName": "deep"},
                                     dimensions=("tract", "skymap")):
    skyMap = connTypes.Input(
        doc="Input definition of geometry/bbox and projection/wcs for "
        "template exposures",
        name="{CoaddName}Coadd_skyMap",
        dimensions=("skymap",),
        storageClass="SkyMap",
    )
    fakeCat = connTypes.Output(
        doc="Catalog of fake sources to draw inputs from.",
        name="{CoaddName}Coadd_fakeSourceCat",
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
    randomSeed = pexConfig.Field(
        doc="Random seed to set for reproducible datasets",
        dtype=int,
        default=1234,
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
        rng = np.random.default_rng(self.config.randomSeed)
        tractBoundingCircle = \
            skyMap.generateTract(tractId).getInnerSkyPolygon().getBoundingCircle()
        tractArea = tractBoundingCircle.getArea() * (180 / np.pi) ** 2
        nFakes = int(self.config.fakeDensity * tractArea)

        self.log.info(
            f"Creating {nFakes} star fakes over tractId={tractId} with "
            f"bounding circle area: {tractArea} deg^2")

        # Concatenate the data and add dummy values for the unused variables.
        # Set all data to PSF like objects.
        randData = {
            "fakeId": [uuid.uuid4().int & (1 << 64) - 1 for n in range(nFakes)],
            **self.createRandomPositions(nFakes, tractBoundingCircle, rng),
            **self.createVisitCoaddSubdivision(nFakes),
            **self.createRandomMagnitudes(nFakes, rng),
            self.config.diskHLR: np.ones(nFakes, dtype="float"),
            self.config.bulgeHLR: np.ones(nFakes, dtype="float"),
            self.config.nDisk: np.ones(nFakes, dtype="float"),
            self.config.nBulge: np.ones(nFakes, dtype="float"),
            self.config.aDisk: np.ones(nFakes, dtype="float"),
            self.config.aBulge: np.ones(nFakes, dtype="float"),
            self.config.bDisk: np.ones(nFakes, dtype="float"),
            self.config.bBulge: np.ones(nFakes, dtype="float"),
            self.config.paDisk: np.ones(nFakes, dtype="float"),
            self.config.paBulge: np.ones(nFakes, dtype="float"),
            self.config.sourceType: nFakes * ["star"]}

        return Struct(fakeCat=pd.DataFrame(data=randData))

    def createRandomPositions(self, nFakes, boundingCircle, rng):
        """Create a set of spatially uniform randoms over the tract bounding
        circle on the sphere.

        Parameters
        ----------
        nFakes : `int`
            Number of fakes to create.
        boundingCicle : `lsst.sphgeom.BoundingCircle`
            Circle bound covering the tract.
        rng : `numpy.random.Generator`
            Initialized random number generator.

        Returns
        -------
        data : `dict`[`str`, `numpy.ndarray`]
            Dictionary of RA and Dec locations over the tract.
        """
        # Create uniform random vectors on the sky around the north pole.
        randVect = np.empty((nFakes, 3))
        randVect[:, 2] = rng.uniform(
            np.cos(boundingCircle.getOpeningAngle().asRadians()),
            1,
            nFakes)
        sinRawTheta = np.sin(np.arccos(randVect[:, 2]))
        rawPhi = rng.uniform(0, 2 * np.pi, nFakes)
        randVect[:, 0] = sinRawTheta * np.cos(rawPhi)
        randVect[:, 1] = sinRawTheta * np.sin(rawPhi)

        # Compute the rotation matrix to move our random points to the
        # correct location.
        rotMatrix = self._createRotMatrix(boundingCircle)
        randVect = np.dot(rotMatrix, randVect.transpose()).transpose()
        decs = np.arcsin(randVect[:, 2])
        ras = np.arctan2(randVect[:, 1], randVect[:, 0])

        return {self.config.decColName: decs,
                self.config.raColName: ras}

    def _createRotMatrix(self, boundingCircle):
        """Compute the 3d rotation matrix to rotate the dec=90 pole to the
        center of the circle bound.

        Parameters
        ----------
        boundingCircle : `lsst.sphgeom.BoundingCircle`
             Circle bound covering the tract.

        Returns
        -------
        rotMatrix : `numpy.ndarray`, (3, 3)
            3x3 rotation matrix to rotate the dec=90 pole to the location of
            the circle bound.

        Notes
        -----
        Rotation matrix follows
        https://mathworld.wolfram.com/RodriguesRotationFormula.html
        """
        # Get the center point of our tract
        center = boundingCircle.getCenter()

        # Compute the axis to rotate around. This is done by taking the cross
        # product of dec=90 pole into the tract center.
        cross = np.array([-center.y(),
                          center.x(),
                          0])
        cross /= np.sqrt(cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2)

        # Get the cosine and sine of the dec angle of the tract center. This
        # is the amount of rotation needed to move the points we created from
        # around the pole to the tract location.
        cosTheta = center.z()
        sinTheta = np.sin(np.arccos(center.z()))

        # Compose the rotation matrix for rotation around the axis created from
        # the cross product.
        rotMatrix = cosTheta * np.array([[1, 0, 0],
                                         [0, 1, 0],
                                         [0, 0, 1]])
        rotMatrix += sinTheta * np.array([[0, -cross[2], cross[1]],
                                          [cross[2], 0, -cross[0]],
                                          [-cross[1], cross[0], 0]])
        rotMatrix += (
            (1 - cosTheta)
            * np.array(
                [[cross[0] ** 2, cross[0] * cross[1], cross[0] * cross[2]],
                 [cross[0] * cross[1], cross[1] ** 2, cross[1] * cross[2]],
                 [cross[0] * cross[2], cross[1] * cross[2], cross[2] ** 2]])
        )
        return rotMatrix

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
            randMags[self.config.magVar % fil] = mags

        return randMags

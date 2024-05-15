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

__all__ = ["MatchInitialPVIInjectedTask",
           "MatchInitialPVIInjectedConfig"]

import astropy.units as u
import numpy as np
from scipy.spatial import cKDTree

from lsst.geom import Box2D
import lsst.pex.config as pexConfig
from lsst.pipe.base import PipelineTask, PipelineTaskConnections, Struct
import lsst.pipe.base.connectionTypes as connTypes

from lsst.source.injection import VisitInjectConfig


class MatchInitialPVIInjectedConnections(
        PipelineTaskConnections,
        defaultTemplates={"coaddName": "deep",
                          "fakesType": "fakes_",
                          "injection_prefix": "injection_",
                          "injected_prefix": "injected_"},
        dimensions=("instrument",
                    "visit",
                    "detector")):
    injectedInitialPVICat = connTypes.Input(
        doc="Catalog of sources injected in the images.",
        name="{fakesType}initial_pvi_catalog",
        storageClass="ArrowAstropy",
        dimensions=("instrument", "visit", "detector"),
        deferLoad=False,
        multiple=False
    )
    diffIm = connTypes.Input(
        doc="Difference image on which the DiaSources were detected.",
        name="{fakesType}{coaddName}Diff_differenceExp",
        storageClass="ExposureF",
        dimensions=("instrument", "visit", "detector"),
    )
    associatedDiaSources = connTypes.Input(
        doc="A DiaSource catalog to match against fakeCat. Assumed "
            "to be SDMified.",
        name="{fakesType}{coaddName}Diff_assocDiaSrc",
        storageClass="DataFrame",
        dimensions=("instrument", "visit", "detector"),
    )
    matchedDiaSources = connTypes.Output(
        doc="A catalog of those fakeCat sources that have a match in "
            "associatedDiaSources. The schema is the union of the schemas for "
            "``fakeCat`` and ``associatedDiaSources``.",
        name="{fakesType}{coaddName}Diff_matchDiaSrc",
        storageClass="DataFrame",
        dimensions=("instrument", "visit", "detector"),
    )


class MatchInitialPVIInjectedConfig(
        VisitInjectConfig,
        pipelineConnections=MatchInitialPVIInjectedConnections):
    """Config for MatchFakesTask.
    """
    matchDistanceArcseconds = pexConfig.RangeField(
        doc="Distance in arcseconds to match within.",
        dtype=float,
        default=0.5,
        min=0,
        max=10,
    )
    doMatchVisit = pexConfig.Field(
        dtype=bool,
        default=True,
        doc="Match visit to trim the fakeCat"
    )
    trimBuffer = pexConfig.Field(
        doc="Size of the pixel buffer surrounding the image."
            "Only those fake sources with a centroid"
            "falling within the image+buffer region will be considered matches.",
        dtype=int,
        default=50,
    )


class MatchInitialPVIInjectedTask(PipelineTask):

    _DefaultName = "matchInitialPVIInjected"
    ConfigClass = MatchInitialPVIInjectedConfig

    def run(self, injectedInitialPVICat, diffIm, associatedDiaSources):
        """Match injected sources to detected diaSources within a difference image bound.

        Parameters
        ----------
        injectedInitialPVICat : `astropy.table.table.Table`
            Table of catalog of synthetic sources to match to detected diaSources.
        diffIm : `lsst.afw.image.Exposure`
            Difference image where ``associatedDiaSources`` were detected.
        associatedDiaSources : `pandas.DataFrame`
            Catalog of difference image sources detected in ``diffIm``.

        Returns
        -------
        result : `lsst.pipe.base.Struct`
            Results struct with components.

            - ``matchedDiaSources`` : Fakes matched to input diaSources. Has
              length of ``injectedCalexpCat``. (`pandas.DataFrame`)
        """

        if self.config.doMatchVisit:
            fakeCat = self._trimFakeCat(injectedInitialPVICat, diffIm)
        else:
            fakeCat = injectedInitialPVICat

        return self._processFakes(fakeCat, associatedDiaSources)

    def _processFakes(self, injectedCat, associatedDiaSources):
        """Match fakes to detected diaSources within a difference image bound.

        Parameters
        ----------
        injectedCat : `astropy.table.table.Table`
            Catalog of injected sources to match to detected diaSources.
        associatedDiaSources : `pandas.DataFrame`
            Catalog of difference image sources detected in ``diffIm``.

        Returns
        -------
        result : `lsst.pipe.base.Struct`
            Results struct with components.

            - ``matchedDiaSources`` : Fakes matched to input diaSources. Has
              length of ``fakeCat``. (`pandas.DataFrame`)
        """
        injectedCat = injectedCat.to_pandas()
        nPossibleFakes = len(injectedCat)

        fakeVects = self._getVectors(
            np.radians(injectedCat.ra),
            np.radians(injectedCat.dec))
        diaSrcVects = self._getVectors(
            np.radians(associatedDiaSources.ra),
            np.radians(associatedDiaSources.dec))

        diaSrcTree = cKDTree(diaSrcVects)
        dist, idxs = diaSrcTree.query(
            fakeVects,
            distance_upper_bound=np.radians(self.config.matchDistanceArcseconds / 3600))
        nFakesFound = np.isfinite(dist).sum()

        self.log.info("Found %d out of %d possible.", nFakesFound, nPossibleFakes)
        diaSrcIds = associatedDiaSources.iloc[np.where(np.isfinite(dist), idxs, 0)]["diaSourceId"].to_numpy()
        matchedFakes = injectedCat.assign(diaSourceId=np.where(np.isfinite(dist), diaSrcIds, 0))
        matchedFakes['dist'] = np.where(np.isfinite(dist), 3600*np.rad2deg(dist), -1)
        return Struct(
            matchedDiaSources=matchedFakes.merge(
                associatedDiaSources.reset_index(drop=True),
                on="diaSourceId",
                how="left",
                suffixes=('_ssi', '_diaSrc')
            )
        )

    def _getVectors(self, ras, decs):
        """Convert ra dec to unit vectors on the sphere.

        Parameters
        ----------
        ras : `numpy.ndarray`, (N,)
            RA coordinates in radians.
        decs : `numpy.ndarray`, (N,)
            Dec coordinates in radians.

        Returns
        -------
        vectors : `numpy.ndarray`, (N, 3)
            Vectors on the unit sphere for the given RA/DEC values.
        """
        vectors = np.empty((len(ras), 3))

        vectors[:, 2] = np.sin(decs)
        vectors[:, 0] = np.cos(decs) * np.cos(ras)
        vectors[:, 1] = np.cos(decs) * np.sin(ras)

        return vectors

    def _addPixCoords(self, fakeCat, image):
        """Add pixel coordinates to the catalog of fakes.

        Parameters
        ----------
        fakeCat : `astropy.table.table.Table`
            The catalog of fake sources to be input
        image : `lsst.afw.image.exposure.exposure.ExposureF`
            The image into which the fake sources should be added
        Returns
        -------
        fakeCat : `astropy.table.table.Table`
        """

        wcs = image.getWcs()

        # Get x/y pixel coordinates for injected sources.
        xs, ys = wcs.skyToPixelArray(
            fakeCat["ra"],
            fakeCat["dec"],
            degrees=True
        )
        fakeCat["x"] = xs
        fakeCat["y"] = ys

        return fakeCat

    def _trimFakeCat(self, fakeCat, image):
        """Trim the fake cat to the exact size of the input image.

        Parameters
        ----------
        fakeCat : `astropy.table.table.Table`
            The catalog of fake sources that was input
        image : `lsst.afw.image.exposure.exposure.ExposureF`
            The image into which the fake sources were added
        Returns
        -------
        fakeCat : `astropy.table.table.Table`
            The original fakeCat trimmed to the area of the image
        """

        # fakeCat must be processed with _addPixCoords before trimming
        fakeCat = self._addPixCoords(fakeCat, image)

        # Prefilter in ra/dec to avoid cases where the wcs incorrectly maps
        # input fakes which are really off the chip onto it.
        ras = fakeCat["ra"] * u.deg
        decs = fakeCat["dec"] * u.deg

        isContainedRaDec = image.containsSkyCoords(ras, decs, padding=0)

        # now use the exact pixel BBox to filter to only fakes that were inserted
        xs = fakeCat["x"]
        ys = fakeCat["y"]

        bbox = Box2D(image.getBBox())
        isContainedXy = xs - self.config.trimBuffer >= bbox.minX
        isContainedXy &= xs + self.config.trimBuffer <= bbox.maxX
        isContainedXy &= ys - self.config.trimBuffer >= bbox.minY
        isContainedXy &= ys + self.config.trimBuffer <= bbox.maxY

        return fakeCat[isContainedRaDec & isContainedXy]

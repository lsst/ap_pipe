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

from scipy.spatial import cKDTree

import lsst.pipe.base as pipeBase
import lsst.pipe.base.connectionTypes as connTypes
from lsst.pipe.tasks.insertFakes import InsertFakesConfig

__all__ = ["MatchApFakesTask",
           "MatchApFakesConfig",
           "MatchApFakesConnections"]


class MatchApFakesConnections(pipeBase.PipelineTaskConnections,
                              defaultTemplates={"CoaddName": "deep".
                                                "fakesType": ""},
                              dimensions=("tract",
                                          "skymap",
                                          "instrument",
                                          "visit",
                                          "detector")):
    fakeCat = connTypes.Input(
        doc="Catalog of fake sources to draw inputs from.",
        name="{CoaddName}Coadd_fakeSourceCat",
        storageClass="DataFrame",
        dimensions=("tract", "skymap")
    )
    diffIm = connTypes.Input(
        doc="Difference image on which the DiaSources were detected.",
        name="{fakesType}{coaddName}Diff_differenceExp",
        storageClass="ExposureF",
        dimensions=("instrument", "visit", "detector"),
    )
    associatedDiaSources = connTypes.Input(
        doc="Optional output storing the DiaSource catalog after matching and "
            "SDMification.",
        name="associatedDiaSources",
        storageClass="DataFrame",
        dimensions=("instrument", "visit", "detector"),
    )
    matchedDiaSources = connTypes.Output(
        doc="",
        name="matchedDiaSources",
        storageClass="DataFrame",
        dimensions=("instrument", "visit", "detector"),
    )


class MatchApFakesConfig(
        InsertFakesConfig,,
        pipelineConnections=MatchApFakesConnections):
    """Config for MatchApFakesTask.
    """
    matchDistanceArcseconds = pexConfig.RangeField(
        doc="Distance in arcseconds to ",
        dtype=float,
        default=1,
        min=0,
        max=10,
    )


class MatchApFakesTask(PipelineTask):
    """Create and store a set of spatially uniform star fakes over the sphere
    for use in AP processing. Additionally assign random magnitudes to said
    fakes and assign them to be inserted into either a visit exposure or
    template exposure.
    """

    _DefaultName = "matchApFakes"
    ConfigClass = MatchApFakesConfig

    def runQuantum(self, butlerQC, inputRefs, outputRefs):
        inputs = butlerQC.get(inputRefs)

        outputs = self.run(**inputs)
        butlerQC.put(outputs, outputRefs)

    def run(self, fakeCat, diffIm, associatedDiaSources):
        """
        """
        trimmedFakes = self.trimFakeCat(fakeCat, diffIm)
        fakeVects = self.getVectors(trimmedFakes[self.config.raColName],
                                    trimmedFakes[self.config.decColName])
        diaSrcVects = self.getVectors(
            associatedDiaSources["ra"],
            associatedDiaSources["decl"])

        diaSrcTree = cKDTree(diaSrcVects)
        dist, idxs = diaSrcTree.query(
            fakeVects,
            distance_upper_bound=np.radians(self.config.matchDistanceArcseconds / 3600))
        trimmedFakes["diaSourceId"] = np.where(
            np.isfinite(dist),
            associatedDiaSources.iloc[np.where(np.isfinite(dist), idxs, 0)]["diaSourceId"],
            0)

        return pipeeBase.Struct(
            matchedDiaSources=trimmedFakes.merge(
                associatedDiaSources, how="left")
        )


    def trimFakeCat(self, fakeCat, image):
        """Trim the fake cat to about the size of the input image.

        Parameters
        ----------
        fakeCat : `pandas.core.frame.DataFrame`
            The catalog of fake sources to be input
        image : `lsst.afw.image.exposure.exposure.ExposureF`
            The image into which the fake sources should be added

        Returns
        -------
        fakeCat : `pandas.core.frame.DataFrame`
            The original fakeCat trimmed to the area of the image
        """
        wcs = image.getWcs()

        bbox = Box2D(image.getBBox())
        corners = bbox.getCorners()

        skyCorners = wcs.pixelToSky(corners)
        region = ConvexPolygon([s.getVector() for s in skyCorners])

        def trim(row):
            coord = SpherePoint(row[self.config.raColName], row[self.config.decColName], radians)
            return region.contains(coord.getVector())

        return fakeCat[fakeCat.apply(trim, axis=1)]

    def getVectors(self, ras, decs):
        """
        """
        vectors = np.empty(len(ras), 3)

        vectors[:, 2] = np.sin(decs)
        vectors[:, 0] = np.cos(decs) * np.cos(ras)
        vectors[:, 1] = np.cos(decs) * np.sin(ras)

        return vectors

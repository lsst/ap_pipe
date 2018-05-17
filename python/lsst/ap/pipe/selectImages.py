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

import numpy as np

import lsst.pex.config as pexConfig
import lsst.pex.exceptions as pexExceptions
import lsst.afw.geom as afwGeom
import lsst.pipe.base as pipeBase
from lsst.pipe.tasks.selectImages import WcsSelectImagesTask, BaseExposureInfo
from lsst.sphgeom import ConvexPolygon

__all__ = ["MaxPsfWcsSelectImagesTask"]


class MaxPsfWcsSelectImageConfig(WcsSelectImagesTask.ConfigClass):
    """Base configuration for MaxPsfSelectImagesTask.
    """
    maxPsfFwhm = pexConfig.Field(dtype=float, doc="Maximum PSF FWHM (in pixels) to warp", default=5.)
    minPsfFwhm = pexConfig.Field(dtype=float, doc="Minimum PSF FWHM (in pixels) to warp", default=0.)


class MaxPsfWcsSelectImagesTask(WcsSelectImagesTask):
    """Select images using their Wcs and a maximum seeing.
    """
    ConfigClass = MaxPsfWcsSelectImageConfig

    def runDataRef(self, dataRef, coordList, makeDataRefList=True, selectDataList=[]):
        """Select images in the selectDataList that overlap the patch.

        Parameters
        ----------
        coordList : `list` of `lsst.afw.geom.SpherePoint`
            List of ICRS sky coordinates specifying boundary of patch
        selectDataList : `list` of `SelectStruct`
            List of SelectStruct, to consider for selection
        makeDataRefList : `boolean`, optional
            Construct a list of data references? Default `True`.

        Returns
        -------
        pipe.base.Struct with filtered exposureList and dataRefList
        (if makeDataRefList is True).

        Notes
        -----
        We use the "convexHull" method in the `~lsst.sphgeom` package to define
        polygons on the celestial sphere, and test the polygon of the
        patch for overlap with the polygon of the image.
        """
        psf_sizes = []
        dataRefList = []
        exposureInfoList = []

        patchVertices = [coord.getVector() for coord in coordList]
        patchPoly = ConvexPolygon.convexHull(patchVertices)

        for data in selectDataList:
            dataRef = data.dataRef
            imageWcs = data.wcs
            cal = dataRef.get("calexp", immediate=True)
            psf_size = cal.getPsf().computeShape().getDeterminantRadius()
            nx, ny = cal.getDimensions()

            imageBox = afwGeom.Box2D(afwGeom.Point2D(0, 0), afwGeom.Extent2D(nx, ny))
            try:
                imageCorners = [imageWcs.pixelToSky(pix) for pix in imageBox.getCorners()]
            except (pexExceptions.DomainError, pexExceptions.RuntimeError) as e:
                # Protecting ourselves from awful Wcs solutions in input images
                self.log.debug("WCS error in testing calexp %s (%s): deselecting", dataRef.dataId, e)
                continue

            imagePoly = ConvexPolygon.convexHull([coord.getVector() for coord in imageCorners])
            if imagePoly is None:
                self.log.debug("Unable to create polygon from image %s: deselecting", dataRef.dataId)
                continue
            if patchPoly.intersects(imagePoly):  # "intersects" also covers "contains" or "is contained by"
                psf_sizes.append(psf_size)
                dataRefList.append(dataRef)
                exposureInfoList.append(BaseExposureInfo(dataRef.dataId, imageCorners))

        filteredDataRefList = []
        filteredExposureInfoList = []
        for size_sigma, dataRef, expInfo in zip(psf_sizes, dataRefList, exposureInfoList):
            # size_sigma is in sigma.  Convert to FWHM
            size_fwhm = size_sigma * np.sqrt(8.*np.log(2.))
            if size_fwhm < self.config.maxPsfFwhm and size_fwhm > self.config.minPsfFwhm:
                self.log.info("%s selected with FWHM of %f pixels" % (dataRef.dataId, size_fwhm))
                filteredDataRefList.append(dataRef)
                filteredExposureInfoList.append(expInfo)
        return pipeBase.Struct(
            dataRefList=filteredDataRefList if makeDataRefList else None,
            exposureInfoList=filteredExposureInfoList,
        )

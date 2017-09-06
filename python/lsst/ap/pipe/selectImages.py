#
# LSST Data Management System
# Copyright 2008, 2009, 2010 LSST Corporation.
#
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.
#
import lsst.pex.config as pexConfig
import lsst.pex.exceptions as pexExceptions
import lsst.afw.geom as afwGeom
import lsst.pipe.base as pipeBase
from lsst.pipe.tasks.selectImages import WcsSelectImagesTask, BaseExposureInfo

__all__ = ["MaxPsfWcsSelectImagesTask"]


class MaxPsfWcsSelectImageConfig(WcsSelectImagesTask.ConfigClass):
    maxPsfFwhm = pexConfig.Field(dtype=float, doc="Maximum PSF FWHM (in pixels) to warp", default=5.)
    minPsfFwhm = pexConfig.Field(dtype=float, doc="Minimum PSF FWHM (in pixels) to warp", default=0.)


class MaxPsfWcsSelectImagesTask(WcsSelectImagesTask):
    """Select images using their Wcs and a maximum seeing"""
    ConfigClass = MaxPsfWcsSelectImageConfig

    def runDataRef(self, dataRef, coordList, makeDataRefList=True, selectDataList=[]):
        """Select images in the selectDataList that overlap the patch

        We use the "convexHull" function in the geom package to define
        polygons on the celestial sphere, and test the polygon of the
        patch for overlap with the polygon of the image.

        We use "convexHull" instead of generating a SphericalConvexPolygon
        directly because the standard for the inputs to SphericalConvexPolygon
        are pretty high and we don't want to be responsible for reaching them.
        If "convexHull" is found to be too slow, we can revise this.

        @param dataRef: Data reference for coadd/tempExp (with tract, patch)
        @param coordList: List of Coord specifying boundary of patch
        @param makeDataRefList: Construct a list of data references?
        @param selectDataList: List of SelectStruct, to consider for selection
        """
        from lsst.geom import convexHull
        psf_sizes = []
        dataRefList = []
        exposureInfoList = []

        patchVertices = [coord.getVector() for coord in coordList]
        patchPoly = convexHull(patchVertices)

        for data in selectDataList:
            dataRef = data.dataRef
            imageWcs = data.wcs
            cal = dataRef.get('calexp', immediate=True)
            psf_size = cal.getPsf().computeShape().getDeterminantRadius()
            nx, ny = data.dims

            imageBox = afwGeom.Box2D(afwGeom.Point2D(0, 0), afwGeom.Extent2D(nx, ny))
            try:
                imageCorners = [imageWcs.pixelToSky(pix) for pix in imageBox.getCorners()]
            except (pexExceptions.DomainError, pexExceptions.RuntimeError) as e:
                # Protecting ourselves from awful Wcs solutions in input images
                self.log.debug("WCS error in testing calexp %s (%s): deselecting", dataRef.dataId, e)
                continue

            imagePoly = convexHull([coord.getVector() for coord in imageCorners])
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
            size_fwhm = size_sigma*2.355
            if size_fwhm < self.config.maxPsfFwhm and size_fwhm > self.config.minPsfFwhm:
                self.log.info("%s selected with FWHM of %f pixels"%(dataRef.dataId, size_fwhm))
                filteredDataRefList.append(dataRef)
                filteredExposureInfoList.append(expInfo)
        return pipeBase.Struct(
            dataRefList = filteredDataRefList if makeDataRefList else None,
            exposureInfoList = filteredExposureInfoList,
        )

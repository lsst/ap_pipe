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

import logging
from astropy.table import Table, vstack

import lsst.pex.config as pexConfig
from lsst.pipe.base import PipelineTask, PipelineTaskConfig, PipelineTaskConnections, Struct
import lsst.pipe.base.connectionTypes as connTypes
from lsst.pipe.tasks.insertFakes import InsertFakesConfig
from lsst.skymap import BaseSkyMap

from lsst.source.injection import generate_injection_catalog

from deprecated.sphinx import deprecated

__all__ = ["CreateRandomApFakesTask",
           "CreateRandomApFakesConfig",
           "CreateRandomApFakesConnections",
           "CreateVisitDetectorFakesTask",
           "CreateVisitDetectorFakesConfig",
           "CreateVisitDetectorFakesConnections"]


class CreateRandomApFakesConnections(PipelineTaskConnections,
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
        name="fakeSourceCat",
        storageClass="DataFrame",
        dimensions=("tract", "skymap")
    )


@deprecated(
    reason="This task will be removed in v28.0 as it is replaced by `source_injection` tasks.",
    version="v28.0",
    category=FutureWarning,
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


@deprecated(
    reason="This task will be removed in v28.0 as it is replaced by `source_injection` tasks.",
    version="v28.0",
    category=FutureWarning,
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

        tract = skyMap.generateTract(tractId)
        tractArea = tract.getOuterSkyPolygon().getBoundingBox().getArea()
        tractArea *= (180 / np.pi) ** 2
        tractWcs = tract.getWcs()
        vertexList = tract.getVertexList()
        vertexRas = [vertex.getRa().asDegrees() for vertex in vertexList]
        vertexDecs = [vertex.getDec().asDegrees() for vertex in vertexList]

        catalog = generate_injection_catalog(
            ra_lim=sorted([np.min(vertexRas), np.max(vertexRas)]),
            dec_lim=sorted([np.min(vertexDecs), np.max(vertexDecs)]),
            mag_lim=(self.config.magMin, self.config.magMax),
            density=self.config.fakeDensity,
            source_type="Star",
            seed=str(tractId),
            wcs=tractWcs
        )

        nFakes = len(catalog)

        self.log.info(
            f"Creating {nFakes} star fakes over tractId={tractId} with "
            f" RA  in ({sorted([np.min(vertexRas), np.max(vertexRas)])} "
            f" Dec in ({sorted([np.min(vertexDecs), np.max(vertexDecs)])}), "
            f"area={tractArea:.4f} deg^2 and "
            f"magnitude range: [{self.config.magMin, self.config.magMax}]")

        onesColumn = np.ones(nFakes, dtype="float")
        zerosColumn = np.zeros(nFakes, dtype="float")
        # Concatenate the data and add dummy values for the unused variables.
        # Set all data to PSF like objects.
        mags = np.asarray(catalog["mag"], dtype=float)
        randData = {
            "fakeId": [uuid.uuid4().int & (1 << 64) - 1 for n in range(nFakes)],
            self.config.ra_col: np.asarray(catalog["ra"], dtype=float),
            self.config.dec_col: np.asarray(catalog["dec"], dtype=float),
            **self.createVisitCoaddSubdivision(nFakes),
            **self.createMagnitudeColumns(mags),
            self.config.disk_semimajor_col: onesColumn,
            self.config.bulge_semimajor_col: onesColumn,
            self.config.disk_n_col: onesColumn,
            self.config.bulge_n_col: onesColumn,
            self.config.disk_axis_ratio_col: onesColumn,
            self.config.bulge_axis_ratio_col: onesColumn,
            self.config.disk_pa_col: zerosColumn,
            self.config.bulge_pa_col: onesColumn,
            self.config.sourceType: np.asarray(catalog["source_type"], dtype=str),
            "source_type": np.asarray(catalog["source_type"], dtype=str),
            "injection_id": np.asarray(catalog["injection_id"], dtype=np.int64)
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

    def createMagnitudeColumns(self, mags):
        """Create magnitude columns from a 1D magnitude array.

        Parameters
        ----------
        mags : `numpy.ndarray`
            Magnitudes to copy to all configured filter-band columns.

        Returns
        -------
        randMags : `dict`[`str`, `numpy.ndarray`]
            Dictionary containing per-band magnitudes plus a ``mag`` column
            compatible with ``source_injection`` catalogs.
        """
        randMags = {}
        for fil in self.config.filterSet:
            randMags[self.config.mag_col % fil] = mags
        randMags["mag"] = mags
        return randMags


class CreateVisitDetectorFakesConnections(
    PipelineTaskConnections,
    defaultTemplates={"coaddName": "deep"},
    dimensions=("instrument",
                "visit",
                "detector")):

    sourceCat = connTypes.Input(
        doc="Catalog of sources detected on the calibrated exposure; ",
        name="single_visit_star_reprocessed_footprints",
        storageClass="SourceCatalog",
        dimensions=["instrument", "visit", "detector"],
    )
    visit_image = connTypes.Input(
        doc="Calibrated exposure to inject synthetic sources into.",
        name="preliminary_visit_image",
        storageClass="ExposureF",
        dimensions=["instrument", "visit", "detector"],
    )
    outputCat = connTypes.Output(
        doc="Catalog of fake sources to draw inputs from.",
        name="VisitDetectorFakeSourceCat",
        storageClass="ArrowAstropy",
        dimensions=["instrument", "visit", "detector"],
    )


class CreateVisitDetectorFakesConfig(
        PipelineTaskConfig,
        pipelineConnections=CreateVisitDetectorFakesConnections
):
    """Config for CreateVisitDetectorFakesTask."""
    randomFakeDensity = pexConfig.RangeField(
        doc="Goal density of visit detector fake sources per square degree.",
        dtype=float,
        default=1000,
        min=1,
    )
    nRandomFakes = pexConfig.RangeField(
        doc="Number of random fakes to add to the visit detector. Overrides "
            "the randomFakeDensity if set to a positive value.",
        dtype=int,
        default=-1,
        min=-1,
    )
    doAddRandomVisitFakes = pexConfig.Field(
        doc="Whether to add random positive fakes to the visit detector.",
        dtype=bool,
        default=True,
    )
    doAddRandomTemplateFakes = pexConfig.Field(
        doc="Whether to add random template fakes to the visit detector (negatives).",
        dtype=bool,
        default=True,
    )
    templateFakeFraction = pexConfig.RangeField(
        doc="Fraction of random fakes that should be added to the template image."
            " The rest will be added to the visit image.",
        dtype=float,
        default=0.25,
        min=0,
        max=1,
    )
    doAddVariableFakes = pexConfig.Field(
        doc="Whether to add variable fakes to the visit detector.",
        dtype=bool,
        default=False,
    )
    variableFakeFraction = pexConfig.RangeField(
        doc="Fraction of variable fakes that should be added to the template image."
            " The rest will be added to the visit image.",
        dtype=float,
        default=0.1,
        min=0,
        max=1,
    )
    variableFakeMean = pexConfig.RangeField(
        doc="Mean magnitude variation for variable fakes.",
        dtype=float,
        default=0.0,
        min=-1,
        max=1,
    )
    variableFakeStd = pexConfig.RangeField(
        doc="Standard deviation of magnitude variation for variable fakes.",
        dtype=float,
        default=0.5,
        min=0,
        max=1,
    )
    doAddHostedFakes = pexConfig.Field(
        doc="Whether to add hosted fakes to the visit detector.",
        dtype=bool,
        default=False,
    )
    fracHostedFakes = pexConfig.RangeField(
        doc="Fraction of hosts with fakes to add to the visit detector.",
        dtype=float,
        default=0.1,
        min=0,
        max=1,
    )
    minHostedFakes = pexConfig.RangeField(
        doc="Minimum number of hosted fakes to add to the visit detector.",
        dtype=int,
        default=20,
        min=1,
    )
    doAddModelFakes = pexConfig.Field(
        doc="Whether to add model fakes to the visit detector.",
        dtype=bool,
        default=False,
    )
    magMin = pexConfig.Field(
        doc="Minimum magnitude for the fake sources.",
        dtype=float,
        default=20,
    )
    magMax = pexConfig.Field(
        doc="Maximum magnitude for the fake sources.",
        dtype=float,
        default=26,
    )


class CreateVisitDetectorFakesTask(PipelineTask):
    """Create and store a set of visit detector fakes for use in AP processing.
    This task creates a catalog of fake sources that can be used to inject
    sources into visit detector images.
    """

    _DefaultName = "createVisitDetectorFakes"
    ConfigClass = CreateVisitDetectorFakesConfig

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.log = logging.getLogger(__name__)

    def runQuantum(self, butlerQC, inputRefs, outputRefs):
        inputs = butlerQC.get(inputRefs)
        outputs = self.run(**inputs)
        butlerQC.put(outputs, outputRefs)

    def _make_unique_injection_ids(self, n_ids, used_ids=None):
        """Generate collision-free injection IDs within the 24-bit ID space."""
        used = set() if used_ids is None else {int(value) for value in used_ids}
        injection_ids = []

        while len(injection_ids) < n_ids:
            candidate = uuid.uuid4().int & ((1 << 24) - 1)
            if candidate in used:
                continue
            used.add(candidate)
            injection_ids.append(candidate)

        return np.asarray(injection_ids, dtype=np.int64)

    def run(self, sourceCat, visit_image):
        """Create a set of visit detector fakes.

        Parameters
        ----------
        sourceCat : `lsst.afw.table.SourceCatalog`
            Catalog of sources detected on the calibrated exposure.
        visit_image : `lsst.afw.image.Exposure`
            Visit image to inject synthetic sources into.

        Returns
        -------
        outputCat : `astropy.table.Table`
            Catalog of fake sources to draw inputs from.
        """
        # Use the visit+detector ids as the random seed.
        visitId = visit_image.getInfo().getVisitInfo().id
        detId = visit_image.detector.getId()
        rng = np.random.default_rng([visitId, detId])

        # set of catalogs to concatenate at the end
        catalog_set = []

        photoCalib = visit_image.getPhotoCalib()
        bbox = visit_image.getBBox()
        xmin, xmax = bbox.getMinX(), bbox.getMaxX()
        ymin, ymax = bbox.getMinY(), bbox.getMaxY()
        visit_stats = visit_image.getInfo().getSummaryStats()

        wcs = visit_image.getWcs()
        magLim = visit_stats.magLim
        max_mag = np.min([magLim+1, self.config.magMax])

        if self.config.doAddRandomVisitFakes:
            # Generate random visit fakes
            self.log.info("Generating random visit fakes.")
            if self.config.nRandomFakes > 0:
                self.log.info(f"Generating random visit fakes with nRandomFakes={self.config.nRandomFakes}.")
                n_random_fakes = self.config.nRandomFakes
            else:
                self.log.info(
                    f"Generating random visit fakes with randomFakeDensity={self.config.randomFakeDensity}.")
                n_random_fakes = self.get_n_fakes_from_density(
                    visit_image=visit_image,
                    density=self.config.randomFakeDensity
                )
                self.log.info(f"Calculated n_random_fakes={n_random_fakes}.")

            # draw random x-y coordinates
            x_ssi = rng.uniform(xmin, xmax, size=n_random_fakes)
            y_ssi = rng.uniform(ymin, ymax, size=n_random_fakes)
            mags = rng.uniform(self.config.magMin, max_mag, size=n_random_fakes)
            ra_ssi, dec_ssi = wcs.pixelToSkyArray(x_ssi, y_ssi, degrees=True)

            random_catalog = Table()
            random_catalog["x"] = x_ssi
            random_catalog["y"] = y_ssi
            random_catalog["mag"] = mags
            random_catalog["ra"] = ra_ssi
            random_catalog["dec"] = dec_ssi
            random_catalog["source_type"] = "Star"
            random_catalog["isVisitSource"] = True
            random_catalog["isTemplateSource"] = False
            catalog_set.append(random_catalog)
        # Ignore now the possibility of _just_ template fakes
        if self.config.doAddModelFakes:
            # Generate model fakes
            self.log.info("Not implemented yet model fakes.")
            # Placeholder for actual model fake generation logic
            pass

        if self.config.doAddHostedFakes:
            # Generate hosted fakes
            self.log.info("Generating hosted fakes.")
            # Select hosts that look like extended sources.
            hostcatalog = photoCalib.calibrateCatalog(sourceCat).asAstropy()
            hostcatalog = self.select_hosts(hostcatalog)
            n_hosts = len(hostcatalog)
            if n_hosts == 0:
                self.log.warning("Hosted fake generation requested, but no valid hosts were selected.")
            else:
                requested_n_fakes = max(
                    int(self.config.fracHostedFakes * n_hosts), self.config.minHostedFakes
                )
                n_fakes = min(requested_n_fakes, n_hosts)
                if n_fakes < requested_n_fakes:
                    self.log.warning(
                        "Reducing hosted fake count from %d to %d because only %d hosts are available.",
                        requested_n_fakes,
                        n_fakes,
                        n_hosts,
                    )

                idx = rng.choice(n_hosts, size=n_fakes, replace=False)
                hostcat = hostcatalog[idx]

                x_hosts = hostcat['slot_Centroid_x']
                y_hosts = hostcat['slot_Centroid_y']
                mag_hosts = hostcat['slot_ModelFlux_mag']
                # the units below are pixels and radians
                pa, a, b = self.get_PA_and_axes(
                    hostcat['slot_Shape_xx'],
                    hostcat['slot_Shape_xy'],
                    hostcat['slot_Shape_yy']
                )
                # random radius and angle for the fake around the host
                theta = rng.uniform(0, 2 * np.pi, size=n_fakes)
                angle = np.sqrt((a*np.cos(theta))**2 + (b*np.sin(theta))**2)
                radii = angle * np.sqrt(rng.uniform(0, 6, size=n_fakes))

                # Polar -> Cartesian  wrt the host in the PA coordinate system
                xs = radii * np.cos(theta)
                ys = radii * np.sin(theta)

                # Retrieve the right position removing the galaxy orientation PA
                x_rots = xs * np.cos(pa) - ys * np.sin(pa)
                y_rots = xs * np.sin(pa) + ys * np.cos(pa)

                x_ssi = x_hosts + x_rots
                y_ssi = y_hosts + y_rots

                # retrieving the global ra dec position of the injection
                ra_ssi, dec_ssi = wcs.pixelToSkyArray(x_ssi, y_ssi, degrees=True)
                delta_ra = (ra_ssi - np.rad2deg(hostcat['coord_ra'])) * 3600.
                delta_dec = (dec_ssi - np.rad2deg(hostcat['coord_dec'])) * 3600.

                delta_mag = rng.normal(loc=1, scale=1, size=n_fakes)
                mags = mag_hosts + delta_mag

                #  Create the table of hosted fakes
                hosted_fakes = Table()
                hosted_fakes["x"] = x_ssi
                hosted_fakes["y"] = y_ssi
                hosted_fakes["mag"] = mags
                hosted_fakes["ra"] = ra_ssi
                hosted_fakes["dec"] = dec_ssi
                hosted_fakes["host_id"] = hostcat['id']
                hosted_fakes["host_flux"] = hostcat['slot_ModelFlux_flux']
                hosted_fakes["host_mag"] = hostcat['slot_ModelFlux_mag']
                hosted_fakes["host_ra"] = np.rad2deg(hostcat['coord_ra'])
                hosted_fakes["host_dec"] = np.rad2deg(hostcat['coord_dec'])
                hosted_fakes["delta_ra"] = delta_ra
                hosted_fakes["delta_dec"] = delta_dec
                hosted_fakes["delta_mag"] = delta_mag
                hosted_fakes["host_a"] = a
                hosted_fakes["host_b"] = b
                hosted_fakes["host_pa"] = pa
                hosted_fakes["source_type"] = "Star"
                hosted_fakes["hosted_fake"] = True
                hosted_fakes["isVisitSource"] = True
                hosted_fakes["isTemplateSource"] = False

                catalog_set.append(hosted_fakes)

        if not catalog_set:
            raise RuntimeError(
                "No fake sources were generated. Enable at least one fakes mode or provide usable hosts."
            )

        catalog = vstack(catalog_set)
        catalog['injection_id'] = self._make_unique_injection_ids(len(catalog))

        if self.config.doAddRandomTemplateFakes:
            is_tmplt_fake = rng.random(len(catalog)) < self.config.templateFakeFraction
            catalog["isTemplateSource"] = is_tmplt_fake
            catalog["isVisitSource"] = ~is_tmplt_fake
        else:
            catalog["isVisitSource"] = True
            catalog["isTemplateSource"] = False

        if self.config.doAddVariableFakes:
            # Generate variable fakes by duplicating some fakes and adding the counterpart
            # either science or template with a magnitude offset drawn from a normal
            # distribution with mean and std defined in the config.
            self.log.info("Generating variable fakes.")
            n_variable_fakes = int(len(catalog) * self.config.variableFakeFraction)
            idx = rng.choice(len(catalog), size=n_variable_fakes, replace=False)
            variable_fakes = catalog[idx].copy()
            variable_fakes["mag_offset"] = rng.normal(
                loc=self.config.variableFakeMean,
                scale=self.config.variableFakeStd,
                size=n_variable_fakes
            )
            variable_fakes["mag"] += variable_fakes["mag_offset"]
            # we flip the source, so for example if it was a visit, we trasnform it into a template
            # with the idea of having duplicate injections, in the same location
            variable_fakes["isVisitSource"] = ~variable_fakes["isVisitSource"]
            variable_fakes["isTemplateSource"] = ~variable_fakes["isTemplateSource"]

            variable_fakes["twin_id"] = variable_fakes["injection_id"]
            variable_fakes["injection_id"] = self._make_unique_injection_ids(
                len(variable_fakes),
                used_ids=catalog["injection_id"],
            )
            # create column of isVariable flag
            catalog["isVariable"] = np.where(np.isin(np.arange(len(catalog)), idx), True, False)
            variable_fakes["isVariable"] = True

            catalog = vstack([catalog, variable_fakes])

        if len(catalog) > len(np.unique(catalog["injection_id"])):
            self.log.warning("Duplicate injection IDs detected after catalog assembly; reassigning them.")
            old_injection_ids = np.asarray(catalog["injection_id"], dtype=np.int64)
            new_injection_ids = self._make_unique_injection_ids(len(catalog))
            # re-assign fresh injection ids
            catalog["injection_id"] = new_injection_ids
            if "twin_id" in catalog.colnames:
                id_map = {old_id: new_id for old_id, new_id in zip(old_injection_ids, new_injection_ids)}
                catalog["twin_id"] = np.asarray(
                    [id_map.get(int(twin_id), int(twin_id)) for twin_id in catalog["twin_id"]],
                    dtype=np.int64,
                )

        catalog["visit"] = visitId
        catalog["detector"] = detId

        return Struct(outputCat=catalog)

    def select_hosts(self, sourceCat):
        """
        Selects host sources from a given source catalog based on a series of classification and flux cuts.
        The selection criteria are:
            - The 'base_ClassificationSizeExtendedness_flag' and
                  'base_ClassificationExtendedness_flag' must both be False.
            - The 'base_ClassificationSizeExtendedness_value' must be greater than 0.9.
            - The 'base_ClassificationExtendedness_value' must be equal to 1.
            - The 'base_PsfFlux_flux' must be greater than 0.
        Parameters
        ----------
        sourceCat : SourceCatalog
            The source catalog containing the columns required for selection.
        *args, **kwargs
            Additional arguments (not used).
        Returns
        -------
        hostCat : ArrowAstropy
            A deep copy of the subset of the source catalog that passes all selection criteria.
        """

        # Avoid calibration stars or psf stars; remove flagged sources sky_sources
        skySourceCut = ~sourceCat['sky_source']

        flagCut = ~sourceCat['base_ClassificationSizeExtendedness_flag']
        flagCut &= ~sourceCat['base_ClassificationExtendedness_flag']
        flagCut &= ~sourceCat['slot_Shape_flag']
        flagCut &= ~sourceCat['slot_Centroid_flag']
        flagCut &= ~sourceCat['base_PixelFlags_flag']

        extendednessCut = sourceCat['base_ClassificationSizeExtendedness_value'] > 0.9
        extendednessCut &= sourceCat['base_ClassificationExtendedness_value'] == 1

        snrCut = sourceCat['slot_ModelFlux_flux']/sourceCat['slot_ModelFlux_fluxErr'] > 15

        hostCat = sourceCat[
            skySourceCut & flagCut & extendednessCut & snrCut].copy()
        return hostCat

    def get_PA_and_axes(self, Ixx, Ixy, Iyy):
        '''
        Calculates the orientation and extent of an object based on its second moments.

        Parameters:
        Ixx (float): Second moment of the object along the x-axis. Often in degree²
        Ixy (float): Second moment of the object along the x and y-axes. Often in degree²
        Iyy (float): Second moment of the object along the y-axis. Often in degree²

        Returns:
        tuple: A tuple containing:
            - theta (float): The orientation angle of the object in radians.
            - a (float): The semi-major axis length of the object.
            - b (float): The semi-minor axis length of the object.
        '''
        # Calculate position angle (orientation)
        theta = 0.5 * np.arctan2(2 * Ixy, Ixx - Iyy)

        # Calculate eigenvalues of the moment matrix
        term1 = (Ixx + Iyy) / 2
        term2 = np.sqrt(((Ixx - Iyy) / 2) ** 2 + Ixy ** 2)
        lambda1 = term1 + term2
        lambda2 = term1 - term2

        a = np.sqrt(lambda1)
        b = np.sqrt(lambda2)

        return theta, a, b

    def get_n_fakes_from_density(self, visit_image, density):
        """Calculate the area of the injection limits in square degrees based on the RA and Dec limits."""
        image_area = visit_image.getConvexPolygon().getBoundingBox().getArea()
        image_area *= (180 / np.pi) ** 2
        number = np.round(density * image_area).astype(int)
        return number

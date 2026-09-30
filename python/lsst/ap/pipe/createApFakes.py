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

from dataclasses import dataclass
from deprecated.sphinx import deprecated


__all__ = [
    "CreateRandomApFakesTask",
    "CreateRandomApFakesConfig",
    "CreateRandomApFakesConnections",
    "CreateVisitDetectorFakesTask",
    "CreateVisitDetectorFakesConfig",
    "CreateVisitDetectorFakesConnections",
]


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
        max=0.5001,
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
        max=0.2501,
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
        default=0.1,
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
    doAddBlendedFakes = pexConfig.Field(
        doc="Whether to add blended fakes to the visit detector.",
        dtype=bool,
        default=False,
    )
    fracBlendedFakes = pexConfig.RangeField(
        doc="Fraction of blended fakes to add to the visit detector.",
        dtype=float,
        default=0.1,
        min=0,
        max=0.2501,
    )
    fracHostedBlendedFakes = pexConfig.RangeField(
        doc="Fraction of blended fakes that are hosted by stars.",
        dtype=float,
        default=0.1,
        min=0,
        max=0.5001,
    )
    blendedFakeMagOffset = pexConfig.Field(
        doc="Standard deviation of magnitude offset for blended fakes.",
        dtype=float,
        default=0.5,
    )
    blendedFakeMaxOffset = pexConfig.Field(
        doc="Maximum positional offset for blended fakes in arcseconds.",
        dtype=float,
        default=3.0,
    )
    blendedFakeMinOffset = pexConfig.Field(
        doc="Minimum positional offset for blended fakes in arcseconds.",
        dtype=float,
        default=0.2,
    )
    maxHostedBlendedFakesPerHost = pexConfig.RangeField(
        doc="Maximum number of hosted blended fakes assigned to the same host in one detector.",
        dtype=int,
        default=2,
        min=1,
    )
    maxHostedBlendedFakesTotal = pexConfig.RangeField(
        doc="Hard cap on number of hosted blended fakes per detector. Set to -1 to disable.",
        dtype=int,
        default=-1,
        min=-1,
    )


@dataclass
class FakeGenerationPlan:
    n_total: int = 0
    n_science: int = 0
    n_template: int = 0
    n_variable: int = 0
    n_blended: int = 0

    n_hosted: int = 0
    n_hosted_science: int = 0
    n_hosted_template: int = 0
    n_hosted_variable: int = 0
    n_hosted_blended: int = 0


class CreateVisitDetectorFakesTask(PipelineTask):
    """Create visit-detector fakes in explicit planning and assembly stages."""

    _DefaultName = "createVisitDetectorFakes"
    ConfigClass = CreateVisitDetectorFakesConfig

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.log = logging.getLogger(__name__)
        self._table_dtypes = [
            ("x", "<f8"),
            ("y", "<f8"),
            ("mag", "<f8"),
            ("ra", "<f8"),
            ("dec", "<f8"),
            ("source_type", "<U4"),
            ("isVisitSource", "?"),
            ("isTemplateSource", "?"),
            ("host_id", "<i8"),
            ("host_flux", "<f8"),
            ("host_mag", "<f8"),
            ("host_ra", "<f8"),
            ("host_dec", "<f8"),
            ("delta_ra", "<f8"),
            ("delta_dec", "<f8"),
            ("delta_mag", "<f8"),  # referred to host_mag
            ("host_type", "<U8"),
            ("host_a", "<f8"),
            ("host_b", "<f8"),
            ("host_pa", "<f8"),
            ("hosted_fake", "?"),
            ("injection_id", "<i8"),
            ("isVariable", "?"),
            ("mag_offset", "<f8"),  # referred to variable parent or blend parent
            ("twin_id", "<i8"),
            ("isBlended", "?"),
            ("blend_twin_id", "<i8"),
            ("visit", "<i8"),
            ("detector", "<i8"),
        ]

    def runQuantum(self, butlerQC, inputRefs, outputRefs):
        outputs = self.run(**butlerQC.get(inputRefs))
        butlerQC.put(outputs, outputRefs)

    def run(self, sourceCat, visit_image):
        """Generate, assemble, validate, and normalize a fake catalog."""
        visit_id = visit_image.getInfo().getVisitInfo().id
        detector_id = visit_image.detector.getId()
        rng = np.random.default_rng([visit_id, detector_id])
        wcs = visit_image.getWcs()
        photo_calib = visit_image.getPhotoCalib()
        sourceCat = photo_calib.calibrateCatalog(sourceCat).asAstropy()
        stats = visit_image.getInfo().getSummaryStats()
        max_mag = min(stats.magLim + 1, self.config.magMax)

        plan = self._make_full_plan(visit_image)
        if plan.n_total <= 0:
            raise RuntimeError(
                "No fake sources will be generated."
            )
        # Build populations one by one
        # Bear in mind that fractions describe primary sources/pairs, not catalog rows.
        populations = []

        # Random science fakes
        if plan.n_science > 0 and self.config.doAddRandomVisitFakes:
            random_science_cat = self._generate_seed_fake_catalog(plan.n_science, visit_image, wcs, rng)
            random_science_cat["mag"] = rng.uniform(self.config.magMin, max_mag, size=plan.n_science)
            random_science_cat["isVisitSource"] = np.ones(plan.n_science, dtype=bool)
            random_science_cat["isTemplateSource"] = np.zeros(plan.n_science, dtype=bool)
            random_science_cat["injection_id"] = self._make_unique_injection_ids(
                len(random_science_cat), used_ids=None)
            populations.append(random_science_cat)

            # Hosted science
            hosted_science_cat, science_hosts = self._generate_hosted_fake_catalog(
                plan.n_hosted_science, sourceCat, wcs, rng, host_type='extended')
            if science_hosts is None:
                self.log.warning(
                    "Hosted science fake generation requested, but no valid extended hosts were selected."
                )
            else:
                hosted_science_cat["isVisitSource"] = np.ones(plan.n_hosted_science, dtype=bool)
                hosted_science_cat["isTemplateSource"] = np.zeros(plan.n_hosted_science, dtype=bool)
                hosted_science_cat["hosted_fake"] = np.ones(plan.n_hosted_science, dtype=bool)
                hosted_science_cat["injection_id"] = self._make_unique_injection_ids(
                    len(hosted_science_cat), used_ids=[cat["injection_id"] for cat in populations])
                populations.append(hosted_science_cat)

        # Template fakes
        if plan.n_template > 0 and self.config.doAddRandomTemplateFakes:
            random_template_cat = self._generate_seed_fake_catalog(plan.n_template, visit_image, wcs, rng)
            random_template_cat["mag"] = rng.uniform(self.config.magMin, max_mag, size=plan.n_template)
            random_template_cat["isVisitSource"] = np.zeros(plan.n_template, dtype=bool)
            random_template_cat["isTemplateSource"] = np.ones(plan.n_template, dtype=bool)
            random_template_cat["injection_id"] = self._make_unique_injection_ids(
                len(random_template_cat), used_ids=[cat["injection_id"] for cat in populations])
            populations.append(random_template_cat)

            # Hosted template fakes
            hosted_template_cat, template_hosts = self._generate_hosted_fake_catalog(
                plan.n_hosted_template, sourceCat, wcs, rng, host_type='extended')
            if template_hosts is None:
                self.log.warning(
                    "Hosted template fake generation requested, but no valid extended hosts were selected."
                )
            else:
                hosted_template_cat["isVisitSource"] = np.zeros(plan.n_hosted_template, dtype=bool)
                hosted_template_cat["isTemplateSource"] = np.ones(plan.n_hosted_template, dtype=bool)
                hosted_template_cat["hosted_fake"] = np.ones(plan.n_hosted_template, dtype=bool)
                hosted_template_cat["injection_id"] = self._make_unique_injection_ids(
                    len(hosted_template_cat), used_ids=[cat["injection_id"] for cat in populations])
                populations.append(hosted_template_cat)

        # Variable fakes
        if plan.n_variable > 0 and self.config.doAddVariableFakes:
            random_variable_cat = self._generate_seed_fake_catalog(plan.n_variable, visit_image, wcs, rng)
            random_variable_cat["mag"] = rng.uniform(self.config.magMin, max_mag, size=plan.n_variable)
            random_variable_cat["isVisitSource"] = np.ones(plan.n_variable, dtype=bool)
            random_variable_cat["isTemplateSource"] = np.zeros(plan.n_variable, dtype=bool)
            random_variable_cat["isVariable"] = np.ones(plan.n_variable, dtype=bool)
            random_variable_cat["injection_id"] = self._make_unique_injection_ids(
                len(random_variable_cat), used_ids=[cat["injection_id"] for cat in populations])
            # make the twins for variable sources
            twins = self._generate_variable_twins(random_variable_cat, rng)
            twins["injection_id"] = self._make_unique_injection_ids(
                    len(twins), used_ids=[cat["injection_id"] for cat in populations + [random_variable_cat]]
            )
            # reciprocate the injection_id for the twins so they can be linked
            random_variable_cat["twin_id"] = twins["injection_id"]
            populations.append(random_variable_cat)
            populations.append(twins)

            # Hosted variable fakes
            hosted_variable_cat, variable_hosts = self._generate_hosted_fake_catalog(
                plan.n_hosted_variable, sourceCat, wcs, rng, host_type='extended')
            if variable_hosts is None:
                self.log.warning(
                    "Hosted variable fake generation requested, but no valid extended hosts were selected."
                )
            else:
                hosted_variable_cat["isVisitSource"] = np.ones(plan.n_hosted_variable, dtype=bool)
                hosted_variable_cat["isTemplateSource"] = np.zeros(plan.n_hosted_variable, dtype=bool)
                hosted_variable_cat["isVariable"] = np.ones(plan.n_hosted_variable, dtype=bool)
                hosted_variable_cat["hosted_fake"] = np.ones(plan.n_hosted_variable, dtype=bool)
                hosted_variable_cat["injection_id"] = self._make_unique_injection_ids(
                    len(hosted_variable_cat), used_ids=[cat["injection_id"] for cat in populations])
                # make the twins for hosted variable sources
                hosted_twins = self._generate_variable_twins(hosted_variable_cat, rng)
                hosted_twins["injection_id"] = self._make_unique_injection_ids(
                    len(hosted_twins),
                    used_ids=[cat["injection_id"] for cat in populations + [hosted_variable_cat]]
                )
                hosted_variable_cat["twin_id"] = hosted_twins["injection_id"]
                populations.append(hosted_variable_cat)
                populations.append(hosted_twins)

        # Blended fakes
        if plan.n_blended > 0 and self.config.doAddBlendedFakes:
            n_sources = plan.n_blended // 2
            blended_cat = self._generate_seed_fake_catalog(n_sources, visit_image, wcs, rng)
            blended_cat["injection_id"] = self._make_unique_injection_ids(
                len(blended_cat), used_ids=[cat["injection_id"] for cat in populations])
            blended_cat["mag"] = rng.uniform(self.config.magMin, max_mag, size=n_sources)
            blended_cat["isVisitSource"] = rng.choice([True, False], size=n_sources)
            blended_cat["isTemplateSource"] = ~blended_cat["isVisitSource"]
            blended_cat["isBlended"] = np.ones(n_sources, dtype=bool)
            # make the twins for blends
            blended_twins = self._generate_blended_twins(blended_cat, rng, wcs)
            blended_twins["isVisitSource"] = rng.choice([True, False], size=n_sources)
            blended_twins["isTemplateSource"] = ~blended_twins["isVisitSource"]

            blended_twins["injection_id"] = self._make_unique_injection_ids(
                len(blended_twins), used_ids=[cat["injection_id"] for cat in populations + [blended_cat]]
            )
            # reciprocate the injection_id for the twins so they can be linked
            blended_cat["blend_twin_id"] = blended_twins["injection_id"]
            populations.append(blended_cat)
            populations.append(blended_twins)

            # Hosted blended fakes are in stars so we don't add twins.
            n_sources = plan.n_hosted_blended
            hosted_blended_cat, blend_hosts = self._generate_hosted_fake_catalog(
                n_sources, sourceCat, wcs, rng, host_type='star')
            if blend_hosts is None:
                self.log.warning(
                    "Hosted blended fake generation requested, but no valid star hosts were selected."
                )
            else:
                hosted_blended_cat, blend_hosts = self._cap_hosted_blended_count(
                    hosted_blended_cat, blend_hosts
                )
                n_sources = len(hosted_blended_cat)
                hosted_blended_cat["injection_id"] = self._make_unique_injection_ids(
                    len(hosted_blended_cat), used_ids=[cat["injection_id"] for cat in populations])
                hosted_blended_cat["mag"] = rng.uniform(self.config.magMin, max_mag, size=n_sources)
                hosted_blended_cat["isVisitSource"] = rng.choice([True, False], size=n_sources)
                hosted_blended_cat["isTemplateSource"] = ~hosted_blended_cat["isVisitSource"]
                hosted_blended_cat["isBlended"] = np.ones(n_sources, dtype=bool)
                hosted_blended_cat["hosted_fake"] = np.ones(n_sources, dtype=bool)
                populations.append(hosted_blended_cat)

        # Merge all populations into a single catalog
        if len(populations) == 0:
            raise RuntimeError("No fakes were generated for this visit detector.")

        populations = [self._set_population_defaults(population) for population in populations]
        catalog = vstack(populations) if populations else Table(dtype=self._table_dtypes)

        self._validate_catalog(catalog)
        self._normalize_catalog(catalog, visit_id, detector_id)
        return Struct(outputCat=catalog)

    def _make_full_plan(self, visit_image):
        """Plan exactly the number of fakes to inject, and their types,
        based on the configuration and the visit image.
        This is prior to knowing available hosts for hosted fakes, so the plan
        may be adjusted later."""

        n_total = 0
        plan = FakeGenerationPlan()
        if self.config.nRandomFakes > 0:
            n_total = self.config.nRandomFakes
        else:
            n_total = self.get_n_fakes_from_density(
                visit_image, self.config.randomFakeDensity
            )

        plan.n_total = n_total

        if self.config.doAddRandomTemplateFakes:
            plan.n_template = int(n_total * self.config.templateFakeFraction)
        if self.config.doAddVariableFakes:
            plan.n_variable = int(n_total * self.config.variableFakeFraction)
        if self.config.doAddBlendedFakes:
            plan.n_blended = int(n_total * self.config.fracBlendedFakes)
            # we will generate n_blends pairs of blended sources,
            # so the total number of blended sources is 2*n_blends
            n_blends = plan.n_blended//2
            plan.n_blended = n_blends * 2
        if self.config.doAddRandomVisitFakes:
            n_science = n_total - plan.n_template - plan.n_variable - plan.n_blended
            if n_science < 0:
                self.log.warning(
                    "Requested number of fakes exceeds the total planned. Adjusting n_science to 0."
                )
                n_science = 0
            plan.n_science = n_science

        if self.config.doAddHostedFakes:
            plan.n_hosted = int(n_total * self.config.fracHostedFakes)
            plan.n_hosted_science = int(plan.n_science * self.config.fracHostedFakes)
            plan.n_science = plan.n_science - plan.n_hosted_science
            plan.n_hosted_template = int(plan.n_template * self.config.fracHostedFakes)
            plan.n_template = plan.n_template - plan.n_hosted_template
            plan.n_hosted_variable = int(plan.n_variable * self.config.fracHostedFakes)
            plan.n_variable = plan.n_variable - plan.n_hosted_variable

        if self.config.fracHostedBlendedFakes > 0:
            plan.n_hosted_blended = int(plan.n_blended * self.config.fracHostedBlendedFakes)
            plan.n_hosted_blended = plan.n_hosted_blended
            plan.n_blended = plan.n_blended - plan.n_hosted_blended

        return plan

    def _set_population_defaults(self, catalog):
        """Ensure population flags and relationship IDs are concrete values."""
        defaults = {
            "isVariable": False,
            "isBlended": False,
            "twin_id": 0,
            "blend_twin_id": 0,
        }
        for name, default in defaults.items():
            if name not in catalog.colnames:
                catalog[name] = np.full(len(catalog), default)
            else:
                values = np.ma.asarray(catalog[name])
                catalog[name] = np.ma.filled(values, default)
        return catalog

    def _generate_seed_fake_catalog(self, n_fakes, visit_image, wcs, rng):
        """Generate a seed catalog of random fakes with positions and magnitudes."""
        if n_fakes <= 0:
            return Table(dtype=self._table_dtypes, masked=False)

        bbox = visit_image.getBBox()
        x = rng.uniform(bbox.getMinX(), bbox.getMaxX(), size=n_fakes)
        y = rng.uniform(bbox.getMinY(), bbox.getMaxY(), size=n_fakes)
        ra, dec = wcs.pixelToSkyArray(x, y, degrees=True)

        zero_table = Table(dtype=self._table_dtypes, masked=False)
        catalog = Table(masked=False)
        catalog["x"] = x
        catalog["y"] = y
        catalog["ra"] = ra
        catalog["dec"] = dec
        catalog["source_type"] = "Star"
        catalog = vstack([zero_table, catalog])

        return catalog

    def _build_hosted_population(self, hosts, wcs, rng, host_type='extended'):
        """Build a population of hosted fakes around selected hosts."""
        if host_type == 'extended':
            pa, a, b = self.get_PA_and_axes(
                hosts["slot_Shape_xx"], hosts["slot_Shape_xy"], hosts["slot_Shape_yy"]
            )
            flux_type = "slot_ModelFlux_flux"
            mag_type = "slot_ModelFlux_mag"
        else:
            pa, a, b = 0, 1, 1  # For stars, we can treat them as circular with no orientation
            flux_type = "slot_PsfFlux_flux"
            mag_type = "slot_PsfFlux_mag"

        n_fakes = len(hosts)
        theta = rng.uniform(0, 2 * np.pi, size=n_fakes)
        radii = np.sqrt((a * np.cos(theta)) ** 2 + (b * np.sin(theta)) ** 2)
        radii *= np.sqrt(rng.uniform(0, 6, size=n_fakes))
        x = hosts["slot_Centroid_x"] + radii * np.cos(theta) * np.cos(pa) - radii * np.sin(theta) * np.sin(pa)
        y = hosts["slot_Centroid_y"] + radii * np.cos(theta) * np.sin(pa) + radii * np.sin(theta) * np.cos(pa)
        ra, dec = wcs.pixelToSkyArray(x, y, degrees=True)

        zero_table = Table(dtype=self._table_dtypes, masked=False)
        catalog = Table(masked=False)
        catalog["x"] = x
        catalog["y"] = y
        # magnitudes are drawn from a normal distribution around host magnitude
        catalog["mag"] = hosts[mag_type] + rng.normal(1, 1, size=n_fakes)
        catalog["ra"] = ra
        catalog["dec"] = dec
        catalog["host_id"] = hosts["id"]
        catalog["host_flux"] = hosts[flux_type]
        catalog["host_mag"] = hosts[mag_type]
        catalog["host_ra"] = np.rad2deg(hosts["coord_ra"])
        catalog["host_dec"] = np.rad2deg(hosts["coord_dec"])
        catalog["delta_ra"] = (ra - catalog["host_ra"]) * 3600
        catalog["delta_dec"] = (dec - catalog["host_dec"]) * 3600
        catalog["delta_mag"] = catalog["mag"] - catalog["host_mag"]
        catalog["host_a"] = a
        catalog["host_b"] = b
        catalog["host_pa"] = pa
        catalog["source_type"] = "Star"
        catalog["host_type"] = host_type
        catalog["hosted_fake"] = np.ones(len(catalog), dtype=bool)
        catalog = vstack([zero_table, catalog])

        return catalog, hosts

    def _generate_hosted_fake_catalog(self, n_fakes, sourceCat, wcs, rng, host_type='extended'):
        """Generate a catalog of hosted fakes around selected host galaxies or stars."""
        if n_fakes <= 0:
            return Table(dtype=self._table_dtypes, masked=False), None

        host_catalog = self.select_hosts(sourceCat, host_type=host_type)
        if len(host_catalog) == 0:
            self.log.warning("No valid hosts were selected for hosted fakes.")
            return Table(dtype=self._table_dtypes, masked=False), None

        # we allow more than one fake per host since we can deal with blending now
        if n_fakes > len(host_catalog):
            self.log.warning(
                "Requested %d hosted fakes, but only %d valid hosts were found. "
                "Some hosts will have multiple fakes.",
                n_fakes,
                len(host_catalog),
            )
            idx = rng.choice(len(host_catalog), size=n_fakes, replace=True)
        else:
            idx = rng.choice(len(host_catalog), size=n_fakes, replace=False)

        selected_hosts = host_catalog[idx]
        return self._build_hosted_population(selected_hosts, wcs, rng, host_type=host_type)

    def _generate_variable_twins(self, variable_catalog, rng):
        """Generate twin sources for variable fakes with magnitude offsets."""
        n_twins = len(variable_catalog)
        if n_twins <= 0:
            return Table(dtype=self._table_dtypes, masked=False)
        # magnitudes are drawn from a normal distribution around the variable source's magnitude
        twins = variable_catalog.copy()
        twins["mag_offset"] = rng.normal(
            loc=self.config.variableFakeMean,
            scale=self.config.variableFakeStd,
            size=n_twins
        )
        twins["mag"] += twins["mag_offset"]
        twins["isVisitSource"] = ~twins["isVisitSource"]
        twins["isTemplateSource"] = ~twins["isTemplateSource"]
        twins["twin_id"] = twins["injection_id"]
        return twins

    def _generate_blended_twins(self, blended_catalog, rng, wcs):
        """Generate twin sources for blended fakes with magnitude and positional offsets."""
        n_twins = len(blended_catalog)
        if n_twins <= 0:
            return Table(dtype=self._table_dtypes, masked=False)

        twins = blended_catalog.copy()
        twins["mag_offset"] = rng.normal(
            loc=0.0,
            scale=self.config.blendedFakeMagOffset,
            size=n_twins
        )
        # we are reusing the delta_ra and delta_dec columns to store the offsets for the twins
        # original host information will be in the entry for the parent blend source
        # stored in the blend_parent_id column
        delta_ra, delta_dec = self._draw_offset_components_arcsec(rng, n_twins)
        twins["delta_ra"] = delta_ra
        twins["delta_dec"] = delta_dec
        twins["mag"] += twins["mag_offset"]

        twins["ra"] += twins["delta_ra"] * np.cos(np.deg2rad(twins["dec"])) / 3600
        twins["dec"] += twins["delta_dec"] / 3600
        twins["x"], twins["y"] = wcs.skyToPixelArray(twins["ra"], twins["dec"], degrees=True)

        twins["blend_twin_id"] = twins["injection_id"]
        return twins

    def _validate_catalog(self, catalog):
        """Validate IDs and reciprocal source relationships."""
        injection_ids = np.asarray(catalog["injection_id"], dtype=np.int64)
        if len(np.unique(injection_ids)) != len(injection_ids):
            raise RuntimeError("Fake injection IDs are not unique.")

        id_set = set(injection_ids)

        variable = np.asarray(catalog["isVariable"], dtype=bool)
        blended = np.asarray(catalog["isBlended"], dtype=bool)

        if np.any(variable & blended):
            raise RuntimeError("Variable and blended fake populations overlap.")

        twin_ids = np.asarray(catalog["twin_id"], dtype=np.int64)
        variable_twin_ids = twin_ids[variable]

        if np.any(variable_twin_ids <= 0):
            raise RuntimeError("Variable fake twin links are incomplete.")

        if not set(variable_twin_ids).issubset(id_set):
            raise RuntimeError("Variable twin IDs do not refer to catalog rows.")

        variable_rows_by_id = {
            int(injection_id): index
            for index, injection_id in enumerate(injection_ids)
            if variable[index]
        }

        for index in np.flatnonzero(variable):
            twin_index = variable_rows_by_id.get(int(twin_ids[index]))
            if twin_index is None:
                raise RuntimeError("Variable twin ID does not identify a variable row.")
            if twin_ids[twin_index] != injection_ids[index]:
                raise RuntimeError("Variable twin links are not reciprocal.")

        # removing hosted blends from the check
        non_hosted_blends = blended & ~np.asarray(catalog["hosted_fake"], dtype=bool)
        blend_twin_ids = np.asarray(catalog["blend_twin_id"], dtype=np.int64)
        blended_twin_ids = blend_twin_ids[non_hosted_blends]

        if np.any(blended_twin_ids <= 0):
            raise RuntimeError("Blended fake twin links are incomplete.")

        if not set(blended_twin_ids).issubset(id_set):
            raise RuntimeError("Blend twin IDs do not refer to catalog rows.")

        rows_by_id = {
            int(injection_id): index
            for index, injection_id in enumerate(injection_ids)
        }

        for index in np.flatnonzero(blend_twin_ids):
            twin_index = rows_by_id[int(blend_twin_ids[index])]
            if blend_twin_ids[twin_index] != injection_ids[index]:
                raise RuntimeError("Blend twin links are not reciprocal.")

    def _normalize_catalog(self, catalog, visit_id, detector_id):
        """Normalize catalog columns to remove units and add visit/detector identifiers."""
        catalog["visit"] = visit_id
        catalog["detector"] = detector_id
        for name in ("ra", "dec", "delta_ra", "delta_dec", "host_ra", "host_dec"):
            if name in catalog.colnames and catalog[name].unit is not None:
                catalog[name] = catalog[name].value

    def select_hosts(self, sourceCat, host_type='extended'):
        """Select hosts from the source catalog."""
        sky = ~sourceCat["sky_source"]
        flags = ~sourceCat["base_ClassificationSizeExtendedness_flag"]
        flags &= ~sourceCat["base_ClassificationExtendedness_flag"]
        flags &= ~sourceCat["slot_Shape_flag"]
        flags &= ~sourceCat["slot_Centroid_flag"]
        flags &= ~sourceCat["base_PixelFlags_flag"]

        if host_type == 'extended':
            extended = sourceCat["base_ClassificationSizeExtendedness_value"] > 0.9
            extended &= sourceCat["base_ClassificationExtendedness_value"] == 1
            snr = sourceCat["slot_ModelFlux_flux"] / sourceCat["slot_ModelFlux_fluxErr"] > 15
            return sourceCat[sky & flags & extended & snr].copy()
        elif host_type == 'star':
            stellar = sourceCat["base_ClassificationSizeExtendedness_value"] < 0.9
            stellar &= sourceCat["base_ClassificationExtendedness_value"] == 0
            snr = sourceCat["slot_PsfFlux_flux"] / sourceCat["slot_PsfFlux_fluxErr"] > 30
            return sourceCat[sky & flags & stellar & snr].copy()
        else:
            raise ValueError("host_type must be 'extended' or 'star'.")

    def get_PA_and_axes(self, Ixx, Ixy, Iyy):
        """Compute the position angle and semi-major/minor axes from second moments."""
        theta = 0.5 * np.arctan2(2 * Ixy, Ixx - Iyy)
        term = np.sqrt(((Ixx - Iyy) / 2) ** 2 + Ixy ** 2)
        return theta, np.sqrt((Ixx + Iyy) / 2 + term), np.sqrt((Ixx + Iyy) / 2 - term)

    def _cap_hosted_blended_count(self, hosted_fakes, hosts):
        """Cap the number of hosted blended fakes based on configuration limits."""
        if len(hosted_fakes) == 0 or len(hosts) == 0:
            return hosted_fakes, hosts

        # check if we have multiple ids for the same host and cap the number of fakes per host
        unique_hosts, counts = np.unique(hosted_fakes["host_id"], return_counts=True)
        capped_hosts = []
        for host_id, count in zip(unique_hosts, counts):
            if count > self.config.maxHostedBlendedFakesPerHost:
                self.log.warning(
                    "Capping hosted blended fakes for host_id %d from %d to %d.",
                    host_id, count, self.config.maxHostedBlendedFakesPerHost
                )
                capped_hosts.append(host_id)
                row_ids = np.where(hosted_fakes["host_id"] == host_id)
                row_ids_to_remove = row_ids[0][self.config.maxHostedBlendedFakesPerHost:]
                hosted_fakes.remove_rows(row_ids_to_remove)
        if len(hosted_fakes) > self.config.maxHostedBlendedFakesTotal:
            self.log.warning(
                "Capping total hosted blended fakes from %d to %d.",
                len(hosted_fakes), self.config.maxHostedBlendedFakesTotal
            )
            hosted_fakes = hosted_fakes[:self.config.maxHostedBlendedFakesTotal]
        return hosted_fakes, hosts

    def _draw_offset_components_arcsec(self, rng, n_points):
        """Draw random offsets in arcseconds for blended fakes.
        The offsets are drawn from a uniform distribution in radius and angle."""
        if n_points <= 0:
            return np.zeros(0), np.zeros(0)
        rmin = max(0.0, self.config.blendedFakeMinOffset)
        rmax = max(rmin, self.config.blendedFakeMaxOffset)
        radius = np.sqrt(rng.uniform(rmin**2, rmax**2, n_points))
        theta = rng.uniform(0, 2 * np.pi, n_points)
        return radius * np.cos(theta), radius * np.sin(theta)

    def get_n_fakes_from_density(self, visit_image, density):
        area = visit_image.getConvexPolygon().getBoundingBox().getArea()
        return np.round(density * area * (180 / np.pi) ** 2).astype(int)

    def _make_unique_injection_ids(self, n_ids, used_ids=None):
        """Generate unique 24-bit IDs for a catalog considering IDs already in use."""
        new_ids = set()
        if used_ids is not None:
            # compile used ids from the existing catalog to avoid collisions
            if isinstance(used_ids, list):
                used_ids = np.concatenate(used_ids)
                used_ids = set(used_ids)
        else:
            used_ids = set()
        # check that the new ids are not in the used set already
        while len(new_ids) < n_ids:
            candidate_id = uuid.uuid4().int & ((1 << 24) - 1)
            if candidate_id not in used_ids.union(new_ids):
                new_ids.add(candidate_id)

        return np.asarray(list(new_ids), dtype=np.int64)

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
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

import lsst.daf.butler.tests as butlerTests
import lsst.geom as geom
from astropy.table import Table
from lsst.pipe.base import testUtils
import lsst.skymap as skyMap
import lsst.utils.tests

from lsst.ap.pipe.createApFakes import (
    CreateRandomApFakesTask,
    CreateRandomApFakesConfig,
    CreateVisitDetectorFakesTask,
    CreateVisitDetectorFakesConfig,
)


class TestCreateApFakes(lsst.utils.tests.TestCase):

    def setUp(self):
        """
        """
        self.tractId = 0
        self.rng = np.random.default_rng(self.tractId)
        simpleMapConfig = skyMap.discreteSkyMap.DiscreteSkyMapConfig()
        simpleMapConfig.raList = [10]
        simpleMapConfig.decList = [-1]
        simpleMapConfig.radiusList = [0.1]
        self.simpleMap = skyMap.DiscreteSkyMap(simpleMapConfig)
        self.tract = self.simpleMap.generateTract(self.tractId)

        bBox = self.tract.getOuterSkyPolygon().getBoundingBox()
        self.nSources = 50
        self.sourceDensity = (self.nSources
                              / (bBox.getArea() * (180 / np.pi) ** 2))
        self.fraction = 0.5
        self.nInVisit = (int(self.nSources * self.fraction)
                         + int((1 - self.fraction) / 2 * self.nSources))
        self.nInTemplate = (self.nSources - self.nInVisit
                            + int(self.nSources * self.fraction))

    def testRunQuantum(self):
        """Test the run quantum method with a gen3 butler.
        """
        root = tempfile.mkdtemp()
        dimensions = {"instrument": ["notACam"],
                      "skymap": ["skyMap"],
                      "tract": [0, 42],
                      }
        testRepo = butlerTests.makeTestRepo(root, dimensions)
        with self.assertWarns(FutureWarning):
            fakesTask = CreateRandomApFakesTask()
        connections = fakesTask.config.ConnectionsClass(
            config=fakesTask.config)
        butlerTests.addDatasetType(
            testRepo,
            connections.skyMap.name,
            connections.skyMap.dimensions,
            connections.skyMap.storageClass)
        butlerTests.addDatasetType(
            testRepo,
            connections.fakeCat.name,
            connections.fakeCat.dimensions,
            connections.fakeCat.storageClass)

        dataId = {"skymap": "skyMap", "tract": 0}
        butler = butlerTests.makeTestCollection(testRepo)
        butler.put(self.simpleMap, "skyMap", {"skymap": "skyMap"})

        quantum = testUtils.makeQuantum(
            fakesTask, butler, dataId,
            {"skyMap": {"skymap": dataId["skymap"]}, "fakeCat": dataId})
        run = testUtils.runTestQuantum(fakesTask, butler, quantum, True)
        # Actual input dataset omitted for simplicity
        run.assert_called_once_with(tractId=dataId["tract"], skyMap=self.simpleMap)
        shutil.rmtree(root, ignore_errors=True)

    def testRun(self):
        """Test the run method.
        """
        with self.assertWarns(FutureWarning):
            fakesConfig = CreateRandomApFakesConfig()
        fakesConfig.fraction = 0.5
        fakesConfig.fakeDensity = self.sourceDensity

        with self.assertWarns(FutureWarning):
            fakesTask = CreateRandomApFakesTask(config=fakesConfig)
        bBox = self.tract.getOuterSkyPolygon().getBoundingBox()
        result = fakesTask.run(self.tractId, self.simpleMap)
        fakeCat = result.fakeCat
        self.assertEqual(len(fakeCat), self.nSources)
        self.assertIn("injection_id", fakeCat.columns)
        self.assertIn("source_type", fakeCat.columns)
        self.assertIn("mag", fakeCat.columns)
        self.assertTrue(np.issubdtype(fakeCat["injection_id"].dtype, np.integer))
        self.assertEqual(fakeCat["injection_id"].nunique(), len(fakeCat))
        self.assertTrue(np.all(fakeCat["source_type"] == "Star"))

        for idx, row in fakeCat.iterrows():
            self.assertTrue(
                bBox.contains(
                    geom.SpherePoint(row[fakesTask.config.ra_col],
                                     row[fakesTask.config.dec_col],
                                     geom.degrees).getVector()))
        self.assertEqual(fakeCat[fakesConfig.visitSourceFlagCol].sum(),
                         self.nInVisit)
        self.assertEqual(fakeCat[fakesConfig.templateSourceFlagCol].sum(),
                         self.nInTemplate)
        for f in fakesConfig.filterSet:
            filterMags = fakeCat[fakesConfig.mag_col % f]
            self.assertEqual(self.nSources, len(filterMags))
            self.assertTrue(
                np.all(fakesConfig.magMin <= filterMags))
            self.assertTrue(
                np.all(fakesConfig.magMax > filterMags))
            self.assertTrue(np.allclose(filterMags, fakeCat["mag"]))

    def testVisitCoaddSubdivision(self):
        """Test that the number of assigned visit to template objects is
        correct.
        """
        with self.assertWarns(FutureWarning):
            fakesConfig = CreateRandomApFakesConfig()
        fakesConfig.fraction = 0.5
        with self.assertWarns(FutureWarning):
            fakesTask = CreateRandomApFakesTask(config=fakesConfig)
        subdivision = fakesTask.createVisitCoaddSubdivision(self.nSources)
        self.assertEqual(
            subdivision[fakesConfig.visitSourceFlagCol].sum(),
            self.nInVisit)
        self.assertEqual(
            subdivision[fakesConfig.templateSourceFlagCol].sum(),
            self.nInTemplate)

    def testRandomMagnitudes(self):
        """Test that the correct number of filters and magnitudes have been
        produced.
        This is using currently the filter mags and an additional non-filter mag
        column. In any case the magnitudes are all random and equal.
        """
        with self.assertWarns(FutureWarning):
            fakesConfig = CreateRandomApFakesConfig()
        fakesConfig.filterSet = ["u", "g"]
        fakesConfig.mag_col = "%s_mag"
        fakesConfig.magMin = 20
        fakesConfig.magMax = 21
        with self.assertWarns(FutureWarning):
            fakesTask = CreateRandomApFakesTask(config=fakesConfig)
        mags = fakesTask.createRandomMagnitudes(self.nSources, self.rng)
        # this is because we have a column for mag without filter
        self.assertEqual(len(fakesConfig.filterSet) + 1, len(mags))

        for f in fakesConfig.filterSet:
            filterMags = mags[fakesConfig.mag_col % f]
            self.assertEqual(self.nSources, len(filterMags))
            self.assertTrue(
                np.all(fakesConfig.magMin <= filterMags))
            self.assertTrue(
                np.all(fakesConfig.magMax > filterMags))


def _make_mock_visit_image(visitId=2024111100094, detId=3,
                           xmin=0, xmax=4096, ymin=0, ymax=4096,
                           magLim=25.0, ra_center=10.0, dec_center=-1.0):
    """Build a minimal MagicMock that satisfies CreateVisitDetectorFakesTask.run."""
    img = MagicMock()

    # visit / detector IDs
    img.getInfo().getVisitInfo().id = visitId
    img.detector.getId.return_value = detId

    # bounding box
    bbox = MagicMock()
    bbox.getMinX.return_value = xmin
    bbox.getMaxX.return_value = xmax
    bbox.getMinY.return_value = ymin
    bbox.getMaxY.return_value = ymax
    img.getBBox.return_value = bbox

    # summary stats — magLim drives max_mag
    stats = MagicMock()
    stats.magLim = magLim
    img.getInfo().getSummaryStats.return_value = stats

    # convex polygon for density calculation (returns a bbox in steradians)
    poly_bbox = MagicMock()
    # ~1e-5 sr ≈ small patch, dense enough to yield O(10) fakes at density=1000
    poly_bbox.getArea.return_value = 1e-5
    img.getConvexPolygon().getBoundingBox.return_value = poly_bbox

    # WCS: pixelToSkyArray returns ra/dec arrays of the right length
    wcs = MagicMock()

    def _pix_to_sky(xs, ys, degrees=True):
        ra = ra_center + xs * 1e-4
        dec = dec_center + ys * 1e-4
        return np.asarray(ra), np.asarray(dec)
    wcs.pixelToSkyArray.side_effect = _pix_to_sky
    img.getWcs.return_value = wcs

    # photoCalib — not used in non-hosted paths, but must exist
    img.getPhotoCalib.return_value = MagicMock()

    return img


class TestCreateVisitDetectorFakesTask(lsst.utils.tests.TestCase):

    def setUp(self):
        self.visit_image = _make_mock_visit_image()
        self.source_cat = MagicMock()  # not used unless doAddHostedFakes

    def _make_task(self, **config_overrides):
        cfg = CreateVisitDetectorFakesConfig()
        cfg.doAddRandomVisitFakes = True
        cfg.doAddRandomTemplateFakes = False
        cfg.doAddHostedFakes = False
        cfg.doAddVariableFakes = False
        cfg.doAddModelFakes = False
        cfg.nRandomFakes = 50
        for k, v in config_overrides.items():
            setattr(cfg, k, v)
        return CreateVisitDetectorFakesTask(config=cfg)

    # ------------------------------------------------------------------
    # Basic smoke test: random-only path
    # ------------------------------------------------------------------
    def testRunRandomOnly(self):
        task = self._make_task()
        result = task.run(self.source_cat, self.visit_image)
        cat = result.outputCat

        self.assertIsInstance(cat, Table)
        self.assertEqual(len(cat), 50)
        # Required columns
        for col in ("ra", "dec", "mag", "x", "y", "source_type",
                    "injection_id", "visit", "detector"):
            self.assertIn(col, cat.colnames)
        # All sources are stars
        self.assertTrue(np.all(cat["source_type"] == "Star"))
        # IDs are unique
        self.assertEqual(len(np.unique(cat["injection_id"])), len(cat))
        # visit/detector are set correctly
        self.assertTrue(np.all(cat["visit"] == 2024111100094))
        self.assertTrue(np.all(cat["detector"] == 3))

    # ------------------------------------------------------------------
    # Template-fraction split
    # ------------------------------------------------------------------
    def testTemplateFakeFraction(self):
        task = self._make_task(
            doAddRandomTemplateFakes=True,
            templateFakeFraction=0.25,
            nRandomFakes=200,
        )
        result = task.run(self.source_cat, self.visit_image)
        cat = result.outputCat

        n_template = int(np.sum(cat["isTemplateSource"]))
        # No source should be both visit AND template (mutually exclusive after split)
        self.assertFalse(np.any(cat["isVisitSource"] & cat["isTemplateSource"]))
        # template fraction should be roughly 25 %
        frac = n_template / len(cat)
        self.assertAlmostEqual(frac, 0.25, delta=0.10)

    # ------------------------------------------------------------------
    # Variable fakes: twin_id bookkeeping
    # ------------------------------------------------------------------
    def testVariableFakesTwinTracking(self):
        task = self._make_task(
            doAddVariableFakes=True,
            variableFakeFraction=0.2,
            nRandomFakes=100,
        )
        result = task.run(self.source_cat, self.visit_image)
        cat = result.outputCat

        # Catalog is larger than the base 100 fakes
        self.assertGreater(len(cat), 100)
        # twin_id column exists
        self.assertIn("twin_id", cat.colnames)
        # Every injection_id is unique
        self.assertEqual(len(np.unique(cat["injection_id"])), len(cat))
        # mag_offset column is present on variable rows
        self.assertIn("mag_offset", cat.colnames)

    # ------------------------------------------------------------------
    # Empty-mode guard raises RuntimeError
    # ------------------------------------------------------------------
    def testEmptyCatalogRaises(self):
        task = self._make_task(
            doAddRandomVisitFakes=False,
            doAddHostedFakes=False,
            doAddModelFakes=False,
        )
        with self.assertRaises(RuntimeError):
            task.run(self.source_cat, self.visit_image)

    # ------------------------------------------------------------------
    # Hosted fakes: sparse-host cap (fewer hosts than minHostedFakes)
    # ------------------------------------------------------------------
    def testHostedFakesSparseHostCap(self):
        """When n_hosts < minHostedFakes the task should clamp, not crash."""
        cfg = CreateVisitDetectorFakesConfig()
        cfg.doAddRandomVisitFakes = False
        cfg.doAddHostedFakes = True
        cfg.doAddRandomTemplateFakes = False
        cfg.doAddVariableFakes = False
        cfg.doAddModelFakes = False
        cfg.fracHostedFakes = 0.99  # near-100 % but within [0, 1) range
        cfg.minHostedFakes = 50  # request 50 but we'll only supply 5 hosts
        task = CreateVisitDetectorFakesTask(config=cfg)

        n_hosts = 5
        host_table = Table({
            "slot_Centroid_x": np.full(n_hosts, 2048.0),
            "slot_Centroid_y": np.full(n_hosts, 2048.0),
            "slot_ModelFlux_mag": np.full(n_hosts, 20.0),
            "slot_ModelFlux_flux": np.full(n_hosts, 1e4),
            "slot_ModelFlux_fluxErr": np.full(n_hosts, 100.0),
            "slot_Shape_xx": np.full(n_hosts, 4.0),
            "slot_Shape_xy": np.zeros(n_hosts),
            "slot_Shape_yy": np.full(n_hosts, 4.0),
            "id": np.arange(n_hosts, dtype=np.int64),
            "coord_ra": np.deg2rad(np.full(n_hosts, 10.0)),
            "coord_dec": np.deg2rad(np.full(n_hosts, -1.0)),
            "sky_source": np.zeros(n_hosts, dtype=bool),
            "base_ClassificationSizeExtendedness_flag": np.zeros(n_hosts, dtype=bool),
            "base_ClassificationExtendedness_flag": np.zeros(n_hosts, dtype=bool),
            "slot_Shape_flag": np.zeros(n_hosts, dtype=bool),
            "slot_Centroid_flag": np.zeros(n_hosts, dtype=bool),
            "base_PixelFlags_flag": np.zeros(n_hosts, dtype=bool),
            "base_ClassificationSizeExtendedness_value": np.ones(n_hosts),
            "base_ClassificationExtendedness_value": np.ones(n_hosts, dtype=int),
        })

        # Patch photoCalib so calibrateCatalog().asAstropy() returns our table
        img = _make_mock_visit_image()
        img.getPhotoCalib().calibrateCatalog.return_value.asAstropy.return_value = host_table

        result = task.run(self.source_cat, img)
        cat = result.outputCat

        # Number of hosted fakes should be clamped to n_hosts, not minHostedFakes
        self.assertEqual(len(cat), n_hosts)
        self.assertIn("hosted_fake", cat.colnames)
        self.assertTrue(np.all(cat["hosted_fake"]))
        self.assertEqual(len(np.unique(cat["injection_id"])), n_hosts)

    # ------------------------------------------------------------------
    # Hosted fakes: zero valid hosts — warning issued, no crash when
    # random fakes are also enabled as fallback
    # ------------------------------------------------------------------
    def testHostedFakesNoHostsWarning(self):
        task = self._make_task(
            doAddRandomVisitFakes=True,
            nRandomFakes=10,
            doAddHostedFakes=True,
        )
        empty_table = Table({
            "slot_Centroid_x": np.array([]),
            "slot_Centroid_y": np.array([]),
            "slot_ModelFlux_mag": np.array([]),
            "slot_ModelFlux_flux": np.array([]),
            "slot_ModelFlux_fluxErr": np.array([]),
            "slot_Shape_xx": np.array([]),
            "slot_Shape_xy": np.array([]),
            "slot_Shape_yy": np.array([]),
            "id": np.array([], dtype=np.int64),
            "coord_ra": np.array([]),
            "coord_dec": np.array([]),
            "sky_source": np.array([], dtype=bool),
            "base_ClassificationSizeExtendedness_flag": np.array([], dtype=bool),
            "base_ClassificationExtendedness_flag": np.array([], dtype=bool),
            "slot_Shape_flag": np.array([], dtype=bool),
            "slot_Centroid_flag": np.array([], dtype=bool),
            "base_PixelFlags_flag": np.array([], dtype=bool),
            "base_ClassificationSizeExtendedness_value": np.array([]),
            "base_ClassificationExtendedness_value": np.array([], dtype=int),
        })
        self.visit_image.getPhotoCalib().calibrateCatalog.return_value.asAstropy.return_value = (
            empty_table
        )

        with self.assertLogs("lsst.ap.pipe.createApFakes", level="WARNING") as cm:
            result = task.run(self.source_cat, self.visit_image)

        self.assertTrue(any("no valid hosts" in msg.lower() for msg in cm.output))
        # Random fakes still produced
        self.assertEqual(len(result.outputCat), 10)


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()

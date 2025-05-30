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

import lsst.daf.butler.tests as butlerTests
import lsst.geom as geom
from lsst.pipe.base import testUtils
import lsst.skymap as skyMap
import lsst.utils.tests

from lsst.ap.pipe.createApFakes import CreateRandomApFakesTask, CreateRandomApFakesConfig


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


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()

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

import astropy.units as u
import numpy as np
import unittest

import lsst.skymap as skyMap
import lsst.utils.tests
from lsst.verify import Name
from lsst.verify.tasks.testUtils import MetricTaskTestCase

from lsst.ap.pipe.createApFakes import CreateRandomApFakesTask, CreateRandomApFakesConfig
from lsst.ap.pipe.metrics import ApFakesCompletenessMetricTask, ApFakesCompletenessMetricConfig


class TestApCompletenessTask(MetricTaskTestCase):

    @classmethod
    def makeTask(cls, magMin=20, magMax=30):
        config = ApFakesCompletenessMetricConfig()
        config.magMin = magMin
        config.magMax = magMax

        return ApFakesCompletenessMetricTask(config=config)

    def setUp(self):
        super().setUp()

        simpleMapConfig = skyMap.discreteSkyMap.DiscreteSkyMapConfig()
        simpleMapConfig.raList = [45]
        simpleMapConfig.decList = [45]
        simpleMapConfig.radiusList = [0.1]

        self.simpleMap = skyMap.DiscreteSkyMap(simpleMapConfig)
        self.tractId = 0
        bCircle = self.simpleMap.generateTract(self.tractId).getInnerSkyPolygon().getBoundingCircle()
        self.targetSources = 1000
        self.sourceDensity = (self.targetSources
                              / (bCircle.getArea() * (180 / np.pi) ** 2))

        fakesConfig = CreateRandomApFakesConfig()
        fakesConfig.fraction = 0.0
        fakesConfig.fakeDensity = self.sourceDensity
        fakesTask = CreateRandomApFakesTask(config=fakesConfig)
        fakeCat = fakesTask.run(self.tractId, self.simpleMap).fakeCat

        self.band = 'g'
        magCut = 25
        magMask = (fakeCat[f"{fakesConfig.magVar}" % self.band] < magCut)
        self.expectedAllMatched = magMask.sum()
        ids = np.where(magMask, np.arange(1, len(fakeCat) + 1, dtype=int), 0)
        self.fakeCat = fakeCat.assign(diaObjectId=ids,
                                      filterName=["g"] * len(fakeCat),
                                      diaSourceId=ids)

    def testValid(self):
        """Test the run method.
        """
        metricComplete = self.makeTask(20, 30)
        result = metricComplete.run(self.fakeCat, self.band)
        lsst.pipe.base.testUtils.assertValidOutput(metricComplete, result)

        meas = result.measurement
        self.assertEqual(meas.metric_name, Name(metric="ap_pipe.apFakesCompletenessMag20t30"))
        self.assertEqual(
            meas.quantity,
            self.expectedAllMatched / self.targetSources * u.dimensionless_unscaled)

    def testMissingData(self):
        """
        """
        result = self.task.run(None, None)
        lsst.pipe.base.testUtils.assertValidOutput(self.task, result)
        meas = result.measurement
        self.assertIsNone(meas)

    def testValidEmpty(self):
        """Test the run method.
        """
        metricComplete = self.makeTask(25, 30)
        result = metricComplete.run(self.fakeCat, self.band)
        lsst.pipe.base.testUtils.assertValidOutput(metricComplete, result)

        meas = result.measurement
        self.assertEqual(meas.metric_name, Name(metric="ap_pipe.apFakesCompletenessMag25t30"))
        self.assertEqual(meas.quantity, 0 * u.dimensionless_unscaled)


# Hack around unittest's hacky test setup system
del MetricTaskTestCase


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()

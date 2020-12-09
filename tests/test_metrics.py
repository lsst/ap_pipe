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

from lsst.pipe.base import testUtils
import lsst.skymap as skyMap
import lsst.utils.tests
from lsst.verify import Name
from lsst.verify.tasks.testUtils import MetricTaskTestCase

from lsst.ap.pipe.createApFakes import CreateRandomApFakesTask, CreateRandomApFakesConfig
from lsst.ap.pipe.metrics import ApFakesCompletenessMetricTask, ApFakesCompletenessMetricConfig


class TestApCompletenessTask(MetricTaskTestCase):

    @classmethod
    def makeTask(cls, magMin=20, magMax=30):
        """Make the task and allow for modification of the config min and max.

        Parameters
        ----------
        magMin : min magnitude, `float`
            Minimum magnitude
        magMax : min magnitude, `float`
            Maximum magnitude
        """
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
        self.magCut = 25
        magMask = (fakeCat[fakesConfig.magVar % self.band] < self.magCut)
        self.expectedAllMatched = magMask.sum()
        ids = np.where(magMask, np.arange(1, len(fakeCat) + 1, dtype=int), 0)
        # Add columns to mimic the matched fakes result without running the
        # full pipeline.
        self.fakeCat = fakeCat.assign(diaObjectId=ids,
                                      filterName=["g"] * len(fakeCat),
                                      diaSourceId=ids)

    def testValid(self):
        """Test the run method.
        """
        result = self.task.run(self.fakeCat, self.band)
        testUtils.assertValidOutput(self.task, result)

        meas = result.measurement
        self.assertEqual(meas.metric_name, Name(metric="ap_pipe.apFakesCompleteness"))
        self.assertEqual(
            meas.quantity,
            self.expectedAllMatched / self.targetSources * u.dimensionless_unscaled)

    def testMissingData(self):
        """Test the run method with no data.
        """
        result = self.task.run(None, None)
        testUtils.assertValidOutput(self.task, result)
        meas = result.measurement
        self.assertIsNone(meas)

    def testValidEmpty(self):
        """Test the run method with a valid but zero result.
        """
        metricComplete = self.makeTask(self.magCut, self.magCut + 5)
        result = metricComplete.run(self.fakeCat, self.band)
        testUtils.assertValidOutput(metricComplete, result)

        meas = result.measurement
        self.assertEqual(meas.metric_name, Name(metric="ap_pipe.apFakesCompleteness"))
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

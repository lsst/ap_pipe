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
import time
import unittest

import lsst.pex.config
from lsst.pipe.base import testUtils
import lsst.skymap as skyMap
from lsst.utils.timer import timeMethod
import lsst.utils.tests
from lsst.verify import Name
import lsst.verify.tasks
from lsst.verify.tasks.testUtils import MetricTaskTestCase

from lsst.ap.pipe.createApFakes import CreateRandomApFakesTask, CreateRandomApFakesConfig
from lsst.ap.pipe.metrics import (ApFakesCompletenessMetricTask, ApFakesCompletenessMetricConfig,
                                  ApFakesCountMetricTask, ApFakesCountMetricConfig,
                                  PipelineTimingMetricTask)


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
        magMask = (fakeCat[fakesConfig.mag_col % self.band] < self.magCut)
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
        # Work around for Mac failing this test.
        self.assertAlmostEqual(
            meas.quantity.value,
            ((self.expectedAllMatched / self.targetSources) * u.dimensionless_unscaled).value,
            places=2)

    def testValidEmpty(self):
        """Test the run method with a valid but zero result.
        """
        metricComplete = self.makeTask(self.magCut, self.magCut + 5)
        result = metricComplete.run(self.fakeCat, self.band)
        testUtils.assertValidOutput(metricComplete, result)

        meas = result.measurement
        self.assertEqual(meas.metric_name, Name(metric="ap_pipe.apFakesCompleteness"))
        self.assertEqual(meas.quantity, 0 * u.dimensionless_unscaled)


class TestApCountTask(MetricTaskTestCase):

    @classmethod
    def makeTask(cls, magMin=20, magMax=25):
        """Make the task and allow for modification of the config min and max.

        Parameters
        ----------
        magMin : min magnitude, `float`
            Minimum magnitude
        magMax : min magnitude, `float`
            Maximum magnitude
        """
        config = ApFakesCountMetricConfig()
        config.magMin = magMin
        config.magMax = magMax

        return ApFakesCountMetricTask(config=config)

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
        magMask = (fakeCat[fakesConfig.mag_col % self.band] < self.magCut)
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
        # Work around for Mac failing this test.
        self.assertAlmostEqual(
            meas.quantity.value,
            (self.expectedAllMatched * u.count).value,
            places=2)

    def testValidEmpty(self):
        """Test the run method with a valid but zero result.
        """
        # Make a mag cut that will have no sources. 30 < g < 35.
        metricComplete = self.makeTask(self.magCut + 5, self.magCut + 10)
        result = metricComplete.run(self.fakeCat, self.band)
        testUtils.assertValidOutput(metricComplete, result)

        meas = result.measurement
        self.assertEqual(meas.metric_name, Name(metric="ap_pipe.apFakesCompleteness"))
        self.assertEqual(meas.quantity, 0 * u.count)


class DummyTask(lsst.pipe.base.Task):
    ConfigClass = lsst.pex.config.Config
    _DefaultName = "NotARealTask"
    taskLength = 0.1

    @timeMethod
    def run(self):
        time.sleep(self.taskLength)


# Can't test against MetadataMetricTestCase, because this class is not a MetadataMetricTask
class TestPipelineTimingMetricTask(MetricTaskTestCase):
    @staticmethod
    def _makeConfig(nameStart=DummyTask._DefaultName, nameEnd=DummyTask._DefaultName):
        config = PipelineTimingMetricTask.ConfigClass()
        config.connections.labelStart = nameStart
        config.connections.labelEnd = nameEnd
        config.targetStart = nameStart + ".run"
        config.targetEnd = nameEnd + ".run"
        config.connections.package = "ap_pipe"
        config.connections.metric = "DummyTime"
        return config

    @classmethod
    def makeTask(cls):
        return PipelineTimingMetricTask(config=cls._makeConfig(nameStart="first", nameEnd="last"))

    def setUp(self):
        super().setUp()
        self.metric = Name("ap_pipe.DummyTime")

        self.startTask = DummyTask(name="first")
        self.startTask.run()
        self.endTask = DummyTask(name="last")
        self.endTask.run()

    def testSingleTask(self):
        task = PipelineTimingMetricTask(config=self._makeConfig(nameStart="first", nameEnd="first"))

        altConfig = lsst.verify.tasks.TimingMetricConfig()
        altConfig.connections.labelName = "first"
        altConfig.target = "first.run"
        altConfig.connections.package = "verify"
        altConfig.connections.metric = "DummyTime"
        altTask = lsst.verify.tasks.TimingMetricTask(config=altConfig)

        result = task.run(self.startTask.getFullMetadata(), self.startTask.getFullMetadata())
        oracle = altTask.run(self.startTask.getFullMetadata())

        self.assertEqual(result.measurement.metric_name, self.metric)
        self.assertAlmostEqual(result.measurement.quantity.to_value(u.s),
                               oracle.measurement.quantity.to_value(u.s))

    def testTwoTasks(self):
        firstTask = PipelineTimingMetricTask(config=self._makeConfig(nameStart="first", nameEnd="first"))
        secondTask = PipelineTimingMetricTask(config=self._makeConfig(nameStart="last", nameEnd="last"))

        result = self.task.run(self.startTask.getFullMetadata(), self.endTask.getFullMetadata())
        firstResult = firstTask.run(self.startTask.getFullMetadata(), self.startTask.getFullMetadata())
        secondResult = secondTask.run(self.endTask.getFullMetadata(), self.endTask.getFullMetadata())

        self.assertEqual(result.measurement.metric_name, self.metric)
        self.assertGreater(result.measurement.quantity, 0.0 * u.s)
        self.assertGreaterEqual(result.measurement.quantity,
                                firstResult.measurement.quantity + secondResult.measurement.quantity)

    def testRunDifferentMethodFirst(self):
        config = self._makeConfig(nameStart="first", nameEnd="last")
        config.targetStart = "first.doProcess"
        task = PipelineTimingMetricTask(config=config)
        try:
            result = task.run(self.startTask.getFullMetadata(), self.endTask.getFullMetadata())
        except lsst.pipe.base.NoWorkFound:
            # Correct behavior for MetricTask
            pass
        else:
            # Alternative correct behavior for MetricTask
            testUtils.assertValidOutput(task, result)
            meas = result.measurement
            self.assertIsNone(meas)

    def testRunDifferentMethodLast(self):
        config = self._makeConfig(nameStart="first", nameEnd="last")
        config.targetStart = "last.doProcess"
        task = PipelineTimingMetricTask(config=config)
        try:
            result = task.run(self.startTask.getFullMetadata(), self.endTask.getFullMetadata())
        except lsst.pipe.base.NoWorkFound:
            # Correct behavior for MetricTask
            pass
        else:
            # Alternative correct behavior for MetricTask
            testUtils.assertValidOutput(task, result)
            meas = result.measurement
            self.assertIsNone(meas)

    def testBadlyTypedKeys(self):
        metadata = self.endTask.getFullMetadata()
        endKeys = [key
                   for key in metadata.paramNames(topLevelOnly=False)
                   if "EndUtc" in key]
        for key in endKeys:
            metadata[key] = 42

        with self.assertRaises(lsst.verify.tasks.MetricComputationError):
            self.task.run(self.startTask.getFullMetadata(), metadata)


# Hack around unittest's hacky test setup system
del MetricTaskTestCase


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()

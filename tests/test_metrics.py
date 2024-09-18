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
import time
import unittest

import lsst.pex.config
from lsst.pipe.base import testUtils
from lsst.utils.timer import timeMethod
import lsst.utils.tests
from lsst.verify import Name
import lsst.verify.tasks
from lsst.verify.tasks.testUtils import MetricTaskTestCase

from lsst.ap.pipe.metrics import PipelineTimingMetricTask


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

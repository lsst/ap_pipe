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

import contextlib
import os
import unittest
from unittest.mock import patch, Mock, ANY

import lsst.utils.tests
import lsst.pex.exceptions as pexExcept
import lsst.daf.persistence as dafPersist
import lsst.pipe.base as pipeBase

from lsst.ap.pipe import ApPipeTask


class PipelineTestSuite(lsst.utils.tests.TestCase):
    '''
    A set of tests for the functions in ap_pipe.
    '''

    @classmethod
    def _makeDefaultConfig(cls):
        config = ApPipeTask.ConfigClass()
        config.load(os.path.join(cls.datadir, "config", "apPipe.py"))
        config.diaPipe.apdb.db_url = "sqlite://"
        config.diaPipe.apdb.isolation_level = "READ_UNCOMMITTED"
        return config

    @classmethod
    def setUpClass(cls):
        try:
            cls.datadir = lsst.utils.getPackageDir("ap_pipe_testdata")
        except pexExcept.NotFoundError:
            raise unittest.SkipTest("ap_pipe_testdata not set up")
        try:
            lsst.utils.getPackageDir("obs_decam")
        except LookupError:
            raise unittest.SkipTest("obs_decam not set up; needed for ap_pipe_testdata")

    def _setupObjPatch(self, *args, **kwargs):
        """Create a patch in setUp that will be reverted once the test ends.

        Parameters
        ----------
        *args
        **kwargs
            Inputs to `unittest.mock.patch.object`.
        """
        patcher = patch.object(*args, **kwargs)
        patcher.start()
        self.addCleanup(patcher.stop)

    def setUp(self):
        self.config = self._makeDefaultConfig()
        self.butler = dafPersist.Butler(inputs={'root': self.datadir})

        def makeMockDataRef(datasetType, level=None, dataId={}, **rest):
            mockDataRef = Mock(dafPersist.ButlerDataRef)
            mockDataRef.dataId = dict(dataId, **rest)
            return mockDataRef

        self._setupObjPatch(self.butler, "dataRef", side_effect=makeMockDataRef)
        self.dataId = {"visit": 413635, "ccdnum": 42}
        self.inputRef = self.butler.dataRef("raw", **self.dataId)

    @contextlib.contextmanager
    def mockPatchSubtasks(self, task):
        """Make mocks for all the ap_pipe subtasks.

        This is needed because the task itself cannot be a mock.
        The task's subtasks do not exist until the task is created, so
        this allows us to mock them instead.

        Parameters
        ----------
        task : `lsst.ap.pipe.ApPipeTask`
            The task whose subtasks will be mocked.

        Yields
        ------
        subtasks : `lsst.pipe.base.Struct`
            All mocks created by this context manager, including:

            ``ccdProcessor``
            ``differencer``
            ``diaPipe``
                a mock for the corresponding subtask. Mocks do not return any
                particular value, but have mocked methods that can be queried
                for calls by ApPipeTask
        """
        with patch.object(task, "ccdProcessor") as mockCcdProcessor, \
                patch.object(task, "differencer") as mockDifferencer, \
                patch.object(task, "diaPipe") as mockDiaPipe:
            yield pipeBase.Struct(ccdProcessor=mockCcdProcessor,
                                  differencer=mockDifferencer,
                                  diaPipe=mockDiaPipe)

    def testGenericRun(self):
        """Test the normal workflow of each ap_pipe step.
        """
        task = ApPipeTask(self.butler, config=self.config)
        with self.mockPatchSubtasks(task) as subtasks:
            task.runDataRef(self.inputRef)
            subtasks.ccdProcessor.runDataRef.assert_called_once()
            subtasks.differencer.runDataRef.assert_called_once()
            subtasks.diaPipe.run.assert_called_once()

    def testReuseExistingOutput(self):
        """Test reuse keyword to ApPipeTask.runDataRef.
        """
        task = ApPipeTask(self.butler, config=self.config)

        self.checkReuseExistingOutput(task, ['ccdProcessor'])
        self.checkReuseExistingOutput(task, ['ccdProcessor', 'differencer'])
        self.checkReuseExistingOutput(task, ['ccdProcessor', 'differencer', 'diaPipe'])

    def checkReuseExistingOutput(self, task, skippable):
        """Check whether a task's subtasks are skipped when "reuse" is set.

        Mock guarantees that all "has this been made" tests pass,
        so skippable subtasks should actually be skipped.
        """
        # extremely brittle because it depends on internal code of runDataRef
        # but it only needs to work until DM-21886, then we can unit-test the subtask
        internalRef = self.inputRef.getButler().dataRef()
        internalRef.put.reset_mock()

        with self.mockPatchSubtasks(task) as subtasks:
            struct = task.runDataRef(self.inputRef, reuse=skippable)
            for subtaskName, runner in {
                'ccdProcessor': subtasks.ccdProcessor.runDataRef,
                'differencer': subtasks.differencer.runDataRef,
                'diaPipe': subtasks.diaPipe.run,
            }.items():
                msg = "subtask = " + subtaskName
                if subtaskName in skippable:
                    runner.assert_not_called()
                    self.assertIsNone(struct.getDict()[subtaskName], msg=msg)
                else:
                    runner.assert_called_once()
                    self.assertIsNotNone(struct.getDict()[subtaskName], msg=msg)

        if 'diaPipe' in skippable:
            internalRef.put.assert_not_called()
        else:
            internalRef.put.assert_called_once_with(ANY, "apdb_marker")

    def testCalexpRun(self):
        """Test the calexp template workflow of each ap_pipe step.
        """
        calexpConfigFile = os.path.join(lsst.utils.getPackageDir('ap_pipe'),
                                        'config', 'calexpTemplates.py')
        calexpConfig = self._makeDefaultConfig()
        calexpConfig.load(calexpConfigFile)
        calexpConfig.differencer.doSelectSources = False  # Workaround for DM-18394

        task = ApPipeTask(self.butler, config=calexpConfig)
        with self.mockPatchSubtasks(task) as subtasks:
            # We use the same dataId here for both template and science
            # in difference imaging. This is OK because everything is a mock
            # and we aren't actually doing any image processing.
            task.runDataRef(self.inputRef, templateIds=[self.dataId])
            self.assertEqual(subtasks.ccdProcessor.runDataRef.call_count, 2)
            subtasks.differencer.runDataRef.assert_called_once()
            subtasks.diaPipe.run.assert_called_once()


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()

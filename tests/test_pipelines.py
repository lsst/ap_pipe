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

import glob
import os.path
import unittest

# need to import pyproj to prevent file handle leakage
import pyproj  # noqa: F401

import lsst.pipe.base
import lsst.utils
import lsst.utils.tests


class PipelineDefintionsTestSuite(lsst.utils.tests.TestCase):
    """Tests of the self-consistency of our pipeline definitions.
    """
    def setUp(self):
        self.path = os.path.join(lsst.utils.getPackageDir("ap_pipe"), "pipelines")

    def test_pipelines(self):
        """Test that each pipeline definition file in `_ingredients/` can be
        used to build a graph.
        """
        files = glob.glob(os.path.join(self.path, "_ingredients/*.yaml"))
        for file in files:
            if "ApTemplate" in file:
                # Our ApTemplate definition cannot be tested here because it
                # depends on drp_tasks, which we cannot make a dependency here.
                continue
            with self.subTest(file):
                pipeline = lsst.pipe.base.Pipeline.from_uri(file)
                if "apPipe" in pipeline.subsets:
                    pipeline.addConfigOverride("diaPipe", "apdb.db_url", "sqlite://")
                # If this fails, it will produce a useful error message.
                pipeline.to_graph()


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()

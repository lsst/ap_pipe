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
import tempfile
import unittest

# need to import pyproj to prevent file handle leakage
import pyproj  # noqa: F401

import lsst.daf.butler.tests as butlerTests
import lsst.pipe.base
from lsst.pipe.base.tests.pipelineStepTester import PipelineStepTester  # Can't use fully-qualified name
import lsst.utils
import lsst.utils.tests


class PipelineDefintionsTestSuite(lsst.utils.tests.TestCase):
    """Tests of the self-consistency of our pipeline definitions.
    """
    def setUp(self):
        self.path = os.path.join(lsst.utils.getPackageDir("ap_pipe"), "pipelines")

    def test_graph_build(self):
        """Test that each pipeline definition file can be
        used to build a graph.
        """
        files = glob.glob(os.path.join(self.path, "**", "*.yaml"))
        for file in files:
            with self.subTest(file):
                pipeline = lsst.pipe.base.Pipeline.from_uri(file)
                pipeline.addConfigOverride("parameters", "apdb_config", "some/file/path.yaml")
                # If this fails, it will produce a useful error message.
                pipeline.to_graph()

    def test_datasets(self):
        files = glob.glob(os.path.join(self.path, "_ingredients", "*.yaml"))
        for file in files:
            with self.subTest(file):
                expected_inputs = {
                    # ISR
                    "raw", "camera", "crosstalk", "crosstalkSources", "bias", "dark", "flat", "ptc",
                    "fringe", "straylightData", "bfKernel", "newBFKernel", "defects", "linearizer",
                    "opticsTransmission", "filterTransmission", "atmosphereTransmission",
                    "illumMaskedImage", "deferredChargeCalib",
                    # Everything else
                    "skyMap", "gaia_dr3_20230707", "gaia_dr2_20200414", "ps1_pv3_3pi_20170110",
                    "goodSeeingCoadd", "pretrainedModelPackage",
                }
                if "WithFakes" in file:
                    expected_inputs.add("injection_catalog")
                tester = PipelineStepTester(
                    filename=file,
                    step_suffixes=[""],  # Test full pipeline
                    initial_dataset_types=[("ps1_pv3_3pi_20170110", {"htm7"}, "SimpleCatalog", False),
                                           ("gaia_dr2_20200414", {"htm7"}, "SimpleCatalog", False),
                                           ("gaia_dr3_20230707", {"htm7"}, "SimpleCatalog", False),
                                           ],
                    expected_inputs=expected_inputs,
                    # Pipeline outputs highly in flux, don't test
                    expected_outputs=set(),
                    pipeline_patches={"parameters:apdb_config": "some/file/path.yaml",
                                      },
                )
                # Tester modifies Butler registry, so need a fresh repo every time
                with tempfile.TemporaryDirectory() as tempRepo:
                    butler = butlerTests.makeTestRepo(tempRepo)
                    tester.run(butler, self)


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()

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
import itertools
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
        # Each pipeline file should have a subset that represents it in
        # higher-level pipelines.
        self.synonyms = {"ApPipe.yaml": "apPipe",
                         "ApPipeWithIsrTaskLSST.yaml": "apPipe",
                         "ApPipeWithFakes.yaml": "apPipe",
                         "SingleFrame.yaml": "singleFrame",
                         "SingleFrameWithIsrTaskLSST.yaml": "singleFrame",
                         "RunIsrWithoutInterChipCrosstalk.yaml": "runIsr",
                         "RunIsrForCrosstalkSources.yaml": "runOverscan",
                         }

    def test_graph_build(self):
        """Test that each pipeline definition file can be
        used to build a graph.
        """
        files = glob.glob(os.path.join(self.path, "**", "*.yaml"))
        for file in files:
            if "QuickTemplate" in file:
                # Our QuickTemplate definition cannot be tested here because it
                # depends on drp_tasks, which we cannot make a dependency here.
                continue
            with self.subTest(file):
                pipeline = lsst.pipe.base.Pipeline.from_uri(file)
                pipeline.addConfigOverride("parameters", "apdb_config", "some/file/path.yaml")
                # If this fails, it will produce a useful error message.
                pipeline.to_graph()

    def test_datasets(self):
        files = glob.glob(os.path.join(self.path, "_ingredients", "*.yaml"))
        for file in files:
            if "QuickTemplate" in file:
                # Our QuickTemplate definition cannot be tested here because it
                # depends on drp_tasks, which we cannot make a dependency here.
                continue
            with self.subTest(file):
                expected_inputs = {
                    # ISR
                    "raw", "camera", "crosstalk", "crosstalkSources", "bias", "dark", "flat", "ptc",
                    "fringe", "straylightData", "bfKernel", "newBFKernel", "defects", "linearizer",
                    "opticsTransmission", "filterTransmission", "atmosphereTransmission",
                    "illumMaskedImage", "deferredChargeCalib",
                    # ISR-LSST
                    "bfk", "cti", "dnlLUT", "gain_correction",
                    # Everything else
                    "skyMap", "gaia_dr3_20230707", "gaia_dr2_20200414", "ps1_pv3_3pi_20170110",
                    "template_coadd", "pretrainedModelPackage",
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

    def test_whole_subset(self):
        """Test that each pipeline's synonymous subset includes all tasks,
        including those imported from other files.
        """
        files = glob.glob(os.path.join(self.path, "**", "*.yaml"))
        for file in files:
            if "QuickTemplate" in file:
                # Our QuickTemplate definition cannot be tested here because it
                # depends on drp_tasks, which we cannot make a dependency here.
                continue
            with self.subTest(file):
                pipeline = lsst.pipe.base.Pipeline.from_uri(file)
                subset = self.synonyms[os.path.basename(file)]
                self.assertEqual(pipeline.subsets[subset], set(pipeline.task_labels),
                                 msg=f"These tasks are missing from subset '{subset}'.")

    def test_ap_pipe_subsets(self):
        """Test the unique subsets of ApPipe.
        """
        files = glob.glob(os.path.join(self.path, "**", "ApPipe*.yaml"))
        required_subsets = {"preload", "prompt", "afterburner"}
        # getRegionTimeFromVisit is part of no subset besides apPipe. This is a
        # very deliberate exception; see RFC-997.
        no_subset_wanted = {"getRegionTimeFromVisit"}

        for file in files:
            with self.subTest(file):
                pipeline = lsst.pipe.base.Pipeline.from_uri(file)
                # Do all steps exist?
                self.assertGreaterEqual(pipeline.subsets.keys(), required_subsets,
                                        msg="An AP pipeline is missing subsets "
                                            f"{required_subsets - pipeline.subsets.keys()}.")
                # Is each task part of exactly one step?
                for set1, set2 in itertools.product(required_subsets, required_subsets):
                    if set1 == set2:
                        continue
                    tasks1 = pipeline.subsets[set1]
                    tasks2 = pipeline.subsets[set2]
                    self.assertTrue(tasks1.isdisjoint(tasks2),
                                    msg=f"Subsets '{set1}' and '{set2}' share tasks "
                                        f"{tasks1.intersection(tasks2)}.")
                subsetted = set().union(*[pipeline.subsets[s] for s in required_subsets])
                self.assertEqual(subsetted, set(pipeline.task_labels) - no_subset_wanted,
                                 msg=f"These tasks are not in any of the subsets {required_subsets}.")

    def test_inherited_subsets(self):
        """Test that instrument-specific pipelines have all the subsets of their
        generic counterparts.

        Note that this does not check inheritance *within* `_ingredients`!
        """
        files = [f for f in glob.glob(os.path.join(self.path, "**", "*.yaml"))
                 if "_ingredients" not in f]
        for file in files:
            with self.subTest(file):
                generic = os.path.join(self.path, "_ingredients", os.path.basename(file))
                if not os.path.exists(generic):
                    continue
                special_subsets = lsst.pipe.base.Pipeline.from_uri(file).subsets.keys()
                generic_subsets = lsst.pipe.base.Pipeline.from_uri(generic).subsets.keys()
                self.assertGreaterEqual(special_subsets, generic_subsets,
                                        msg="The instrument-specific pipeline is missing subsets "
                                            f"{generic_subsets - special_subsets}.")


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()

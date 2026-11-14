# This file is part of ap_pipe.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import tempfile
import unittest

import yaml

import lsst.utils.tests
from lsst.ap.pipe.cmCampaignToBps import makeBpsConfig, readCampaign, writeBpsConfig

CAMPAIGN = """
kind: campaign
metadata:
  name: test_${{ yesterday | as_day_obs }}
---
kind: node
metadata:
  kind: step
  name: STEP
spec:
  bps:
    pipeline_yaml: "${AP_PIPE_DIR}/pipelines/step.yaml"
---
kind: butler
metadata:
  name: repo
spec:
  repo: embargo
  collections:
    campaign_input:
    - LSSTCam/defaults
    - LSSTCam/runs/prompt-${{ yesterday | as_day_obs }}
    campaign_public_output: "u/test/${{yesterday|as_day_obs}}"
  include_files:
    - "${AP_PIPE_DIR}/a.yaml"
  predicates:
  - instrument='LSSTCam'
  - day_obs=${{ yesterday | as_day_obs }}
---
kind: bps
metadata:
  name: bps
spec:
  pipeline_yaml: "${AP_PIPE_DIR}/pipelines/campaign.yaml"
  extra_qgraph_options:
    - "--skip-existing-in LSSTCam/runs/prompt-${{ yesterday | as_day_obs }}"
    - "--dataset-query-constraint off"
  include_files:
    - "${AP_PIPE_DIR}/a.yaml"
    - "${AP_PIPE_DIR}/b.yaml"
  literals:
    numberOfRetries: 3
---
kind: lsst
metadata:
  name: lsst
spec:
  campaign: Test
  environment:
    SOME_VAR: value
---
kind: wms
metadata:
  name: wms
spec:
  auto_provision: true
  provisioned_extra_arguments:
    - "--exclusive"
---
kind: site
metadata:
  name: site
spec:
  provisioned_account_group: rubin:production
---
kind: schedule
spec:
  expressions:
    yesterday: "datetime.now(timezone.utc) - timedelta(days=1)"
"""


class CmCampaignToBpsTestCase(lsst.utils.tests.TestCase):

    def setUp(self):
        self.documents = list(yaml.safe_load_all(CAMPAIGN))

    def testPayload(self):
        config = makeBpsConfig(self.documents)
        self.assertEqual(config["payload"], {
            "payloadName": "test_{dayObs}",
            "butlerConfig": "embargo",
            "inCollection": "LSSTCam/defaults,LSSTCam/runs/prompt-{dayObs}",
            "output": "u/test/{dayObs}",
            "dataQuery": "instrument='LSSTCam' AND day_obs={dayObs}",
        })
        self.assertEqual(config["extraQgraphOptions"],
                         "--skip-existing-in LSSTCam/runs/prompt-{dayObs} --dataset-query-constraint off")

    def testMerging(self):
        config = makeBpsConfig(self.documents)
        # The step's pipeline overrides the campaign BPS manifest.
        self.assertEqual(config["pipelineYaml"], "${AP_PIPE_DIR}/pipelines/step.yaml")
        self.assertEqual(config["includeConfigs"], ["${AP_PIPE_DIR}/a.yaml", "${AP_PIPE_DIR}/b.yaml"])
        self.assertEqual(config["environment"], {"SOME_VAR": "value"})
        self.assertEqual(config["numberOfRetries"], 3)
        self.assertEqual(config["campaign"], "Test")
        self.assertNotIn("project", config)

    def testProvisioning(self):
        config = makeBpsConfig(self.documents)
        self.assertTrue(config["provisionResources"])
        self.assertEqual(config["provisioning"]["provisioningAccountingUser"], "rubin:production")
        self.assertEqual(config["provisioning"]["provisioningQueue"], "milano")
        self.assertEqual(config["provisioning"]["provisioningExtraOptions"], "--cpu 16 --exclusive")
        self.assertEqual(config["releaseExpr"], "HoldReasonCode >= 6")

    def testDefaultManifest(self):
        extra = {"kind": "lsst", "metadata": {"name": "other"}, "spec": {"campaign": "Other"}}
        with self.assertRaises(ValueError):
            makeBpsConfig(self.documents + [extra])
        extra["metadata"]["default"] = True
        self.assertEqual(makeBpsConfig(self.documents + [extra])["campaign"], "Other")

    def testOneStep(self):
        step = next(doc for doc in self.documents if doc["kind"] == "node")
        with self.assertRaises(ValueError):
            makeBpsConfig(self.documents + [step])

    def testUnsupportedTemplate(self):
        self.documents[0]["metadata"]["name"] = "test_${{ day_obs | random_n(8) }}"
        with self.assertRaises(ValueError):
            makeBpsConfig(self.documents)

    def testRoundTrip(self):
        with tempfile.TemporaryDirectory() as tempDir:
            campaignPath = os.path.join(tempDir, "campaign.yaml")
            bpsPath = os.path.join(tempDir, "bps.yaml")
            with open(campaignPath, "w") as stream:
                stream.write(CAMPAIGN)
            config = makeBpsConfig(readCampaign(campaignPath))
            writeBpsConfig(config, bpsPath, campaignPath)
            with open(bpsPath) as stream:
                self.assertEqual(yaml.safe_load(stream), config)


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()

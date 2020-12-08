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

"""Metrics for ap_pipe tasks.
"""

__all__ = [
    "ApFakesCompletenessMetricTask", "ApFakesCompletenessMetricConfig",
]

import astropy.units as u
import numpy as np

import lsst.pex.config as pexConfig
from lsst.pipe.base import Struct
import lsst.pipe.base.connectionTypes as connTypes
from lsst.pipe.tasks.insertFakes import InsertFakesConfig
from lsst.verify import Measurement, Name
from lsst.verify.tasks import MetricTask, MetricComputationError


class ApFakesCompletenessMetricConnections(
        MetricTask.ConfigClass.ConnectionsClass,
        dimensions={"instrument", "visit", "detector", "band"},
        defaultTemplates={"coaddName": "deep",
                          "fakesType": "",
                          "package": "ap_pipe",
                          "metric": "apFakesCompleteness"}):
    """ApFakesCompleteness connections.
    """
    matchedFakes = connTypes.Input(
        doc="Fakes matched to their detections in the difference image.",
        name="{fakesType}{coaddName}Diff_matchDiaSrc",
        storageClass="DataFrame",
        dimensions=("instrument", "visit", "detector"),
    )


class ApFakesCompletenessMetricConfig(
        MetricTask.ConfigClass,
        InsertFakesConfig,
        pipelineConnections=ApFakesCompletenessMetricConnections):
    """ApFakesCompleteness config.
    """
    magMin = pexConfig.RangeField(
        doc="Minimum magnitude the mag distribution. All magnitudes requested "
            "are set to the same value.",
        dtype=int,
        default=20,
        min=1,
        max=40,
    )
    magMax = pexConfig.RangeField(
        doc="Maximum magnitude the mag distribution. All magnitudes requested "
            "are set to the same value.",
        dtype=int,
        default=30,
        min=1,
        max=40,
    )

    @property
    def metricName(self):
        """The metric calculated by a `MetricTask` with this config
        (`lsst.verify.Name`, read-only).
        """
        return Name(package=self.connections.package,
                    metric=f"{self.connections.metric}Mag{self.magMin}t{self.magMax}")


class ApFakesCompletenessMetricTask(MetricTask):
    """Metric task for summarizing the completeness of fakes inserted into the
    AP pipeline.
    """
    _DefaultName = "apFakesCompleteness"
    ConfigClass = ApFakesCompletenessMetricConfig

    def runQuantum(self, butlerQC, inputRefs, outputRefs):
        inputs = butlerQC.get(inputRefs)
        inputs["band"] = butlerQC.quantum.dataId["band"]

        outputs = self.run(**inputs)
        butlerQC.put(outputs, outputRefs)

    def run(self, matchedFakes, band):
        """Compute the completeness of recovered fakes within a magnitude
        range.

        Parameters
        ----------
        matchedFakes : `lsst.afw.table.SourceCatalog` or `None`
            Catalog of fakes that were inserted into the ccdExposure matched
            to their detected counterparts.

        Returns
        -------
        result : `lsst.pipe.base.Struct`
            A `~lsst.pipe.base.Struct` containing the following component:
            ``measurement``
                the ratio (`lsst.verify.Measurement` or `None`)
        """
        if matchedFakes is not None:
            metricName = \
                f"{self.config.metricName}"
            magnitudes = matchedFakes[f"{self.config.magVar}" % band]
            magCutFakes = matchedFakes[np.logical_and(magnitudes > self.config.magMin,
                                                      magnitudes < self.config.magMax)]
            if len(magCutFakes) <= 0.0:
                raise MetricComputationError(
                    "No matched fakes catalog sources found; Completeness is "
                    "ill defined.")
            else:
                meas = Measurement(
                    metricName,
                    (magCutFakes["diaSourceId"] > 0).sum() / len(magCutFakes) * u.dimensionless_unscaled)
        else:
            self.log.info("Nothing to do: no matched catalog found.")
            meas = None
        return Struct(measurement=meas)

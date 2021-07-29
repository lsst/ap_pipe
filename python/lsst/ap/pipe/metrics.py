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
    "ApFakesCountMetricTask", "ApFakesCountMetricConfig"
]

import astropy.units as u
import numpy as np
import traceback

import lsst.pex.config as pexConfig
from lsst.pipe.base import Struct
import lsst.pipe.base.connectionTypes as connTypes
from lsst.pipe.tasks.insertFakes import InsertFakesConfig
from lsst.verify import Measurement
from lsst.verify.tasks import MetricTask, MetricComputationError


class ApFakesCompletenessMetricConnections(
        MetricTask.ConfigClass.ConnectionsClass,
        dimensions={"instrument", "visit", "detector", "band"},
        defaultTemplates={"coaddName": "deep",
                          "fakesType": "fakes_",
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


# Inherits from InsertFakesConfig to preserve column names in the fakes
# catalog.
class ApFakesCompletenessMetricConfig(
        MetricTask.ConfigClass,
        InsertFakesConfig,
        pipelineConnections=ApFakesCompletenessMetricConnections):
    """ApFakesCompleteness config.
    """
    magMin = pexConfig.RangeField(
        doc="Minimum of cut on magnitude range used to compute completeness "
            "in.",
        dtype=float,
        default=20,
        min=1,
        max=40,
    )
    magMax = pexConfig.RangeField(
        doc="Maximum of cut on magnitude range used to compute completeness "
            "in.",
        dtype=int,
        default=30,
        min=1,
        max=40,
    )


class ApFakesCompletenessMetricTask(MetricTask):
    """Metric task for summarizing the completeness of fakes inserted into the
    AP pipeline.
    """
    _DefaultName = "apFakesCompleteness"
    ConfigClass = ApFakesCompletenessMetricConfig

    def runQuantum(self, butlerQC, inputRefs, outputRefs):
        try:
            inputs = butlerQC.get(inputRefs)
            inputs["band"] = butlerQC.quantum.dataId["band"]
            outputs = self.run(**inputs)
            if outputs.measurement is not None:
                butlerQC.put(outputs, outputRefs)
            else:
                self.log.debugf("Skipping measurement of {!r} on {} "
                                "as not applicable.", self, inputRefs)
        except MetricComputationError:
            # Apparently lsst.log doesn't have built-in exception support?
            self.log.errorf(
                "Measurement of {!r} failed on {}->{}\n{}",
                self, inputRefs, outputRefs, traceback.format_exc())

    def run(self, matchedFakes, band):
        """Compute the completeness of recovered fakes within a magnitude
        range.

        Parameters
        ----------
        matchedFakes : `lsst.afw.table.SourceCatalog` or `None`
            Catalog of fakes that were inserted into the ccdExposure matched
            to their detected counterparts.
        band : `str`
            Single character name of the observed band for this quanta.

        Returns
        -------
        result : `lsst.pipe.base.Struct`
            A `~lsst.pipe.base.Struct` containing the following component:
            ``measurement``
                the ratio (`lsst.verify.Measurement` or `None`)
        """
        if matchedFakes is not None:
            magnitudes = np.fabs(matchedFakes[f"{self.config.mag_col}" % band])
            magCutFakes = matchedFakes[np.logical_and(magnitudes > self.config.magMin,
                                                      magnitudes < self.config.magMax)]
            if len(magCutFakes) <= 0.0:
                raise MetricComputationError(
                    "No matched fakes catalog sources found; Completeness is "
                    "ill defined.")
            else:
                meas = Measurement(
                    self.config.metricName,
                    ((magCutFakes["diaSourceId"] > 0).sum() / len(magCutFakes))
                    * u.dimensionless_unscaled)
        else:
            self.log.info("Nothing to do: no matched catalog found.")
            meas = None
        return Struct(measurement=meas)


class ApFakesCountMetricConnections(
        ApFakesCompletenessMetricConnections,
        dimensions={"instrument", "visit", "detector", "band"},
        defaultTemplates={"coaddName": "deep",
                          "fakesType": "fakes_",
                          "package": "ap_pipe",
                          "metric": "apFakesCompleteness"}):
    pass


class ApFakesCountMetricConfig(
        ApFakesCompletenessMetricConfig,
        pipelineConnections=ApFakesCountMetricConnections):
    """ApFakesCompleteness config.
    """
    pass


class ApFakesCountMetricTask(ApFakesCompletenessMetricTask):
    """Metric task for summarizing the completeness of fakes inserted into the
    AP pipeline.
    """
    _DefaultName = "apFakesCount"
    ConfigClass = ApFakesCountMetricConfig

    def run(self, matchedFakes, band):
        """Compute the number of fakes inserted within a magnitude
        range.

        Parameters
        ----------
        matchedFakes : `lsst.afw.table.SourceCatalog` or `None`
            Catalog of fakes that were inserted into the ccdExposure matched
            to their detected counterparts.
        band : `str`
            Single character name of the observed band for this quanta.

        Returns
        -------
        result : `lsst.pipe.base.Struct`
            A `~lsst.pipe.base.Struct` containing the following component:
            ``measurement``
                the ratio (`lsst.verify.Measurement` or `None`)
        """
        if matchedFakes is not None:
            magnitudes = np.fabs(matchedFakes[f"{self.config.mag_col}" % band])
            magCutFakes = matchedFakes[np.logical_and(magnitudes > self.config.magMin,
                                                      magnitudes < self.config.magMax)]
            meas = Measurement(self.config.metricName,
                               len(magCutFakes) * u.count)
        else:
            self.log.info("Nothing to do: no matched catalog supplied.")
            meas = None
        return Struct(measurement=meas)

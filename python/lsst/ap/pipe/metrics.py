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
    "PipelineTimingMetricTask", "PipelineTimingMetricConfig",
]

import astropy.units as u
from datetime import datetime

import lsst.pex.config as pexConfig
from lsst.pipe.base import Struct, NoWorkFound
import lsst.pipe.base.connectionTypes as connTypes
from lsst.verify import Measurement, Datum
from lsst.verify.tasks import AbstractMetadataMetricTask, MetricTask, MetricComputationError


class PipelineTimingMetricConnections(
        MetricTask.ConfigClass.ConnectionsClass,
        dimensions={"instrument", "visit", "detector"},
        defaultTemplates={"labelStart": "",
                          "labelEnd": "",
                          "package": "ap_pipe",
                          "metric": "ApPipelineTime"}):
    metadataStart = connTypes.Input(
        name="{labelStart}_metadata",
        doc="The starting task's metadata.",
        storageClass="TaskMetadata",
        dimensions={"instrument", "exposure", "detector"},
        multiple=False,
    )
    metadataEnd = connTypes.Input(
        name="{labelEnd}_metadata",
        doc="The final task's metadata.",
        storageClass="TaskMetadata",
        dimensions={"instrument", "visit", "detector"},
        multiple=False,
    )


class PipelineTimingMetricConfig(MetricTask.ConfigClass, pipelineConnections=PipelineTimingMetricConnections):
    # Don't include the dimensions hack that MetadataMetricConfig has; unlike
    # TimingMetricTask, this task is not designed to be run on multiple
    # pipelines.
    targetStart = pexConfig.Field(
        dtype=str,
        doc="The method to take as the starting point of the starting task, "
            "optionally prefixed by one or more task names in the format of "
            "`lsst.pipe.base.Task.getFullMetadata()`.")
    targetEnd = pexConfig.Field(
        dtype=str,
        doc="The method to take as the stopping point of the final task, "
            "optionally prefixed by one or more task names in the format of "
            "`lsst.pipe.base.Task.getFullMetadata()`.")


class PipelineTimingMetricTask(AbstractMetadataMetricTask):
    """A Task that computes a wall-clock time for an entire pipeline, using
    metadata produced by the `lsst.utils.timer.timeMethod` decorator.

    Parameters
    ----------
    args
    kwargs
        Constructor parameters are the same as for
        `lsst.verify.tasks.MetricTask`.
    """

    _DefaultName = "pipelineTimingMetric"
    ConfigClass = PipelineTimingMetricConfig

    @classmethod
    def getInputMetadataKeys(cls, config):
        """Get search strings for the metadata.

        Parameters
        ----------
        config : ``cls.ConfigClass``
            Configuration for this task.

        Returns
        -------
        keys : `dict`
            A dictionary of keys, optionally prefixed by one or more tasks in
            the format of `lsst.pipe.base.Task.getFullMetadata()`.

             ``"StartTimestamp"``
                 The key for an ISO 8601-compliant text string where the target
                 pipeline started (`str`).
             ``"EndTimestamp"``
                 The key for an ISO 8601-compliant text string where the target
                 pipeline ended (`str`).
        """
        return {"StartTimestamp": config.targetStart + "StartUtc",
                "EndTimestamp": config.targetEnd + "EndUtc",
                }

    def run(self, metadataStart, metadataEnd):
        """Compute the pipeline wall-clock time from science task metadata.

        Parameters
        ----------
        metadataStart : `lsst.pipe.base.TaskMetadata`
            A metadata object for the first quantum run by the pipeline.
        metadataEnd : `lsst.pipe.base.TaskMetadata`
            A metadata object for the last quantum run by the pipeline.

        Returns
        -------
        result : `lsst.pipe.base.Struct`
            A `~lsst.pipe.base.Struct` containing the following component:

            - ``measurement``: the value of the metric
              (`lsst.verify.Measurement` or `None`)

        Raises
        ------
        lsst.verify.tasks.MetricComputationError
            Raised if the strings returned by `getInputMetadataKeys` match
            more than one key in either metadata object.
        lsst.pipe.base.NoWorkFound
            Raised if the metric is ill-defined. Typically this means that at
            least one pipeline step was not run.
        """
        metadataKeys = self.getInputMetadataKeys(self.config)
        timingsStart = self.extractMetadata(metadataStart, metadataKeys)
        timingsEnd = self.extractMetadata(metadataEnd, metadataKeys)

        if timingsStart["StartTimestamp"] is None:
            raise NoWorkFound(f"Nothing to do: no timing information for {self.config.targetStart} found.")
        if timingsEnd["EndTimestamp"] is None:
            raise NoWorkFound(f"Nothing to do: no timing information for {self.config.targetEnd} found.")

        try:
            startTime = datetime.fromisoformat(timingsStart["StartTimestamp"])
            endTime = datetime.fromisoformat(timingsEnd["EndTimestamp"])
        except (TypeError, ValueError) as e:
            raise MetricComputationError("Invalid metadata") from e
        else:
            totalTime = (endTime - startTime).total_seconds()
            meas = Measurement(self.config.metricName, totalTime * u.second)
            meas.notes["estimator"] = "utils.timer.timeMethod"
            meas.extras["start"] = Datum(timingsStart["StartTimestamp"])
            meas.extras["end"] = Datum(timingsEnd["EndTimestamp"])
            return Struct(measurement=meas)

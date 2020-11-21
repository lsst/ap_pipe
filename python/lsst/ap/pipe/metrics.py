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

__all__ = [
    "ApFakesCompletenessMetricTask", "ApFakesCompletenessMetricConfig",
]


from lsst.pipe.tasks.insertFakes import InsertFakesConfig
from lsst.verify.tasks import MetricTask, MetricConfig, MetricConnections, \
    MetricComputationError


class ApFakesCompletenessMetricConnections(
        MetricTask.ConfigClass.ConnectionsClass,
        dimensions={"instrument", "visit", "detector", "band"},
        defaultTemplates={"coaddName": "deep",
                          "fakesType": "",
                          "package": "ap_pipe",
                          "metric": "apFakesCompleteness"}):
    """
    """
    matchedFakes = connectionTypes.Input(
        doc="Fakes matched to their detections in the difference image.",
        name="{fakesType}{CoaddName}Diff_matchDiaSrc",
        storageClass="DataFrame",
        dimensions=("instrument", "visit", "detector"),
    )


class ApFakesCompletenessMetricConfig(
        MetricTask.ConfigClass,
        InsertFakesConfig,
        pipelineConnections=ApFakesCompletenessMetricConnections):
    """
    """
    magMin = pexConfig.RangeField(
        doc="Minimum magnitude the mag distribution. All magnitudes requested "
            "are set to the same value.",
        dtype=float,
        default=20,
        min=1,
        max=40,
    )
    magMax = pexConfig.RangeField(
        doc="Maximum magnitude the mag distribution. All magnitudes requested "
            "are set to the same value.",
        dtype=float,
        default=30,
        min=1,
        max=40,
    )


class ApFakesCompletenessMetricTask(MetricTask):
    """
    """
    _DefaultName = "apFakesCompleteness"
    ConfigClass = ApFakesCompletenessMetricConfig

    def run(self, matchedFakes):
        """Compute the completeness of recovered fakes within a magnitude
        range..

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
            filterName = matchedFakes["filterName"][matchedFakes["diaSourceId"] > 0].unique()[0]
            metricName = \
                f"{self.config.metricName}{filterName}{self.config.magMin:.1f}t{self.config.magMin:.1f}"
            magnitudes = mmatchedFakes[f"{filterName}{self.config.magVar}"]
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

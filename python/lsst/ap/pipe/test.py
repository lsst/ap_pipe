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

import lsst.pex.config as pexConfig
from lsst.pipe.base import PipelineTask, PipelineTaskConfig, PipelineTaskConnections, Struct, \
    NoWorkFound, connectionTypes

__all__ = ["InitOnlyTask"]


class InitOnlyConnections(PipelineTaskConnections, dimensions={}):
    dummy = connectionTypes.InitOutput(
        doc="This is a simulation of a config-writing task.",
        name="dummy",
        storageClass="Config",
    )

    def adjustQuantum(self, _inputs, _outputs, _label, _dataId):
        raise NoWorkFound("This task does no work after init.")


class InitOnlyConfig(PipelineTaskConfig, pipelineConnections=InitOnlyConnections):
    pass


class InitOnlyTask(PipelineTask):
    _DefaultName = "init_only"
    ConfigClass = InitOnlyConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log.info("RUNNING INIT-ONLY TASK")
        self.dummy = pexConfig.Config()

    def runQuantum(self, _butlerQC, _inputRefs, _outputRefs):
        raise AssertionError("This task does no work after init.")

    def run(self):
        return Struct()

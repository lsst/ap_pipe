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

from __future__ import absolute_import, division, print_function

__all__ = ['ApPipeTaskRunner']

import os
import sys
import traceback

import lsst.log
import lsst.pipe.base as pipeBase


class ApPipeTaskRunner(pipeBase.ButlerInitializedTaskRunner):

    def makeTask(self, parsedCmd=None, args=None):
        """Construct an ApPipeTask with both a Butler and a database.

        Parameters
        ----------
        parsedCmd : `argparse.Namespace`
            Parsed command-line options, as returned by the `~lsst.pipe.base.ArgumentParser`; if specified
            then args is ignored.
        args
            Args tuple passed to `TaskRunner.__call__`. First argument must be
            a path to the database file and second argument must be a dataref.

        Raises
        ------
        RuntimeError
            Raised if ``parsedCmd`` and ``args`` are both `None`.
        """
        if parsedCmd is not None:
            butler = parsedCmd.butler
            dbFile = os.path.join(parsedCmd.output, 'association.db')
        elif args is not None:
            dbFile, dataRef, _ = args
            butler = dataRef.butlerSubset.butler
        else:
            raise RuntimeError('parsedCmd or args must be specified')
        return self.TaskClass(config=self.config, log=self.log, butler=butler, dbFile=dbFile)

    @staticmethod
    def getTargetList(parsedCmd, **kwargs):
        """Get a list of (dbFile, rawRef, calexpRef, kwargs) for `TaskRunner.__call__`.
        """
        # Hack to allow makeTask(args). Remove once DM-11767 (or possibly DM-13672) resolved
        dbFile = os.path.join(parsedCmd.output, 'association.db')
        argDict = dict(
            templateIds = parsedCmd.templateId.idList,
            reuse = parsedCmd.reuse,
            **kwargs
        )
        butler = parsedCmd.butler
        return [(dbFile,
                 butler.dataRef('raw', **dataId),
                 dict(calexpRef=butler.dataRef('calexp', **dataId), **argDict))
                for dataId in parsedCmd.id.idList]

    # TODO: workaround for DM-11767 or DM-13672; can remove once ApPipeTask.__init__ no longer needs dbFile
    # TODO: find a way to pass the DB argument that doesn't require duplicating TaskRunner.__call__
    def __call__(self, args):
        """Run the Task on a single target.

        Parameters
        ----------
        args
            A path to the database file, followed by arguments for Task.run().

        Returns
        -------
        struct : `lsst.pipe.base.Struct`
            Contains these fields if ``doReturnResults`` is `True`:

            - ``dataRef``: the provided data reference.
            - ``metadata``: task metadata after execution of run.
            - ``result``: result returned by task run, or `None` if the task fails.
            - ``exitStatus`: 0 if the task completed successfully, 1 otherwise.

            If ``doReturnResults`` is `False` the struct contains:

            - ``exitStatus`: 0 if the task completed successfully, 1 otherwise.
        """
        _, dataRef, kwargs = args
        if self.log is None:
            self.log = lsst.log.Log.getDefaultLogger()
        if hasattr(dataRef, "dataId"):
            self.log.MDC("LABEL", str(dataRef.dataId))
        elif isinstance(dataRef, (list, tuple)):
            self.log.MDC("LABEL", str([ref.dataId for ref in dataRef if hasattr(ref, "dataId")]))
        task = self.makeTask(args=args)
        result = None                   # in case the task fails
        exitStatus = 0                  # exit status for the shell
        if self.doRaise:
            result = task.run(dataRef, **kwargs)
        else:
            try:
                result = task.run(dataRef, **kwargs)
            except Exception as e:
                # The shell exit value will be the number of dataRefs returning
                # non-zero, so the actual value used here is lost.
                exitStatus = 1

                # don't use a try block as we need to preserve the original exception
                eName = type(e).__name__
                if hasattr(dataRef, "dataId"):
                    task.log.fatal("Failed on dataId=%s: %s: %s", dataRef.dataId, eName, e)
                elif isinstance(dataRef, (list, tuple)):
                    task.log.fatal("Failed on dataIds=[%s]: %s: %s",
                                   ", ".join(str(ref.dataId) for ref in dataRef), eName, e)
                else:
                    task.log.fatal("Failed on dataRef=%s: %s: %s", dataRef, eName, e)

                if not isinstance(e, pipeBase.TaskError):
                    traceback.print_exc(file=sys.stderr)
        task.writeMetadata(dataRef)

        # remove MDC so it does not show up outside of task context
        self.log.MDCRemove("LABEL")

        if self.doReturnResults:
            return pipeBase.Struct(
                exitStatus=exitStatus,
                dataRef=dataRef,
                metadata=task.metadata,
                result=result,
            )
        else:
            return pipeBase.Struct(
                exitStatus=exitStatus,
            )

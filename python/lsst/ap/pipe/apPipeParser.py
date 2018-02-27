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
# salong with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import absolute_import, division, print_function

__all__ = ['ApPipeParser']

import argparse
import fnmatch
import os
import re
import shutil
import sys

import lsst.log as lsstLog
import lsst.pex.config as pexConfig
import lsst.daf.persistence as dafPersist
import lsst.pipe.base as pipeBase

DEFAULT_INPUT_NAME = "PIPE_INPUT_ROOT"
DEFAULT_CALIB_NAME = "PIPE_CALIB_ROOT"
DEFAULT_OUTPUT_NAME = "PIPE_OUTPUT_ROOT"


class ApPipeParser(pipeBase.ArgumentParser):
    """Custom argument parser to handle multiple input repos.
    """

    def __init__(self, *args, **kwargs):
        pipeBase.ArgumentParser.__init__(
            self,
            description='Process raw decam images with MasterCals '
                        'from basic processing --> source association',
            *args,
            **kwargs)
        inputDataset = 'raw'
        self.add_id_argument("--id", inputDataset,
                             help="data IDs, e.g. --id visit=12345 ccd=1,2^0,3")

        self.add_argument('--template', dest='rawTemplate',
                          help="path to input template repository, relative to $%s" % DEFAULT_INPUT_NAME)
        self.add_id_argument("--templateId", inputDataset, doMakeDataRefList=True,
                             help="Optional template data ID (visit only), e.g. --templateId visit=410929")

        self.add_argument('--skip', action='store_true',
                          help="Skip pipeline steps that have already been started. "
                          "Only useful if --clobber-output not used.")

    # TODO: workaround for lack of support for multi-input butlers; see DM-11865
    # Can't delegate to pipeBase.ArgumentParser.parse_args because creating the
    # Butler more than once causes repo conflicts
    def parse_args(self, config, args=None, log=None, override=None):
        """Parse arguments for a command-line task.

        Parameters
        ----------
        config : `lsst.pex.config.Config`
            Config for the task being run.
        args : `list`, optional
            Argument list; if `None` then ``sys.argv[1:]`` is used.
        log : `lsst.log.Log`, optional
            `~lsst.log.Log` instance; if `None` use the default log.
        override : callable, optional
            A config override function. It must take the root config object as its only argument and must
            modify the config in place. This function is called after camera-specific overrides files are
            applied, and before command-line config overrides are applied (thus allowing the user the final
            word).

        Returns
        -------
        namespace : `argparse.Namespace`
            A `~argparse.Namespace` instance containing fields:

            - ``camera``: camera name.
            - ``config``: the supplied config with all overrides applied, validated and frozen.
            - ``butler``: a `lsst.daf.persistence.Butler` for the data.
            - An entry for each of the data ID arguments registered by `add_id_argument`,
              the value of which is a `~lsst.pipe.base.DataIdArgument` that includes public elements
              ``idList`` and ``refList``.
            - ``log``: a `lsst.log` Log.
            - An entry for each command-line argument, with the following exceptions:
              - config is the supplied config, suitably updated.
              - configfile, id and loglevel are all missing.
            - ``obsPkg``: name of the ``obs_`` package for this camera.
        """
        if args is None:
            args = sys.argv[1:]

        if len(args) < 1 or args[0].startswith("-") or args[0].startswith("@"):
            self.print_help()
            if len(args) == 1 and args[0] in ("-h", "--help"):
                self.exit()
            else:
                self.exit("%s: error: Must specify input as first argument" % self.prog)

        # Note that --rerun may change namespace.input, but if it does we verify that the
        # new input has the same mapper class.
        namespace = argparse.Namespace()
        namespace.input = _fixPath(DEFAULT_INPUT_NAME, args[0])
        if not os.path.isdir(namespace.input):
            self.error("Error: input=%r not found" % (namespace.input,))

        namespace.config = config
        namespace.log = log if log is not None else lsstLog.Log.getDefaultLogger()
        mapperClass = dafPersist.Butler.getMapperClass(namespace.input)
        namespace.camera = mapperClass.getCameraName()
        namespace.obsPkg = mapperClass.getPackageName()

        self.handleCamera(namespace)

        self._applyInitialOverrides(namespace)
        if override is not None:
            override(namespace.config)

        # Add data ID containers to namespace
        for dataIdArgument in self._dataIdArgDict.values():
            setattr(namespace, dataIdArgument.name, dataIdArgument.ContainerClass(level=dataIdArgument.level))

        namespace = argparse.ArgumentParser.parse_args(self, args=args, namespace=namespace)
        del namespace.configfile

        self._parseDirectories(namespace)
        namespace.template = _fixPath(DEFAULT_INPUT_NAME, namespace.rawTemplate)
        del namespace.rawTemplate

        if namespace.clobberOutput:
            if namespace.output is None:
                self.error("--clobber-output is only valid with --output or --rerun")
            elif namespace.output == namespace.input:
                self.error("--clobber-output is not valid when the output and input repos are the same")
            if os.path.exists(namespace.output):
                namespace.log.info("Removing output repo %s for --clobber-output", namespace.output)
                shutil.rmtree(namespace.output)

        namespace.log.debug("input=%s", namespace.input)
        namespace.log.debug("calib=%s", namespace.calib)
        namespace.log.debug("output=%s", namespace.output)
        namespace.log.debug("template=%s", namespace.template)

        obeyShowArgument(namespace.show, namespace.config, exit=False)

        # No environment variable or --output or --rerun specified.
        if self.requireOutput and namespace.output is None and namespace.rerun is None:
            self.error("no output directory specified.\n"
                       "An output directory must be specified with the --output or --rerun\n"
                       "command-line arguments.\n")

        self._makeButler(namespace)

        # convert data in each of the identifier lists to proper types
        # this is done after constructing the butler, hence after parsing the command line,
        # because it takes a long time to construct a butler
        self._processDataIds(namespace)
        if "data" in namespace.show:
            for dataIdName in self._dataIdArgDict.keys():
                for dataRef in getattr(namespace, dataIdName).refList:
                    print("%s dataRef.dataId = %s" % (dataIdName, dataRef.dataId))

        if namespace.show and "run" not in namespace.show:
            sys.exit(0)

        if namespace.debug:
            try:
                import debug
                assert debug  # silence pyflakes
            except ImportError:
                sys.stderr.write("Warning: no 'debug' module found\n")
                namespace.debug = False

        del namespace.loglevel

        if namespace.longlog:
            lsstLog.configure_prop("""
log4j.rootLogger=INFO, A1
log4j.appender.A1=ConsoleAppender
log4j.appender.A1.Target=System.out
log4j.appender.A1.layout=PatternLayout
log4j.appender.A1.layout.ConversionPattern=%-5p %d{yyyy-MM-ddThh:mm:ss.sss} %c (%X{LABEL})(%F:%L)- %m%n
""")
        del namespace.longlog

        namespace.config.validate()
        namespace.config.freeze()

        return namespace

    def _makeButler(self, namespace):
        """Create a butler according to parsed command line arguments.

        The butler is stored as ``namespace.butler``.

        Parameters
        ----------
        namespace : `argparse.Namespace`
            a parsed command line containing all information needed to set up a new butler.
        """
        butlerArgs = {}  # common arguments for butler elements
        if namespace.calib:
            butlerArgs = {'mapperArgs': {'calibRoot': namespace.calib}}

        if namespace.output:
            inputs = [{'root': namespace.input}]
            outputs = [{'root': namespace.output, 'mode': 'rw'}]
        else:
            inputs = [{'root': namespace.input, 'mode': 'rw'}]
            outputs = []

        if namespace.template:
            ApPipeParser._addRepo(inputs, {'root': namespace.template, 'mode': 'r'})

        for repoList in inputs, outputs:
            for repo in repoList:
                repo.update(butlerArgs)

        if namespace.output:
            namespace.butler = dafPersist.Butler(inputs=inputs, outputs=outputs)
        else:
            namespace.butler = dafPersist.Butler(outputs=inputs)

    @staticmethod
    def _addRepo(repos, newRepo):
        """Add an extra repository to a collection.

        ``newRepo`` will be updated, possibly after validity checks.

        Parameters
        ----------
        repos : `iterable` of `dict`
            The collection of repositories to update. Each element must be a
            valid input or output argument to an `lsst.daf.persistence.Butler`.
        newRepo : `dict`
            The repository to add.
        """
        # workaround for DM-13626, blocks DM-11482
        duplicate = False
        for repo in repos:
            if os.path.samefile(repo['root'], newRepo['root']):
                duplicate = True

        if not duplicate:
            repos.append(newRepo)


# TODO: duplicated code; can remove once DM-11865 resolved
def _fixPath(defName, path):
    """Apply environment variable as default root, if present, and abspath.

    Parameters
    ----------
    defName : `str`
        Name of environment variable containing default root path; if the
        environment variable does not exist then the path is relative to
        the current working directory
    path : `str`
        Path relative to default root path.

    Returns
    -------
    abspath : `str`
        Path that has been expanded, or `None` if the environment variable
        does not exist and path is `None`.
    """
    defRoot = os.environ.get(defName)
    if defRoot is None:
        if path is None:
            return None
        return os.path.abspath(path)
    return os.path.abspath(os.path.join(defRoot, path or ""))


# TODO: duplicated code; can remove once DM-11865 resolved
def obeyShowArgument(showOpts, config=None, exit=False):
    """Process arguments specified with ``--show`` (but ignores ``"data"``).

    Parameters
    ----------
    showOpts : `list` of `str`
        List of options passed to ``--show``.
    config : optional
        The provided config.
    exit : bool, optional
        Exit if ``"run"`` isn't included in ``showOpts``.

    Parameters
    ----------
    Supports the following options in showOpts:

    - ``config[=PAT]``. Dump all the config entries, or just the ones that match the glob pattern.
    - ``history=PAT``. Show where the config entries that match the glob pattern were set.
    - ``tasks``. Show task hierarchy.
    - ``data``. Ignored; to be processed by caller.
    - ``run``. Keep going (the default behaviour is to exit if --show is specified).

    Calls ``sys.exit(1)`` if any other option found.
    """
    if not showOpts:
        return

    for what in showOpts:
        showCommand, showArgs = what.split("=", 1) if "=" in what else (what, "")

        if showCommand == "config":
            matConfig = re.search(r"^(?:config.)?(.+)?", showArgs)
            pattern = matConfig.group(1)
            if pattern:
                class FilteredStream(object):
                    """A file object that only prints lines that match the glob "pattern"

                    N.b. Newlines are silently discarded and reinserted;  crude but effective.
                    """

                    def __init__(self, pattern):
                        # obey case if pattern isn't lowecase or requests NOIGNORECASE
                        mat = re.search(r"(.*):NOIGNORECASE$", pattern)

                        if mat:
                            pattern = mat.group(1)
                            self._pattern = re.compile(fnmatch.translate(pattern))
                        else:
                            if pattern != pattern.lower():
                                print(u"Matching \"%s\" without regard to case "
                                      "(append :NOIGNORECASE to prevent this)" % (pattern,), file=sys.stdout)
                            self._pattern = re.compile(fnmatch.translate(pattern), re.IGNORECASE)

                    def write(self, showStr):
                        showStr = showStr.rstrip()
                        # Strip off doc string line(s) and cut off at "=" for string matching
                        matchStr = showStr.split("\n")[-1].split("=")[0]
                        if self._pattern.search(matchStr):
                            print(u"\n" + showStr)

                fd = FilteredStream(pattern)
            else:
                fd = sys.stdout

            config.saveToStream(fd, "config")
        elif showCommand == "history":
            matHistory = re.search(r"^(?:config.)?(.+)?", showArgs)
            pattern = matHistory.group(1)
            if not pattern:
                print("Please provide a value with --show history (e.g. history=XXX)", file=sys.stderr)
                sys.exit(1)

            pattern = pattern.split(".")
            cpath, cname = pattern[:-1], pattern[-1]
            hconfig = config            # the config that we're interested in
            for i, cpt in enumerate(cpath):
                try:
                    hconfig = getattr(hconfig, cpt)
                except AttributeError:
                    print("Error: configuration %s has no subconfig %s" %
                          (".".join(["config"] + cpath[:i]), cpt), file=sys.stderr)

                    sys.exit(1)

            try:
                print(pexConfig.history.format(hconfig, cname))
            except KeyError:
                print("Error: %s has no field %s" % (".".join(["config"] + cpath), cname), file=sys.stderr)
                sys.exit(1)

        elif showCommand == "data":
            pass
        elif showCommand == "run":
            pass
        elif showCommand == "tasks":
            showTaskHierarchy(config)
        else:
            print(u"Unknown value for show: %s (choose from '%s')" %
                  (what, "', '".join("config[=XXX] data history=XXX tasks run".split())), file=sys.stderr)
            sys.exit(1)

    if exit and "run" not in showOpts:
        sys.exit(0)


def showTaskHierarchy(config):
    """Print task hierarchy to stdout.

    Parameters
    ----------
    config : `lsst.pex.config.Config`
        Configuration to process.
    """
    print(u"Subtasks:")
    taskDict = getTaskDict(config=config)

    fieldNameList = sorted(taskDict.keys())
    for fieldName in fieldNameList:
        taskName = taskDict[fieldName]
        print(u"%s: %s" % (fieldName, taskName))


def getTaskDict(config, taskDict=None, baseName=""):
    """Get a dictionary of task info for all subtasks in a config

    Parameters
    ----------
    config : `lsst.pex.config.Config`
        Configuration to process.
    taskDict : `dict`, optional
        Users should not specify this argument. Supports recursion; if provided, taskDict is updated in
        place, else a new `dict` is started).
    baseName : `str`, optional
        Users should not specify this argument. It is only used for recursion: if a non-empty string then a
        period is appended and the result is used as a prefix for additional entries in taskDict; otherwise
        no prefix is used.

    Returns
    -------
    taskDict : `dict`
        Keys are config field names, values are task names.

    Notes
    -----
    This function is designed to be called recursively. The user should call with only a config
    (leaving taskDict and baseName at their default values).
    """
    if taskDict is None:
        taskDict = dict()
    for fieldName, field in config.items():
        if hasattr(field, "value") and hasattr(field, "target"):
            subConfig = field.value
            if isinstance(subConfig, pexConfig.Config):
                subBaseName = "%s.%s" % (baseName, fieldName) if baseName else fieldName
                try:
                    taskName = "%s.%s" % (field.target.__module__, field.target.__name__)
                except Exception:
                    taskName = repr(field.target)
                taskDict[subBaseName] = taskName
                getTaskDict(config=subConfig, taskDict=taskDict, baseName=subBaseName)
    return taskDict

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

__all__ = ["makeApdb"]

import argparse

import lsst.dax.apdb as daxApdb
from lsst.pipe.base.configOverrides import ConfigOverrides
from lsst.ap.association import DiaPipelineConfig


class ConfigOnlyParser(argparse.ArgumentParser):
    """Argument parser that knows standard config arguments.
    """

    def __init__(self, description=None, **kwargs):
        if description is None:
            # Description must be readable in both Sphinx and make_apdb.py -h
            description = """\
Create a Alert Production Database using config overrides for
`lsst.dax.apdb.ApdbConfig`.

This script takes the same ``--config`` and ``--config-file`` arguments as
pipeline runs. However, the configs are at a lower level than the AP pipeline.

The config overrides must define ``db_url`` to create a valid config.
"""

        super().__init__(description=description, **kwargs)

        self.add_argument("-c", "--config", nargs="*", action=ConfigValueAction,
                          help="config override(s), e.g. "
                               "``-c prefix=fancy db_url=\"sqlite://\"``",
                          metavar="NAME=VALUE")
        self.add_argument("-C", "--config-file", dest="configfile", nargs="*", action=ConfigFileAction,
                          help="config override file(s) for ApdbConfig")

    def parse_args(self, args=None, namespace=None):
        """Parse arguments for an `ApdbConfig`.

        Parameters
        ----------
        args : `list` [`str`], optional
            Argument list; if `None` then ``sys.argv`` is used.
        namespace : `argparse.Namespace`, optional
            An object to take the attributes. The default is a new empty
            `~argparse.Namespace` object

        Returns
        -------
        namespace : `argparse.Namespace`
            A `~argparse.Namespace` instance containing fields:
            - ``config``: the supplied config with all overrides applied,
                validated and frozen.
        """
        if not namespace:
            namespace = argparse.Namespace()
        namespace.overrides = ConfigOverrides()

        # ConfigFileAction and ConfigValueAction require namespace.overrides to exist
        namespace = super().parse_args(args, namespace)
        del namespace.configfile
        # Make ApdbConfig as a subconfig of DiaPipelineConfig to ensure correct defaults get set
        namespace.config = DiaPipelineConfig().apdb.value
        try:
            namespace.overrides.applyTo(namespace.config)
        except Exception as e:  # yes, configs really can raise anything
            message = str(e)
            if "diaPipe" in message:
                message = "it looks like one of the config files uses ApPipeConfig; " \
                    "try dropping 'diaPipe.apdb'\n" + message
            self.error(f"cannot apply config: {message}")

        namespace.config.validate()
        namespace.config.freeze()

        return namespace


def makeApdb(args=None):
    """Create an APDB according to a config.

    The command-line arguments should provide config values or a config file
    for `ApdbConfig`.

    Parameters
    ----------
    args : `list` [`str`], optional
        List of command-line arguments; if `None` use `sys.argv`.

    Returns
    -------
    apdb : `lsst.dax.apdb.Apdb`
        The newly configured APDB object.
    """

    parser = ConfigOnlyParser()
    parsedCmd = parser.parse_args(args=args)

    apdb = daxApdb.make_apdb(config=parsedCmd.config)
    apdb.makeSchema()
    return apdb


# --------------------------------------------------------------------
# argparse.Actions for use with ConfigOverrides
# ConfigOverrides is normally used with Click; there is no built-in
# argparse support.


class ConfigValueAction(argparse.Action):
    """argparse action to override config parameters using
    name=value pairs from the command-line.
    """

    def __call__(self, parser, namespace, values, option_string):
        if namespace.overrides is None:
            return
        for nameValue in values:
            name, sep, valueStr = nameValue.partition("=")
            if not valueStr:
                parser.error(f"{option_string} value {nameValue} must be in form name=value")
            if "diaPipe.apdb" in name:
                parser.error(f"{nameValue} looks like it uses ApPipeConfig; try dropping 'diaPipe.apdb'")

            namespace.overrides.addValueOverride(name, valueStr)


class ConfigFileAction(argparse.Action):
    """argparse action to load config overrides from one or more files.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        if namespace.overrides is None:
            return
        for configfile in values:
            namespace.overrides.addFileOverride(configfile)

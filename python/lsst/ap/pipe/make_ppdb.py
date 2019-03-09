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

__all__ = ["makePpdb"]

import argparse

from lsst.pipe.base import ConfigFileAction, ConfigValueAction
from lsst.ap.association import make_dia_object_schema, make_dia_source_schema

from .ap_pipe import ApPipeConfig


class ConfigOnlyParser(argparse.ArgumentParser):
    """Argument parser that knows standard config arguments.
    """

    def __init__(self, description=None, **kwargs):
        if description is None:
            description = "Create a PPDB using config overrides. At the very " \
                "least, the overrides must define ppdb.db_url, or the final " \
                "config will not be valid."

        super().__init__(description=description, **kwargs)

        self.add_argument("-c", "--config", nargs="*", action=ConfigValueAction,
                          help="config override(s), e.g. -c foo=newfoo bar.baz=3", metavar="NAME=VALUE")
        self.add_argument("-C", "--configfile", dest="configfile", nargs="*", action=ConfigFileAction,
                          help="config override file(s)")

    def parse_args(self, args=None, namespace=None):
        """Parse arguments for an `ApPipeConfig`.

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
        namespace.config = ApPipeConfig()

        # ConfigFileAction and ConfigValueAction require namespace.config to exist
        namespace = super().parse_args(args, namespace)
        del namespace.configfile

        namespace.config.validate()
        namespace.config.freeze()

        return namespace


def makePpdb(args=None):
    """Create a PPDB according to a config.

    The command-line arguments should provide config values or a config file
    for `ApPipeConfig`.

    Parameters
    ----------
    args : `list` [`str`], optional
        List of command-line arguments; if `None` use `sys.argv`.

    Returns
    -------
    ppdb : `lsst.dax.ppdb.Ppdb`
        The newly configured PPDB object.
    """

    parser = ConfigOnlyParser()
    parsedCmd = parser.parse_args(args=args)

    ppdb = parsedCmd.config.ppdb.apply(
        afw_schemas=dict(DiaObject=make_dia_object_schema(),
                         DiaSource=make_dia_source_schema()))
    ppdb.makeSchema()
    return ppdb

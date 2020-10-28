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

import shlex
import unittest

import lsst.utils.tests
from lsst.ap.pipe.make_apdb import ConfigOnlyParser


class MakeApdbParserTestSuite(lsst.utils.tests.TestCase):

    def _parseString(self, commandLine):
        """Tokenize and parse a command line string.

        Parameters
        ----------
        commandLine : `str`
            a string containing Unix-style command line arguments, but not the
            name of the program

        Returns
        -------
        parsed : `argparse.Namespace`
            The parsed command line.
        """
        return self.parser.parse_args(shlex.split(commandLine))

    def setUp(self):
        self.parser = ConfigOnlyParser()

    def testExtras(self):
        """Verify that a command line containing extra arguments is rejected.
        """
        args = '-c db_url="dummy" --id visit=42'
        with self.assertRaises(SystemExit):
            self._parseString(args)

    def testSetValue(self):
        """Verify that command-line arguments get propagated.
        """
        args = '-c db_url="dummy" -c dia_object_index=pix_id_iov'
        parsed = self._parseString(args)
        self.assertEqual(parsed.config.db_url, 'dummy')
        self.assertEqual(parsed.config.dia_object_index, 'pix_id_iov')

    def testSetValueFile(self):
        """Verify that config files are handled correctly.
        """
        with lsst.utils.tests.getTempFilePath(ext=".py") as configFile:
            with open(configFile, mode='wt') as config:
                config.write('config.db_url = "dummy"\n')
                config.write('config.dia_object_index = "pix_id_iov"\n')

            args = f"-C {configFile}"
            parsed = self._parseString(args)

        self.assertEqual(parsed.config.db_url, 'dummy')
        self.assertEqual(parsed.config.dia_object_index, 'pix_id_iov')


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()

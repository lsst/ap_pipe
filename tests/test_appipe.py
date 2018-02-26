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
import unittest
import lsst.utils.tests
import lsst.ap.pipe as ap_pipe


class PipelineTestSuite(lsst.utils.tests.TestCase):
    '''
    A set of tests for the functions in ap_pipe.

    TODO: write more tests for DM-11422.
    '''

    INGESTED_DIR = 'ingested'
    CALIBINGESTED_DIR = 'calibingested'
    PROCESSED_DIR = 'processed'
    DIFFIM_DIR = 'diffim'

    def testGetOutputRepos(self):
        '''
        Test that the output repos are constructed properly
        '''
        self.assertEqual(ap_pipe.get_output_repo('.', self.INGESTED_DIR), './ingested')
        self.assertEqual(ap_pipe.get_output_repo('.', self.CALIBINGESTED_DIR), './calibingested')
        self.assertEqual(ap_pipe.get_output_repo('.', self.PROCESSED_DIR), './processed')
        self.assertEqual(ap_pipe.get_output_repo('.', self.DIFFIM_DIR), './diffim')

#    def testDoIngest(self):
        # test something

#    def testDoIngestCalibs(self):
        # test something

#    def testDoProcessCcd(self):
        # test something

#    def testDoDiffIm(self):
        # test something


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()

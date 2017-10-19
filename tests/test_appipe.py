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

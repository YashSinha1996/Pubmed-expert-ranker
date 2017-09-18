"""Test suite for mscanner.utils

@copyright: 2007 Graham Poulter

@license: This source file is free software. It comes without any warranty, to
the extent permitted by applicable law. You can redistribute it and/or modify
it under the Do Whatever You Want Public License. Terms and conditions: 
   0. Do Whatever You Want
"""

import logging
import unittest
from mscanner import tests
from mscanner.core import iofuncs

class IOTests(unittest.TestCase):
    
    @tests.usetempfile
    def test_read_pmids(self, fn):
        allpairs = [(10.0,1), (20.0,2), (30.0,3), (40.0,4), (50.0,5)]
        fn.write_lines(["# comment", "1 10", "2 20 blah", "3 30", "4 40", "5 50"])
        includes = [1,2,3,4]
        excludes = [1]
        pmids, broke, excl  = iofuncs.read_pmids_careful(fn, includes, excludes)
        self.assertEqual(list(pmids), [2,3,4])
        self.assertEqual(list(broke), [5])
        self.assertEqual(list(excl), [1])
        pairs = list(iofuncs.read_scores(fn))
        self.assertEqual(pairs, allpairs)


if __name__ == "__main__":
    unittest.main()
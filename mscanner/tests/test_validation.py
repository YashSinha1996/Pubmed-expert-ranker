"""Test suite for mscanner.validation

@copyright: 2007 Graham Poulter

@license: This source file is free software. It comes without any warranty, to
the extent permitted by applicable law. You can redistribute it and/or modify
it under the Do Whatever You Want Public License. Terms and conditions: 
   0. Do Whatever You Want
"""

import logging
import numpy as nx
from path import path
import pprint as pp
import tempfile
import unittest

from mscanner.core.FeatureScores import FeatureScores
from mscanner.core.Validator import LeaveOutValidator, CrossValidator
from mscanner.core.metrics import PerformanceVectors
from mscanner import tests


class PerformanceVectorsTests(unittest.TestCase):

    def test_PerformanceVectors(self):
        p = PerformanceVectors(
            pscores = nx.array([1,2,3,4,4,5,5], dtype=nx.float32),
            nscores = nx.array([0,0,1,1,2,4,5], dtype=nx.float32),
            alpha = 0.5)
        logging.debug("PerformanceVectors: %s", pp.pformat(p.__dict__))
        
    def test_PerformanceRange(self):
        pass



class ValidatorTests(unittest.TestCase):

    def setUp(self):
        self.prefix = path(tempfile.mkdtemp(prefix="valid-"))
        logging.debug("Prefix is: %s", self.prefix)


    def tearDown(self):
        self.prefix.rmtree(ignore_errors=True)


    def test_make_partitions(self):
        """Test that partitioning function for cross-validation"""
        starts, sizes = CrossValidator.make_partitions(10,5)
        self.assert_((starts == [0,2,4,6,8]).all())
        self.assert_((sizes == [2,2,2,2,2]).all())
        starts, sizes = CrossValidator.make_partitions(33,5)
        self.assert_((starts == [0,7,14,21,27]).all())
        self.assert_((sizes == [7,7,7,6,6]).all())


    def _make_validator(self, featinfo):
        return CrossValidator(
            featdb = {0:[0,1,2], 1:[0,1], 2:[0,1], 3:[0,1], 4:[1,2], 
                      5:[1,2], 6:[1,2], 7:[0,1,2]},
            featinfo = featinfo,
            positives = nx.array([0, 1, 2, 3]),
            negatives = nx.array([4, 5, 6, 7]),
            nfolds = 4,
        )
    

    def _check_scores(self, featinfo, cpscores, cnscores):
        val = self._make_validator(featinfo)
        pscores, nscores = val.validate(randomise=False)
        logging.debug("pscores: %s", pp.pformat(pscores))
        logging.debug("pscores should be: %s", pp.pformat(cpscores))
        logging.debug("nscores: %s", pp.pformat(nscores))
        logging.debug("nscores  should be: %s", pp.pformat(cnscores))
        self.assert_(nx.allclose(pscores,cpscores,rtol=1e-3))
        self.assert_(nx.allclose(nscores,cnscores,rtol=1e-3))


    def test_cross_validate(self):
        logging.debug("scores_bayes")
        self._check_scores(
            FeatureScores([2,5,7], pseudocount = 0.1, make_scores="scores_bayes"),
            nx.array([-2.39789534,  2.20616317,  2.20616317,  4.60405827]),
            nx.array([-4.60405827, -2.20616317, -2.20616317,  2.39789534]))


    def test_leaveout_validate(self):
        """Test of leave-out-one cross validation.  Manually calculate
        scores on the articles to see if they are correct"""
        val = LeaveOutValidator(
            featdb = {0:[0,1,2], 1:[0,1], 2:[0,1], 3:[0,1], 4:[1,2], 
                      5:[1,2], 6:[1,2], 7:[0,1,2]},
            featinfo = FeatureScores([2,5,7], pseudocount = 0.1),
            positives = nx.array([0, 1, 2, 3]),
            negatives = nx.array([4, 5, 6, 7]),
            nfolds = None,
        )
        pscores, nscores = val.validate()
        cpscores = nx.array([-2.14126396, 1.30037451, 1.30037451, 1.30037451])
        cnscores = nx.array([-1.30037451, -1.30037451, -1.30037451,  2.14126396])
        self.assert_(nx.allclose(pscores,cpscores,rtol=1e-3))
        self.assert_(nx.allclose(nscores,cnscores,rtol=1e-3))



if __name__ == "__main__":
    tests.start_logging()
    unittest.main()

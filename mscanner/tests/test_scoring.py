"""Test suite for mscanner.scoring

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

from mscanner.configuration import rc
from mscanner.medline.FeatureDatabase import FeatureDatabase
from mscanner.medline.FeatureStream import FeatureStream
from mscanner.medline.FeatureMapping import FeatureMapping
from mscanner.core.FeatureScores import FeatureScores, FeatureCounts
from mscanner.fastscores.ScoreCalculator import ScoreCalculator
from mscanner.fastscores.FeatureCounter import FeatureCounter
from mscanner import tests


class CScoreModuleTests(unittest.TestCase):
    """Tests of the L{cscore} package"""
    
    def setUp(self):
        self.citations = [
            (1,20010101,[4]), 
            (2,20020101,[0,1,2]), 
            (3,20030101,[0,2,3]), 
            (4,20040101,[0,1]), 
            (5,20050101,[1,2,3])]

    
    def test_ctypes(self):
        try:
            from ctypes import cdll, c_int, byref
        except ImportError:
            return
        lib = cdll.LoadLibrary(ScoreCalculator.dll_path)
        output = c_int()
        lib.double_int(2, byref(output))
        self.assertEqual(output.value, 4)
        lib.double_array.argtypes = [ c_int,
            nx.ctypeslib.ndpointer(dtype=nx.int32, ndim=1, flags='CONTIGUOUS') ]
        a = nx.array([1,2,3,4])
        b = a * 2
        lib.double_array(len(a), a)
        self.assert_(nx.allclose(a, b))


    @tests.usetempfile
    def test_FeatureCounter(self, tmpfile):
        """Test the system for fast feature counting"""
        fs = FeatureStream(open(tmpfile, "w"))
        for pmid, date, feats in self.citations:
            fs.write(pmid, date, nx.array(feats, nx.uint16))
        fs.close()
        fc = FeatureCounter(
            docstream = tmpfile,
            numdocs = len(self.citations),
            numfeats = 5,
            mindate = 20020101,
            maxdate = 20070101,
            exclude = set([4,8,9]))
        p_ndocs, py_counts = fc.py_counts()
        c_ndocs, c_counts = fc.c_counts()
        logging.debug("py_counts: %d, %s", p_ndocs, pp.pformat(py_counts))
        logging.debug("c_counts: %d, %s", c_ndocs, pp.pformat(c_counts))
        self.assertEqual(p_ndocs, c_ndocs)
        self.assert_(nx.allclose(py_counts, c_counts))


    @tests.usetempfile
    def test_ScoreCalculator(self, tmpfile):
        """Consistency test between the implemtnations for calculating """
        featscores = nx.array([0.1, 5.0, 10.0, -5.0, -6.0])
        # Write citations to disk
        fs = FeatureStream(open(tmpfile, "w"))
        for pmid, date, feats in self.citations:
            fs.write(pmid, date, nx.array(feats, nx.uint16))
        fs.close()
        # Construct the document score calculator
        scorer = ScoreCalculator(
            docstream = tmpfile,
            numdocs = len(self.citations),
            featscores = featscores,
            offset = 5.0,
            limit = 5,
            threshold = 0.0,
            mindate = 20020101,
            maxdate = 20050101,
            exclude = set([5,8,9]))
        # Compare pyscore and cscore_pipe
        out_pyscore = scorer.pyscore()
        out_pipe = scorer.cscore_pipe()
        logging.debug("out_py: %s", pp.pformat(out_pyscore))
        logging.debug("out_pipe: %s", pp.pformat(out_pipe))
        scores_pipe = nx.array([score for score,pmid in out_pipe])
        scores_py = nx.array([score for score,pmid in out_pyscore])
        self.assert_(nx.allclose(scores_pipe, scores_py))
        # Compare pyscore and cscore_dll 
        try: 
            import  ctypes
        except ImportError: 
            return
        out_dll = scorer.cscore_dll()
        logging.debug("out_dll: %s", pp.pformat(out_dll))
        scores_dll = nx.array([score for score,pmid in out_dll])
        self.assert_(nx.allclose(scores_dll, scores_py))



class FeatureScoresTests(unittest.TestCase):
    """Tests of the L{scoring} module"""
    
    def setUp(self):
        self.pfreqs = nx.array([1,2,0])
        self.nfreqs = nx.array([2,1,0])
        self.pdocs = 2
        self.ndocs = 3
        self.featmap = FeatureMapping()


    def test_pseudocount(s):
        """Constant pseudocount"""
        f = FeatureScores(s.featmap, pseudocount=0.1,
                          make_scores="scores_noabsence")
        f.update(s.pfreqs, s.nfreqs, s.pdocs, s.ndocs)
        s.assert_(nx.allclose(
            f.scores, nx.array([-0.35894509,  0.93430924,  0.28768207])))


    def test_tfidf(s):
        """TFIDF calculation."""
        f = FeatureScores(s.featmap, pseudocount=0.1)
        f.update(s.pfreqs, s.nfreqs, s.pdocs, s.ndocs)
        tfidfs = nx.array([])
        #s.assert_(nx.allclose(f.tfidf, tfidfs))
        logging.debug("TFIDF: %s", pp.pformat(f.tfidf))


    def test_bayes(s):
        """Bayes score calculation"""
        s.featmap.numdocs = 10
        s.featmap.counts = [3,2,1]
        f = FeatureScores(s.featmap, pseudocount=None)
        f.update(s.pfreqs, s.nfreqs, s.pdocs, s.ndocs)
        logging.debug("Pfreqs (bayes): %s", pp.pformat(f.pfreqs))
        logging.debug("Nfreqs (bayes): %s", pp.pformat(f.nfreqs))
        logging.debug("PresScores (bayes): %s", pp.pformat(f.present_scores))
        logging.debug("AbsScores (bayes): %s", pp.pformat(f.absent_scores))
        logging.debug("Scores (bayes): %s", pp.pformat(f.scores))
        logging.debug("Base score (bayes): %f", f.base)
        s.assert_(nx.allclose(
            f.scores, nx.array([-0.57054485,  1.85889877,  0.29626582])))        


    def test_noabsence(s):
        """Old score calculation (lacks feature absence)"""
        s.featmap.numdocs = 10
        s.featmap.counts = [3,2,1]
        f = FeatureScores(s.featmap, pseudocount=None,
                          make_scores="scores_noabsence")
        f.update(s.pfreqs, s.nfreqs, s.pdocs, s.ndocs)
        logging.debug("Scores (noabsence): %s", pp.pformat(f.scores))
        s.assert_(nx.allclose(
            f.scores, nx.array([-0.28286278,  0.89381787,  0.28768207])))


    def test_constpseudo(s):
        """Constant pseudocount in old score calculation, with masking."""
        f = FeatureScores(s.featmap, pseudocount=0.1,
                          make_scores="scores_noabsence",
                          get_postmask="mask_nonpositives")
        f.update(s.pfreqs, s.nfreqs, s.pdocs, s.ndocs)
        logging.debug("Scores (constpseudo): %s", pp.pformat(f.scores))
        s.assert_(nx.allclose(
            f.scores, nx.array([-0.35894509,  0.93430924,  0.        ])))


    def test_FeatureCounts(self):
        featdb = {1:[1,2], 2:[2,3], 3:[3,4]}
        counts = FeatureCounts(5, featdb, [1,2,3])
        self.assert_(nx.all(counts == [0,1,2,2,1]))



if __name__ == "__main__":
    tests.start_logger()
    unittest.main()

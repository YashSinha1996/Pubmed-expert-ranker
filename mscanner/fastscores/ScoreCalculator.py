"""Calculates citation scores"""

from __future__ import division
import logging
import numpy as nx
from path import path

from mscanner import update
from mscanner.configuration import rc
from mscanner.medline.FeatureStream import FeatureStream


__copyright__ = "2007 Graham Poulter"
__author__ = "Graham Poulter <http://graham.poulter.googlepages.com>"
__license__ = """This program is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your option)
any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>."""


class ScoreCalculator:
    """Different methods for calculating the scores of all documents in the
    database.  The idea is to pick between them based on speed, since
    the faster ones may not be available on certain platforms.
    
    @ivar docstream: Path to file containing feature vectors for documents to
    score, in L{mscanner.medline.FeatureStream.FeatureStream} format.
    
    @ivar numdocs: Number of documents in the stream of feature vectors.
    
    @ivar featscores: Numpy array of double-precision feature scores.
    
    @ivar offset: Sum of the Bayesian prior score and the base log likelihood 
    of an article with no features.

    @ivar limit: Maximum number of results to return.
    
    @ivar threshold: Cutoff score for including an article in the results
    
    @ivar mindate: YYYYMMDD integer: documents must have this date or later
    (default 11110101)
    
    @ivar maxdate: YYYYMMDD integer: documents must have this date or earlier
    (default 33330303)

    @ivar exclude: Set of PMIDs that are not allowed to appear in the results
    """
    
    executable_path = path(__file__).dirname() / "_ScoreCalculator"
    """Path to executable for article score calculation"""
    
    dll_path = path(__file__).dirname() / "_ScoreCalculator.dll"
    """Path to shared library for article score calculation"""

    def __init__(self,
                 docstream,
                 numdocs,
                 featscores,
                 offset,
                 limit,
                 threshold=None,
                 mindate=None,
                 maxdate=None,
                 exclude=set(),
                 ):
        # Callers may want to pass None, but the C code needs numbers.
        if threshold is None: threshold = -10000.0
        if mindate is None: mindate = 10110101
        if maxdate is None: maxdate = 30330303
        update(self, locals())


    def score(s):
        """Meta-method to top-scoring PubMed IDs in Medline
        
        @note: All implementations iterate over the document stream and to find
        articles that are between mindate and maxdate, are not members of
        exclude, and have scores above the threshold.
        
        @note: This method picks between L{cscore_dll}, L{cscore_pipe} and
        L{pyscore} in decreasing order of preference (due to speed).
        
        @return: List of (score, PMID) in decreasing order of score
        """
        score = s.cscore_dll
        if s.dll_path.isfile():
            try: 
                import ctypes
            except ImportError: 
                score = s.cscore_pipe
        else:
            score = s.cscore_pipe
        if score == s.cscore_pipe and not s.executable_path.isfile():
            score = s.pyscore
        return score()


    def pyscore(s):
        """Pure python implementation of L{score}"""
        logging.info("Performing query using ScoreCalculator.pyscore")
        results = [(-100000, 0)] * s.limit
        import heapq
        ndocs = 0
        logging.debug("Calculating article scores")
        marker = 0
        docs = FeatureStream(open(s.docstream, "rb"))
        try:
            for idx, (docid, date, features) in enumerate(docs):
                if idx == marker:
                    logging.debug("Scored %d citations so far", idx)
                    marker += 100000
                if (docid in s.exclude or date < s.mindate or date > s.maxdate):
                    continue
                score = s.offset + nx.sum(s.featscores[features])
                if score >= s.threshold:
                    ndocs += 1
                    if score >= results[0][0]:
                        heapq.heapreplace(results, (score,docid))
        finally:
            docs.close()
        if ndocs > s.limit:
            ndocs = limit
        return heapq.nlargest(ndocs, results)


    def cscore_pipe(s):
        """Calculate article scores by piping to the cscore program"""
        logging.info("Performing query using ScoreCalculator.cscore_pipe")
        import struct
        import subprocess as sp
        p = sp.Popen([
            s.executable_path, 
            s.docstream,
            str(s.numdocs),
            str(len(s.featscores)),
            str(s.offset),
            str(s.limit+len(s.exclude)),
            str(s.threshold),
            str(s.mindate),
            str(s.maxdate),
            ], stdout=sp.PIPE, stdin=sp.PIPE)
        p.stdin.write(s.featscores.tostring())
        output = p.stdout.read(8)
        count = 0
        # Go through results in decreasing order to filter them
        result = []
        while output != "":
            score, pmid = struct.unpack("fI", output)
            if pmid not in s.exclude:
                result.append((score, pmid))
                count += 1
                if count >= s.limit:
                    break
            output = p.stdout.read(8)
        p.stdout.close()
        return result


    def cscore_dll(s):
        """Calculate article scores, using ctypes to call cscores"""
        logging.info("Performing query using ScoreCalculator.cscore_dll")
        from ctypes import cdll, byref, c_int, c_void_p, c_char_p, c_float, c_double
        import itertools
        import numpy as nx
        # Set up arguments and call cscore2 function using ctypes
        carray = lambda dtype: nx.ctypeslib.ndpointer(
            dtype=dtype, ndim=1, flags='CONTIGUOUS')
        o_numresults = c_int()
        cscore = cdll.LoadLibrary(s.dll_path)
        cscore.cscore.argtypes = [ 
            c_char_p,           # docstream
            c_int,              # numdocs
            c_int,              # len(featscores)
            c_float,            # offset
            c_int,              # limit
            c_float,            # threshold
            c_int,              # mindate
            c_int,              # maxdate
            carray(nx.float64), # featscores
            c_void_p,           # o_numresults
            carray(nx.float32), # o_scores
            carray(nx.int32),   # o_pmids
        ]
        output_size = s.limit + len(s.exclude) # extra space for exclusions
        o_scores = nx.zeros(output_size, dtype=nx.float32)
        o_pmids = nx.zeros(output_size, dtype=nx.int32)
        # Now call this monstrously paramaterised function
        cscore.cscore(
            s.docstream,
            s.numdocs,
            len(s.featscores), 
            s.offset,
            output_size,
            s.threshold,
            s.mindate,
            s.maxdate,
            s.featscores,
            byref(o_numresults),
            o_scores, 
            o_pmids)
        # Go through results in decreasing order to filter them
        count_filtered = 0
        count_total = 0
        result = []
        if o_numresults.value == 0:
            return result
        for score, pmid in itertools.izip(o_scores, o_pmids):
            if pmid not in s.exclude:
                result.append((score, pmid))
                count_filtered += 1
                if count_filtered >= s.limit:
                    break
            count_total += 1
            if count_total >= o_numresults.value:
                break
        return result
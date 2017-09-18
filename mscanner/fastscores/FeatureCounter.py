"""Calculates the number of occurrences of each feature for
all articles in Medline between two dates."""

from __future__ import division
import numpy as nx
from path import path
import struct

from mscanner import update
from mscanner.medline.FeatureStream import FeatureStream


class FeatureCounter:
    """Class for calculating feature counts in a subset of Medline.

    @ivar docstream: Path to file containing feature vectors for documents to
    score, in L{mscanner.medline.FeatureStream.FeatureStream} format.
    
    @ivar numdocs: Number of documents in the stream of feature vectors.
    
    @ivar numfeats: Number of distinct features in Medline (length of the 
    vector of feature counts).

    @ivar mindate: YYYYMMDD integer: documents must have this date or later
    (default 11110101)
    
    @ivar maxdate: YYYYMMDD integer: documents must have this date or earlier
    (default 33330303)

    @ivar exclude: PMIDs that are not allowed to appear in the results    
    """
    
    counter_path = path(__file__).dirname() / "_FeatureCounter"
    """Executable file for counting features in a file"""
    
    def __init__(self,
                 docstream,
                 numdocs,
                 numfeats,
                 mindate=None,
                 maxdate=None,
                 exclude=set(),
                 ):
        if mindate is None: mindate = 10110101
        if maxdate is None: maxdate = 30330303
        update(self, locals())


    def py_counts(s):
        """Simply iterate over the documents and count how
        many times each feature occurs in the specified range
        
        @return: Number of documents counted, and vector of feature counts."""
        featcounts = nx.zeros(s.numfeats, nx.int32)
        docs = FeatureStream(open(s.docstream, "rb"))
        ndocs = 0
        try:
            for docid, date, features in docs:
                if (date >= s.mindate and date <= s.maxdate 
                    and docid not in s.exclude):
                    featcounts[features] += 1
                    ndocs += 1
        finally:
            docs.close()
        return ndocs, featcounts


    def c_counts(s):
        """Pipes parameters to a C program that parses the stream
        of documents with features, which counts the number
        of occurrences of each feature, only considering documents
        added to Medline in the specified date range.
        
        @return: Number of documents counted, and vector of feature counts."""
        import subprocess as sp
        p = sp.Popen([
            s.counter_path, 
            s.docstream,
            str(s.numdocs),
            str(s.numfeats),
            str(s.mindate),
            str(s.maxdate),
            str(len(s.exclude)),
            ], stdout=sp.PIPE, stdin=sp.PIPE)
        p.stdin.write(nx.array(sorted(s.exclude)))
        # First integer of output is the number of documents parsed
        ndocs = struct.unpack("I", p.stdout.read(4))[0]
        # Then a vector of feature counts
        featcounts = nx.fromfile(p.stdout, nx.int32, s.numfeats)
        return ndocs, featcounts

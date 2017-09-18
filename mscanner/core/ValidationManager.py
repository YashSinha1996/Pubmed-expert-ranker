"""Environment for performing cross-validation-based analyses"""

from __future__ import with_statement
from __future__ import division

import codecs
from itertools import chain, izip
import logging
import numpy as nx
import time

import warnings
warnings.simplefilter("ignore", UserWarning)

from mscanner.configuration import rc
from mscanner.medline.Databases import Databases
from mscanner.core import iofuncs
from mscanner.core.FeatureScores import FeatureScores, FeatureCounts
from mscanner.core.metrics import (PerformanceVectors, PerformanceRange, 
                                   PredictedMetrics)
from mscanner.core.Plotter import Plotter
from mscanner.core.Validator import CrossValidator


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



class ValidationBase(object):
    """Base class for all validation operations.
    
    Derived classes need to calculate all attributes other than those set in
    the constructor. The attributes are required by L{_write_report}.
    
    @group Set in the constructor: env, outdir, dataset, timestamp

    @ivar env: L{Databases} instance for accessing Medline

    @ivar outdir: Path to directory for output files, which is created if it
    does not exist.
    
    @ivar dataset: Title of the dataset to use when printing reports

    @ivar timestamp: Time at the start of the operation


    
    @ivar pscores: Result scores for positive articles

    @ivar nscores: Result scores for negative articles

    @ivar featinfo: L{FeatureScores} instance for calculating feature scores

    @ivar nfolds: Number of cross validation folds (may not be relevant)

    @ivar notfound_pmids: List of input PMIDs not found in the database

    @ivar metric_vectors: L{PerformanceVectors} instance

    @ivar metric_range: L{PerformanceRange} instance
    
    @ivar logfile: logging.FileHandler for logging to output directory
    """

    
    def __init__(self, outdir, dataset, env=None):
        """Constructor"""
        self.dataset = dataset
        self.outdir = outdir
        if not outdir.exists():
            outdir.makedirs()
            outdir.chmod(0777)
        self.env = env if env else Databases()
        self.timestamp = time.time() 
        self.nfolds = None
        self.pscores, self.nscores = None, None
        self.featinfo = None
        self.metric_vectors = None
        self.metric_range = None
        self.notfound_pmids = []
        self.logfile = iofuncs.open_logfile(self.outdir/rc.report_logfile)


    def __del__(self):
        iofuncs.close_logfile(self.logfile)


    def _crossvalid_scores(self, positives, negatives):
        """Calculate article scores under cross validation
        
        @param positives: Vector of relevant PubMed IDs
        
        @param negatives: Vector of irrelevant PubMed IDs
        
        @note: Feature database lookups are slow so we cache them all
        beforehand in a dictionary.
        
        @note: Before returning, we re-caculate feature scores in L{featinfo} 
        using ALL of the training data.
        
        @note: L{positives} and L{negatives} are scrambled so that they
        can be split into validation folds.  The returned scores correspond,
        so you can zip(positives, pscores) and zip(negatives, nscores) to
        pair up the scores with the articles.
        
        @return: Two vectors, containing scores for the positive and negative
        articles respectively (unsorted for reconstruction of folds)."""
        self.validator = CrossValidator(
            featdb = dict((k,self.env.featdb[k]) for k in 
                          chain(positives,negatives)),
            featinfo = self.featinfo,
            positives = positives,
            negatives = negatives,
            nfolds = self.nfolds)
        pscores, nscores = self.validator.validate()
        # Finally set feature scores using all available data
        self._update_featscores(positives, negatives)
        return pscores, nscores


    def _get_performance(self, threshold=None):
        """Calculate performance statistics.
        
        @param threshold: Specify a particular threshold, or None to estimate
        using F measure."""
        logging.info("Eval performance using alpha=%s, utility_r=%s", 
                     str(rc.alpha), str(rc.utility_r))
        v = PerformanceVectors(self.pscores, self.nscores, rc.alpha, rc.utility_r)
        self.metric_vectors = v
        if threshold is None:
            threshold, idx = v.threshold_maximising(v.FMa)
        else:
            threshold, idx = v.index_for(threshold)
        logging.info("Threshold is %f (uscores index=%d)", threshold, idx)
        average = v.metrics_for(idx)
        self.metric_range = PerformanceRange(
            self.pscores, self.nscores, self.nfolds, threshold, average)


    def _init_featinfo(self):
        """Initialise L{featinfo} for use in validation"""
        self.featinfo = FeatureScores(
            featmap = self.env.featmap, 
            pseudocount = rc.pseudocount, 
            mask = self.env.featmap.get_type_mask(rc.exclude_types),
            make_scores = rc.make_scores,
            get_postmask = rc.get_postmask)


    def _update_featscores(self, pos, neg):
        """Update the feature scores in L{featinfo} using the given 
        vectors of positive and negative citations."""
        self.featinfo.update(
            pos_counts = FeatureCounts(
                len(self.env.featmap), self.env.featdb, pos),
            neg_counts = FeatureCounts(
                len(self.env.featmap), self.env.featdb, neg),
            pdocs = len(pos),
            ndocs = len(neg))


    def _write_report(self):
        """Write an HTML validation report. 
        
        Only redraws figures for which output files do not already exist
        (likewise for term scores, but the index is always re-written)."""
        # Write term scores to file
        if not (self.outdir/rc.report_term_scores).exists():
            logging.debug("Writing features scores to %s", rc.report_term_scores)
            with codecs.open(self.outdir/rc.report_term_scores, "wb", "utf-8") as f:
                self.featinfo.write_csv(f)
        # Aliases for the performance data
        p = self.metric_vectors
        t = self.metric_range.average
        # Do not overwriting existing plots
        plotter = Plotter(overwrite=False) 
        # Predicted precision/recall performance
        if hasattr(self, "pred_low") and hasattr(self, "pred_high"):
            plotter.plot_predictions(self.outdir/rc.report_prediction_img, 
                                     self.pred_low, self.pred_high)
        # Report cross validation results instead of prediction results
        else:
            # ROC curve
            plotter.plot_roc(
                self.outdir/rc.report_roc_img, p.FPR, p.TPR, t.FPR)
            # Precision-recall curve
            plotter.plot_precision(
                self.outdir/rc.report_prcurve_img, p.TPR, p.PPV, t.TPR)
            # F-Measure curve
            plotter.plot_fmeasure(
                self.outdir/rc.report_fmeasure_img, p.uscores, p.TPR, p.PPV, 
                p.FM, p.FMa, self.metric_range.threshold)
        # Article score histogram
        plotter.plot_score_histogram(
            self.outdir/rc.report_artscores_img, p.pscores, p.nscores, 
            self.metric_range.threshold)
        # Feature score histogram
        plotter.plot_feature_histogram(
            self.outdir/rc.report_featscores_img, self.featinfo.scores)
        # Write index file
        logging.debug("FINISH: Writing %s for %s", rc.report_index, self.dataset)
        from Cheetah.Template import Template
        with iofuncs.FileTransaction(self.outdir/rc.report_index, "w") as ft:
            Template(file=str(rc.templates/"validation.tmpl"), 
                     filter="Filter", searchList=dict(VM=self)).respond(ft)



def SplitValidation(ValidationBase):
    """Carries out split-sample validation, as in the 2005 TREC
    Genomics Track categorisation task.
    """

    def validation(self, fptrain, fntrain, fptest, fntest):
        """Carry out split-sample validation.  
        
        @note: All corpora are represented as lists of PubMed IDs.
        
        @param fptrain: File with positive training examples
        
        @param fntrain: File with negative training examples

        @param fptest: File with positive testing examples

        @param fntest: File with negative testing examples
        """
        logging.info("START: Split validation for %s", self.dataset)
        s = self
        s.nfolds = 1 # Effectively a single fold
        s.ptrain, s.ntrain = None, None
        s.ptest, s.ntest = None, None
        s.notfound_pmids = []
        s.ptrain, broke, excl = iofuncs.read_pmids_careful(fptrain, s.env.featdb)
        s.ptest, broke, excl = iofuncs.read_pmids_careful(fptest, s.env.featdb)
        s.ntrain, broke, excl = iofuncs.read_pmids_careful(
            fntrain, s.env.featdb, set(s.ptrain))
        s.ntest, broke, excl = iofuncs.read_pmids_careful(
            fntest, s.env.featdb, set(s.ptest))
        if len(s.ptrain)>0 and len(s.ptest)>0 \
           and len(s.ntrain)>0 and len(s.ntest)>0:
            s._init_featinfo()
            s._test_scores()
            s._get_performance()
            s._write_report()
        else:
            logging.error("At least one input file contained no valid PubMed IDs")
            return


    def _test_scores(self):
        """Get performance statistics using split validation. 
        
        The training sample is used to calculate feature scores, which are then
        used to get the scores of the testing sample. Cross validation is used
        on the training sample to calculate a threshold optimising utility. The
        threshold is then applied to the testing sample to obtain performance
        metrics."""
        s = self
        # Calculate cross-validated scores on training data
        train_pscores, train_nscores = s._crossvalid_scores(s.ptrain, s.ntrain)
        # Calculate split-sample scores on the testing data
        s.pscores = s.featinfo.scores_of(s.env.featdb, s.ptest)
        s.nscores = s.featinfo.scores_of(s.env.featdb, s.ntest)
        # Cross validation on training data for a threshold maximising utility
        trainperf = PerformanceVectors(
            train_pscores, train_nscores, rc.alpha, rc.utility_r)
        threshold = trainperf.threshold_maximising(trainperf.U)[0]
        # Apply that threshold to calculating performance on the test split
        self._get_performance(threshold)



class CrossValidation(ValidationBase):
    """Carries out N-fold cross validation.

    @group Additional attributes: positives, negatives

    @ivar positives: IDs of positive articles

    @ivar negatives: IDs of negative articles
    """
    

    def validation(self, pos, neg, nfolds=10):
        """Loads data and perform cross validation to calculate scores
        on that data.
        
        @note: This saves articles scores to the report directory, and 
        if possible it will load load those scores instead of calculating
        from scratch.
        
        @param pos, neg: Parameters for L{_load_input}
        
        @param nfolds: Number of validation folds to use.
        """
        logging.info("START: Cross validation for %s", self.dataset)
        # Keep our own number of folds attribute
        self.nfolds = nfolds
        self.notfound_pmids = []
        self._init_featinfo()
        # Try to load saved results
        try:
            self.positives, self.pscores = iofuncs.read_scores_array(
                self.outdir/rc.report_positives)
            self.negatives, self.nscores = iofuncs.read_scores_array(
                self.outdir/rc.report_negatives)
            self._update_featscores(self.positives, self.negatives)
        # Failed to load, so perform cross validation
        except IOError:
            if not self._load_input(pos, neg):
                return
            self.pscores, self.nscores = \
                self._crossvalid_scores(self.positives, self.negatives)
            iofuncs.write_scores(self.outdir/rc.report_positives,
                                 izip(self.pscores, self.positives))
            iofuncs.write_scores(self.outdir/rc.report_negatives, 
                                 izip(self.nscores, self.negatives))


    def report_validation(self):
        """Report cross validation results, using default threshold of 0"""
        if len(self.positives)>0 and len(self.negatives)>0:
            self._get_performance(0.0)
            self._write_report()

    
    def report_predicted(self, relevant_low, relevant_high, medline_size):
        """Experimental: report predicted query performance
        
        @param relevant_low: Minimum expected relevant articles in Medline
        
        @param relevant_high: Maximum expected relevant articles in Medline

        @param medline_size: Number of articles in rest of Medline, or None
        to use L{Databases.article_list} minus relevant articles.
        """
        if len(self.positives)>0 and len(self.negatives)>0:
            # Calculate the performance
            self._get_performance()
            if medline_size is None:
                medline_size = len(self.env.article_list) - len(self.positives)
            v = self.metric_vectors
            self.pred_low = PredictedMetrics(
                v.TPR, v.FPR, v.uscores, relevant_low, medline_size)
            self.pred_high = PredictedMetrics(
                v.TPR, v.FPR, v.uscores, relevant_high, medline_size)
            self._write_report()


    def _load_input(self, pos, neg):
        """Sets L{positives} and L{negatives} by various means
        
        @param pos: Path to file of input PubMed IDs, or something convertible
        to an integer array.

        @param neg: Path to file of input negative PMIDs, or something
        convertible to integer array, or an integer representing the
        number of PubMed IDs to select at random from the database.
        
        @return: True if the load was successful, False otherwise.
        """
        if isinstance(pos, basestring):
            logging.info("Loading positive PubMed IDs from %s", pos.basename())
            self.positives, self.notfound_pmids, exclude = \
                iofuncs.read_pmids_careful(pos, self.env.featdb)
        else:
            self.positives = nx.array(pos, nx.int32)
        if isinstance(neg, int):
            logging.info("Selecting %d random negative PubMed IDs" % neg)
            # Clamp number of negatives to the number available
            maxnegs = len(self.env.article_list) - len(self.positives)
            if neg > maxnegs:
                neg = maxnegs
            # Take a sample of random citations
            self.negatives = self._random_subset(
                neg, self.env.article_list, set(self.positives))
        elif isinstance(neg, basestring):
            logging.info("Loading negative PubMed IDs from %s", neg.basename())
            # Read list of negative PMIDs from disk
            self.negatives, notfound, exclude = iofuncs.read_pmids_careful(
                    neg, self.env.featdb, set(self.positives))
            self.notfound_pmids = list(self.notfound_pmids) + list(notfound)
            iofuncs.write_pmids(self.outdir/rc.report_negatives_exclude, exclude)
        else:
            self.negatives = nx.array(neg, nx.int32)
        # Writing out broken PubMed IDs
        iofuncs.write_pmids(
            self.outdir/rc.report_input_broken, self.notfound_pmids)
        # Checking that we have the input
        if len(self.positives)>0 and len(self.negatives)>0:
            return True
        else:
            logging.error("No valid PubMed IDs in at least one input (error page)")
            iofuncs.no_valid_pmids_page(
                self.outdir/rc.report_index, self.dataset, self.notfound_pmids)
            return False
        return True


    @staticmethod
    def _random_subset(k, pool, exclude):
        """Choose a random subset of k articles from pool
        
        This is a good algorithm when the pool is large (say, 16 million
        items), we don't mind if the order of pool gets scrambled, and we have
        to exclude certain items from being selected.
        
        @param k: Number of items to choose from pool
        @param pool: Array of items to choose from (will be scrambled!)
        @param exclude: Set of items that may not be chosen
        @return: A new array of the chosen items
        """
        from random import randint
        import numpy as nx
        n = len(pool)
        assert 0 <= k <= n
        for i in xrange(k):
            # Non-selected items are in 0 ... n-i-1
            # Selected items are n-i ... n
            dest = n-i-1
            choice = randint(0, dest) # 0 ... n-i-1 inclusive
            while pool[choice] in exclude:
                choice = randint(0, dest)
            # Move the chosen item to the end, where so it will be part of the
            # selected items in the next iteration. Note: this works using single
            # items - it but would break with slices due to their being views into
            # the vector.
            pool[dest], pool[choice] = pool[choice], pool[dest]
        # Phantom iteration: selected are n-k ... n
        return nx.array(pool[n-k:])

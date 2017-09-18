"""Cross-validation and performance statistic calculation"""

from __future__ import division
import logging
import numpy as nx

from mscanner import update
from mscanner.core.FeatureScores import FeatureScores, FeatureCounts


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


class CrossValidator:
    """Cross-validated calculation of article scores.
    
    @group Constructor Parameters: featdb,featinfo,positives,negatives,nfolds,alpha,postfilter

    @ivar featdb: Mapping from doc id to list of feature ids
    
    @ivar featinfo: L{FeatureScores} instance to handle training
    
    @ivar positives: Array of positive PMIDs for validation
    
    @ivar negatives: Array of negative PMIDs for validation
    
    @ivar nfolds: Number of validation folds

    
    @group From validate: pscores,nscores
    
    @ivar pscores: Scores of positive articles after validation
    
    @ivar nscores: Scores of negative articles after validation
    """

    def __init__(self, featdb, featinfo, positives,  negatives, nfolds):
        """Constructor parameters set corresponding instance attributes."""
        pscores = None
        nscores = None
        update(self, locals())


    @staticmethod
    def make_partitions(nitems, nparts):
        """Calculate partitions of input data for cross validation
        
        @param nitems: Number of items to partition
        @param nparts: Number of partitions
        @return: List of start indeces, and list of lengths for partitions
        """
        base, rem = divmod(nitems, nparts)
        sizes = base * nx.ones(nparts, nx.int32)
        sizes[:rem] += 1
        starts = nx.zeros(nparts, nx.int32)
        starts[1:] = nx.cumsum(sizes[:-1])
        return starts, sizes


    def validate(self, randomise=True):
        """Perform n-fold validation and return the raw performance measures
        
        @param randomise: Randomise validation splits (use False for debugging)
        
        @return: L{pscores}, L{nscores}
        """
        s = self
        pdocs = len(s.positives)
        ndocs = len(s.negatives)
        logging.debug("Cross-validating %d pos and %d neg items", pdocs, ndocs)
        if randomise:
            nx.random.shuffle(s.positives)
            nx.random.shuffle(s.negatives)
        s.pstarts, s.psizes = s.make_partitions(pdocs, s.nfolds)
        s.nstarts, s.nsizes = s.make_partitions(ndocs, s.nfolds)
        s.pscores = nx.zeros(pdocs, nx.float32)
        s.nscores = nx.zeros(ndocs, nx.float32)
        pcounts = FeatureCounts(len(s.featinfo), s.featdb, s.positives)
        ncounts = FeatureCounts(len(s.featinfo), s.featdb, s.negatives)
        for fold, (pstart,psize,nstart,nsize) in \
            enumerate(zip(s.pstarts,s.psizes,s.nstarts,s.nsizes)):
            logging.debug("Fold %d: pstart = %d, psize = %s; nstart = %d, nsize = %d", 
                      fold, pstart, psize, nstart, nsize)
            # Get new feature scores
            s.featinfo.update(
                pos_counts = pcounts - FeatureCounts(
                    len(s.featinfo), s.featdb, 
                    s.positives[pstart:pstart+psize]), 
                neg_counts = ncounts - FeatureCounts(
                    len(s.featinfo), s.featdb, 
                    s.negatives[nstart:nstart+nsize]),
                pdocs = pdocs-psize, 
                ndocs = ndocs-nsize,
                prior = nx.log(pdocs/ndocs),
            )
            # Calculate the article scores for the test fold
            s.pscores[pstart:pstart+psize] = s.featinfo.scores_of(
                s.featdb, s.positives[pstart:pstart+psize])
            s.nscores[nstart:nstart+nsize] = s.featinfo.scores_of(
                s.featdb, s.negatives[nstart:nstart+nsize])
        return s.pscores, s.nscores



class LeaveOutValidator(CrossValidator):
    """Instead of N-fold cross validation, this class performs leave
    out one validation in which all but one of the citations is used
    to train the feature scores, which are then used to calculate
    the score of the left out document.
    
    This is a lot slower than cross validation, although performance metrics
    are a bit higher. We have optimised the calculation of scores by
    calculating counts for all articles and just subtracting 1 for each feature
    present in the left out article.
    
    Also, this version only has one scoring method: background Medline for
    pseudocounts, with prior probability of observation being 50%. """
    
    def validate(self):
        """Performs leave-out-one validation, returning the resulting scores.
        
        
        @return: L{pscores}, L{nscores}
        """
        # Set up base feature scores
        pcounts = FeatureCounts(len(self.featinfo), self.featdb, self.positives)
        ncounts = FeatureCounts(len(self.featinfo), self.featdb, self.negatives)
        self.pscores = nx.zeros(len(self.positives), nx.float32)
        self.nscores = nx.zeros(len(self.negatives), nx.float32)
        pdocs = len(self.positives)
        ndocs = len(self.negatives)
        mask = self.featinfo.mask
        # Set up pseudocount
        if isinstance(self.featinfo.pseudocount, nx.ndarray):
            ps = self.featinfo.pseudocount
        else:
            ps = nx.zeros(len(self.featinfo), nx.float32) + self.featinfo.pseudocount
        marker = 0
        # Discount this article in feature score calculations
        def score_of(pmid, p_mod, n_mod):
            f = [fid for fid in self.featdb[doc] if not mask or not mask[fid]]
            return nx.sum(nx.log(
                ((pcounts[f]+p_mod+ps[f])/(pdocs+p_mod+2*ps[f]))/
                ((ncounts[f]+n_mod+ps[f])/(ndocs+n_mod+2*ps[f]))))
        # Get scores for positive articles
        for idx, doc in enumerate(self.positives):
            self.pscores[idx] = score_of(doc, -1, 0)
        # Get scores for negative articles
        for idx, doc in enumerate(self.negatives):
            self.nscores[idx] = score_of(doc, 0, -1)
        return self.pscores, self.nscores
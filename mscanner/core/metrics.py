"""Calculates performance statistics given the scores of the positive and
negative citations

@note: Order of confusion matrix is *always* TP, TN, FP, FN (do not mess up on
this!)

"""

from __future__ import division
import numpy as nx
import copy # used in PerformanceRanges

from mscanner import update
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


class PerformanceVectors:
    """Contains vectors of performance metrics at all possible threshold
    
    @note: The performance statistics are calculated at every discreet
    threshold and stored in vectors.
    
    @note: This copies L{pscores} and L{nscores} *before* sorting!

    @note: If L{utility_r} is None, we use ratio of negatives to positives in the data.
    
    @group Passed to constructor: pscores, nscores, alpha, utility_r
    @ivar pscores: Vector of scores for positive articles, in increasing order.
    @ivar nscores: Vector of scores for negative articles, in increasing order.
    @ivar alpha: Balance of recall and precision in the F measure.
    @ivar utility_r: Value of a relevant article (irrelevant articles have
    value -1).

    @group From _confusion_vectors: uscores, PE, NE, TP, TN, FP, FN
    @ivar uscores: Unique scores in increasing order.
    @ivar PE: Number of positives with each score in L{uscores}.
    @ivar NE: Number of negatives with each score in L{uscores}.
    @ivar TP, TN, FP, FN: Vectors for confusion matrix at each distinct threshold.
    
    @group From _ratio_vectors: TPR, FPR, PPV, FM, FMa, U
    @ivar TPR: True positive rate at each threshold
    @ivar FPR: False positive rate at each threshold
    @ivar PPV: Positive predictive value at each threshold
    @ivar FM: F measure at each threshold using alpha
    @ivar FMa: F measure at each threshold using given alpha
    @ivar U: Utility at each threshold
        
    @group From _curve_areas: ROC_area, PR_area
    @ivar ROC_area: Area under ROC curve (trapezoidal under-estimate)
    @ivar PR_area: Aread under precision-recall curve.

    @group From _roc_error: W, W_stderr
    @ivar W: Area under ROC curve (better than trapezoidal area)
    @ivar W_stderr: Standard error of area under ROC curve.

    @group From _averaged_precision: AvPrec
    @ivar AvPrec: Averaged precision (better than trapezoidal area)

    @group From _breakeven: bep_index, breakeven
    @ivar bep_index: Index into L{uscores} for break-even point. 
    @ivar breakeven: Value at the point where precision=recall.
    """


    def __init__(self, pscores, nscores, alpha, utility_r=None):
        pscores = pscores.copy()
        nscores = nscores.copy()
        pscores.sort()
        nscores.sort()
        if utility_r is None:
            utility_r = len(nscores)/len(pscores)
        update(self, locals())
        self._confusion_vectors()
        self._ratio_vectors(self.alpha)
        self._curve_areas()
        self._roc_error()
        self._averaged_precision()
        self._breakeven()


    def _confusion_vectors(self):
        """Calculates confusion matrix counts by iterating over pscores
        
        Sets L{uscores}, L{PE}, L{NE}, L{TP}, L{TN}, L{FP}, L{FN}
        """
        s = self
        self.uscores = nx.unique(nx.concatenate((s.pscores,s.nscores)))
        vlen = len(s.uscores)
        P = len(s.pscores)
        N = len(s.nscores)
        self.PE = nx.zeros(vlen, nx.float32) # positives with given score
        self.NE = nx.zeros(vlen, nx.float32) # negatives with given score
        self.TP = nx.zeros(vlen, nx.float32) # true positives
        self.TN = nx.zeros(vlen, nx.float32) # true negatives
        self.FP = nx.zeros(vlen, nx.float32) # false positives
        self.FN = nx.zeros(vlen, nx.float32) # false negatives
        TN = 0
        FN = 0
        for idx, threshold in enumerate(s.uscores):

            # Classify positives scoring < threshold as negative
            # (look up score for the next article to classify)
            while (FN < P) and (s.pscores[FN] < threshold):
                FN += 1
            TP = P - FN # TP+FN=P

            # pcount-FN = number of positives having threshold score
            pcount = FN # Start at FN, subtract it later
            while (pcount < P) and s.pscores[pcount] == threshold:
                pcount += 1
            s.PE[idx] = pcount-FN
            
            # Classify negatives scoring < threshold as negative
            while (TN < N) and (s.nscores[TN] < threshold):
                TN += 1
            FP = N - TN  # TN+FP=N

            # ncount-TN = number of negatives having threshold score
            ncount = TN # Start at TN and subtract it later
            while (ncount < N) and s.nscores[ncount] == threshold:
                ncount += 1
            s.NE[idx] = ncount-TN
            
            s.TP[idx] = TP
            s.TN[idx] = TN
            s.FP[idx] = FP
            s.FN[idx] = FN


    def _ratio_vectors(self, alpha):
        """Calculate performance using vector algebra

        @param alpha: Weight of precision in calculating FMa
        
        Sets L{TPR}, L{FPR}, L{PPV}, L{FM}, L{FMa}, L{U}
        """
        s = self
        # TPR is recall
        self.TPR = s.TP / len(s.pscores)
        # FPR is 1-specificity
        self.FPR = s.FP / len(s.nscores)
        # PPV is precision
        self.PPV = s.TP / (s.TP + s.FP) 
        self.PPV[s.TP+s.FP == 0] = 1.0
        # FM is F-Measure
        self.FM = 2 * s.TPR * s.PPV / (s.TPR + s.PPV) 
        # FMa is the alpha-weighted F-Measures
        self.FMa = 1.0 / (alpha / s.PPV + (1 - alpha) / s.TPR)
        # U is the utility function
        self.U = (s.utility_r * s.TP - s.FP) / (self.utility_r * len(s.pscores))


    def _curve_areas(self):
        """Calculate areas under ROC and precision-recall curves
        
        Uses trapz(y, x). TPR is decreasing as threshold climbs, so vectors
        have to be reversed.
        
        This method underestimates ROC areas because boundary points (0,0) and
        (1,1) usually are not present in the data. Better to use L{_roc_error}
        which does not have that problem.
        
        Sets L{ROC_area}, L{PR_area}"""
        from scipy.integrate import trapz
        self.ROC_area = trapz(self.TPR[::-1], self.FPR[::-1])
        self.PR_area = trapz(self.PPV[::-1], self.TPR[::-1])


    def _mergescores(self):
        """Merges pscores and nscores in a single pass
        
        @note: L{nscores} and L{pscores} must be in increasing order of score.        
        
        @return: Iterator over (score, relevance) in decreasing order of score.
        Relevance is True for members of pscores, and False for members of
        nscores. """
        s = self
        p_idx = len(s.pscores)-1
        n_idx = len(s.nscores)-1
        while p_idx >= 0 or n_idx >= 0:
            if p_idx >= 0 and \
            (n_idx < 0 or s.pscores[p_idx] >= s.nscores[n_idx]):
                yield s.pscores[p_idx], True
                p_idx -= 1
            elif n_idx >= 0 and \
            (p_idx < 0 or s.nscores[n_idx] > s.pscores[p_idx]):
                yield s.nscores[n_idx], False
                n_idx -= 1


    def _averaged_precision(self):
        """Average the precision over each point of recall
        
        Sets L{AvPrec}, which is precision averaged over each point where a
        relevant document is returned"""
        AvPrec = 0.0
        TP = 0
        FP = 0
        for score, relevant in self._mergescores():
            if relevant:
                TP += 1
                AvPrec += TP/(TP+FP)
            else:
                FP += 1
        self.AvPrec = AvPrec/TP


    def _roc_error(self):
        """Area under ROC and its standard error
        
        Uses method of Hanley1982 to calculate standard error on the Wilcoxon
        statistic W, which corresponds to the area under the ROC by trapezoidal
        rule.
        
        @note: The vectors r1 .. r7 correspond to rows of Table II in
        Hanley1982.

        Sets L{W} and L{W_stderr}
        """
        s = self
        # r1 is number of negatives with each score,
        # r2 is number of positives rated higher than each score
        # r3 is number of positives with each score
        # r4 is number of negatives rated lower than each score
        r1 = s.NE
        r2 = s.TP - s.PE
        r3 = s.PE
        r4 = s.TN
        r5 = r1 * r2 + 0.5 * r1 * r3
        r6 = r3 * (r4**2 + r4*r1 + (r1**2)/3)
        r7 = r1 * (r2**2 + r2*r3 + (r3**2)/3)
        N = float(len(s.nscores))
        P = float(len(s.pscores))
        W = r5.sum() / (N*P)
        Q2 = r6.sum() / (P * N**2)
        Q1 = r7.sum() / (N * P**2)
        W_stderr = nx.sqrt((W*(1-W)+(P-1)*(Q1-W**2)+(N-1)*(Q2-W**2))/(P*N))
        #print W, Q1, Q2, W_stderr
        self.W = W
        self.W_stderr = W_stderr


    def _breakeven(self):
        """Calculate break-even point where precision equals recall.
        Sets L{breakeven}, L{bep_index}
        """
        s = self
        diff = nx.absolute(nx.subtract(s.TPR, s.PPV))
        self.bep_index = nx.nonzero(diff == nx.min(diff))[0][0]
        self.breakeven = 0.5*(s.TPR[s.bep_index]+s.PPV[s.bep_index])


    def threshold_maximising(self, vector):
        """Find threshold to maximise the given vector
        @return: The threshold score, and its index in L{uscores}"""
        idx = nx.nonzero(vector == nx.max(vector))[0][0]
        return self.uscores[idx], idx


    def index_for(self, threshold):
        """Calculate index into L{uscores} corresponding to given threshold.
        @return: The highest available threshold less than the specified one,
        and its index in L{uscores}."""
        diffs = self.uscores - threshold
        idx = nx.nonzero(diffs == nx.min(diffs[diffs >= 0]))[0][0]
        return self.uscores[idx], idx


    def matrix_for(self, index):
        """Get confusion matrix at a threshold index into L{uscores}.
        @return: TP, TN, FP, FN representing the confusion matrix."""
        TP = int(self.TP[index])
        TN = int(self.TN[index])
        FP = int(self.FP[index])
        FN = int(self.FN[index])
        return TP, TN, FP, FN


    def metrics_for(self, index):
        """Get L{PerformanceMetrics} at a threshold index into L{uscores}."""
        TP, TN, FP, FN = self.matrix_for(index)
        return PerformanceMetrics(TP, TN, FP, FN, self.alpha, self.utility_r)



class PerformanceMetrics:
    """Performance metrics derived from a particular confusion matrix.
    
    @note: L{PerformanceRange} depends on all attributes being
    numerical (so that comparison operators work).
    
    @group TP, TN, FP, FN, alpha, utility_r: Passed to constructor.
    
    @ivar TP, TN, FP, FN: Confusion matrix.

    @ivar alpha: Weight of precision in F measure calculation.
    
    @ivar utility_r: Weight of a true positive (false positive is -1) (if
    None we use N/P).
    
    @ivar P: Number of relevant items.
    @ivar N: Number of irrelevant items.
    @ivar A: Total number of items (P+N).
    @ivar T: Number of correct classifications.
    @ivar F: Number of incorrect classifications.
    @ivar TPR, FNR, TNR, FPR: Confusion matrix ratios.
    @ivar PPV, NPV: Positive and negative predictive value.
    @ivar accuracy: Equals T/A.
    @ivar enrichment: Equals precision/prevalence.
    @ivar error: Equals F/A.
    @ivar fmeasure: Harmonic mean of TPR and PPV [alpha=0.5]
    @ivar fmeasure_alpha: Alpha-weighted F measure [alpha!=0.5]
    @ivar precision: Equals PPV.
    @ivar prevalence: Equals P/A.
    @ivar recall: Equals TPR.
    @ivar specificity: Equals TNR.
    @ivar fp_tp_ratio: Equals FP/TP.
    """
    
    def __init__(self, TP, TN, FP, FN, alpha=0.5, utility_r=None):
        # Sums of the confusion matrix
        P = TP + FN
        N = TN + FP
        A = P + N
        T = TP + TN
        F = FP + FN
        # Performance ratios
        TPR = TP/P if P > 0 else 0 # TPR = TP/P = sensitivity = recall
        FNR = FN/P if P > 0 else 0 # FNR = FN/P = 1-TP/P = 1-sensitivity = 1-recall
        TNR = TN/N if N > 0 else 0 # TNR = TN/N = specificity
        FPR = FP/N if N > 0 else 0 # FPR = FP/N = 1 - TN/N = 1-specificity
        PPV = TP/(TP+FP) if TP+FP>0 else 1 # PPV=precision
        NPV = TN/(TN+FN) if TN+FN>0 else 1
        # Derived performance ratios
        recall = TPR
        specificity = TNR
        precision = PPV
        accuracy = T/A if A > 0 else 0
        prevalence = P/A if A > 0 else 0
        fp_tp_ratio = FP/TP if TP > 0 else 0
        FDR = 1 - precision
        error = 1 - accuracy
        enrichment = precision / prevalence if prevalence > 0 else 0
        # Utility measure
        if utility_r is None:
            utility_r = N/P
        utility = (utility_r * TP - FP) / (utility_r * P)
        # F measure
        fmeasure, fmeasure_alpha = 0, 0
        if recall > 0 and precision > 0:
            fmeasure = 2 * TPR * PPV / (TPR + PPV)
            fmeasure_alpha = 1.0 / ((alpha/PPV) + ((1-alpha)/TPR))
        update(self, locals())



class PredictedMetrics:
    """Predict the performance metrics vectors for query results
    knowing only the true and false positive rates in testing.
    
    This also requires specifiying the size of the database against
    which the query will be performed, and also the number of relevant
    documents guessed to be present in the database.

    @group Passed to constructor: TPR, FPR, thresholds, relevant, total
    @ivar TPR: True Positive Rate in test corpus at each threshold (increasing)
    @ivar FPR: False Positive Rate in test corpus at each threshold (increasing)
    @ivar thresholds: Threshold scores corresponding to TPR and FPR (decreasing)
    @ivar relevant: Number of relevant articles in database
    @ivar total: Total number of articles in database
    
    @group Calculated in constructor: prevalence, TP, FP, results, precision
    @ivar prevalence: Fraction of relevant articles in database
    @ivar TP: Predicted number of true positives at each threshold
    @ivar FP: Predicted number of false positives at each threshold
    @ivar results: Predicted number of results at each threshold (TP+FP)
    @ivar PPV: Predicted Precision (positive predictive value) at each threshold
    """
    
    def __init__(self, TPR, FPR, thresholds, relevant, total):
        """Constructor, calculates the predicted statistics"""
        prevalence = relevant / total
        TP = TPR * relevant
        FP = FPR * (total - relevant)
        results = TP + FP
        PPV = TP / results
        update(self, locals())



class PerformanceRange:
    """Given a threshold, find the minimum and maximum for the precision,
    recall across the validation folds.

    @group Passed via constructor: pscores, nscores, nfolds, threshold, average
    @ivar pscores: Unsorted scores of positive documents.
    @ivar nscores: Unsorted scores of negative documents.
    @ivar nfolds: Number of cross validation folds
    @ivar threshold: Predict documents above this score to be positive.
    @ivar average: L{PerformanceMetrics} globally estimated using all folds
    
    @ivar TP: Vector for number of TP in each fold
    @ivar TN: Vector for number of TN in each fold
    @ivar FP: Vector for number of FP in each fold
    @ivar FN: Vector for number of FN in each fold
    
    @ivar minimum: L{PerformanceMetrics} with the miminum values across folds
    @ivar maximum: L{PerformanceMetrics} with the maximum values across folds
    """
    
    def __init__(self, pscores, nscores, nfolds, threshold, average):
        """Parameters correspond to instance variables"""
        minimum = copy.copy(average)
        maximum = copy.copy(average)
        update(self, locals())
        self._make_confusion_vectors()
        self._calculate_min_max()


    def _calculate_min_max(self):
        """Finds (min,max) of precision, etc., using the TP/TN/FP/FN vectors
        over the folds."""
        for TP, TN, FP, FN in zip(self.TP, self.TN, self.FP, self.FN):
            metrics = PerformanceMetrics(
                TP, TN, FP, FN, self.average.alpha, self.average.utility_r)
            for key, value in metrics.__dict__.iteritems():
                if value < getattr(self.minimum, key):
                    setattr(self.minimum, key, value)
                if value > getattr(self.maximum, key):
                    setattr(self.maximum, key, value)


    def _make_confusion_vectors(self):
        """Finds TP, TN, FP, FN at the threshold over each validation fold"""
        for vname in ["TP", "TN", "FP", "FN"]:
            setattr(self, vname, nx.zeros(self.nfolds, nx.float32))
        # Recreate the validation partitions in the score vectors
        pstarts, psizes = CrossValidator.make_partitions(
            len(self.pscores), self.nfolds)
        nstarts, nsizes = CrossValidator.make_partitions(
            len(self.nscores), self.nfolds)
        # Calculate confusion matrix within each vector
        for fold, (pstart,psize,nstart,nsize) in \
            enumerate(zip(pstarts,psizes,nstarts,nsizes)):
            self._confusion_matrix(fold, 
                self.pscores[pstart:pstart+psize],
                self.nscores[nstart:nstart+nsize])

    
    def _confusion_matrix(self, fold, pos, neg):
        """Find TP, TN, FP, FN at threshold inside a single validation fold.
        @param fold: Number of the cross validation fold
        @param pos: Scores for relevant articles in the fold
        @param neg: Scores for irrelevant articles in the fold"""
        # Find False Negatives and True Positives
        pos = nx.array(pos)
        pos.sort()
        P = len(pos)
        FN = 0
        while (FN < P) and (pos[FN] < self.threshold):
            FN += 1
        self.FN[fold] = FN
        self.TP[fold] = P - FN # TP+FN=P
        # Find True Negatives and False Positives
        neg = nx.array(neg)
        neg.sort()
        N = len(neg)
        TN = 0
        while (TN < N) and (neg[TN] < self.threshold):
            TN += 1
        self.TN[fold] = TN
        self.FP[fold] = N - TN # TN+FP=N


    def stats_for(self, name):
        """Return tuple of average, minimum and maximum values for the named
        statistic (must be an attribute name in L{PerformanceMetrics}"""
        return (getattr(self.average, name), 
                getattr(self.minimum, name),
                getattr(self.maximum, name))


    def fmt_stats(self, name, places=3):
        """Return a string for the average, minimum and maximum values
        of the named statistic across folds"""
        numfmt = "%%.%df" % places
        if self.nfolds > 1:
            fmtstring = "%s (%s to %s)" % (numfmt,numfmt,numfmt)
            return fmtstring % self.stats_for(name)
        else:
            return numfmts % getattr(self.average, name)

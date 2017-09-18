"""Environment for performing query-based analyses."""

from __future__ import with_statement
from __future__ import division

import codecs
import logging
import numpy as nx
import time
from contextlib import closing
import warnings
warnings.simplefilter("ignore", UserWarning)

from mscanner.configuration import rc
from mscanner.medline import Shelf
from mscanner.medline.Databases import Databases
from mscanner.core.FeatureScores import FeatureScores, FeatureCounts
from mscanner.core import CitationTable, iofuncs
from mscanner.fastscores.ScoreCalculator import ScoreCalculator
from mscanner.fastscores.FeatureCounter import FeatureCounter


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


class QueryManager:
    """Class for performing a single query

    @group Passed via constructor: outdir, dataset, limit, env, threshold, 
    prior, mindate, maxdate, t_mindate, t_maxdate
    
    @ivar outdir: Path to directory for output files, which is created if it
    does not exist.
    
    @ivar dataset: Title of the dataset to use when printing reports
    
    @ivar limit: Maximum number of results (may be fewer due to threshold)
    
    @param env: L{Databases} to use (if None, we open them just for us).

    @ivar threshold: Decision threshold for the classifier (default should be 0).
    Use None to retrieve everything up to the result limit.
    
    @ivar prior: Prior score to add to all article scores.  Use None
    to estimate from the relative sizes of the input data.
    
    @ivar mindate, maxdate: Min/max YYYYMMDD integer for query results (ignore
    articles outside this range).
    
    @ivar t_mindate, t_maxdate: Min/max YYYYMMDD integer for counting feature
    occurrences in Medline background corpus (defaults to mindate, maxdate).
    
    
    
    @ivar timestamp: Time at the start of the operation.
    
    @ivar pmids: Sequence of input PubMed IDs (list/vector) from L{_load_input}
    
    @ivar featinfo: FeatureScores with feature scores, from L{query}
    
    @ivar inputs: List of (pmid, score) for input PMIDs
    
    @ivar results: List of (pmid, score) for result PMIDs
    
    @ivar notfound_pmids: List of input PMIDs not found in the database
    
    @ivar logfile: logging.FileHandler for logging to output directory
    """


    def __init__(self, outdir, dataset, limit, env=None, 
                 threshold=None, prior=None, 
                 mindate=None, maxdate=None, 
                 t_mindate=None, t_maxdate=None):
        # Set attributes from parameters
        self.outdir = outdir
        self.dataset = dataset
        self.limit = limit
        self.threshold = threshold
        self.prior = prior
        self.mindate = mindate
        self.maxdate = maxdate
        self.t_mindate = mindate if t_mindate is None else t_mindate
        self.t_maxdate = maxdate if t_maxdate is None else t_maxdate
        # Create output dir
        if not outdir.exists():
            outdir.makedirs()
            outdir.chmod(0777)
        # Set more attributes
        self.timestamp = time.time()
        self.env = env if env else Databases()
        self.pmids = None
        self.featinfo = None
        self.inputs = None
        self.results = None
        self.notfound_pmids = None
        self.logfile = iofuncs.open_logfile(self.outdir/rc.report_logfile)


    def __del__(self):
        iofuncs.close_logfile(self.logfile)


    def query(self, input, train_exclude=None):
        """Performs a query given PubMed IDs as input
        
        @param input: Path to a list of PubMed IDs, or the list itself.
        
        @param train_exclude: PMIDs to exclude from background when training
        """
        logging.info("START: Query for %s", self.dataset)
        if not self._load_input(input):
            return
        self._make_feature_info(train_exclude)
        try:
            self._load_results()
        except IOError: 
            self._make_results()
            self._save_results()
        
        
    def _load_input(self, input):
        """Construct L{pmids} and L{notfound_pmids}.
        
        @param input: Path to file listing PubMed IDs, or something convertible
        to a set PubMed IDs.
        
        @return: True on success, False on failure."""
        if isinstance(input, basestring):
            logging.info("Loading PubMed IDs from %s", input.basename())
            self.pmids, self.notfound_pmids, exclude = \
                iofuncs.read_pmids_careful(input, self.env.featdb)
            iofuncs.write_pmids(
                self.outdir/rc.report_input_broken, self.notfound_pmids)
        else:
            self.pmids = input # Hope its a list/vector
        if len(self.pmids) > 0:
            return True
        else:
            logging.error("No valid PubMed IDs in %s", input.basename())
            iofuncs.no_valid_pmids_page(
                self.outdir/rc.report_index, self.dataset, self.notfound_pmids)
            return False


    def _make_feature_info(self, train_exclude=None):
        """Generate the L{featinfo} attribute using the L{pmids}
        as examples of relevant citations.
        
        @param train_exclude: PMIDs to exclude from background when training
        """
        logging.info("Making scores for %d features", len(self.env.featmap))
        # Parameters for the FeatureScores instance
        self.featinfo = FeatureScores(
            featmap = self.env.featmap,
            pseudocount = rc.pseudocount,
            mask = self.env.featmap.get_type_mask(rc.exclude_types),
            make_scores = rc.make_scores,
            get_postmask = rc.get_postmask)
        
        # Count features from the positive articles
        pdocs = len(self.pmids)
        pos_counts = FeatureCounts(
            len(self.env.featmap), self.env.featdb, self.pmids)
        
        # Background is all of Medline minus input examples
        if self.t_mindate is None and self.t_maxdate is None:
            logging.info("Background PMIDs = Medline - input PMIDs")
            ndocs = self.env.featmap.numdocs - len(self.pmids)
            neg_counts = nx.array(self.env.featmap.counts, nx.int32) - pos_counts
        
        # Background is Medline within a specific date range
        else:
            logging.info("Background PMIDs = Medline between %s and %s", 
                         str(self.t_mindate), str(self.t_maxdate))
            # Have the option to exclude more than just training PMIDs
            if train_exclude is None:
                train_exclude = self.pmids
            ndocs, neg_counts = FeatureCounter(
                docstream = rc.featurestream,
                numdocs = self.env.featmap.numdocs,
                numfeats = len(self.env.featmap),
                mindate = self.t_mindate,
                maxdate = self.t_maxdate,
                exclude = train_exclude).c_counts()
        
        # Evaluating feature scores from the counts
        self.featinfo.update(pos_counts, neg_counts, pdocs, ndocs, self.prior)


    def _load_results(self):
        """Read L{inputs} and L{results} from the report directory"""
        self.inputs = list(iofuncs.read_scores(self.outdir/rc.report_input_scores))
        self.results = list(iofuncs.read_scores(self.outdir/rc.report_result_scores))
        logging.info("Loaded saved results for %s", self.dataset)


    def _save_results(self):
        """Write L{inputs} and L{results} with scores in the report directory."""
        iofuncs.write_scores(self.outdir/rc.report_input_scores, 
                             self.inputs, sort=True)
        iofuncs.write_scores(self.outdir/rc.report_result_scores, 
                             self.results, sort=True)


    def _make_results(self):
        """Perform the query to generate L{inputs} and L{results}"""
        # Calculate decreasing (score, PMID) for input PMIDs
        logging.info("Finding scores for %d input documents", len(self.pmids))
        self.inputs = zip(
            self.featinfo.scores_of(self.env.featdb, self.pmids), 
            self.pmids)
        self.inputs.sort(reverse=True)
        # Calculate results as decreasing (score, PMID)
        logging.info("Find scores of Medline between dates %s to %s", 
                     str(self.mindate), str(self.maxdate))
        self.results = ScoreCalculator(
            rc.featurestream,
            self.env.featmap.numdocs,
            self.featinfo.scores,
            self.featinfo.base+self.featinfo.prior,
            self.limit,
            self.threshold,
            self.mindate,
            self.maxdate,
            set(self.pmids),
            ).score()
        logging.info("Got %d results (limit %d)", len(self.results), self.limit)


    def write_report(self, maxreport=None):
        """Write the HTML report for the query results
        
        @note: Article database lookups are carried out beforehand because
        lookups while doing template output is extremely slow.
        
        @param maxreport: Largest number of records to write to the HTML reports
        (L{maxreport} may override the result limit).
        """
        # Cancel report if there are no results
        if self.results is None: return
        
        logging.debug("Creating report for data set %s", self.dataset)
        
        # By default report all results
        if maxreport is None or maxreport > len(self.results):
            maxreport = len(self.results)
        
        logging.debug("Writing features to %s", rc.report_term_scores)
        with codecs.open(self.outdir/rc.report_term_scores, "wb", "utf-8") as f:
            self.featinfo.write_csv(f)
        
        logging.debug("Writing citations to %s", rc.report_input_citations)
        self.inputs.sort(reverse=True)
        inputs = [ (s,self.env.artdb[str(p)]) for s,p in self.inputs]
        CitationTable.write_citations(
            "input", self.dataset, inputs, 
            self.outdir/rc.report_input_citations, 
            rc.citations_per_file)
        
        logging.debug("Writing citations to %s", rc.report_result_citations)
        self.results.sort(reverse=True)
        outputs = [ (s,self.env.artdb[str(p)]) for s,p in self.results[:maxreport] ]
        CitationTable.write_citations(
            "output", self.dataset, outputs,
            self.outdir/rc.report_result_citations, 
            rc.citations_per_file)
        
        # Write ALL output citations to a single HTML, and a zip file
        if len(outputs) > 0:
            logging.debug("Writing citations to %s", rc.report_result_all)
            outfname = self.outdir/rc.report_result_all
            zipfname = str(outfname + ".zip")
            CitationTable.write_citations(
                "output", self.dataset, outputs, outfname, len(outputs))
            from zipfile import ZipFile, ZIP_DEFLATED
            with closing(ZipFile(zipfname, "w", ZIP_DEFLATED)) as zf:
                zf.write(str(outfname), str(outfname.basename()))
        
        # Index.html
        logging.debug("FINISH: Writing %s for %s", rc.report_index, self.dataset)
        from Cheetah.Template import Template
        with iofuncs.FileTransaction(self.outdir/rc.report_index, "w") as ft:
            Template(file=str(rc.templates/"results.tmpl"), 
                     filter="Filter", searchList=dict(QM=self)).respond(ft)

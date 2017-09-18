"""Configuration for MedScanner

Some parameters change while the program is running, such as the query and
validation parameters.

Parameters can be made to depend on others by using lambda, which the rc object
auto-calls those so they appear as normal data attributes."""


from path import path
from mscanner.core.Storage import RCStorage


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


rc = RCStorage()
"""Global configuration options"""

#### PATH CONFIGURATION

## Path to MScanner source directory
rc.sources = path(__file__).dirname()
## Path to directory for report templates
rc.templates = lambda: rc.sources / "core" / "templates"
## Path to working information directory
rc.working = lambda: rc.sources.parent / "data"
## Path to cache directory
rc.cache = lambda: rc.working / "cache"
## Path to web directory
rc.htdocs = lambda: rc.sources / "htdocs"
## DB environment directory
rc.db_env_home = lambda: rc.cache / "db_home"
## DB of article objects
rc.articledb = lambda: rc.cache / "articles.db"
## Path for list of of article IDs
rc.articlelist = lambda: rc.cache / "articles.txt"
## Path for number of articles
rc.narticles = lambda: rc.cache / "narticles.txt"
## Path for DB of term features for each article
rc.featuredb = lambda: rc.cache / "features.db"
## Path for binary stream of PMIDs and feature arrays
rc.featurestream = lambda: rc.cache / "features.stream"
## Path for feature<->ID mapping
rc.featuremap = lambda: rc.cache / "featuremap.txt"
## Path for list of files already processed
rc.processed = lambda: rc.cache / "processed.txt"
## Path for directory with compressed Medline
rc.medline = lambda: rc.working / "medline"
## Path for log file
rc.logfile = lambda: rc.cache / "lastlog.txt"
## Path to corpora directory
rc.corpora = lambda: rc.working / "corpora"
## Path to outputs directory
rc.web_report_dir = lambda: rc.htdocs / "static" / "output"
## Path to the descriptor queue
rc.queue_path = lambda: rc.working / "queue"

### ALL OUTPUTS
## Name of index file
rc.report_index = path("index.html")
## Name of descriptor file
rc.report_descriptor = path("descriptor.txt")
## Name of term score file
rc.report_term_scores = path("terms.csv")
## Name of file to echo the log to
rc.report_logfile = path("logging.txt")

### QUERY
## Name of list of scores of input PMIDs
rc.report_input_scores = path("inputs.txt")
## Name of list of broken input PMIDs
rc.report_input_broken = path("broken.txt")
## Name of result score file
rc.report_result_scores = path("results.txt")
## Name of file with citation records for the input
rc.report_input_citations = path("inputs.html")
## Name of first page with citation records for the output
rc.report_result_citations = path("results.html")
## Name of file with *ALL* outupt citation records
rc.report_result_all = path("all_results.html")
## Name of zip file with ALL output citations records
rc.report_result_all_zip = rc.report_result_all + ".zip"

### VALIDATION
## Name of file with positive PMIDs and scores
rc.report_positives = path("positives.txt")
## Name of file with broken positive PMIDs
rc.report_positives_broken = path("positives_broken.txt")
## Name of file with negative PMIDs and scores
rc.report_negatives = path("negatives.txt")
## Name of file with excluded negative PMIDs
rc.report_negatives_exclude = path("negatives_exclude.txt")
## Name of histogram file
rc.report_artscores_img = path("artscores.png")
## Name of feature score density file
rc.report_featscores_img = path("featscores.png")
## Name of ROC curve file
rc.report_roc_img = path("roc.png")
## Name of PR curve file
rc.report_prcurve_img = path("prcurve.png")
## Name of PRF vs threshold file
rc.report_fmeasure_img = path("fmeasure.png")
## Name of predicted precision graph
rc.report_prediction_img = path("prediction.png")

#### Non-Path parameters

## Whether to use transactions while updating
rc.use_transactions = False
## Number of seconds to pause before next file while updating
rc.save_delay = 3
## Server for sending e-mails
rc.smtpserver = "smtp.uct.ac.za" # "smtp.stanford.edu"
## Email to send website queries to
rc.webmaster_email = "graham.poulter@gmail.com"
## Base directory for the website
rc.siteurl = "http://mscanner.stanford.edu"
## Whether to link to .js and .css files instead of including them
rc.link_headers = False
## 0<Alpha<1.  Alpha=0.5 maximises standard F-Measure.
rc.alpha = 0.5
## The utility of retrieving a positive article (defaults to N/P)
rc.utility_r = None
## Number of citations per output file
rc.citations_per_file = 250

## Parameters affecting FeatureScores 

## Per-term pseudocount to use (None for background frequency)
rc.pseudocount = None
## Types of features to exclude
rc.exclude_types = []
## Method name for calculating feature probabilities
rc.make_scores = "scores_bayes"
## Method name for calculating mask after scores (may be None)
rc.get_postmask = None
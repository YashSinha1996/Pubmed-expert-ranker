"""I/O functions - for reading and writing certain file formats."""

from __future__ import with_statement
from __future__ import division

import numpy as nx
from itertools import izip

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


def write_pmids(filename, pmids):
    """Write list of PMIDs one per line to file"""
    with open(filename, "w") as f:
        f.write("\n".join(str(s) for s in pmids))


def read_pmids(filename):
    """Yield PubMed IDs listed one per line in a file. Empty lines and lines
    starting with # are ignored."""
    with open(filename) as f:
        for line in f:
            sline = line.strip()
            if sline == "" or sline.startswith("#"):
                continue
            yield int(sline.split()[0])


def read_pmids_array(filename):
    """Read array of PubMed IDs one per line from file"""
    return nx.array(read_pmids(filename), nx.int32)


def read_pmids_careful(filename, include=None, exclude=[]):
    """Reads array of PubMed IDs one per line, with checking.

    @param include: Only return members of this set (other PubMed IDs are
    considered "broken").

    @param exclude: Do not return members of this set
    
    @return: Arrays for result, broken and excluded PubMed IDs
    """
    results = []
    broken = []
    excluded = []
    for pmid in read_pmids(filename):
        if include is not None and pmid not in include:
            broken.append(pmid)
        elif pmid in exclude:
            excluded.append(pmid)
        else:
            results.append(pmid)
    return tuple(nx.array(a, nx.int32) for a in [results,broken,excluded])


def write_lines(filename, items, desc=None, sep="\t"):
    """Basic function for writing sequence of items to text files
    
    @param filename: Name of file to write to

    @param items: Sequence of items convertible using str().  Tuples
    are written as separated values.
    
    @param desc: Optional string to write at the top of the file

    @param sep: Separator for values
    """
    with open(filename, "w") as f:
        if desc is not None:
            f.write(desc.strip()+"\n")
        for item in items:
            if hasattr(item, "__iter__"):
                f.write(sep.join([str(x) for x in item]))
            else:
                f.write(str(item))
            f.write("\n")


def write_scores(filename, pairs, sort=False):
    """Write scores and PubMed IDs to file
    
    @param pairs: Iterable over (score, PMID)

    @param sort: If True, write them in decreasing order of score
    """
    sorted_pairs = sorted(pairs, reverse=True) if sort else pairs
    filename.write_lines("%-10d %f" % (p,s) for s,p in sorted_pairs)


def read_scores(filename):
    """Yield (score, pmid) pairs from file written by L{write_scores}"""
    with open(filename, "r") as f:
        for line in f:
            sline = line.strip()
            if sline == "" or sline.startswith("#"):
                continue
            splits = sline.split()
            yield float(splits[1]), int(splits[0])
    

def read_scores_array(filename):
    """Reads a file written by L{write_scores}
    
    @param filename: Path to file from which to read the pmid,score

    @return: An array of PubMed IDs, and an array of scores"""
    scores, pmids = izip(*read_scores(filename))
    return nx.array(pmids,nx.int32), nx.array(scores,nx.float32)


def no_valid_pmids_page(filename, dataset, pmids):
    """Print an error page when no valid PMIDs were found
    
    @param filename: Path to output file

    @param pmids: List of any provided PMIDs (all invalid)
    """
    from Cheetah.Template import Template
    from mscanner.configuration import rc
    with FileTransaction(filename, "w") as ft:
        page = Template(file=str(rc.templates/"notfound.tmpl"))
        page.dataset = dataset
        page.notfound_pmids = pmids
        page.respond(ft)


class FileTransaction(file):
    """Transaction for Cheetah templates to output direct-to-file.
    
    Cheetah defaults to DummyTransaction which creates a huge list and
    joins them up to create a string.  This is way slower than writing to
    file directly.
    
    Usage::
        with FileTransaction("something.html","wb") as ft:
            Template().respond(ft)
    """
    
    def __init__(self, *args, **kw):
        """Open the file, same parameters as for the builtin"""
        file.__init__(self, *args, **kw)
        self.response = self

    def writeln(self):
        """Write a line of output"""
        self.write(txt)
        self.write('\n')

    def getvalue(self):
        """Not implemented"""
        return None

    def __call__(self):
        return self



def start_logger(console=True, logfile=True):
    """Set up logging to file or console
    @param console: If True, log to the console.
    @param logfile: If True, log to rc.logfile."""
    # Configure the root logger to print everything
    from mscanner.configuration import rc
    import logging
    rootlog = logging.getLogger()
    rootlog.setLevel(logging.DEBUG)
    format = logging.Formatter("%(asctime)-9s %(levelname)-8s %(message)s", "%H:%M:%S")
    # Configure primary file logger
    if logfile:
        filelog = logging.FileHandler(rc.logfile, "a")
        filelog.setFormatter(format)
        rootlog.addHandler(filelog)
    # Configure logging to console
    if console:
        console = logging.StreamHandler()
        console.setFormatter(format)
        rootlog.addHandler(console)


def open_logfile(filename, logname="", mode="a"):
    """Add a file handler to a logger using my default format.
    @param filename: File to write to
    @param logname: Name of log to write to (default '')
    @param mode: File open mode (default 'a')
    @return: The logging.FileHandler instance
    """
    import logging
    logger = logging.getLogger(logname)
    handler = logging.FileHandler(filename, mode)
    handler.setFormatter(logging.Formatter(
        "%(asctime)-9s %(levelname)-8s %(message)s", "%H:%M:%S"))
    logger.addHandler(handler)
    return handler


def close_logfile(handler, logname=""):
    """Remove and close a log file previously added with L{open_logfile}.  Does
    nothing if called a second time.
    @param handler: FileHandler instance to remove
    @param logname: Name of the logger (defaults to '')
    """
    import logging
    logger = logging.getLogger(logname)
    if handler in logger.handlers:
        logger.removeHandler(handler)
    if not handler.stream.closed:
        handler.close()

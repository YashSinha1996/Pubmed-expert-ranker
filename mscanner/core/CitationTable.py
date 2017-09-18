"""Writes HTML pages with interactive citation tables"""

from __future__ import with_statement
from __future__ import division

from mscanner.configuration import rc
from mscanner.core import iofuncs
from Cheetah.Template import Template

import warnings
warnings.simplefilter("ignore", UserWarning)


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


def write_citations(mode, dataset, citations, fname, perfile):
    """Writes a set of HTML files containing citation records
    
    @param mode: 'input' or 'output'
    
    @param dataset: Dataset title to print at the top of the page

    @param citations: List of (score, Article) in descending order of score

    @param fname: Basic name for output files. ../results.html becomes
    ../results.html, ../results_02.html, ../results_03.html etc.)

    @param perfile: Number of citations per file (the very last file 
    may however have up to 2*perfile-1 citations)
    """
    # List of ranks where each file's citation records start
    starts = range(0, len(citations), perfile)
    # If the last file is less than half full, we concat to second-last
    if len(starts)>1 and (len(citations)-starts[-1]) < (perfile//2):
        del starts[-1]
    # List of HTML files containing the citations
    from path import path
    fnames = [path(fname.basename())] # First file is the basic name
    fnames += [path(fname.namebase + ("_%02d" % x) + fname.ext)
                for x in range(2, 1+len(starts))]
    values = dict()
    page = Template(
        file=str(rc.templates/"citations.tmpl"), 
        filter="Filter", searchList=[values])
    for count, start in enumerate(starts):
        if count+1 < len(starts):
            towrite = citations[start:start+perfile]
        else:
            towrite = citations[start:]
        values.update(dict(
            cite_table = CitationTable(start+1, towrite),
            dataset = dataset,
            mode = mode, 
            report_length = len(towrite),
            filelist = fnames,
            cur_idx = count))
        with iofuncs.FileTransaction(fname.dirname()/fnames[count], "w") as ft:
            page.respond(ft)
        


def CitationTable(startrank, citations):
    """Create an HTML table of citations (uses ElementTree)
    
    We use Cheetah when there is more HTML than logic, and ElementTree when
    there is more logic than HTML. The old Cheetah template was getting
    cluttered from all the logic. This way also outputs less whitespace.
    
    @param startrank: Rank of the first article in the table

    @param citations: Iterable of (score, Article) in decreasing order of score
    
    @return: HTML string for the <table> element containing citations
    """
    from xml.etree.cElementTree import ElementTree, Element, SubElement
    table = Element("table", id="citations")
    ncols = 9 # Number of columns in the table
    cg = SubElement(table, "colgroup")
    SubElement(cg, "col", {"class":"classification"})
    SubElement(cg, "col", {"class":"rank"})
    SubElement(cg, "col", {"class":"score"})
    SubElement(cg, "col", {"class":"pmid"})
    SubElement(cg, "col", {"class":"date"})
    SubElement(cg, "col", {"class":"author"})
    SubElement(cg, "col", {"class":"abstract"})
    SubElement(cg, "col", {"class":"title"})
    SubElement(cg, "col", {"class":"journal"})
    thead = SubElement(table, "thead")
    tr = SubElement(thead, "tr")
    SubElement(tr, "th", title="Classification").text = "C"
    SubElement(tr, "th", title="Rank").text = "R"
    SubElement(tr, "th").text = "Score"
    SubElement(tr, "th").text = "PMID"
    SubElement(tr, "th").text = "Date"
    SubElement(tr, "th", title="Author").text = "Au"
    SubElement(tr, "th", title="Abstract").text = "Ab"
    SubElement(tr, "th").text = "Title"
    SubElement(tr, "th").text = "Journal"
    tbody = SubElement(table, "tbody")
    ncbi = "http://www.ncbi.nlm.nih.gov/entrez/query.fcgi?"
    ncbi_pmid = ncbi+"cmd=Retrieve&db=pubmed&list_uids="
    ncbi_jour = ncbi+"CMD=search&DB=journals&term="
    for idx, (score, art) in enumerate(citations):
        pmid = str(art.pmid)
        tr = SubElement(tbody, "tr", {"class":"main"}, id="P"+pmid)
        # Classification
        SubElement(tr, "td").text = " "
        # Rank
        SubElement(tr, "td").text = str(idx+startrank)
        # Score
        SubElement(tr, "td").text = "%.2f" % score
        # PMID
        td = SubElement(tr, "td")
        SubElement(td, "a", href=ncbi_pmid+pmid).text = pmid
        # Date the record acquired "Medline" status
        td = SubElement(tr, "td")
        td.text = "%04d.%02d.%02d" % art.date_completed
        # Expand Author button
        td = SubElement(tr, "td")
        td.text = "+" if art.authors else " "
        # Expand Abstract button
        td = SubElement(tr, "td")
        td.text = "+" if art.abstract else " "
        # Title
        td = SubElement(tr, "td")
        td.text = art.title
        # ISSN
        td = SubElement(tr, "td")
        a = SubElement(td, "a")
        a.text = " "
        if art.issn:
            a.set("href", ncbi_jour+art.issn)
            a.text = art.journal if art.journal else art.issn
        # Expanded authors
        tr = SubElement(tbody, "tr", {"class":"author"})
        td = SubElement(tr, "td", {"colspan":str(ncols)})
        td.text = " "
        if art.authors:
            for initials, lastname in art.authors:
                if initials: td.text += initials + " "
                if lastname: td.text += lastname + ", "
        # Expanded Abstract
        tr = SubElement(tbody, "tr", {"class":"abstract"})
        td = SubElement(tr, "td", {"colspan":str(ncols)})
        td.text = " "
        if art.abstract:                        
            td.text = art.abstract
    import cStringIO
    s = cStringIO.StringIO()
    # Tell silly etree to use UTF-8 and not "us-ascii" for output
    ElementTree(table).write(s, "utf-8") 
    return s.getvalue()

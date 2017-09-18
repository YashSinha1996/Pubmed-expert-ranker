"""web.py handler for the output listing page"""

__copyright__ = "2007 Graham Poulter"
__author__ = "Graham Poulter <http://graham.poulter.googlepages.com>"
__license__ = "GPL"

import web
import md5

import output, query_logic
from mscanner.htdocs import forms, queue
from mscanner.configuration import rc


OutputForm = forms.Form(
    forms.Hidden(
        "operation",
        forms.Validator(lambda x: x in ["download", "delete"], "Invalid op")),
    
    forms.Checkbox(
        "omit_mesh",
        forms.checkbox_validator),
    
    forms.Hidden(
        "dataset",
        query_logic.dataset_validator),
    
    forms.Hidden(
        "delcode",
        query_logic.delcode_validator),
)
"""Structure for the form on the outputs page"""



class OutputPage:
    """Page linking to outputs"""
    
    def print_page(self, page):
        """Add the final version of the queue and output the page"""
        page.queue = queue.QueueStatus()
        page.visible = [ d for d in page.queue.donelist 
            if "hidden" not in d or d.hidden == False ]
        print page


    def GET(self):
        """Just list the available output directories"""
        web.header('Content-Type', 'text/html; charset=utf-8') 
        page = output.output()
        self.print_page(page)
        
        
    def POST(self):
        """Attempt to download or delete one of the outputs"""
        web.header('Content-Type', 'text/html; charset=utf-8') 
        page = output.output()
        oform = OutputForm()
        
        # Errors in the form
        if not oform.validates(web.input()):
            e = ["<li>%s: %s</li>\n" % (n,e) for n,e in 
                 oform.errors.iteritems() if e is not None]
            page.errors = "".join(["<p>Errors</p><ul>\n"]+e+["</ul>\n"])
            self.print_page(page)
            return
        
        # The thing we are trying to operate on
        page.target = oform.d.dataset 
        
        # Deleting something
        if oform.d.operation == "delete":
            target = page.target
            q = queue.QueueStatus()
            if target not in q:
                page.delete_error = "there is no task with that name."
            elif q.status[target] == q.RUNNING:
                page.delete_error = "MScanner is busy with the task."
            elif q.status[target] in [q.WAITING, q.DONE]:
                md5code = md5.new(oform.d.delcode).hexdigest()
                if "delcode" in q[target] and md5code != q[target].delcode:
                    page.delete_error = "incorrect deletion code."
                else:
                    if q.status[target] == q.DONE:
                        try:
                            queue.delete_output(target)
                        except OSError, e:
                            page.delete_error = str(e)
                    elif q.status[target] == q.WAITING:
                        try:
                            q[target]._filename.remove()
                        except OSError, e:
                            page.delete_error = str(e)
            self.print_page(page)
        
        # Save the output directory as a zip file for download
        elif oform.d.operation == "download":
            q = queue.QueueStatus()
            if page.target not in q or q.status[page.target] is not q.DONE:
                page.download_error = "Specified output is not available"
                self.print_page(page)
            else:
                outdir = rc.web_report_dir / page.target
                outfile = outdir / (page.target + ".zip")
                if not outfile.exists():
                    from zipfile import ZipFile, ZIP_DEFLATED
                    zf = ZipFile(str(outfile), "w", ZIP_DEFLATED)
                    for fpath in outdir.files():
                        # Omit existing zip files
                        if fpath.endswith(".zip"):
                            continue
                        # Omit MeSH terms if the user requests it
                        if fpath.basename() == rc.report_term_scores:
                            if forms.ischecked(oform.d.omit_mesh):
                                continue
                        # Omit all-in-one result file
                        if fpath.basename() == rc.report_result_all:
                            continue
                        zf.write(str(fpath), str(fpath.basename()))
                    zf.close()
                    outfile.chmod(0777)
                ds = web.urlquote(page.target)
                web.seeother("static/output/" + ds + "/" + ds + ".zip")
            

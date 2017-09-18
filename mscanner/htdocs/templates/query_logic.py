"""web.py handler for the query submission page"""

__copyright__ = "2007 Graham Poulter"
__author__ = "Graham Poulter <http://graham.poulter.googlepages.com>"
__license__ = "GPL"

import web
import time
import md5
import sys

import query
from mscanner.htdocs import forms, queue
from mscanner.configuration import rc


def parse_pmids(pmids):
    """Parse a string into a list of integer PubMed IDs"""
    return [int(y) for y in pmids.split()]


delcode_validator = forms.RegexValidator(
    r"^[ a-zA-Z0-9.;:_-]{0,10}$", 
    "Should be 0-10 characters long, containing "+
    "only letters, numbers and .;:,_- punctuation.")
"""Checks deletion code for valid format"""


dataset_validator = forms.RegexValidator(
    r"^[ a-zA-Z0-9.,;:_-]{1,30}$",
    "Should be 1-30 characters long, containing "+
    "only letters, numbers and .,;:_- punctuation.")
"""Checks task name for valid format"""



def parse_date(date_code):
    """Convert YYYY/MM/DD date string to YYYYMMDD integer."""
    year, month, day = date_code.split("/")
    date = int("%04d%02d%02d" % (int(year),int(month),int(day)))
    return date if date >= 19650101 else None


def date_is_valid(date_code):
    """Must be a YYYY/MM/DD date string, before today"""
    try:
        date = parse_date(date_code)
        yesterday = int(time.strftime("%Y%m%d"))-1
        return (date is None or date < yesterday)
    except:
        return False


def task_does_not_exist(dataset):
    """True if task does not exist in queue or output directory"""
    return not task_exists(dataset)


def task_exists(dataset):
    """True if task exists in queue or output directory"""
    return (rc.queue_path / dataset).isfile() or\
           (rc.web_report_dir / dataset).isdir()


QueryForm = forms.Form(
    forms.Hidden(
        "captcha",
        forms.Validator(
            lambda x: x == "orange", "Should be the word 'orange'"),
        label="Enter the word 'orange'"),
    
    forms.Textarea(
        "positives", 
        forms.Validator(lambda x: len(parse_pmids(x)) > 0,
            "Should be numbers separated by line breaks"),
        label="Input Citations", rows=3, cols=10),
    
    forms.Textbox(
        "dataset", 
        dataset_validator, 
        forms.Validator(task_does_not_exist, "Task already exists"),
        label="Task Name", size=30),
    
    forms.Textbox(
        "delcode", delcode_validator, label="Deletion Code", size=8),
    
    forms.Checkbox(
        "hidden", forms.checkbox_validator, label="Hide output"),
    
    forms.Textbox(
        "limit", 
        forms.Validator(lambda x: 100 <= int(x) <= 10000,
            "Should be between 100 and 10000."),
        label="Result limit"),
    
    forms.Textbox(
        "mindate", 
        forms.Validator(date_is_valid, 
        "Date should be YYYY/MM/DD, and the day before yesterday at latest."),
        label="Minimum date", size=12),

    forms.Textbox(
        "prevalence", 
        forms.Validator(lambda x: x.strip() == "" or 1e-6 <= float(x) <= 0.1,
            "Should be empty, or a number between 0.000001 (10^-6) and 0.1"),
        label="Estimated prevalence", size=8),
    
    forms.Textbox(
        "minscore", 
        forms.Validator(lambda x: -1000 <= float(x) <= 1000,
            "Should be between -1000 and +1000."),
        label="Minimum score", size=8),
    
    forms.Textbox(
        "numnegs", 
        forms.Validator(lambda x: 100 <= int(x) <= 100000,
            "Should be between 100 and 100000."),
        label="Number of Negatives", size=8),
    
    forms.Radio(
        "operation",
        [ ("retrieval", "Medline retrieval operation"), 
          ("validate", "Cross validation operation") ],
        forms.Validator(lambda x: x in ["retrieval", "validate"], 
                        "Invalid operation")),
)
"""Structure of the query form"""


# Initial values to fill into the form (see queue.py for meanings)
form_defaults = dict(
    captcha = "orange",
    delcode = "",
    dataset = "",
    hidden = False,
    limit = 1000,
    mindate = "0000/00/00",
    minscore = "0",
    numnegs = 50000,
    operation = "retrieval",
    positives = "",
    prevalence = "",
)
"""Default values for the query form"""



class QueryPage:
    """Submission form for queries or validation"""
    
    def GET(self):
        """Print the query form, filled with default values"""
        web.header('Content-Type', 'text/html; charset=utf-8') 
        page = query.query()
        page.inputs = QueryForm()
        page.inputs.fill(form_defaults)
        print page


    def POST(self):
        """Submit the query form, maintains previous values"""
        web.header('Content-Type', 'text/html; charset=utf-8') 
        qform = QueryForm()
        if qform.validates(web.input()):
            # Add a descriptor to the queue
            inputs = qform.d
            inputs.submitted = time.time()
            inputs.hidden = forms.ischecked(inputs.hidden)
            # MD5 hash the deletion code
            delcode_plain = inputs.delcode
            inputs.delcode = md5.new(delcode_plain).hexdigest()
            # Parse the date string to integer
            inputs.mindate = parse_date(inputs.mindate)
            # Check for default prevalence
            if inputs.prevalence.strip() == "":
                inputs.prevalence = None 
            queue.write_descriptor(rc.queue_path / inputs.dataset, 
                                   parse_pmids(inputs.positives), inputs)
            # Show status page for the task
            time.sleep(0.05) # So we show up in the queue
            web.seeother("status?dataset=%s;delcode=%s" % 
                         (inputs.dataset, web.urlquote(delcode_plain)))
        else:
            # Errors in the form, print it again
            page = query.query()
            page.queue = queue.QueueStatus(with_done=True)
            page.inputs = qform
            print page

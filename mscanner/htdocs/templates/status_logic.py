"""web.py handler for the status page"""

__copyright__ = "2007 Graham Poulter"
__author__ = "Graham Poulter <http://graham.poulter.googlepages.com>"
__license__ = "GPL"

import web

import status, query_logic
from mscanner.htdocs import forms, queue
from mscanner.configuration import rc


StatusForm = forms.Form(
    forms.Hidden(
        "operation",
        forms.Validator(lambda x: x == "delete", "Invalid operation")),
    
    forms.Textbox(
        "dataset",
        query_logic.dataset_validator,
        forms.Validator(query_logic.task_exists, "Task does not exist"),
        label="Task name"
        ),
    
    forms.Textbox(
        "delcode",
        query_logic.delcode_validator,
        label="Deletion code"
        ),
)
"""Structure for the delete-this-task form on the status page"""



class StatusPage:
    """Lists the current status of MScanner and a given task.
    
    If the dataset and delcode parameters are given over the web,
    it provides a form for deleting the specified task.
    """
    
    def GET(self):
        """Print the status page"""
        web.header('Content-Type', 'text/html; charset=utf-8') 
        page = status.status()
        page.queue = queue.QueueStatus()
        page.log_lines = rc.logfile.lines()[-30:]
        page.inputs = StatusForm()
        dataset = "" # The task to print the status for
        if page.queue.running is not None:
            dataset = page.queue.running.dataset
        page.inputs.fill({"dataset":dataset, "delcode":"", "operation":"delete"})
        # Have we been given a dataset to print status for?
        web_inputs = web.input()
        if "dataset" in web_inputs:
            web_inputs.operation = "delete"
            if "delcode" not in web_inputs:
                web_inputs.delcode = "" 
            page.inputs.validates(web_inputs)
        print page

#!/export/home/medscan/local32/bin/python2.5

"""Simple tests using the web.py framework

Usage::
    python testing.py

Which starts the built-in web.py server on localhost:8080
"""

import sys
sys.path.insert(0,"/export/home/medscan/source")
from mscanner import configuration

import web
web.webapi.internalerror = web.debugerror
import forms
import pprint

def pformat(obj):
    """Nicely format any python object"""
    return web.websafe(pprint.pformat(obj))

urls = (
    '/hello/(.*)', 'HelloPage',
    '/form', 'FormPage',)

class HelloPage:
    """Simple page, e.g. http://localhost:8080/hello/joe?times=5"""
    def GET(self, name):
        i = web.input(times=1)
        if not name:
            name = 'world'
        for c in range(int(i.times)):
            print 'Hello,', name+'!'

form_template = """
<html>
<head>
<title>Test Form</title
<style type="text/css">
th { text-align: left; background-color: #EEEEEE; }
tr.error { background-color: #FFEEEE; }
</style>
</head>
<body>
<p>%s</p>
<form action="" method="post">
%s
<p><input type="submit"></p>
</form>
</body>
</html>
"""
           
TestForm = forms.Form(
forms.Textbox(
    'text', 
    forms.Validator(lambda x: len(x) < 3, "Must be shorter than 3"),
    pre="Before", post="After", label="Text input", 
    id="different_id", class_="aclass", size=8),
forms.Password("password", label="Password"),
forms.Checkbox("checkbox", forms.checkbox_validator, label="Checkbox"),
forms.Hidden("hidden", value="nowai", label="Hidden value"),
forms.File("file", label="Pick a file"),
forms.Button("somebutton", label="A button"),
forms.Textarea("textarea", label="A text area"),
forms.Dropdown("dropdown", ("X","Y","Z"), label="A dropdown"),
forms.Radio(
    'radio', 
    [ ("a", "A"), ("b", "B"), ("c", "C")],
    forms.Validator(lambda x: x in ["a","b"], "Must choose a or b"),
    label="Radio buttons"),
)    
class FormPage:
    """Form testing page, on http://localhost:8080/form"""    
    
    def GET(self):
        form = TestForm()
        print form_template % ("", form.render())
    
    def POST(self):
        input = web.input()
        form = TestForm(input)
        print form_template % (
            pformat(input)+"<br>"+pformat(form.d), form.render())

if __name__ == "__main__":
    try:
        web.run(urls, globals())
    except KeyboardInterrupt:
        pass

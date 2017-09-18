"""Programmatic form construction and validation

@note: Originally web.form (part of web.py by Aaron Swartz, http://webpy.org).
I (Graham Poulter) needed form validation, and used web.form as a starting
point. Virtually every line has been modified, but the module architecture is
due to Aaron.

@author: Aaron Swartz 
@author: Graham Poulter

@license: Public Domain (specified by Aaron Swartz)
"""

import copy
import re
import web
from web import utils, net

def attrget(obj, attr, value=None):
    """Retrieve something either as dictionary key or instance attribute
    
    @param obj: Thing to retrieve from
    @param attr: Name of thing to retrieve
    @param value: Default if attr is not found"""
    if hasattr(obj, '__contains__') and attr in obj: return obj[attr]
    if hasattr(obj, attr): return getattr(obj, attr)
    return value

class Form:
    """Programmatically construct a form
    
    @ivar inputs: List of input fields in the form
    @ivar valid: True if the form is unfilled, or validly filled
    @ivar note: Message about invalid stuff
    @ivar validators: List of validators that operate on the whole form
    """
    
    def __init__(self, *inputs, **kw):
        """Construct a form.  Positional parameters are the form inputs.
        
        @param inputs: List of input fields in the form
        
        @keyword validators: Optional keyword, providing, a list of additional
        validators on the form besides the ones associated with an input."""
        self.inputs = inputs
        self.valid = True
        self.note = None
        self.validators = kw.pop('validators', [])


    def __call__(self, inputs=None):
        """Call the original instance to create copies to fill.
        
        @param inputs: Optional a storage object which fills the form."""
        newform = copy.deepcopy(self)
        if inputs: 
            newform.validates(inputs)
        return newform


    def render(self):
        """An HTML table rendering of the form inputs"""
        e_row = '<tr class="error"><td colspan="2">%s</td></tr>\n'
        i_row = '<tr class="input"><th>%s</th><td class="value">%s %s %s</td></tr>\n'
        # Render non-hidden inputs
        rows = []
        if self.note: 
            rows.append(e_row % self.note)
        for i in self.inputs:
            if not isinstance(i, Hidden):
                rows.append(i_row % (i.renderlabel(), i.pre, i.render(), i.post))
                if i.note: 
                    rows.append(e_row % i.note)
        out = "\n".join(['<table class="form">'] + rows + ["</table>"])
        # Now render the hidden inputs
        out += "\n".join(
            ["<div>"] + 
            [i.render() for i in self.inputs if isinstance(i, Hidden)] + 
            ["</div>"])
        return out


    def render_errors(self):
        errors = ["<li>%s: %s</li>" % (n,e) for n,e in 
                 self.errors.iteritems() if e is not None]
        return "\n".join(["<p>Errors</p><ul>"] + errors + ["</ul>"])
    
    
    def validates(self, source, _validate=True):
        """Validate the form, also filling its values
        
        @param source: Storage object from which to set form values
        
        @returns: True/False about whether the form validates."""
        if hasattr(self, "_d"): 
            del self._d # Refresh the data property
        isvalid = True
        for i in self.inputs:
            value = attrget(source, i.name)
            if _validate:
                isvalid = i.validate(value) and isvalid
            else:
                i.value = value
        if _validate:
            isvalid = self._validate(source) and isvalid
        self.valid = isvalid
        return isvalid


    def _validate(self, source):
        """Run additional validators for the form
        
        @param source: Storage object containing form values        
        """
        for v in self.validators:
            if not v.valid(source):
                self.note = v.msg
                return False
        return True


    def fill(self, source=None):
        """Fill the form without validating

        @param source: Storage object from which to set form values
        """
        self.validates(source, _validate=False)
    
    
    def __getitem__(self, key):
        """Dictionary access to inputs.
        
        @param key: Name of input to retrieve"""
        for x in self.inputs:
            if x.name == key: return x
        raise KeyError, key
    
    
    @property
    def d(self):
        """A storage dictionary of the form inputs (deleted by validates())"""
        try:
            return self._d
        except AttributeError:
            self._d = utils.storage([(i.name, i.value) for i in self.inputs])
            return self._d
    
    
    @property
    def errors(self):
        """A storage dictionary of the form errors."""
        return utils.storage([(i.name, i.note) for i in self.inputs])



class Input(object):
    """Represents input widgets in the form

    @ivar name: The name= attribute for the input
    @ivar validators: List of Validator to apply to the input
    @ivar label: Contents of the <label> for the input
    @ivar pre: Text before the input
    @ivar post: Text after the input
    @ivar id: For id= attribute (but defaults to name if not provided)
    @ivar attrs: Other attributes

    @ivar note: Message set by the first validator that fails
    """
    
    def __init__(self, name, *validators, **attrs):
        """Constructor - parameters correspond to instance variables.
        
        @keyword class_: Specifies the class= attribute.
        """
        self.name = name
        self.note = None
        self.validators = validators
        self.label = attrs.pop('label', name)
        self.value = attrs.pop('value', None)
        self.pre = attrs.pop('pre', "")
        self.post = attrs.pop('post', "")
        self.id = attrs.setdefault("id", name)
        if 'class_' in attrs: 
            attrs['class'] = attrs['class_']
            del attrs['class_']
        self.attrs = attrs


    def validate(self, value):
        """Validate the input
        
        @param value: Value to fill the input 
        
        @return: True if all validators work, otherwise False and sets the note
        to the validator message"""
        self.value = value
        for v in self.validators:
            if not v.valid(value):
                self.note = v.msg
                return False
        return True


    def render(self):
        """Render the <input> element itself"""
        raise NotImplementedError
    
    
    def renderlabel(self):
        """Render the label for the input"""
        return '<label for="%s">%s</label>' % (self.id, self.label)


    def addatts(self):
        """Render additional attributes within a tag"""
        str = ""
        for (n, v) in self.attrs.items():
            str += ' %s="%s"' % (n, net.websafe(v))
        return str
    
    
    
class Textbox(Input):
    """Widget for a text input"""
    
    def render(self):
        value = ' value="%s"' % net.websafe(self.value) if self.value else ""
        return '<input type="text" name="%s"%s%s>' % (
            net.websafe(self.name), value, self.addatts())


    
class Password(Input):
    """Widget for a password input"""
    
    def render(self):
        value = ' value="%s"' % net.websafe(self.value) if self.value else ""
        return '<input type="password" name="%s"%s%s>' % (
            net.websafe(self.name), value, self.addatts())



class Checkbox(Input):
    """Widget for a checkbox input"""
    
    def render(self):
        checked = ' checked="checked"' if self.value else ''
        return '<input type="checkbox" name="%s"%s%s>' % (
            net.websafe(self.name), checked, self.addatts())
    


class Hidden(Input):
    """Widget for a hidden input"""

    def render(self):
        value = ' value="%s"' % net.websafe(self.value) if self.value else ""
        return '<input type="hidden" name="%s"%s>' % (
            net.websafe(self.name), value)



class File(Input):
    """Widget for a file input"""
    
    def render(self):
        value = ' value="%s"' % net.websafe(self.value) if self.value else ""
        return '<input type="file" name="%s"%s%s>' % (
            net.websafe(self.name), value, self.addatts())
    
    
    
class Button(Input):
    """Widget for a button.
    
    @note: The form was submitted by pressing this button if the buttons' name
    is in web.inputs (with empty string for value)
    """
    
    def render(self):
        x = '<button name="%s"%s>%s</button>' % (
            self.name, self.addatts(), self.label)
        return x



class Textarea(Input):
    """Widget for a <textarea>"""
    
    def render(self):
        value = net.websafe(self.value) if self.value else ""
        return '<textarea name="%s"%s>%s</textarea>' % (
            net.websafe(self.name), self.addatts(), value)



class Dropdown(Input):
    """Widget for <select> dropdown box"""
    
    def __init__(self, name, args, *validators, **attrs):
        """Constructor
        
        @param args: List of values or (value,description) pairs for the
        dropdown box."""
        self.args = args
        super(Dropdown, self).__init__(name, *validators, **attrs)


    def render(self):
        x = '<select name="%s"%s>\n' % (
            net.websafe(self.name), self.addatts())
        for arg in self.args:
            if type(arg) == tuple:
                value, desc = arg
            else:
                value, desc = arg, arg 
            if self.value == value: 
                select_p = ' selected="selected"'
            else: 
                select_p = ''
            x += '<option%s value="%s">%s</option>\n' % (
                select_p, net.websafe(value), net.websafe(desc))
        x += '</select>\n'
        return x



class Radio(Input):
    """Widget for a set of radio buttons"""
    
    def __init__(self, name, args, *validators, **attrs):
        """Constructor
        
        @param args: List of values or (value,description) pairs for radio
        buttons."""
        self.args = args
        super(Radio, self).__init__(name, *validators, **attrs)


    def renderlabel(self):
        """Plain-text label: no unique ID for set of buttons"""
        return self.label


    def render(self, only=None):
        """Write a list of radio inputs. 
        
        @param only: Render just the radio button whose name matches."""
        out = ""
        for arg in self.args:
            if type(arg) == tuple:
                value, desc = arg
            else:
                value, desc = arg, arg 
            if only is not None and value != only:
                continue
            if self.value == value: 
                select_p = ' checked="checked"'
            else: 
                select_p = ''
            out += '<span><input type="radio" name="%s" value="%s"%s> %s </span>' % \
            (net.websafe(self.name), net.websafe(value), select_p, net.websafe(desc))
        return out



class Validator:
    """Generic validator to pass to an Input or Form constructor."""

    def __init__(self, test, msg): 
        """Constructor
        
        @param test: Applied to input value when used as an input validator,
        and applied to the Storage source for the form when used as a form
        validator.
        
        @param msg: To be assigned to the note when validator fails.
        """
        utils.autoassign(self, locals())
        
    def __deepcopy__(self, memo): 
        return copy.copy(self)
    
    def valid(self, value):
        """Returns true if the test function succeeds"""
        try: 
            return self.test(value)
        except: 
            return False



class RegexValidator(Validator):
    """Tests that the value matches a particular regular expression"""

    def __init__(self, rexp, msg):
        """Constructor
        
        @param rexp: String containing the regular expression
        """
        self.rexp = re.compile(rexp)
        self.msg = msg
    
    def valid(self, value):
        return bool(self.rexp.match(value))



notnull = Validator(bool, "Required")
"""Use to specify that the input should not be left empty"""


checkbox_validator = Validator(
    lambda x: x == None or x == "on", "Bad checkbox")
"""Use to be sure the checkbox has valid input"""


def ischecked(value):
    """True if the Checkbox was pressed"""
    return True if value == "on" else bool(value)


def buttonpressed(value):
    """True if the Button was pressed"""
    return True if value == "" else bool(value)
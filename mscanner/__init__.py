"""MScanner project tree.

The package file contains a few general-purpose functions used
throughout the project."""


def update(obj, vars, exclude=['self']):
    """Update instance attributes (using a dictionary)
    
    Example: C{update(self, locals())}
    
    @param obj: Instance to update using setattr()
    @param vars: Dictionary of variables to store
    @param exclude: Variables to exclude, defaults to ['self']
    """
    for k, v in vars.iteritems():
        if k not in exclude:
            setattr(obj, k, v)


def delattrs(obj, *vars):
    """Remove named attributes from instance
    
    Example: C{delattrs(self, "_property", "_other")}
    
    @param objs: Object to update via delattr
    @param vars: Instance attribute names to delete
    """
    for ivar in vars:
        try:
            delattr(obj, ivar)
        except AttributeError:
            pass

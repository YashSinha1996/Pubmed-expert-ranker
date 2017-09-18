#!/export/home/medscan/local32/bin/python2.5

"""Controller for the MScanner web interface 

In this context, the view is the template code, and the model is the queue
programme."""

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

import sys
sys.path.insert(0,"/export/home/medscan")
import web

from mscanner.htdocs import templates

# Set informative error handler
web.webapi.internalerror = web.debugerror

# URLs for the application
urls = (
    '/', 'FrontPage',
    '/query', 'templates.query_logic.QueryPage',
    '/status', 'templates.status_logic.StatusPage',
    '/output', 'templates.output_logic.OutputPage',
    '/contact', 'templates.contact_logic.ContactPage',
)
"""Mapping between URLs and objects to process the requests"""

class FrontPage:
    """Front page of the site"""
    def GET(self):
        """Return the front page for MScanner"""
        web.header('Content-Type', 'text/html; charset=utf-8') 
        page = templates.front.front()
        print page

if __name__ == "__main__":
    try:
        web.run(urls, globals())
    except KeyboardInterrupt:
        pass

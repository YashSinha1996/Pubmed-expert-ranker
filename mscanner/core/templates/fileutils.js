/****************** CROSS-BROWSER READ/WRITE ******************/

/* cross-browser function to read a file 
Note: fname must be a full filesystem path
*/
function readFile(fname) {
   if (window.ActiveXObject) {
      return readFileIE(fname);
   } else if (netscape) {
      return readFileNetscape(fname);
   } else {
      throw "Can only read local files from Internet Explorer or Netscape/Mozilla/Firefox";
   }
}

/* cross-browser function to write a file 
Note: fname must be a full filesystem path
*/
function writeFile(fname, text) {
   if (window.ActiveXObject) {
      writeFileIE(fname, text);
   } else if (netscape) {
      writeFileNetscape(fname, text);
   } else {
      throw "Can only write local files from Internet Explorer or Netscape/Mozilla/Firefox";
   }
}

/**************** INTERNET EXPLORER ************************/

function readFileIE(fname, text) {
   fso = new window.ActiveXObject("Scripting.FileSystemObject");
   os = fso.OpenTextFile(fname, 1);
   result = os.ReadAll();
   os.Close();
   return result;
}

function writeFileIE(fname, text) {
   fso = new window.ActiveXObject("Scripting.FileSystemObject");
   os = fso.CreateTextFile(fname, true);
   os.Write(text);
   os.Close();
   return true;
}

/***************** NETSCAPE **********************************/

function readFileNetscape(fname) {
   try {
      netscape.security.PrivilegeManager.enablePrivilege("UniversalXPConnect");
   } catch (e) {
      throw "Permission to read file was denied.";
   }
   var file = Components.classes["@mozilla.org/file/local;1"]
   file = file.createInstance(Components.interfaces.nsILocalFile);
   try {
      file.initWithPath(fname);
   } catch (e) {
      throw "Invalid path to file: " + fname;
   }
   if (file.exists() == false) {
      throw "File does not exist: " + fname;
   }
   var is = Components.classes["@mozilla.org/network/file-input-stream;1"]
   is = is.createInstance(Components.interfaces.nsIFileInputStream );
   is.init( file,0x01, 00004, null);
   var sis = Components.classes["@mozilla.org/scriptableinputstream;1"]
   sis = sis.createInstance(Components.interfaces.nsIScriptableInputStream);
   sis.init(is);
   return sis.read(sis.available());
}

function writeFileNetscape(fname, text) {
   try {
      netscape.security.PrivilegeManager.enablePrivilege("UniversalXPConnect");
   } catch (e) {
      throw "Permission to save file was denied.";
   }
   var file = Components.classes["@mozilla.org/file/local;1"]
   file = file.createInstance(Components.interfaces.nsILocalFile);
   try {
      file.initWithPath(fname);
   } catch (e) {
      throw "Invalid path to file: " + fname;
   }
   if (file.exists() == false) {
      file.create(Components.interfaces.nsIFile.NORMAL_FILE_TYPE, 0644);
   } 
   var os = Components.classes["@mozilla.org/network/file-output-stream;1"]
   os = os.createInstance(Components.interfaces.nsIFileOutputStream);
   os.init(file, 0x04 | 0x08 | 0x20, 420, 0);
   var result = os.write(text, text.length);
   os.flush();
   os.close();
}

/*************** HELPER FUNCTIONS ***************************/

/* Safe check for whether a variable is defined */
function isdefined( variable) {
    return (typeof(window[variable]) == "undefined")?  false: true;
}

/* True if we are in a file:/// URL */
function areWeLocal() {
   return document.URL.substr(0,7) == "file://";
}

/* Returns true if it is possible to save/load files */
function canWeSave() {
   var isdef = isdefined;
   return areWeLocal() && (
   isdef("ActiveXObject") || (isdef("netscape") && isdef("Components")));
}

/* Convert a file:/// URL to a system path */
function fileURLasPath(url) {
   if (url.substr(0,7) != "file://") {
      throw "URL is not a local file: " + url;
   }
   if (url.substr(7,1) == "/") // netscape style file:///C:/blah
      return decodeURI(url).substr(8).replace(/\//g, "\\");
   else // windows IE style file://C:\blah
      return url.substr(7)
}

/* Recover the file name of a system path */
function baseName(path) {
   if(path.lastIndexOf("\\") == -1)
      return path;
   else
      return path.substr(path.lastIndexOf("\\")+1)
}

/* Return current directory on the disk, so that file name
can be appended.  Raises an exception if we are not at a file:/// */
function currentDir() {
   if (areWeLocal() == false) {
      throw "This function only works when the HTML file is"
      "opened locally: the address bar should start with file:///"
      "and not http://"
   }
   // remove file part of the path, keeping / as separator
   fpath = fileURLasPath(document.URL)
   return fpath.substr(0,fpath.lastIndexOf("\\")) + "\\"
}

/* Load XML document, calls back when ready. 
Based on http://www.quirksmode.org/dom/importxml.html 
*/
function importXML(filename, callback) {
   if (document.implementation && document.implementation.createDocument) {
      xmlDoc = document.implementation.createDocument("", "", null);
      xmlDoc.onload = callback;
   }
   else if (window.ActiveXObject) {
      xmlDoc = new ActiveXObject("Microsoft.XMLDOM");
      xmlDoc.onreadystatechange = function () {
         if (xmlDoc.readyState == 4) callback(xmlDoc);
      };
   }
   else {
      throw 'Your browser cannot load XML documents';
   }
   xmlDoc.load(filename);
}
/*
Cells in each row are:
0 - Classification
1 - Rank
2 - Score
3 - PMID
4 - Year
5 - Expand Author
6 - Expand Abstract
7 - Title
8 - ISSN
*/

/************************ HELPER FUNCTIONS ***********************/

/* Return target of the event */
function event_target(event) {
   if (!event) var event = window.event;
   var targ = null;
   if (event.target) 
      targ = event.target; // Netscape
   else if (event.srcElement)
      targ = event.srcElement; // Microsoft
   if (targ.nodeType == 3) // defeat Safari bug
      targ = targ.parentNode;
   return targ;
}  

/* return a bound method, can be used to create event handlers
that don't switch to the context of the HTML element */
function bind(obj, method) {
   return function() { return method.apply(obj, arguments); }
}

/* Use onclick="return noenter()" to prevent default form submission 
action when enter key is pressed in an input field  */
function noenter() {
  return !(window.event && window.event.keyCode == 13); 
}

/********************* OPENING RESULTS IN PUBMED ***************************/

/* Open positive documents in PubMed 
BUG: Internet Explorer barfs on long query strings!

all=true: Open all visible citations in PubMed
all=false: Open only manually-marked relevant citations in PubMed
*/
function openPubMed(all) {
   var rows = document.getElementById("citations").rows
   var qstring = "http://www.ncbi.nlm.nih.gov/entrez/query.fcgi?cmd=Retrieve&amp;db=pubmed&amp;list_uids="
   var count = 0
   for (var i = 0; i < rows.length; i++) {
      if (rows[i].className == "main") {
         var pmid = rows[i].id.substr(1)
         if (getTag(pmid) == 2 ||
            (all == true && rows[i].style.display != "none")) {
            if (count > 0) qstring += ","
            qstring += pmid
            count++
         }
      }
   }
   if(count == 0)
      alert("Cannot open PubMed as there are no PubMed IDs to open")
   else
      window.open(qstring)
}

/* Adds events for opening citations in PubMed */
function initPubMedOpening() {
   $("open_pubmed_relevant").onclick = function() { openPubMed(false) }
   $("open_pubmed_all").onclick = function() { openPubMed(true) }
}

/******************* LOADING/SAVING OF CITATION TAGS ********************/

/*
0 = Unclassified (gray)
1 = Negative (blue)
2 = Positive (red)
*/

/* Read classifications from disk */
function loadTags(fname) 
{
   try {
      var text = readFile(fname)
   } catch (err) {
      alert("Failed to read classifications from file: " + err)
      return
   }
   var lines = text.split("\n");
   for (var i = 0; i < lines.length; i++) {
      var values = lines[i].split(",")
      var pmid = values[0]
      var score = values[1]
      var classification = values[2]
      switch(classification) {
         case " ": setTag(pmid, 0); break
         case "0": setTag(pmid, 1); break
         case "1": setTag(pmid, 2); break
      }
   }
   alert("Successfully loaded classifications");
}

/* Save classifications to disk */
function saveTags(fname) {
   var text = ""
   var rows = document.getElementById("citations").rows
   for (var i = 0; i < rows.length; i++) {
      if (rows[i].className == "main") {
         var pmid = rows[i].id.substr(1)
         var score = rows[i].cells[2].innerHTML
         var line = pmid+","+score+","
         switch(getTag(pmid)) {
            case 0: line += " \n"; break
            case 1: line += "0\n"; break
            case 2: line += "1\n"; break
         }
         text += line;
      }
   }
   try {
      writeFile(fname, text)
      alert("Successfully saved classifications")
   } catch (err) {
      alert("Failed to save classifications: " + err)
   }
}

/* Set up the saving/loading of classifications */
/* Get classification tag (0,1,2) */
function getTag(pmid) {
   var cls = $("P"+pmid).cells[0].className
   switch(cls) {
      case "": return 0; break
      case "neg": return 1; break
      case "pos": return 2; break
      default: throw "Invalid tag class: " + color
   }
}

/* Set classification tag (value may be 0, 1 or 2) */
function setTag(pmid, value) {
   var tag = $("P"+pmid).cells[0]
   var newcls = null
   switch (value) {
      case 0: newcls = ""; break
      case 1: newcls = "neg"; break
      case 2: newcls = "pos"; break
      default: throw "Invalid tag code: " + value
   }
   /* We avoid assigning to className where possible because
   this is a very slow operation in Internet Explorer */
   if (newcls != null && tag.className != newcls) {
      tag.className = newcls
   }
}

function initTagSaving() {
   if (areWeLocal() == false || canWeSave() == false) {
      // hide ability to save/load citations for non-local pages
      $("save_load_div").style.display = "none"
   } else {
      $("save_warning_div").style.display = "none"
      $('save_tags').onclick = function() {
         saveTags(fileURLasPath($('save_target').href)) }
      $('load_tags').onclick = function() {
         loadTags(fileURLasPath($('save_target').href)) }
   }
}

/******************* CITATION TABLE EVENTS **************************/

/* Hide all expanded author/abstract rows in the citations table */
function hideTableRows() {
   var rows = document.getElementById("citations").rows
   // row 0 is the heading
   for (i = 1; i < rows.length; i+=3) {
      rows[i].style.display = ""
      rows[i+1].style.display = "none"     
      rows[i+2].style.display = "none"
   }
   $("vis_count").innerHTML = (rows.length-1)/3
}

/* Adds the events for classification/author/abstract display */
function initTableEvents() {

   hideTableRows()

   /* Cycles cell forward on left clicks, backward on right */
   function onclick_classify(e) {
      /* Target is cell, with parent row who has "P"+PMID as its id */
      var pmid = this.parentNode.id.substr(1);
      setTag(pmid, (getTag(pmid)+2) % 3)
   }
   
   /* Author row is sibling of target's parent row. */
   function onclick_author() {
      toggle(this.parentNode.nextSibling)
   }

   /* Abstract row is second sibling of target's parent row. */
   function onclick_abstract() {
      toggle(this.parentNode.nextSibling.nextSibling)
   }
   
   /* Loop over rows to add event handlers */
   var rows = document.getElementById("citations").rows
   // row 0 is the heading
   for (var i = 1; i < rows.length; i+=3) {
      rows[i].cells[0].onclick = onclick_classify
      rows[i].cells[5].onclick = onclick_author
      rows[i].cells[6].onclick = onclick_abstract
   }
}


/****************** APPENDING TO THE CITATION TABLE ************************/

/* 
Read citations from disk and append to the table
If append is false, we prepend the data to the table instead.
*/
function loadCitations(fname) {
   var text = readFile(fname)
   var table = text.match(/<[t]body>[^\v]*?<\/tbody>/)
   var blob = table[0].substr(7,table[0].length-15)
   var tbody = $("citations").getElementsByTagName("tbody")[0]
   tbody.innerHTML += blob
   /* new HTML - no events are linked yet */
   initTableEvents()
}

/* Note: We can only append result files if innerHTML can be set on tables
(works at least in mozilla browsers) and we are a local file. */

appendable_files = [] // list of files to append
function initResultAppending() {
   /* hide the feature if it is not supported. toSource detects Netscape. */
   if (canWeSave() == false || (!"a".toSource)) {
      $("append_results_div").style.display = "none"
      return
   }
   /* make a list of files to load */
   nodes = $("appendable_files").getElementsByTagName("a")
   for(var i = 0; i < nodes.length; i++) {
      appendable_files.push(nodes[i].href)
   }
   function setupNextAppend() {
      if (appendable_files.length == 0) {
         $("next_to_append").href = "#"
         $("next_to_append").innerHTML = "(no more files to append)"
      } else {
         function fn(url) { return url.substr(url.lastIndexOf("/")+1) }
         $("next_to_append").href = appendable_files.shift()
         $("next_to_append").innerHTML = fn($("next_to_append").href)
      }
   }
   $("append_results").onclick = function() {
      if ($("next_to_append").href != "#") {
         loadCitations(fileURLasPath($("next_to_append").href))
         setupNextAppend()
      }
   }
   setupNextAppend()
}

/*********************** FILTERING OF CITATIONS ************************/

/* Filter visible citations  */
function filterCitations() {
   var rows = document.getElementById("citations").rows
   form = document.filter_form

   var date_min = form.date_min.value
   if(date_min == "") date_min = "1900.01.01"
   var date_max = form.date_max.value
   if(date_max == "") date_max = "2100.01.01"
   var score_min = parseFloat(form.score_min.value)
   if(form.score_min.value == "") score_min = -100.0
   
   var title_filt = form.title_regex.value
   var abstract_filt = form.title_abstract_regex.value
   var exclude_filt = form.exclude_regex.value
   var journal_filt = form.journal_regex.value
   var author_filt = form.author_regex.value
   var r_title = RegExp(title_filt, "i")
   var r_abstract = RegExp(abstract_filt, "i")
   var r_exclude = RegExp(exclude_filt, "i")
   var r_journal = RegExp(journal_filt, "i")
   var r_author = RegExp(author_filt, "i")
   
   var hiding = 0 // number of rows we have hidden this time
   /* row 0 is the heading */
   for (var i = 1; i < rows.length; i+=3) {
      if (rows[i].className == "main" && rows[i].style.display != "none") {
            var cells = rows[i].cells
            var score = parseFloat(cells[2].innerHTML)
            var mdate = cells[4].innerHTML
            var title = cells[7].innerHTML
            var journal = cells[8].firstChild.innerHTML // hyperlink in cell
            var author = rows[i+1].cells[0].innerHTML
            var abst = title + rows[i+2].cells[0].innerHTML
            /* Apply filter criteria */
            if ( (score >= score_min) 
               && (mdate >= date_min && mdate <= date_max)
               && (title_filt == "" || r_title.test(title))
               && (abstract_filt == "" || r_abstract.test(abst))
               && (exclude_filt == "" || !r_exclude.test(abst))
               && (journal_filt == "" || r_journal.test(journal))
               && (author_filt == "" || r_author.test(author))) {
               // do nothing
            } else {
               rows[i].style.display = "none"
               hiding++
            }
            rows[i+1].style.display = "none"
            rows[i+2].style.display = "none"          
      }
   }
   $("vis_count").innerHTML = parseInt($("vis_count").innerHTML) - hiding
   return false // suppress form action
}

/* Sort all the citation rows */
var current_sort = "score"
function sortCitations() {

   var rows = document.getElementById("citations").rows

   function str_cmp(a, b) {
      if(a < b) return -1
      else if (a == b) return 0
      else return +1
   }

   function score_cmp(a,b) {
      // Faster and more stable: sorting by increasing rank
      return parseInt(a[0].childNodes[1].innerHTML) -
             parseInt(b[0].childNodes[1].innerHTML)
   }
   function date_cmp(a,b) {
      // decreasing by date stamp
      return str_cmp(b[0].childNodes[4].innerHTML,
                    a[0].childNodes[4].innerHTML)
   }
   function journal_cmp(a,b) {
      // increasing by journal name
      return str_cmp(a[0].childNodes[8].firstChild.innerHTML,
                     b[0].childNodes[8].firstChild.innerHTML)
   }
   function author_cmp(a,b) {
      // increasing by last name of the first author
      ma = a[1].childNodes[0].innerHTML.match(/[a-z]\ ([^\ ]+)/i)
      mb = b[1].childNodes[0].innerHTML.match(/[a-z]\ ([^\ ]+)/i)
      if (ma != null && mb != null)
         return str_cmp(ma[1], mb[1])
      else if (ma != null) 
         return -1
      else 
         return +1
   }

   var new_sort = document.filter_form.orderby.value
   if(new_sort == current_sort) return
   var compare = null
   switch (new_sort) {
      case "score": compare = score_cmp; break
      case "date": compare = date_cmp; break
      case "journal": compare = journal_cmp; break
      case "author": compare = author_cmp; break
      default: throw "Invalid orderby comparison: " + new_sort
   }
   
   // Strategy is to group the triplets of rows in to an array
   // then clear the table, sort the array, and re-create the table
   t = $("citations")
   tbody = t.childNodes[2]
   x = [] // create array of row triplets
   for(i = 1; i < t.rows.length; i+=3)
       x[(i-1)/3] = [ t.rows[i], t.rows[i+1], t.rows[i+2] ]
   t.removeChild(tbody) // remove table body
   tbody = document.createElement("tbody") // create empty table body
   t.appendChild(tbody) // add empty table body
   x.sort(compare) // sort the row triplets
   for(i = 0; i < x.length; i+=1) {
       tbody.appendChild(x[i][0])
       tbody.appendChild(x[i][1])
       tbody.appendChild(x[i][2])
   }
   
   // update the sort
   current_sort = new_sort
}

/* Hide the visible rows, and show the hidden rows */
function invertSelection() {
   var rows = document.getElementById("citations").rows
   var vis_count = 0;
   // row 0 is the heading
   for (i = 1; i < rows.length; i+=3) {
      if(rows[i].style.display == "") {
         rows[i].style.display = "none"
      } else {
         rows[i].style.display = ""
         vis_count++
      }
      rows[i+1].style.display = "none"     
      rows[i+2].style.display = "none"
   }
   $("vis_count").innerHTML = vis_count
}

/* Event handling for the citation filter */
function initCitationFilter() {
   $("clear_filter").onclick = hideTableRows
   $("do_filter").onclick = function() {
      sortCitations()
      filterCitations()
   }
   $("invert_selection").onclick = invertSelection
   document.filter_form.onsubmit = filterCitations
}

/************************** WINDOW LOADING ******************************/

window.onload = function() {
   $("script_warning").style.display = "none"
   make_toggles()
   initPubMedOpening()
   initTagSaving()
   initResultAppending()
   initTableEvents()
   initCitationFilter()
}

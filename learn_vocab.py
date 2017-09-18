
# coding: utf-8
import urllib.request as rq

terms_common=rq.urlopen("http://www.bliss.org.uk/common-medical-terms")

from bs4 import BeautifulSoup as bs

parsed=bs(terms_common.read(),"lxml")

terms=parsed.find_all("span",class_="vag-bold-5")
from tempfile import TemporaryFile as tf
files=[]
terms_desc={}

for term in terms:
    med_term=term.string
    if len(med_term)>1:
        print(med_term+","+term.next_sibling.next_sibling.string)
        filer=tf("r+")
        filer.write(str(term.next_sibling.next_sibling.string))
        terms_desc[med_term]=str(term.next_sibling.next_sibling.string)
        filer.seek(0)
        files.append(filer)

for filer in files:
    print(filer.read())
    filer.seek(0)

from sklearn.feature_extraction.text import TfidfVectorizer as tfidf

learnt=tfidf("file")

transd=learnt.fit_transform(files)

print(transd)

import pickle
with open("learnt-tf.pck","w+b") as ltf:
    pickle.dump(learnt,ltf)
import json
with open("terms-desc.json","w") as t_desc:
    json.dump(terms_desc,t_desc)

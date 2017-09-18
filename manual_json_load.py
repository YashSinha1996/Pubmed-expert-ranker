import json
with open("terms-desc.json","r") as ted_def:
    terms_desc=json.load(ted_def)

from tempfile import TemporaryFile as tf
files=[]

for term_key in terms_desc.keys():
    if len(term_key)>1:
        filer=tf("r+")
        filer.write(terms_desc[term_key])
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

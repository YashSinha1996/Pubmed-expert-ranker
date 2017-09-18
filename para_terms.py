from sklearn.feature_extraction.text import TfidfVectorizer as tfidf


def tf(sent):
    words=tfidf().build_tokenizer()(sent.lower())
    tf={}
    for word in words:
        if word in tf:
            tf[word]+=1
        else:
            tf[word]=1
    for key in tf.keys():
        tf[key]=tf[key]/len(words)
    return tf


def tf_tdf_sent(sent,learnt):
    tfs=tf(sent)
    #print(tfs)
    tfs_sorted=[]
    for word in tfs.keys():
        try:
            tfs[word]=tfs[word]*learnt.idf_[learnt.vocabulary_[word]]
        except Exception:
            tfs[word]=0
        tfs_sorted.append((tfs[word],word))
    tfs_sorted=sorted(tfs_sorted)
    tfs_sorted.reverse()
    return (tfs,tfs_sorted)


# tfs_dict,tfs_list=tf_tdf_sent("My baby is very small and light",learnt)

term_threshold=10

def search(term,desc):
    term_l=term.lower()
    desc_l=desc.lower()
    word_tok=tfidf().build_tokenizer()
    desc=word_tok(desc_l)
    terms=word_tok(term_l)
    return all([x in desc for x in terms])
# search("hi hello","hello (hi")


def query_terms(tfs_list_sorted,terms_desc):
    possible_terms={}
    # print(tfs_list_sorted)
    if len(tfs_list_sorted)<2:
        #print("Exhausted")
        if len(terms_desc)<10:
            return list(terms_desc.keys())
        else:
            return []
    for term in terms_desc.keys():
        if search(tfs_list_sorted[0][1],terms_desc[term]) or  search(tfs_list_sorted[1][1],terms_desc[term]):
            possible_terms[term]=terms_desc[term]
    if len(possible_terms.keys())<=term_threshold:
        return possible_terms.keys()
    else:
        possiblity=query_terms(tfs_list_sorted[1:],possible_terms)
        if not possiblity:
            print(possiblity)
            return list(possible_terms.keys())
        else:
            return possiblity
    
import pickle
import json
def searcher(query):
    with open("learnt-tf.pck","r+b") as ltf,open("terms-desc.json","r") as ted_def:
        learnt=pickle.load(ltf)
        terms_desc=json.load(ted_def)
        return query_terms(tf_tdf_sent(query,learnt)[1],terms_desc)

if __name__ == '__main__':
    print(searcher("My baby is heart"))
    print(tfidf().build_tokenizer()("My baby is weighing less."))
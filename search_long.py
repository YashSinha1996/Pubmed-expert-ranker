from ranker import topic_z_scorer
from para_terms import searcher 
from sklearn.feature_extraction.text import TfidfVectorizer as tfidf

def combine_z(z_1,z_2):
	# print("to combine_z")
	if not z_2:
		return z_1
	# print('combining')
	for key in z_2.keys():
		# print(key)
		if key in z_1.keys():
			z_1[key]+=z_2[key]
		else:
			z_1[key]=z_2[key]
	return z_1

def search(query):
	key_terms=searcher(query)
	termlist=[]
	print(key_terms)
	if not key_terms:
		# print("here")
		key_terms=tfidf().build_tokenizer()(query)
	# print(key_terms)
	ranked={}
	for term in key_terms:
		if term not in termlist:
			ranks,authrs=topic_z_scorer(term)
			if not ranked:
				ranked=authrs
			else:
				ranked=combine_z(ranked,authrs)
			termlist.append(term)
		# print(ranked,authrs)
	for term in key_terms:
		sub_terms=tfidf().build_tokenizer()(query)
		for sub_term in sub_terms:
			if sub_term not in termlist:
				ranks,authrs=topic_z_scorer(sub_term)
				authrs={auth:authrs[auth]*0.75 for auth in authrs}
				if not ranked:
					ranked=authrs
				else:
					ranked=combine_z(ranked,authrs)
				termlist.append(sub_term)

	for term in tfidf().build_tokenizer()(query):
		for word in tfidf().build_tokenizer()(term):
			if word not in termlist:
				ranks,authrs=topic_z_scorer(word)
				authrs={auth:authrs[auth]*1.25 for auth in authrs}
				if not ranked:
					ranked=authrs
				else:
					ranked=combine_z(ranked,authrs)
				termlist.append(word)

	ranks_final=sorted([(ranked[key],key) for key in ranked.keys()])
	ranks_final.reverse()
	print(ranks_final)
	return [name[1] for name in ranks_final]

if __name__ == '__main__':
	import sys
	# print(sys.argv[1])
	if len(sys.argv) > 1:
		for name in search(sys.argv[1])[:10]:
			print(name)
	else:
		for name in search("Coronary Heart Disease")[:10]:
			print(name)


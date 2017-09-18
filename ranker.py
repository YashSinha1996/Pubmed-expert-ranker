import MySQLdb
import math
from nltk.stem.porter import *

def score(a,b,c,d):
 	n1 = float(a + b)
 	n2 = float(c + d)
 	p = float(a + c)/(a + b + c + d)
 	q = 1 - p
 	p1 = a/float(a + b)
 	p2 = c/float(c + d)
 	r = math.sqrt(p * q * ((1/n1) + (1/n2)) )
 	z = (abs(p1 - p2) - (1/(2*n1)) - (1/(2*n2)) ) / float(r)
 	return z


db=MySQLdb.connect(host="127.0.0.1",user="root",passwd="password",db="pubmed")
curr=db.cursor()
def topic_z_scorer(topic):
	# print(topic)
	stemmer = PorterStemmer()
	curr.execute("select count(*) from pubmed_article")
	topic=str(stemmer.stem(topic))
	ranks=[]
	auth_ranks={}
	# print(topic)
	total_articles=int(curr.fetchone()[0])
	curr.execute(""" select pmid from keywords as k where keyword like "%s%%" """ % (topic) )
	pmid_list=[pm[0] for pm in curr.fetchall()]
	curr.execute(""" select pmid from mesh as k where headings like "%s%%" """ % (topic) )
	pmid_list.extend([pm[0] for pm in curr.fetchall()])
	curr.execute(""" select pmid from pubmed_article as k where title like "%s%%" """ % (topic) )
	pmid_list.extend([pm[0] for pm in curr.fetchall()])
	# print(pmid_list)
	a_b=len(pmid_list)
	if not a_b:
		return [()],{}
	pmid_list_str="( "
	for pmid in pmid_list[:-1]:
		pmid_list_str+="\""+pmid+"\", "
	pmid_list_str+="\""+pmid_list[-1]+"\" )"
	# print(pmid_list_str)
	actual_exec="""select author_name from authors where pmid in %s """ % (pmid_list_str)
	# print(actual_exec)
	curr.execute(actual_exec)
	author_name_list=[pm[0] for pm in curr.fetchall()]
	# print(author_name_list)
	pmid_set=set(pmid_list)
	for author in author_name_list:
		if not author:
			continue
		curr.execute("""select pmid,author_score from authors where author_name="%s" """ % (author) )
		res=curr.fetchall()
		author_pub_list=set([pm[0] for pm in res])
		a_set=pmid_set & author_pub_list
		author_score=sum([paper[1] for paper in res if paper[0] in a_set])
		a=len(a_set)
		b=a_b-a
		a_c=len(author_pub_list)
		c=a_c-a
		d=(total_articles-a_c)-b
		# print(author,a,b,c,d,a+b+c+d,total_articles)
		ranks.append((score(a,b,c,d) + author_score,author))
		auth_ranks[author]= (score(a,b,c,d) + author_score)
	ranks=sorted(ranks)
	ranks.reverse()
	# print(ranks)
	return ranks,auth_ranks


if __name__ == '__main__':
	import sys
	# print(sys.argv[1])
	if len(sys.argv) > 1:
		ranks,auth=topic_z_scorer(sys.argv[1])
		names=[name[1] for name in ranks]
		for name in names:
			print(name)
	else:
		ranks,auth=topic_z_scorer("heart")
		names=[name[1] for name in ranks]
		for name in names:
			print(name)
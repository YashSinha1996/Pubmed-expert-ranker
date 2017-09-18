import requests
from bs4 import BeautifulSoup
import pubmed_parser as pp
import MySQLdb
# This entire programs takes a lot of time. Oh yeah, install the above two repo's first, i.e bs4 and requests. 

def get_citations(pmcid):
	pmcid="PMC"+pmcid
	# print(pmcid)
	articles_url = 'http://www.ncbi.nlm.nih.gov/pmc/articles/%s' % pmcid
	headers = {
		'User-Agent': (
			"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) "
			"AppleWebKit/537.36 (KHTML, like Gecko) "
			"Chrome/39.0.2171.95 Safari/537.36"
		)
	}
	page = requests.get(articles_url, headers=headers)
	soup = BeautifulSoup(page.content, "lxml")
	pubmed_article_urls = [
		span.a['href'] for span in soup.findAll("span", {"class": "nowrap ref pubmed"})
	]
	return [url.replace(r'/pubmed/', '') for url in pubmed_article_urls]

if __name__ == '__main__': 
	db=MySQLdb.connect(host="127.0.0.1",user="root",passwd="password",db="pubmed")
	curr=db.cursor()
	curr.execute("select pmc from pubmed_article where pmc like 'P%';")
	pmc_list=[pm[0][3:] for pm in curr.fetchall()]
	print(pmc_list)
	try:
		#As you can see, there is no Foriegn Key constraint as at this point of time our 
		# db simply isn't big enough for us to impliment that constarint as it will be violated all the time becuase 
		# we don't have all the papers in our db 
		curr.execute("""create table citations (
				citated_by varchar(500),
				citated_to varchar(500)
			);
			""")
	except Exception as e:
		print("citations",e)

	print(pmc_list[6])
	# exit(0)
	for pmcid in pmc_list:
		#CIitations given by these papers
		print(pmcid)
		try:
			by_this=get_citations(pmcid)
			for to_cite in by_this:
				print("\tTo "+to_cite)
				curr.execute("""insert into citations (citated_by,citated_to) values ('%s','%s');""" % ( pmcid, to_cite) )
			print(pmcid)
			db.commit()
		except Exception as e:
			print("citations to",e)
		try:
			by_this=pp.parse_citation_web(pmcid,"PMC")['pmc_cited']
			for to_cite in by_this:
				print("\tFrom "+to_cite)
				curr.execute("""insert into citations (citated_by,citated_to) values ('%s','%s');""" % ( to_cite, pmcid) )
			db.commit()
		except Exception as e:
			print("citations from",e)


import pubmed_parser as pp
import pandas as pd
import MySQLdb
pubmed_data=pp.parse_medline_xml("medsample1.xml")
db=MySQLdb.connect(host="127.0.0.1",user="root",passwd="password",db="pubmed")
curr=db.cursor()
print(pubmed_data[5].keys())
print(pubmed_data[5])
try:
	curr.execute("""create table pubmed_article (
			pmid varchar(100) primary key,
			pmc varchar(100),
			issn_linking varchar(100),
			pubdate varchar(100),
			nlm_id varchar(50),
			title text,
			deleted varchar(50),
			abstract text,
			affiliation varchar(1000),
			journal varchar(1000),
			medline_ta varchar(100),
			country varchar(500),
			other_id varchar(200)
		);
		""")

except Exception as e:
	print("article",e)

try:
	curr.execute("""create table authors (
			author_name varchar(500),
			pmid varchar(100),
			FOREIGN KEY (pmid) REFERENCES pubmed_article(pmid)
		);
		""")
	
except Exception as e:
	print("authors",e)

try:
	curr.execute("""create table mesh (
			headings varchar(500),
			pmid varchar(100),
			FOREIGN KEY (pmid) REFERENCES pubmed_article(pmid)
		);
		""")
except Exception as e:
	print("mesh",e)

try:
	curr.execute("""create table keywords (
			keyword varchar(500),
			pmid varchar(100),
			FOREIGN KEY (pmid) REFERENCES pubmed_article(pmid)
		);
		""")
except Exception as e:
	print("keywords",e)

for i,row in enumerate(pubmed_data):
	try:
		k="""insert into pubmed_article
			(pmid,pmc,journal,issn_linking,medline_ta,country,abstract,other_id,title,deleted,nlm_id,pubdate
			,affiliation) values("%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s");""" % (
				row['pmid'],row['pmc'],row['journal'],row['issn_linking'],row['medline_ta'],row['country'],
				row['abstract'],row['other_id'],row['title'],row['delete'],row['nlm_unique_id'],row['pubdate'],
				row['affiliation']
				)
		print(k)
		curr.execute(k)
		if row['author']:
			authors_row=[" ".join(x.split()) for x in row['author'].split(';')]
			print(authors_row)
			try:
				for auth in authors_row:
					curr.execute("""insert into authors
						(author_name,pmid) values("%s","%s");"""% (auth,row['pmid'])
						)
			except Exception:
				pass
		if row['mesh_terms']:
			mesh_terms_row=[" ".join(x.split()) for x in row['mesh_terms'].split(';')]
			print(mesh_terms_row)
			try:
				for mesh in mesh_terms_row:
					curr.execute("""insert into mesh
						(headings,pmid) values("%s","%s");"""% (mesh,row['pmid'])
						)
			except Exception:
				pass
		if row['keywords']:
			keywords_row=[" ".join(x.split()) for x in row['keywords'].split(';')]
			print(keywords_row)
			try:
				for key in keywords_row:
					curr.execute("""insert into keywords
						(keyword,pmid) values("%s","%s");"""% (key,row['pmid'])
						)
			except Exception:
				pass
	except Exception:
		pass
	db.commit()
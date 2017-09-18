.PHONY: all clean

all: contact.py front.py output.py query.py status.py

%.py: %.tmpl
	${CHEETAH} compile $<

contact.py: page.py
front.py: page.py
output.py: page.py
query.py: page.py
status.py: page.py

clean:
	rm -f *.bak *.pyc

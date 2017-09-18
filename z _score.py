import math
# a is the number of articles on a given subject from a given author.
# b is the number of articles on a given subject excluding a given author.
# c is the number of articles excluding a given subject from a given author.
# d is the number of articles excluding a given subject and excluding a given author.

a = float(input(' Enter a: '))  
b = float(input(' Enter b: '))
c = float(input(' Enter c: '))
d = float(input(' Enter d: '))

def score(a,b,c,d):
 	n1 = (a + b)
 	n2 = (c + d)
 	p = (a + c)/(a + b + c + d)
 	q = 1 - p
 	p1 = a/(a + b)
 	p2 = c/(c + d)
 	r = math.sqrt(p * q * ((1/n1) + (1/n2)) )
 	z = (abs(p1 - p2) - (1/(2*n1)) - (1/(2*n2)) ) / r
 	return z

print (" The z score is ", score(a,b,c,d))

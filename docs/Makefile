.SUFFIXES: .dot .png .twopi
.PHONY:	 all

all:  lifecycle.png
	echo "Done"

%.png:	%.dot
	dot -O -T png $<

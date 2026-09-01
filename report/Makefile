# The one command: `make -C report` (or `make` from inside report/).
#
# The document builds with a TeX installation alone. Python is NOT required:
# report/figures/*.pdf are generated artifacts and are committed, so a clean
# checkout compiles without running anything. `make figures` regenerates them
# and needs the project installed (pip install -e .).

LATEXMK := latexmk

.PHONY: all figures clean distclean

all: main.pdf

main.pdf: main.tex $(wildcard sections/*.tex) $(wildcard figures/*.pdf) refs.bib
	$(LATEXMK) -pdf main.tex

# Regenerates every committed figure. Run it, then commit the PDFs it changes:
# a figure and the claim it supports move through the same pull request, which
# is what makes the report's provenance appendix true.
figures:
	python figures/make_scanpath.py

clean:
	$(LATEXMK) -c

distclean:
	$(LATEXMK) -C

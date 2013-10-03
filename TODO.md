TODO
====
This list is in no particular order, and things will get done
when/if I need them or I have spare time :) 

--ijm.


Line finding
============

The line finding algorithm is robust but cannot tell large blocks
of black from lines of black. So I need to add something that finds
and removes solid blocks.

Many tables use whitespace to delineate columns or rows but simply
running the same scan for white as is done for black returns a lot
of junk. For example, if the font used is a fixed space font, the
scanner returns grid with cells that are one character wide, and
one character high across the whole page.

Horizontal white rows are probably easiest to add, and in fact the
histogram data is already computed. However this puts a row boundary
between EVERY row of text, and makes automatic cropping much harder
and multi-cell consolidation impractical.

A significant number of tuning options will be needed in order
to control the width of whitespace recognised, weather or not to
remove already detected black delimiters etc.


Cell finding
============

The cell finding algorithm is very simplistic. It starts at the top
left and find all connected cells to its right, then descends,
stopping if any cell divider is seen, and remembers which cells
have been visited. This makes it 'width greedy'. It attempts to
start a search for every cell so it will find all sizes of rectangular
cells, but it will fail to find, and so split up, 2 of the 4 possible
L shapes, only 1 of the 4 C or U shapes, or any O shape (where a
cell surrounds another cell).

An option is needed to select width greedy, height greedy, square greedy.

A flood file algorithm would make a single cell for text around
a table, rather than the current splitting it into rectangles, but
this would also require a graph view of cell relationships.

Popplar wrapper
===============
A short peice of code that wrapps the poppler library to give the
same functionality as ppmtotext but over a socket or file descriptor,
and able to process sequential requests. At the moment pdf-extract
executes ppmtotext once for every cell it finds! This would be much
faster if a wrapper didn't need to be spun up repeatedly.

A wrapper is needed to comply with the MIT Expat vs GPL incompatibility.

Blank row or column removal
===========================
It shouldn't be to hard to notice when a complete row or column is
empty, and remove it from the result. However a number of tuning
options would be needed, including not removing empty row/column,
not remove empty row/column in the middle of the table, ignore white
space, ignore punctuation. etc.

Delimiter thickness hints
=========================
I should be able to record the relative thicknesses of the delimiters
around a cell, so that later on it would be possible to extract
table and heading boundaries for tables that use them in a detectable
way.

Better Hierarchical information
==============================
I want to keep the cell location data structure flat (because
ultimately the page is always flat), but I could include more
information about cell relationships, and facilitate rebuilding a
representative document object model down stream. I'd particularly
like to be able to automatically separate two tables on the same
page, and to auto-join a multi-page table.

Miscellaneous
=============

* An option to change the program called to extract text in each
cell: currently it calls pdftotext, but it could easily be ocrad
or any other pdf tool that can take a cropping rectangle.



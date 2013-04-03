Line finding
============

The line finding algorithm is robust but cannot tell large blocks
of black from lines of black. Also open areas of white might also
be considered cell delimiters.

 * Finding and removing blocks of solid colour.
 * Finding lines of white space between black delimiters.

Cell finding
============

The cell finding algorithm is very simplistic. It starts at the top
left and find all connected cells to its right, then descends,
stopping if any cell divider is seen, and remembers which cells
have been visited. This makes it 'width greedy'. It attempts to
start a search for every cell.

* An option is needed to select width greedy, height greedy, square greedy.
* A flood file algorithm would make a single cell for text around
a table, rather than the current splitting it into rectangles, but
this would also require a graph view of cell relationships.

Miscellaneous
=============

* An option to change the program called to extract text in each
cell: currently it calls pdftotext, but it could easily be ocrad
or any other pdf tool that can take a cropping rectangle.



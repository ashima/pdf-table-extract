import pandas as pd
import pdftableextract as pdf

pages = ["1"]
cells = [pdf.process_page("example.pdf",p) for p in pages]

#flatten the cells structure
cells = [item for sublist in cells for item in sublist ]

#without any options, process_page picks up a blank table at the top of the page.
#so choose table '1'
li = pdf.table_to_list(cells, pages)[1]

#li is a list of lists, the first line is the header, last is the footer (for this table only!)
#column '0' contains store names
#row '1' contains column headings
#data is row '2' through '-1'

data =pd.DataFrame(li[2:-1], columns=li[1], index=[l[0] for l in li[2:-1]])
print data

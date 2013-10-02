import argparse
import sys
import logging
from .core import PDFTableExtract
#-----------------------------------------------------------------------

def procargs() :
  p = argparse.ArgumentParser( description="Finds tables in a PDF page.")
  p.add_argument("-i", dest='infile',  help="input file" )
  p.add_argument("-o", dest='outfile', help="output file", default=None,
     type=str)
  p.add_argument("--greyscale_threshold","-g", help="grayscale threshold (%%)", type=int, default=25 )
  p.add_argument("-p", type=str, dest='page', required=True, action="append",
     help="a page in the PDF to process, as page[:firstrow:lastrow]." )
  p.add_argument("-c", type=str, dest='crop',
     help="crop to left:top:right:bottom. Paints white outside this "
          "rectangle."  )
  p.add_argument("--line_length", "-l", type=float, default=0.17 ,
     help="line length threshold (length)" )
  p.add_argument("--bitmap_resolution", "-r", type=int, default=300,
     help="resolution of internal bitmap (dots per length unit)" )
  p.add_argument("-name", help="name to add to XML tag, or HTML comments")
  p.add_argument("-pad", help="imitial image pading (pixels)", type=int,
     default=2 )
  p.add_argument("-white",action="append", 
    help="paint white to the bitmap as left:top:right:bottom in length units."
         "Done before painting black" )
  p.add_argument("-black",action="append", 
    help="paint black to the bitmap as left:top:right:bottom in length units."
         "Done after poainting white" )
  p.add_argument("-bitmap", action="store_true",
     help = "Dump working bitmap not debuging image." )
  p.add_argument("-checkcrop",  action="store_true",
     help = "Stop after finding croping rectangle, and output debuging "
            "image (use -bitmap).")
  p.add_argument("-checklines", action="store_true",
     help = "Stop after finding lines, and output debuging image." )
  p.add_argument("-checkdivs",  action="store_true",
     help = "Stop after finding dividors, and output debuging image." )
  p.add_argument("-checkcells", action="store_true",
     help = "Stop after finding cells, and output debuging image." )
  p.add_argument("-colmult", type=float, default=1.0,
     help = "color cycling multiplyer for checkcells and chtml" )
  p.add_argument("-boxes", action="store_true",
     help = "Just output cell corners, don't send cells to pdftotext." )
  p.add_argument("-t", choices=['cells_csv','cells_json','cells_xml',
     'table_csv','table_html','table_chtml'],
     default="cells_xml",
     help = "output type (table_chtml is colorized like '-checkcells') "
            "(default cells_xml)" )
  p.add_argument("--whitespace","-w", choices=['none','normalize','raw'], default="normalize",
     help = "What to do with whitespace in cells. none = remove it all, "
            "normalize (default) = any whitespace (including CRLF) replaced "
            "with a single space, raw = do nothing." )

  return p.parse_args()

def main():
    import core
    args = procargs()
    logging.basicConfig()
    pte = PDFTableExtract(infile=args.infile, 
                outfilename=args.outfile, 
                greyscale_threshold=args.greyscale_threshold,
                page=args.page,
                crop=args.crop,
                line_length=args.line_length,
                bitmap_resolution=args.bitmap_resolution,
                name=args.name,
                pad=args.pad,
                white=args.white,
                black=args.black)

    cells = []
    if args.checkcrop or args.checklines or args.checkdivs or args.checkcells:
        for pgs in args.page :
            print "MAIN"
            pte.process_page(pgs,
                bitmap=args.bitmap, 
                checkcrop=args.checkcrop, 
                checklines=args.checklines, 
                checkdivs=args.checkdivs,
                checkcells=args.checkcells,
                whitespace=args.whitespace,
                boxes=args.boxes)
    else:
        for pgs in args.page :
            cells.extend(pte.process_page(pgs,
                    bitmap=args.bitmap, 
                    checkcrop=args.checkcrop, 
                    checklines=args.checklines, 
                    checkdivs=args.checkdivs,
                    checkcells=args.checkcells,
                    whitespace=args.whitespace,
                    boxes=args.boxes))


            print cells
            getattr(pte, "o_{0}".format(args.t))(cells, args.page)




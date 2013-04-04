# Description : PDF Table Extraction Utility
#      Author : Ian McEwan, Ashima Research.
#  Maintainer : ijm
#     Lastmod : 20130402 (ijm)
#     License : Copyright (C) 2011 Ashima Research. All rights reserved.
#               Distributed under the MIT Expat License. See LICENSE file.
#               https://github.com/ashima/pdf-table-extract

import sys, argparse, subprocess, re, csv, json
from numpy import *
from pipes import quote
from xml.dom.minidom import getDOMImplementation

#-----------------------------------------------------------------------

def procargs() :
  p = argparse.ArgumentParser( description="Finds tables in a PDF page.")
  p.add_argument("-i", dest='infile',  help="input file" )
  p.add_argument("-o", dest='outfile', help="output file", default=sys.stdout,
     type=argparse.FileType('w') )
  p.add_argument("-p", dest='page', required=True, action="append",
     help="a page in the PDF to process, as page[:firstrow:lastrow]." )
  p.add_argument("-g", help="grayscale threshold (%%)", type=int, default=25 )
  p.add_argument("-l", type=float, default=0.17 ,
     help="line length threshold (length)" )
  p.add_argument("-r", type=int, default=300,
     help="resolution of internal bitmap (dots per length unit)" )
  p.add_argument("-name", help="name to add to XML tag, or HTML comments")
  p.add_argument("-pad", help="imitial image pading (pixels)", type=int,
     default=2 )
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
  p.add_argument("-w", choices=['none','normalize','raw'], default="normalize",
     help = "What to do with whitespace in cells. none = remove it all, "
            "normalize (default) = any whitespace (including CRLF) replaced "
            "with a single space, raw = do nothing." )

  return p.parse_args()

#-----------------------------------------------------------------------
def colinterp(a,x) :
  l = len(a)-1
  i = min(l, max(0, int (x * l)))
  (u,v) = a[i:i+2,:]
  return u - (u-v) * ((x * l) % 1.0)

colarr = array([ [255,0,0],[255,255,0],[0,255,0],[0,255,255],[0,0,255] ])

def col(x) :
  return colinterp(colarr,(args.colmult * x)% 1.0) / 2

#-----------------------------------------------------------------------
# PNM stuff.

def noncomment(fd):
  while True:
    x = fd.readline() 
    if x.startswith('#') :
      continue
    else:
      return x

def readPNM(fd):
  t = noncomment(fd)
  s = noncomment(fd)
  m = noncomment(fd) if not (t.startswith('P1') or t.startswith('P4')) else '1'
  data = fd.read()

  xs, ys = s.split()
  width = int(xs)
  height = int(ys)
  m = int(m)

  if m != 255 :
    print "Just want 8 bit pgms for now!"
  
  d = fromstring(data,dtype=uint8)
  d = reshape(d, (height,width) )
  return (m,width,height, d)

def writePNM(fd,img):
  s = img.shape
  m = 255
  if img.dtype == bool :
    img = img + uint8(0) 
    t = "P5"
    m = 1
  elif len(s) == 2 :
    t = "P5"
  else:
    t = "P6"
    
  fd.write( "%s\n%d %d\n%d\n" % (t, s[1],s[0],m) )
  fd.write( uint8(img).tostring() )


def dumpImage(args,bmp,img) :
    writePNM(args.outfile, bmp if args.bitmap else img)
    args.outfile.close()

#-----------------------------------------------------------------------
# Proccessing function.

def process_page(pgs) :
  (pg,frow,lrow) = (map(int,(pgs.split(":")))+[None,None])[0:3]

  p = subprocess.Popen( ("pdftoppm -gray -r %d -f %d -l %d %s " %
      (args.r,pg,pg,quote(args.infile))),
      stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True )

#-----------------------------------------------------------------------
# image load secion.

  (maxval, width, height, data) = readPNM(p.stdout)

  pad = int(args.pad)
  height+=pad*2
  width+=pad*2
  
# reimbed image with a white padd.
  bmp = ones( (height,width) , dtype=uint8 )
  bmp[pad:height-pad,pad:width-pad] = ( data[:,:] > int(255.0*args.g/100.0) )

# Set up Debuging image.
  img = zeros( (height,width,3) , dtype=uint8 )
  img[:,:,0] = bmp*255
  img[:,:,1] = bmp*255
  img[:,:,2] = bmp*255

#-----------------------------------------------------------------------
# Find bounding box.

  t=0
  while t < height and sum(bmp[t,:]==0) == 0 :
    t=t+1
  if t > 0 :
    t=t-1
  
  b=height-1
  while b > t and sum(bmp[b,:]==0) == 0 :
    b=b-1
  if b < height-1:
    b = b+1
  
  l=0
  while l < width and sum(bmp[:,l]==0) == 0 :
    l=l+1
  if l > 0 :
    l=l-1
  
  r=width-1
  while r > l and sum(bmp[:,r]==0) == 0 :
    r=r-1
  if r < width-1 :
    r=r+1
  
# Mark bounding box.
  bmp[t,:] = 0
  bmp[b,:] = 0
  bmp[:,l] = 0
  bmp[:,r] = 0
  
  if args.checkcrop :
    dumpImage(args,bmp,img)
    sys.exit(0)
#-----------------------------------------------------------------------
# Line finding section.
#
# Find all verticle or horizontal lines that are more than rlthresh 
# long, these are considered lines on the table grid.

  lthresh = int(args.l * args.r)
  vs = zeros(width, dtype=int)
  for i in range(width) :
    dd = diff( where(bmp[:,i])[0] ) 
    if len(dd)>0:
      v = max ( dd )
      if v > lthresh :
        vs[i] = 1
    else:
# it was a solid black line.
      if bmp[0,i] == 0 :
        vs[i] = 1
  vd= ( where(diff(vs[:]))[0] +1 )

  hs = zeros(height, dtype=int)
  for j in range(height) :
    dd = diff( where(bmp[j,:]==1)[0] )
    if len(dd) > 0 :
      h = max ( dd )
      if h > lthresh :
        hs[j] = 1
    else:
# it was a solid black line.
      if bmp[j,0] == 0 :
        hs[j] = 1
  hd=(  where(diff(hs[:]==1))[0] +1 )

#-----------------------------------------------------------------------
# Look for dividors that are too large.

  maxdiv=10
  i=0

  while i < len(vd) :
    if vd[i+1]-vd[i] > maxdiv :
      vd.pop(i)
      vd.pop(i)
    else:
      i=i+2
  
  j = 0 
  while j < len(hd):
    if hd[j+1]-hd[j] > maxdiv :
      hd.pop(j)
      hd.pop(j)
    else:
      j=j+2
  
  if args.checklines :
    for i in vd :
      img[:,i] = [255,0,0] # red
  
    for j in hd :
      img[j,:] = [0,0,255] # blue
    dumpImage(args,bmp,img)
    sys.exit(0)
  
#-----------------------------------------------------------------------
# divider checking.
#
# at this point vd holds the x coordinate of vertical  and 
# hd holds the y coordinate of horizontal divider tansitions for each 
# vertical and horizontal lines in the table grid.

  def isDiv(a, l,r,t,b) :
          # if any col or row (in axis) is all zeros ...
    return sum( sum(bmp[t:b, l:r], axis=a)==0 ) >0 

  if args.checkdivs :
    img = img / 2
    for j in range(0,len(hd),2):
      for i in range(0,len(vd),2):
        if i>0 :
          (l,r,t,b) = (vd[i-1], vd[i],   hd[j],   hd[j+1]) 
          img[ t:b, l:r, 1 ] = 192
          if isDiv(1, l,r,t,b) :
            img[ t:b, l:r, 0 ] = 0
            img[ t:b, l:r, 2 ] = 255
          
        if j>0 :
          (l,r,t,b) = (vd[i],   vd[i+1], hd[j-1], hd[j] )
          img[ t:b, l:r, 1 ] = 128
          if isDiv(0, l,r,t,b) :
            img[ t:b, l:r, 0 ] = 255
            img[ t:b, l:r, 2 ] = 0
  
    dumpImage(args,bmp,img)
    sys.exit(0)
  
#-----------------------------------------------------------------------
# Cell finding section.
# This algorithum is width hungry, and always generates rectangular
# boxes.

  cells =[] 
  touched = zeros( (len(hd), len(vd)),dtype=bool )
  j = 0
  while j*2+2 < len (hd) :
    i = 0
    while i*2+2 < len(vd) :
      u = 1
      v = 1
      if not touched[j,i] :
        while 2+(i+u)*2 < len(vd) and \
            not isDiv( 0, vd[ 2*(i+u) ], vd[ 2*(i+u)+1],
               hd[ 2*(j+v)-1 ], hd[ 2*(j+v) ] ):
          u=u+1
        bot = False
        while 2+(j+v)*2 < len(hd) and not bot :
          bot = False
          for k in range(1,u+1) :
            bot |= isDiv( 1, vd[ 2*(i+k)-1 ], vd[ 2*(i+k)],
               hd[ 2*(j+v) ], hd[ 2*(j+v)+1 ] )
          if not bot :
            v=v+1
        cells.append( (i,j,u,v) )
        touched[ j:j+v, i:i+u] = True
      i = i+1
    j=j+1
  
  
  if args.checkcells :
    nc = len(cells)+0.
    img = img / 2
    for k in range(len(cells)):
      (i,j,u,v) = cells[k]
      (l,r,t,b) = ( vd[2*i+1] , vd[ 2*(i+u) ], hd[2*j+1], hd[2*(j+v)] )
      img[ t:b, l:r ] += col( k/nc )
    dumpImage(args,bmp,img)
    sys.exit(0)
  
  
#-----------------------------------------------------------------------
# fork out to extract text for each cell.

  whitespace = re.compile( r'\s+')
   
  def getCell( (i,j,u,v) ):
    (l,r,t,b) = ( vd[2*i+1] , vd[ 2*(i+u) ], hd[2*j+1], hd[2*(j+v)] )
    p = subprocess.Popen(
    ("pdftotext -r %d -x %d -y %d -W %d -H %d -layout -nopgbrk -f %d -l %d %s -"
         % (args.r, l-pad, t-pad, r-l, b-t, pg, pg, quote(args.infile) ) ),
        stdout=subprocess.PIPE, shell=True )
    
    ret = p.communicate()[0]
    if args.w != 'raw' :
      ret = whitespace.sub( "" if args.w == "none" else " ", ret )
      if len(ret) > 0 :
        ret = ret[ (1 if ret[0]==' ' else 0) : 
                   len(ret) - (1 if ret[-1]==' ' else 0) ]
    return (i,j,u,v,pg,ret)

  #if args.boxes :
  #  cells = [ x + (pg,"",) for x in cells ]
  #else :
  #  cells = map(getCell, cells)
  
  if args.boxes :
    cells = [ x + (pg,"",) for x in cells if 
              ( frow == None or (x[1] >= frow and x[1] <= lrow)) ]
  else :
    cells = [ getCell(x)   for x in cells if 
              ( frow == None or (x[1] >= frow and x[1] <= lrow)) ]
  return cells

#-----------------------------------------------------------------------
# Output section.

def o_cells_csv(cells,pgs) :
    csv.writer( args.outfile , dialect='excel' ).writerows(cells)
  
def o_cells_json(cells,pgs) :
    json.dump({ 
      "src": args.infile,
      "name": args.name,
      "colnames": ( "x","y","width","height","page","contents" ),
      "cells":cells
      }, args.outfile)
 
def o_cells_xml(cells,pgs) : 
  doc = getDOMImplementation().createDocument(None,"table", None)
  root = doc.documentElement;
  root.setAttribute("src",args.infile)
  root.setAttribute("name",args.name)
  for cl in cells :
    x = doc.createElement("cell")
    map(lambda(a): x.setAttribute(*a), zip("xywhp",map(str,cl)))
    if cl[5] != "" :
      x.appendChild( doc.createTextNode(cl[5]) )
    root.appendChild(x)
  args.outfile.write( doc.toprettyxml() )
  
def o_table_csv(cells,pgs) : 
  tab = [ [ [ "" for x in range(len(vd)/2 +1)
            ] for x in range(len(hd)/2+1) 
          ] for x in range(len(pgs))
        ]
  for (i,j,u,v,pg,value) in cells :
    tab[pg][j][i] = value
  for t in tab:
    csv.writer( args.outfile , dialect='excel' ).writerows(t)
  
def o_table_html(cells,pgs) : 
  oj = 0 
  opg = 0
  doc = getDOMImplementation().createDocument(None,"table", None)
  root = doc.documentElement;
  if (args.t == "table_chtml" ):
    root.setAttribute("border","1")
    root.setAttribute("cellspaceing","0")
    root.setAttribute("style","border-spacing:0")
  nc = len(cells)
  tr = None
  for k in range(nc):
    (i,j,u,v,pg,value) = cells[k]
    if j > oj or pg > opg:
      if pg > opg:
        root.appendChild( doc.createComment(
          "Name: %s, Source: %s page %d." % (args.name,args.infile, pg) ));
      if tr :
        root.appendChild(tr)
      tr = doc.createElement("tr")
      oj = j
      opg = pg
    td = doc.createElement("td")
    if value != "" :
      td.appendChild( doc.createTextNode(value) )
    if u>1 :
      td.setAttribute("colspan",str(u))
    if v>1 :
      td.setAttribute("rowspan",str(v))
    if args.t == "table_chtml" :
      td.setAttribute("style", "background-color: #%02x%02x%02x" %
            tuple(128+col(k/(nc+0.))))
    tr.appendChild(td)
  root.appendChild(tr)
  args.outfile.write( doc.toprettyxml() )
  
#-----------------------------------------------------------------------
# main

args = procargs()

cells = []
for pgs in args.page :
  cells.extend(process_page(pgs))

{ "cells_csv" : o_cells_csv,   "cells_json" : o_cells_json,
  "cells_xml" : o_cells_xml,   "table_csv"  : o_table_csv,
  "table_html": o_table_html,  "table_chtml": o_table_html,
  } [ args.t ](cells,args.page)


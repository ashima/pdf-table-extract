import sys
from numpy import array, fromstring, ones, zeros, uint8, diff, where, sum
import subprocess
from pipes import quote
from .pnm import readPNM, dumpImage
import re
from pipes import quote
from xml.dom.minidom import getDOMImplementation
import json
import csv
#-----------------------------------------------------------------------
def colinterp(a,x) :
    """Interpolates colors"""
    l = len(a)-1
    i = min(l, max(0, int (x * l)))
    (u,v) = a[i:i+2,:]
    return u - (u-v) * ((x * l) % 1.0)

colarr = array([ [255,0,0],[255,255,0],[0,255,0],[0,255,255],[0,0,255] ])

def col(x, colmult=1.0) :
    """colors"""
    return colinterp(colarr,(colmult * x)% 1.0) / 2


def process_page(infile, pgs, 
    outfilename=None,
    greyscale_threshold=25,
    page=None,
    crop=None,
    line_length=0.17
    bitmap_resolution=300,
    name=None,
    pad=2,
    white=None,
    black=None,
    bitmap=False, 
    checkcrop=False, 
    checklines=False, 
    checkdivs=False,
    checkcells=False,
    whitespace="normalize",
    boxes=False) :
    
  outfile = open(outfilename,'w') if outfilename else sys.stdout
  page=page or []
  (pg,frow,lrow) = (map(int,(pgs.split(":")))+[None,None])[0:3]

  p = subprocess.Popen( ("pdftoppm -gray -r %d -f %d -l %d %s " %
      (bitmap_resolution,pg,pg,quote(infile))),
      stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True )

#-----------------------------------------------------------------------
# image load secion.

  (maxval, width, height, data) = readPNM(p.stdout)

  pad = int(pad)
  height+=pad*2
  width+=pad*2
  
# reimbed image with a white padd.
  bmp = ones( (height,width) , dtype=bool )
  bmp[pad:height-pad,pad:width-pad] = ( data[:,:] > int(255.0*greyscale_threshold/100.0) )

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

  def boxOfString(x,p) :
    s = x.split(":")
    if len(s) < 4 :
      raise ValueError("boxes have format left:top:right:bottom[:page]")
    return ([bitmap_resolution * float(x) + pad for x in s[0:4] ]
                + [ p if len(s)<5 else int(s[4]) ] ) 


# translate crop to paint white.
  whites = []
  if crop :
    (l,t,r,b,p) = boxOfString(crop,pg) 
    whites.extend( [ (0,0,l,height,p), (0,0,width,t,p),
                     (r,0,width,height,p), (0,b,width,height,p) ] )

# paint white ...
  if white :
    whites.extend( [ boxOfString(b, pg) for b in white ] )

  for (l,t,r,b,p) in whites :
    if p == pg :
      bmp[ t:b+1,l:r+1 ] = 1
      img[ t:b+1,l:r+1 ] = [255,255,255]
  
# paint black ...
  if black :
    for b in black :
      (l,t,r,b) = [bitmap_resolution * float(x) + pad for x in b.split(":") ]
      bmp[ t:b+1,l:r+1 ] = 0
      img[ t:b+1,l:r+1 ] = [0,0,0]

  if checkcrop :
    dumpImage(outfile,bmp,img, bitmap, pad)
    return True
    
#-----------------------------------------------------------------------
# Line finding section.
#
# Find all vertical or horizontal lines that are more than rlthresh 
# long, these are considered lines on the table grid.

  lthresh = int(line_length * bitmap_resolution)
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
      vd = delete(vd,i)
      vd = delete(vd,i)
    else:
      i=i+2
  
  j = 0 
  while j < len(hd):
    if hd[j+1]-hd[j] > maxdiv :
      hd = delete(hd,j)
      hd = delete(hd,j)
    else:
      j=j+2
  
  if checklines :
    for i in vd :
      img[:,i] = [255,0,0] # red
  
    for j in hd :
      img[j,:] = [0,0,255] # blue
    dumpImage(outfile,bmp,img)
    return True
#-----------------------------------------------------------------------
# divider checking.
#
# at this point vd holds the x coordinate of vertical  and 
# hd holds the y coordinate of horizontal divider tansitions for each 
# vertical and horizontal lines in the table grid.

  def isDiv(a, l,r,t,b) :
          # if any col or row (in axis) is all zeros ...
    return sum( sum(bmp[t:b, l:r], axis=a)==0 ) >0 

  if checkdivs :
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
    dumpImage(outfile,bmp,img)
    return True
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
  
  
  if checkcells :
    nc = len(cells)+0.
    img = img / 2
    for k in range(len(cells)):
      (i,j,u,v) = cells[k]
      (l,r,t,b) = ( vd[2*i+1] , vd[ 2*(i+u) ], hd[2*j+1], hd[2*(j+v)] )
      img[ t:b, l:r ] += col( k/nc )
    dumpImage(outfile,bmp,img)
    return True
  
#-----------------------------------------------------------------------
# fork out to extract text for each cell.

  whitespace = re.compile( r'\s+')
   
  def getCell( (i,j,u,v) ):
    (l,r,t,b) = ( vd[2*i+1] , vd[ 2*(i+u) ], hd[2*j+1], hd[2*(j+v)] )
    p = subprocess.Popen(
    ("pdftotext -r %d -x %d -y %d -W %d -H %d -layout -nopgbrk -f %d -l %d %s -"
         % (bitmap_resolution, l-pad, t-pad, r-l, b-t, pg, pg, quote(infile) ) ),
        stdout=subprocess.PIPE, shell=True )
    
    ret = p.communicate()[0]
    if whitespace != 'raw' :
      ret = whitespace.sub( "" if whitespace == "none" else " ", ret )
      if len(ret) > 0 :
        ret = ret[ (1 if ret[0]==' ' else 0) : 
                   len(ret) - (1 if ret[-1]==' ' else 0) ]
    return (i,j,u,v,pg,ret)
      
  if boxes :
    cells = [ x + (pg,"",) for x in cells if 
              ( frow == None or (x[1] >= frow and x[1] <= lrow)) ]
  else :
    cells = [ getCell(x)   for x in cells if 
              ( frow == None or (x[1] >= frow and x[1] <= lrow)) ]
  return cells

#-----------------------------------------------------------------------
tput section.

def o_cells_csv(cells,pgs) :
  csv.writer( outfile , dialect='excel' ).writerows(cells)

def o_cells_json(cells,pgs) :
  """Output JSON formatted cell data"""
  json.dump({ 
    "src": infile,
    "name": name,
    "colnames": ( "x","y","width","height","page","contents" ),
    "cells":cells
    }, outfile)

def o_cells_xml(self, cells,pgs) : 
  """Output XML formatted cell data"""
  doc = getDOMImplementation().createDocument(None,"table", None)
  root = doc.documentElement;
  root.setAttribute("src",self.infile)
  if self.name :
    root.setAttribute("name",self.name)
  for cl in cells :
    x = doc.createElement("cell")
    map(lambda(a): x.setAttribute(*a), zip("xywhp",map(str,cl)))
    if cl[5] != "" :
      x.appendChild( doc.createTextNode(cl[5]) )
    root.appendChild(x)
  self.outfile.write( doc.toprettyxml() )
  
def o_table_csv(self, cells,pgs) :
  """Output CSV formatted table"""
  l=[0,0,0]

  for (i,j,u,v,pg,value) in cells :
      r=[i,j,pg]
      l = [max(x) for x in zip(l,r)]
  
  tab = [ [ [ "" for x in range(l[0]+1)
            ] for x in range(l[1]+1)
          ] for x in range(l[2]+1)
        ]
  for (i,j,u,v,pg,value) in cells :
    tab[pg][j][i] = value
  for t in tab:
    csv.writer( self.outfile , dialect='excel' ).writerows(t)
  
def o_table_html(self, cells,pgs, output_type=None) : 
  """Output HTML formatted table"""
  oj = 0 
  opg = 0
  doc = getDOMImplementation().createDocument(None,"table", None)
  root = doc.documentElement;
  if (output_type == "table_chtml" ):
    root.setAttribute("border","1")
    root.setAttribute("cellspaceing","0")
    root.setAttribute("style","border-spacing:0")
  nc = len(cells)
  tr = None
  for k in range(nc):
    (i,j,u,v,pg,value) = cells[k]
    if j > oj or pg > opg:
      if pg > opg:
        s = "Name: " + self.name + ", " if self.name else ""
        root.appendChild( doc.createComment( s + 
          ("Source: %s page %d." % (self.infile, pg) )));
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
    if output_type == "table_chtml" :
      td.setAttribute("style", "background-color: #%02x%02x%02x" %
            tuple(128+col(k/(nc+0.))))
    tr.appendChild(td)
  root.appendChild(tr)
  args.outfile.write( doc.toprettyxml() )
  
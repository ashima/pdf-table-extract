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
  bmp = ones( (height,width) , dtype=bool )
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

  def boxOfString(x,p) :
    s = x.split(":")
    if len(s) < 4 :
      raise Exception("boxes have format left:top:right:bottom[:page]")
    return ([args.r * float(x) + args.pad for x in s[0:4] ]
                + [ p if len(s)<5 else int(s[4]) ] ) 


# translate crop to paint white.
  whites = []
  if args.crop :
    (l,t,r,b,p) = boxOfString(args.crop,pg) 
    whites.extend( [ (0,0,l,height,p), (0,0,width,t,p),
                     (r,0,width,height,p), (0,b,width,height,p) ] )

# paint white ...
  if args.white :
    whites.extend( [ boxOfString(b, pg) for b in args.white ] )

  for (l,t,r,b,p) in whites :
    if p == pg :
      bmp[ t:b+1,l:r+1 ] = 1
      img[ t:b+1,l:r+1 ] = [255,255,255]
  
# paint black ...
  if args.black :
    for b in args.black :
      (l,t,r,b) = [args.r * float(x) + args.pad for x in b.split(":") ]
      bmp[ t:b+1,l:r+1 ] = 0
      img[ t:b+1,l:r+1 ] = [0,0,0]

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
# main

def main_script():
    args = procargs()

    cells = []
    for pgs in args.page :
      cells.extend(process_page(pgs))

    { "cells_csv" : o_cells_csv,   "cells_json" : o_cells_json,
      "cells_xml" : o_cells_xml,   "table_csv"  : o_table_csv,
      "table_html": o_table_html,  "table_chtml": o_table_html,
      } [ args.t ](cells,args.page)


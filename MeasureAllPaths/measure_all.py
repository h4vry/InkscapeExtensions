#!/usr/bin/env python 
'''
This extension module can measure the path lengths in a
given unit.

Based on Measure Paths Which is 
Copyright (C) 2010 Alvin Penner
Copyright (C) 2006 Georg Wiora
Copyright (C) 2006 Nathan Hurst
Copyright (C) 2005 Aaron Spike, aaron@ekips.org

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
'''
import inkex, simplestyle, simplepath, sys, cubicsuperpath, bezmisc, locale
# Set current system locale
locale.setlocale(locale.LC_ALL, '')

def numsegs(csp):
    return sum([len(p)-1 for p in csp])
def interpcoord(v1,v2,p):
    return v1+((v2-v1)*p)
def interppoints(p1,p2,p):
    return [interpcoord(p1[0],p2[0],p),interpcoord(p1[1],p2[1],p)]
def pointdistance((x1,y1),(x2,y2)):
    return math.sqrt(((x2 - x1) ** 2) + ((y2 - y1) ** 2))
def bezlenapprx(sp1, sp2):
    return pointdistance(sp1[1], sp1[2]) + pointdistance(sp1[2], sp2[0]) + pointdistance(sp2[0], sp2[1])
def tpoint((x1,y1), (x2,y2), t = 0.5):
    return [x1+t*(x2-x1),y1+t*(y2-y1)]
def cspbezsplit(sp1, sp2, t = 0.5):
    m1=tpoint(sp1[1],sp1[2],t)
    m2=tpoint(sp1[2],sp2[0],t)
    m3=tpoint(sp2[0],sp2[1],t)
    m4=tpoint(m1,m2,t)
    m5=tpoint(m2,m3,t)
    m=tpoint(m4,m5,t)
    return [[sp1[0][:],sp1[1][:],m1], [m4,m,m5], [m3,sp2[1][:],sp2[2][:]]]
def cspbezsplitatlength(sp1, sp2, l = 0.5, tolerance = 0.001):
    bez = (sp1[1][:],sp1[2][:],sp2[0][:],sp2[1][:])
    t = bezmisc.beziertatlength(bez, l, tolerance)
    return cspbezsplit(sp1, sp2, t)
def cspseglength(sp1,sp2, tolerance = 0.001):
    bez = (sp1[1][:],sp1[2][:],sp2[0][:],sp2[1][:])
    return bezmisc.bezierlength(bez, tolerance)    
def csplength(csp):
    total = 0
    lengths = []
    for sp in csp:
        lengths.append([])
        for i in xrange(1,len(sp)):
            l = cspseglength(sp[i-1],sp[i])
            lengths[-1].append(l)
            total += l            
    return lengths, total
def csparea(csp):
    area = 0.0
    n0 = 0.0
    x0 = 0.0
    y0 = 0.0
    for sp in csp:
        for i in range(len(sp)):            # calculate polygon area
            area += 0.5*sp[i-1][1][0]*(sp[i][1][1] - sp[i-2][1][1])
            if abs(sp[i-1][1][0]-sp[i][1][0]) > 0.001 or abs(sp[i-1][1][1]-sp[i][1][1]) > 0.001:
                n0 += 1.0
                x0 += sp[i][1][0]
                y0 += sp[i][1][1]
        for i in range(1, len(sp)):         # add contribution from cubic Bezier
            bezarea  = ( 0.0*sp[i-1][1][1] + 2.0*sp[i-1][2][1] + 1.0*sp[i][0][1] - 3.0*sp[i][1][1])*sp[i-1][1][0]
            bezarea += (-2.0*sp[i-1][1][1] + 0.0*sp[i-1][2][1] + 1.0*sp[i][0][1] + 1.0*sp[i][1][1])*sp[i-1][2][0]
            bezarea += (-1.0*sp[i-1][1][1] - 1.0*sp[i-1][2][1] + 0.0*sp[i][0][1] + 2.0*sp[i][1][1])*sp[i][0][0]
            bezarea += ( 3.0*sp[i-1][1][1] - 1.0*sp[i-1][2][1] - 2.0*sp[i][0][1] + 0.0*sp[i][1][1])*sp[i][1][0]
            area += 0.15*bezarea
    return abs(area), x0/n0, y0/n0

class Length(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)
        self.OptionParser.add_option("--type",
                        action="store", type="string", 
                        dest="type", default="length",
                        help="Type of measurement")
        self.OptionParser.add_option("-f", "--fontsize",
                        action="store", type="int", 
                        dest="fontsize", default=20,
                        help="Size of length lable text in px")
        self.OptionParser.add_option("-o", "--offset",
                        action="store", type="float", 
                        dest="offset", default=-6,
                        help="The distance above the curve")
        self.OptionParser.add_option("-u", "--unit",
                        action="store", type="string", 
                        dest="unit", default="mm",
                        help="The unit of the measurement")
        self.OptionParser.add_option("-p", "--precision",
                        action="store", type="int", 
                        dest="precision", default=2,
                        help="Number of significant digits after decimal point")
        self.OptionParser.add_option("-s", "--scale",
                        action="store", type="float", 
                        dest="scale", default=1,
                        help="The distance above the curve")
        self.OptionParser.add_option("-r", "--orient",
                        action="store", type="inkbool", 
                        dest="orient", default=True,
                        help="Keep orientation of text upright")
        self.OptionParser.add_option("--tab",
                        action="store", type="string", 
                        dest="tab", default="sampling",
                        help="The selected UI-tab when OK was pressed") 
        self.OptionParser.add_option("--measurehelp",
                        action="store", type="string", 
                        dest="measurehelp", default="",
                        help="dummy") 
                        
    def effect(self):
        # get number of digits
        prec = int(self.options.precision)
        total = 0
        stotal = 0
        totals = {}
        # loop over all selected paths
        for node in self.document.getroot().iterdescendants():
        #path = "*"
        #for node in self.document.xpath(path, namespaces=inkex.NSS):
            if node.tag == inkex.addNS('path','svg'):
                id = node.get('id')
                self.group = inkex.etree.SubElement(node.getparent(),inkex.addNS('text','svg'))                
                t = node.get('transform')
                #inkex.debug(node.get("style"))
                d = node.get('d')
                if  not ("stroke" in simplestyle.parseStyle(node.get("style")) and len(simplepath.parsePath(d))):
                    continue
                stroke = simplestyle.parseStyle(node.get("style"))["stroke"]
                a =[]
                p = cubicsuperpath.parsePath(node.get('d'))
                num = 1
                factor = 1.0/self.unittouu('1'+self.options.unit)
                if self.options.type == "length":
                    slengths, stotal = csplength(p)
                else:
                    stotal,x0,y0 = csparea(p)
                    stotal *= factor*self.options.scale
                total += stotal
                if stroke in totals:
                    totals[stroke] += stotal
                else:
                    totals[stroke] = stotal
                # Format the length as string
        
        for key in totals:            
            lenstr = locale.format("%(len)25."+str(prec)+"f",{'len':round(totals[key]*factor*self.options.scale,prec)}).strip()
            val = key
            for color in simplestyle.svgcolors.keys():                
                if simplestyle.svgcolors.get(color) == key:
                    val = color
            inkex.debug(val + ":\t" + lenstr + "\t" + self.options.unit)


if __name__ == '__main__':
    e = Length()
    e.affect()


# vim: expandtab shiftwidth=4 tabstop=8 softtabstop=4 encoding=utf-8 textwidth=99

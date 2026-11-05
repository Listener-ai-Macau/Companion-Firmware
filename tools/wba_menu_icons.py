"""Pixel-hinted monochrome Companion menu shapes.

Every pixel is classified once from continuous shape geometry at the native
resolution. Rounded corners and counters share their center/radius; no rounded
Bezier vertices, image rotation, resampling, antialiasing or dither is used.
"""
import math


class NativeInk:
    def __init__(self,draw,x=0,y=0):self.draw=draw;self.x=x;self.y=y

    def mask(self,box,inside,fill=0):
        left,top,right,bottom=box
        for yy in range(math.floor(top),math.ceil(bottom)+1):
            for xx in range(math.floor(left),math.ceil(right)+1):
                if inside(xx,yy):self.draw.point((self.x+xx,self.y+yy),fill=fill)

    def roundrect(self,box,radius,fill=0,stroke=None):
        left,top,right,bottom=box
        cx=(left+right)/2;cy=(top+bottom)/2
        hx=(right-left+1)/2;hy=(bottom-top+1)/2
        radius=min(radius,hx,hy)
        def inside(px,py):
            qx=abs(px-cx)-(hx-radius);qy=abs(py-cy)-(hy-radius)
            dist=math.hypot(max(qx,0),max(qy,0))+min(max(qx,qy),0)-radius
            return dist<=0 and (stroke is None or dist>=-stroke)
        self.mask(box,inside,fill)

    def ellipse(self,box,fill=0,stroke=None):
        left,top,right,bottom=box
        cx=(left+right)/2;cy=(top+bottom)/2
        rx=(right-left+1)/2;ry=(bottom-top+1)/2
        def inside(px,py):
            outer=((px-cx)/rx)**2+((py-cy)/ry)**2<=1
            inner=stroke is not None and rx>stroke and ry>stroke and ((px-cx)/(rx-stroke))**2+((py-cy)/(ry-stroke))**2<1
            return outer and not inner
        self.mask(box,inside,fill)

    def line(self,points,width=2.4,fill=0):
        segments=[]
        for (ax,ay),(bx,by) in zip(points,points[1:]):
            dx=bx-ax;dy=by-ay;length=dx*dx+dy*dy
            if length:segments.append((ax,ay,dx,dy,length))
        if not segments:return
        radius=width/2
        box=(min(p[0] for p in points)-radius,min(p[1] for p in points)-radius,
             max(p[0] for p in points)+radius,max(p[1] for p in points)+radius)
        def inside(px,py):
            for ax,ay,dx,dy,length in segments:
                t=max(0,min(1,((px-ax)*dx+(py-ay)*dy)/length))
                if (px-ax-t*dx)**2+(py-ay-t*dy)**2<=radius*radius:return True
            return False
        self.mask(box,inside,fill)

    def curve(self,start,segments,width=2.0,fill=0):
        # Keep subpixel vertices until the final distance-to-stroke test.
        points=[start];ax,ay=start
        for c1,c2,end in segments:
            for n in range(1,25):
                t=n/24;s=1-t
                points.append((s**3*ax+3*s*s*t*c1[0]+3*s*t*t*c2[0]+t**3*end[0],
                               s**3*ay+3*s*s*t*c1[1]+3*s*t*t*c2[1]+t**3*end[1]))
            ax,ay=end
        self.line(points,width,fill)

    def arc(self,cx,cy,radius,start,end,width=2.4,fill=0):
        half=width/2
        def inside(px,py):
            angle=math.degrees(math.atan2(py-cy,px-cx))%360
            return start<=angle<=end and abs(math.hypot(px-cx,py-cy)-radius)<=half
        self.mask((cx-radius-half,cy-radius-half,cx+radius+half,cy+radius+half),inside,fill)
        for angle in (start,end):
            rad=math.radians(angle);xx=cx+radius*math.cos(rad);yy=cy+radius*math.sin(rad)
            self.ellipse((xx-half+.5,yy-half+.5,xx+half-.5,yy+half-.5),fill)


def category_icon(d,ident,x,y):
    ink=NativeInk(d,x,y)
    if ident==1:
        ink.roundrect((15,4,28,28),7)
        for yy in (11,16,21):ink.roundrect((18,yy,25,yy+1),1,fill=1)
        ink.arc(21.5,24,13,0,180,width=2.4)
        for xx in (8.5,34.5):ink.line([(xx,20),(xx,24)])
        ink.line([(21.5,37),(21.5,40)])
        ink.line([(15.5,40),(27.5,40)])
    elif ident==2:
        ink.roundrect((5,7,38,37),9,stroke=2.4)
        ink.line([(13.5,24),(22.5,15)],width=2.0)
        ink.line([(24.5,25),(29.5,20)],width=2.0)
        ink.roundrect((19,34,24,35),1)
    elif ident==3:
        # Preserve the approved home's broad face and rounded eye ratio.
        # Native highlights are compact ovals; thin diamond glints and tall
        # eyes made the previous 44px face appear pinched and distorted.
        for left in (4,29):
            ink.ellipse((left,14,left+10,27))
            ink.ellipse((left+2,16,left+5,20),fill=1)
            ink.ellipse((left+7,23,left+8,24),fill=1)
        ink.curve((5,10),[((7,8.5),(10,8.5),(13,9.5))],width=1.8)
        ink.curve((30,9.5),[((33,8.5),(36,8.5),(38,10))],width=1.8)
        ink.ellipse((20,26,23,27))
        ink.curve((17.5,31),[((18.5,33),(20,33),(21.5,30.5)),
                            ((23,33),(24.5,33),(25.5,31))],width=1.4)
        ink.ellipse((1,29,4,30));ink.ellipse((39,29,42,30))
    elif ident==4:
        # Two true round-ended capsules: negative openings share the same
        # axes, so the contours never turn into separately rounded polygons.
        axes=[];shift=5.5/math.sqrt(2)
        for cx,cy in ((14,29),(29,14)):
            points=[(cx-shift,cy+shift),(cx+shift,cy-shift)];axes.append(points)
            ink.line(points,width=13)
        for points in axes:ink.line(points,width=8.2,fill=1)
    elif ident==5:
        ink.roundrect((7,13,36,38),7,stroke=2.4)
        ink.roundrect((5,7,38,13),3,stroke=2.0)
        ink.line([(18,21),(25,21)],width=2.0)
    elif ident==6:
        ink.roundrect((18,4,25,7),2)
        ink.roundrect((10,9,33,39),7,stroke=2.4)
        d.polygon(((x+24,y+15),(x+17,y+25),(x+22,y+25),
                   (x+20,y+33),(x+27,y+22),(x+23,y+22)),fill=0)
    elif ident==7:
        for yy,cx in ((12.5,14.5),(30.5,28.5)):
            ink.line([(7,yy),(36,yy)],width=2.0)
            ink.ellipse((cx-5.5,yy-5.5,cx+5.5,yy+5.5))
            ink.ellipse((cx-3,yy-3,cx+3,yy+3),fill=1)
    elif ident==8:
        ink.ellipse((5,5,38,38),stroke=2.4)
        ink.ellipse((20,13,23,16))
        ink.line([(21.5,22),(21.5,30)],width=2.8)
    else:raise ValueError('Unknown Companion category: '+str(ident))


def chevron(d,x,y,left=False,fill=0):
    dx=-4 if left else 4
    NativeInk(d).line([(x,y-4),(x+dx,y),(x,y+4)],width=1.6,fill=fill)


def back_button(d):
    NativeInk(d).line([(22,25),(17,30),(22,35)],width=1.8)


def radio_control(d,cx,cy,selected):
    ink=NativeInk(d)
    ink.ellipse((cx-6,cy-6,cx+6,cy+6),stroke=1.8)
    if selected:ink.ellipse((cx-2.5,cy-2.5,cx+2.5,cy+2.5))


def switch_control(d,left,top,on):
    ink=NativeInk(d)
    box=(left,top,left+26,top+14)
    ink.roundrect(box,7,fill=0,stroke=None if on else 1.6)
    cx=left+(19 if on else 7)
    ink.ellipse((cx-3.5,top+3.5,cx+3.5,top+10.5),fill=1 if on else 0)

import math, numpy as np, cairo
W,H=1080,1920
surf=cairo.ImageSurface(cairo.FORMAT_ARGB32,W,H); c=cairo.Context(surf)
g=cairo.LinearGradient(0,0,0,H); g.add_color_stop_rgb(0,0.05,0.06,0.10); g.add_color_stop_rgb(1,0.025,0.03,0.05)
c.set_source(g); c.paint()
rg=cairo.RadialGradient(W/2,560,40,W/2,560,560); rg.add_color_stop_rgba(0,0.18,0.28,0.36,0.35); rg.add_color_stop_rgba(1,0,0,0,0)
c.set_source(rg); c.paint()
WHITE=(0.96,0.96,0.94); GOLD=(0.91,0.77,0.42); RED=(0.94,0.36,0.32)
c.select_font_face("DejaVu Sans Mono",cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_BOLD)

yaw,pitch=math.radians(18+180),math.radians(14)
def cam(p):
    x,y,z=p
    x1=x*math.cos(yaw)-z*math.sin(yaw); z1=x*math.sin(yaw)+z*math.cos(yaw)
    y2=y*math.cos(pitch)-z1*math.sin(pitch); z2=y*math.sin(pitch)+z1*math.cos(pitch)
    return np.array([x1,y2,z2])
OX,OY,S=W*0.5,860,3.3
def P(p): q=cam(p); return (OX+q[0]*S, OY-q[1]*S)
def path(pts):
    c.new_path(); c.move_to(*P(pts[0]))
    for p in pts[1:]: c.line_to(*P(p))
    c.close_path()
def vis(f):
    a,b,cc=[cam(p) for p in f[:3]]; return np.cross(b-a,cc-a)[2]<0
def stroke(w=2.4,col=WHITE,a=0.95):
    c.set_source_rgba(*col,a); c.set_line_width(w); c.set_line_join(cairo.LINE_JOIN_ROUND); c.stroke()
def metal(f):
    path(f); xs=[P(p) for p in f]; y0=min(q[1] for q in xs); y1=max(q[1] for q in xs)
    gr=cairo.LinearGradient(0,y0,0,y1)
    for t,v in ((0,0.78),(0.3,0.92),(0.55,0.58),(1,0.38)): gr.add_color_stop_rgb(t,v*0.95,v*0.97,v)
    c.set_source(gr); c.fill_preserve(); stroke(2.2)
def glassfill(f,streak=True):
    path(f); xs=[P(p) for p in f]; x0=min(q[0] for q in xs); x1=max(q[0] for q in xs); y0=min(q[1] for q in xs); y1=max(q[1] for q in xs)
    gr=cairo.LinearGradient(x0,y0,x1,y1); gr.add_color_stop_rgb(0,0.08,0.10,0.16); gr.add_color_stop_rgb(1,0.02,0.03,0.05)
    c.set_source(gr); c.fill_preserve()
    if streak:
        c.save(); c.clip_preserve(); st=cairo.LinearGradient(x0,y0,x1,y1)
        for t,a in ((0.25,0),(0.31,0.14),(0.37,0),(0.6,0),(0.63,0.07),(0.66,0)): st.add_color_stop_rgba(t,1,1,1,a)
        c.set_source(st); c.fill_preserve(); c.restore()
    stroke(1.4,WHITE,0.85)

# ---------- the iPhone Duo: a book-style foldable standing half open ----------
Wd,Ht,T=72.0,152.0,5.8      # each half: width, height, thickness (mm)
open_deg=128                 # angle between the two halves
a=math.radians((180-open_deg)/2)
def half(sign):
    # hinge along the y axis at x=0,z=0; the half runs out to +x (sign=1) or -x (sign=-1), swung back by a
    u=np.array([sign*math.cos(a),0,math.sin(a)])         # along the width
    n=np.array([-sign*math.sin(a)*0+ -math.sin(a)*sign*0,0,0])
    n=np.array([math.sin(a)*(-1 if sign>0 else 1)*-1,0,-math.cos(a)])  # thickness, toward the back
    o=np.array([0,0,0.0])
    q=lambda s,t,r: o+s*Wd*u+np.array([0,t*Ht,0])+r*T*(-n)*-1
    front=[q(0,0,0),q(1,0,0),q(1,1,0),q(0,1,0)]
    back=[q(0,0,1),q(0,1,1),q(1,1,1),q(1,0,1)]
    outer=[q(1,0,0),q(1,0,1),q(1,1,1),q(1,1,0)]
    topf=[q(0,1,0),q(1,1,0),q(1,1,1),q(0,1,1)]
    bottom=[q(0,0,0),q(0,0,1),q(1,0,1),q(1,0,0)]
    return dict(front=front,back=back,outer=outer,top=topf,bottom=bottom), q
faces=[]
for sign in (-1,1):
    f,q=half(sign)
    for name,pts in f.items():
        if sign<0: pts=pts[::-1]
        faces.append((name,pts,sign,q))
# shadow
c.save(); c.translate(OX,OY+30); c.scale(1,0.22); c.arc(0,0,330,0,2*math.pi); c.restore()
sh=cairo.RadialGradient(OX,OY+30,10,OX,OY+30,330); sh.add_color_stop_rgba(0,0,0,0,0.7); sh.add_color_stop_rgba(1,0,0,0,0)
c.set_source(sh); c.fill()
# hinge spine behind the fold
sp=[np.array((x,y,z)) for x,y,z in ((-6,0,7),(6,0,7),(6,Ht,7),(-6,Ht,7))]
faces.sort(key=lambda it: -np.mean([cam(p)[2] for p in it[1]]))
# draw spine first (it is at the back)
path(sp); c.set_source_rgb(0.30,0.32,0.36); c.fill_preserve(); stroke(2.0)
for name,pts,sign,q in faces:
    if not vis(pts): continue
    metal(pts)
    if name=='front':
        m=0.035
        inner=[q(m if sign>0 else m,0.03,0),q(1-m,0.03,0),q(1-m,0.97,0),q(m,0.97,0)]
        if sign<0: inner=inner[::-1]
        glassfill(inner)
# the crease: the one inner screen bends across the hinge
c.move_to(*P((0,Ht*0.03,0))); c.line_to(*P((0,Ht*0.97,0))); stroke(2.0,WHITE,0.55)
# the crack zone: just below where the flex cable crosses the hinge
cz=np.array((0,Ht*0.36,0)); x,y=P(cz)
c.set_source_rgba(*RED,0.95); c.set_line_width(2.2)
for ang,ln in ((0.3,26),(1.9,20),(3.6,24),(4.9,18),(2.7,14)):
    c.move_to(x,y); c.line_to(x+ln*math.cos(ang),y+ln*math.sin(ang)); c.stroke()
c.set_source_rgba(*RED,0.9); c.set_font_size(22); c.move_to(x+40,y+8); c.show_text("CRACK ZONE")
c.set_source_rgba(*WHITE,0.92); c.set_font_size(26); c.move_to(W*0.08,170); c.show_text("iPHONE DUO  ·  BOOK-STYLE FOLDABLE")
c.set_source_rgba(*GOLD,0.95); c.set_font_size(20); c.move_to(W*0.08,205); c.show_text("ONE INNER SCREEN FOLDS ACROSS THE HINGE")

# ---------- how the hinge holds the screen: cross-sections ----------
def section(cx,cy,closed,bar_dropped):
    sc=3.0
    def L(x,y): return (cx+x*sc, cy-y*sc)
    if not closed:
        # flat plates, centre support bar level with them, the screen lying flat on top
        for x0,x1 in ((-70,-9),(9,70)):
            c.rectangle(*L(x0,6),(x1-x0)*sc,6*sc); c.set_source_rgb(0.55,0.58,0.63); c.fill_preserve(); stroke(1.8)
        c.rectangle(*L(-8,6),16*sc,6*sc); c.set_source_rgb(0.80,0.66,0.38); c.fill_preserve(); stroke(1.8)
        for xr in (-12,12):   # curved guide rails sit level
            c.new_path(); c.arc(*L(xr,-4),9*sc,math.pi*1.05,math.pi*1.95) if False else None
        c.move_to(*L(-70,9)); c.line_to(*L(70,9)); stroke(4.0,(0.55,0.75,0.95),0.95)
        # flex cable crossing the hinge below
        c.move_to(*L(-40,-4)); c.curve_to(*L(-10,-4),*L(-10,-12),*L(0,-12)); c.curve_to(*L(10,-12),*L(10,-4),*L(40,-4)); stroke(2.4,GOLD,0.95)
    else:
        # closed: plates face each other, the screen bends in a teardrop around the gap
        ang=math.radians(4)
        for side in (-1,1):
            x=side*16
            c.rectangle(*L(x-3 if side>0 else x-3,70),6*sc,62*sc); c.set_source_rgb(0.55,0.58,0.63); c.fill_preserve(); stroke(1.8)
        # centre support bar: should drop into the gap
        by=-6 if bar_dropped else 8
        c.rectangle(*L(-7,by+4),14*sc,6*sc)
        c.set_source_rgb(0.80,0.66,0.38); c.fill_preserve(); stroke(1.8)
        # the screen: two straight runs and a round teardrop loop at the bottom
        c.new_path(); c.move_to(*L(-12,70)); c.line_to(*L(-12,18))
        c.curve_to(*L(-12,0),*L(-16,-8),*L(0,-8 if bar_dropped else 6))
        c.curve_to(*L(16,-8),*L(12,0),*L(12,18)); c.line_to(*L(12,70))
        stroke(4.0,(0.55,0.75,0.95),0.95)
        if not bar_dropped:
            x,y=L(0,6); c.set_source_rgba(*RED,0.35); c.arc(x,y,26,0,2*math.pi); c.fill()
            c.set_source_rgba(*RED,1); c.arc(x,y,7,0,2*math.pi); c.fill()
def label(x,y,text,col=WHITE,size=19,a=0.92):
    c.set_source_rgba(*col,a); c.set_font_size(size); c.move_to(x,y); c.show_text(text)

top=1240
label(W*0.08,top-40,"HOW THE HINGE HOLDS THE SCREEN",GOLD,24,0.95)
section(W*0.25,top+150,False,True)
label(W*0.08,top+250,"OPEN: SCREEN LIES FLAT",WHITE,19)
label(W*0.08,top+280,"centre bar supports it",WHITE,17,0.7)
section(W*0.58,top+230,True,True)
label(W*0.47,top+330,"CLOSED: BAR DROPS",WHITE,19)
label(W*0.47,top+360,"screen loops freely",WHITE,17,0.7)
section(W*0.85,top+230,True,False)
label(W*0.73,top+330,"IF THE BAR STAYS UP",RED,19)
label(W*0.73,top+360,"screen presses on it",WHITE,17,0.7)
# key
ky=top+470
for i,(col,txt) in enumerate((((0.55,0.75,0.95),"inner screen"),((0.80,0.66,0.38),"centre support bar"),((0.55,0.58,0.63),"hinge plates"),(GOLD,"flex cable"))):
    x=W*0.08+(i%2)*W*0.45; y=ky+(i//2)*40
    c.rectangle(x,y-14,26,14); c.set_source_rgb(*col); c.fill(); label(x+38,y,txt,WHITE,18,0.85)
label(W*0.08,ky+110,"Source: iFixit teardown (hypothesis, not confirmed)",WHITE,15,0.5)
surf.write_to_png('/tmp/claude-0/-home-claude/799125be-9bd5-56f2-8793-b19dc1429680/scratchpad/hinge/duo.png')

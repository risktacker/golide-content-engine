import math, numpy as np, cairo
W,H=1080,1920
surf=cairo.ImageSurface(cairo.FORMAT_ARGB32,W,H); c=cairo.Context(surf)
g=cairo.LinearGradient(0,0,0,H); g.add_color_stop_rgb(0,0.06,0.07,0.10); g.add_color_stop_rgb(1,0.02,0.025,0.04)
c.set_source(g); c.paint()
WHITE=(0.96,0.96,0.94); GOLD=(0.91,0.77,0.42); RED=(0.95,0.36,0.32)
yaw,pitch=math.radians(-32),math.radians(26)
def cam(p):
    x,y,z=p
    x1=x*math.cos(yaw)-z*math.sin(yaw); z1=x*math.sin(yaw)+z*math.cos(yaw)
    y2=y*math.cos(pitch)-z1*math.sin(pitch); z2=y*math.sin(pitch)+z1*math.cos(pitch)
    return np.array([x1,y2,z2])
OX,OY,S=W*0.40,0,7.0
ORG=[0]
def P(p): q=cam(p); return (OX+q[0]*S, ORG[0]-q[1]*S)
def path(pts):
    c.new_path(); c.move_to(*P(pts[0]))
    for p in pts[1:]: c.line_to(*P(p))
    c.close_path()
def stroke(w=1.6,col=WHITE,a=0.9):
    c.set_source_rgba(*col,a); c.set_line_width(w); c.set_line_join(cairo.LINE_JOIN_ROUND); c.stroke()
def box(x0,x1,y0,y1,z0,z1,col,top_alpha=1.0,line=1.4):
    """axis-aligned slab, draws its 3 visible faces (top, front z=z1? , side) cleanly"""
    v=lambda x,y,z: np.array((x,y,z),float)
    faces=[([v(x0,y1,z0),v(x1,y1,z0),v(x1,y1,z1),v(x0,y1,z1)],1.0),      # top
           ([v(x0,y0,z1),v(x1,y0,z1),v(x1,y1,z1),v(x0,y1,z1)],0.62),     # front
           ([v(x1,y0,z0),v(x1,y0,z1),v(x1,y1,z1),v(x1,y1,z0)],0.45),     # right
           ([v(x0,y0,z0),v(x0,y1,z0),v(x0,y1,z1),v(x0,y0,z1)],0.45)]     # left
    for f,k in faces:
        a,b,cc=[cam(p) for p in f[:3]]
        if np.cross(b-a,cc-a)[2]>0 and np.cross(cc-a,b-a)[2]>0: continue
        # visibility: face normal toward camera
        n=np.cross(cam(f[1])-cam(f[0]),cam(f[3])-cam(f[0]))
        if n[2]>0: continue
        path(f); c.set_source_rgba(col[0]*k,col[1]*k,col[2]*k,top_alpha if k==1.0 else 1.0); c.fill_preserve(); stroke(line)
QUEUE=[]
def label(pt,text,col=WHITE,size=19,dx=0):
    x,y=P(pt); QUEUE.append([x,y,text,col,size])
def flush(min_gap=34):
    QUEUE.sort(key=lambda q:q[1]); last=-1e9
    for q in QUEUE:
        q.append(max(q[1],last+min_gap)); last=q[5]
    for x,y,text,col,size,ly in QUEUE: _label(x,y,ly,text,col,size)
    QUEUE.clear()
def _label(x,y,ly,text,col,size):
    lx=W*0.72
    c.move_to(x+4,y); c.line_to(lx-40,ly); c.line_to(lx-10,ly); c.set_source_rgba(*WHITE,0.35); c.set_line_width(1.1); c.stroke()
    c.arc(x,y,3.2,0,2*math.pi); c.set_source_rgba(*col,0.95); c.fill()
    c.select_font_face("DejaVu Sans Mono",cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_BOLD)
    c.set_font_size(size); c.set_source_rgba(*col,0.95); c.move_to(lx,ly+6); c.show_text(text)

L=60.0     # length along the hinge axis (x)
Wd=46.0    # width across the fold (z), centred on 0
# ------------- display stack, exploded upward (top first in the list) -------------
layers=[("REPLACEABLE COVER LAYER",(0.62,0.78,0.86),0.55),
        ("ULTRA-THIN GLASS",(0.70,0.84,0.92),0.55),
        ("OPTICAL ADHESIVE",(0.80,0.80,0.74),0.45),
        ("POLARIZER",(0.36,0.42,0.70),0.9),
        ("TOUCH SENSOR",(0.30,0.60,0.56),0.9),
        ("OLED EMITTERS",(0.78,0.36,0.56),0.95),
        ("THIN-FILM BACKPLANE",(0.70,0.58,0.30),0.95),
        ("BACK FILM",(0.45,0.47,0.52),0.95),
        ("SUPPORT PLATE",(0.66,0.68,0.72),1.0)]
ORG[0]=1070
base=12.0; gap=12.5; th=1.1
for i,(name,col,al) in enumerate(layers):
    k=min(1.0,max(0.0,A*len(layers)-i))
    if k<=0: continue
    k=k*k*(3-2*k)
    y=base+(len(layers)-1-i)*gap+(1-k)*28
    box(-L/2,L/2,y,y+th,-Wd/2,Wd/2,col,al,1.3)
    corners=[np.array(p) for p in ((-L/2,y+th,-Wd/2),(L/2,y+th,-Wd/2),(L/2,y+th,Wd/2),(-L/2,y+th,Wd/2))]
    label(max(corners,key=lambda p:P(p)[0]),name,WHITE,18)
# bracket title for the stack
c.select_font_face("DejaVu Sans",cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_BOLD)
c.set_font_size(26); c.set_source_rgba(*GOLD,0.95); c.move_to(W*0.07,150); c.show_text("THE INNER SCREEN: 10+ THIN LAYERS")
c.set_font_size(20); c.set_source_rgba(*WHITE,0.7); c.move_to(W*0.07,182); c.show_text("each one must bend at the fold without cracking")

# ------------- hinge assembly, below -------------
flush()
if not SHOW_HINGE: raise SystemExit
c.select_font_face("DejaVu Sans",cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_BOLD)
c.set_font_size(26); c.set_source_rgba(*GOLD,0.95); c.move_to(W*0.07,1180); c.show_text("THE HINGE UNDERNEATH")
ORG[0]=1520
yb=10.0
# flat plates either side
box(-L/2,L/2,yb,yb+2.2,-Wd/2,-6.5,(0.62,0.64,0.68))
box(-L/2,L/2,yb,yb+2.2,6.5,Wd/2,(0.62,0.64,0.68))
label((L/2,yb+2.2,6.5+10),"FLAT HINGE PLATES",WHITE,18,0)
# central support bar (gold-ish) with the flex-cable opening cut in it
box(-L/2,-6,yb-0.4,yb+2.0,-5.5,5.5,(0.82,0.68,0.40))
box(6,L/2,yb-0.4,yb+2.0,-5.5,5.5,(0.82,0.68,0.40))
label((L/2,yb+2.0,0),"CENTRE SUPPORT BAR",GOLD,18)
# flex cable crossing the hinge through the opening
c.set_line_cap(cairo.LINE_CAP_ROUND)
fc=[np.array((0,yb-4.5,z)) for z in np.linspace(-Wd/2+2,Wd/2-2,30)]
fc=[p+np.array((0,-2.5*math.cos(p[2]/Wd*math.pi)**8,0)) for p in fc]
for wdt,col,al in ((9,(0.55,0.40,0.12),1),(6,GOLD,1)):
    c.new_path(); c.move_to(*P(fc[0]))
    for p in fc[1:]: c.line_to(*P(p))
    c.set_source_rgba(*col,al); c.set_line_width(wdt); c.stroke()
label((0,yb-4.5,Wd/2-6),"FLEX CABLE",GOLD,18,0)
# curved guide rails under the plates
for x in (-L/2+5,L/2-5):
    pts=[np.array((x,yb-0.2-5.5*math.sin(t),-6.5-9*math.cos(t)*0+(-6+12*t/math.pi)*0+ -13*math.cos(t))) for t in np.linspace(0.15,math.pi-0.15,40)]
    c.new_path(); c.move_to(*P(pts[0]))
    for p in pts[1:]: c.line_to(*P(p))
    c.set_source_rgba(0.82,0.84,0.88,0.95); c.set_line_width(3.0); c.stroke()
label((L/2-5,yb-5.7,0),"CURVED GUIDE RAILS",WHITE,18)
# gear trains at both ends, with springs
def gear(x,z,r,teeth=14):
    pts=[]
    for k in range(teeth*2):
        t=2*math.pi*k/(teeth*2); rr=r if k%2==0 else r*0.82
        pts.append(np.array((x,yb-8+rr*math.sin(t),z+rr*math.cos(t))))
    path(pts); c.set_source_rgb(0.42,0.44,0.48); c.fill_preserve(); stroke(1.4)
    hub=[np.array((x,yb-8+r*0.3*math.sin(t),z+r*0.3*math.cos(t))) for t in np.linspace(0,2*math.pi,20)]
    path(hub); c.set_source_rgb(0.12,0.12,0.14); c.fill_preserve(); stroke(1.1)
for x in (-L/2-20,L/2+20):
    gear(x,-4.4,4.2); gear(x,4.4,4.2)
label((L/2+20,yb-8,4.4),"SYNCHRONISING GEARS",WHITE,18)
for x0,dirn in ((-L/2-4,-1),(L/2+4,1)):
    pts=[np.array((x0+dirn*8*t/(2*math.pi*5),yb-8+2.2*math.sin(t),0+2.2*math.cos(t))) for t in np.linspace(0,2*math.pi*5,200)]
    c.new_path(); c.move_to(*P(pts[0]))
    for p in pts[1:]: c.line_to(*P(p))
    c.set_source_rgba(0.85,0.86,0.90,0.95); c.set_line_width(1.8); c.stroke()
label((L/2+12,yb-8,0),"TENSION SPRINGS",WHITE,18)
# crack zone: where the flex-cable opening meets the centre support
cx,cy=P((-6,yb+2.0,0))
rg=cairo.RadialGradient(cx,cy,2,cx,cy,34); rg.add_color_stop_rgba(0,*RED,0.85); rg.add_color_stop_rgba(1,*RED,0)
c.set_source(rg); c.arc(cx,cy,34,0,2*math.pi); c.fill()
c.set_source_rgba(*RED,1); c.arc(cx,cy,6,0,2*math.pi); c.fill()
flush(30)
c.select_font_face("DejaVu Sans Mono",cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_BOLD)
c.set_font_size(19); c.set_source_rgba(*RED,1); c.move_to(W*0.07,1780); c.show_text("CRACK ZONE: where the cable opening")
c.move_to(W*0.07,1806); c.show_text("meets the centre support")
c.set_font_size(15); c.set_source_rgba(*WHITE,0.5); c.move_to(W*0.07,H-60); c.show_text("Based on the iFixit iPhone Duo teardown. Layer names typical of foldable OLEDs.")
OUT and surf.write_to_png('/tmp/claude-0/-home-claude/799125be-9bd5-56f2-8793-b19dc1429680/scratchpad/hinge/arch.png')

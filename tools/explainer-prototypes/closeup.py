import math, numpy as np, cairo
W,H=1080,1920
surf=cairo.ImageSurface(cairo.FORMAT_ARGB32,W,H); c=cairo.Context(surf)
g=cairo.LinearGradient(0,0,0,H); g.add_color_stop_rgb(0,0.06,0.07,0.10); g.add_color_stop_rgb(1,0.02,0.025,0.04)
c.set_source(g); c.paint()
rg=cairo.RadialGradient(W/2,1020,30,W/2,1020,560); rg.add_color_stop_rgba(0,0.20,0.28,0.38,0.35); rg.add_color_stop_rgba(1,0,0,0,0)
c.set_source(rg); c.paint()
WHITE=(0.96,0.96,0.94); GOLD=(0.91,0.77,0.42); RED=(0.95,0.36,0.32)
def stroke(w=2.0,col=WHITE,a=0.95):
    c.set_source_rgba(*col,a); c.set_line_width(w); c.set_line_join(cairo.LINE_JOIN_ROUND); c.set_line_cap(cairo.LINE_CAP_ROUND); c.stroke()
def metal_fill(x0,y0,x1,y1,dark=False):
    gr=cairo.LinearGradient(x0,y0,x1,y1)
    k=0.7 if dark else 1.0
    for t,v in ((0,0.82),(0.35,0.95),(0.6,0.62),(1,0.42)): gr.add_color_stop_rgb(t,v*0.93*k,v*0.95*k,v*k)
    c.set_source(gr); c.fill_preserve()

CX,CY=W/2,1000          # hinge centre (end view, looking along the hinge axis)
ang=math.radians(28)    # each half leans this far from vertical: the phone is closing
Lh,T=640,46             # half length and thickness in px

def half(side):
    """one phone half as a rotated slab; the screen is on its inner face."""
    c.save(); c.translate(CX+side*70,CY-40); c.rotate(side*ang)
    # body
    x0=-T/2 if side>0 else -T/2
    c.rectangle(-T/2+side*0,-Lh,T,Lh); metal_fill(-T/2,-Lh,T/2,0)
    stroke(2.2)
    # end-face details: battery block and board inside (simple, ordered)
    c.rectangle(-T/2+9,-Lh+60,T-18,Lh*0.45); c.set_source_rgb(0.20,0.21,0.24); c.fill_preserve(); stroke(1.2,WHITE,0.5)
    c.restore()

def inner_point(side,dist):
    """a point on the inner face of a half, dist px from the hinge end"""
    a=side*ang
    ox,oy=CX+side*70,CY-40
    # inner face is at x = -side*T/2 in local coords
    lx,ly=-side*T/2,-dist
    return (ox+lx*math.cos(a)-ly*math.sin(a), oy+lx*math.sin(a)+ly*math.cos(a))

# ---- guide rails (behind): the curved tracks each half rides on ----
for r in (150,178):
    for a0,a1 in ((200,250),(290,340)):
        c.new_path(); c.arc(CX,CY+40,r,math.radians(a0),math.radians(a1)); stroke(7,(0.40,0.42,0.47),1)
        c.new_path(); c.arc(CX,CY+40,r,math.radians(a0),math.radians(a1)); stroke(1.4,WHITE,0.6)
half(-1); half(1)

# ---- synchronising gears: one fixed to each half, meshed at the centre ----
def gear(x,y,r,teeth,rot):
    c.new_path()
    for k in range(teeth*2+1):
        t=rot+2*math.pi*k/(teeth*2); rr=r if k%2==0 else r*0.84
        (c.move_to if k==0 else c.line_to)(x+rr*math.cos(t),y+rr*math.sin(t))
    c.close_path(); gr=cairo.RadialGradient(x-r*0.3,y-r*0.3,2,x,y,r); gr.add_color_stop_rgb(0,0.85,0.86,0.9); gr.add_color_stop_rgb(1,0.38,0.40,0.45)
    c.set_source(gr); c.fill_preserve(); stroke(1.6)
    c.arc(x,y,r*0.28,0,2*math.pi); c.set_source_rgb(0.1,0.1,0.12); c.fill_preserve(); stroke(1.2)
gear(CX-56,CY+215,58,12,0.0); gear(CX+56,CY+215,58,12,math.pi/12)

# ---- tension springs: hold each half at its angle ----
def spring(x0,y0,x1,y1,turns=9,amp=14):
    n=200; dx,dy=x1-x0,y1-y0; L=math.hypot(dx,dy); ux,uy=dx/L,dy/L; px,py=-uy,ux
    c.new_path()
    for i in range(n+1):
        t=i/n; s=amp*math.sin(t*turns*2*math.pi)
        x=x0+dx*t+px*s; y=y0+dy*t+py*s
        (c.move_to if i==0 else c.line_to)(x,y)
    stroke(2.4,(0.86,0.87,0.91),1)
spring(CX-330,CY+215,CX-130,CY+215); spring(CX+130,CY+215,CX+330,CY+215)

# ---- centre support bar: dropped down below the screen loop (working case) ----
bx,by,bw,bh=CX-50,CY+140,100,24
c.rectangle(bx,by,bw,bh); gr=cairo.LinearGradient(bx,by,bx,by+bh); gr.add_color_stop_rgb(0,0.93,0.78,0.46); gr.add_color_stop_rgb(1,0.62,0.48,0.22)
c.set_source(gr); c.fill_preserve(); stroke(1.8)

# ---- the screen: a stack of thin layers bending in a teardrop loop between the halves ----
layers=[((0.62,0.80,0.90),"cover layer"),((0.72,0.86,0.94),"ultra-thin glass"),((0.40,0.46,0.74),"polarizer"),
        ((0.32,0.62,0.58),"touch sensor"),((0.82,0.38,0.58),"OLED emitters"),((0.74,0.60,0.30),"backplane"),((0.66,0.68,0.72),"support plate")]
def screen_path(off):
    # straight run down each inner face, then a teardrop loop under the hinge
    top=Lh-30
    pL0=inner_point(-1,top); pL1=inner_point(-1,90)
    pR0=inner_point(1,top);  pR1=inner_point(1,90)
    # offset each layer outward from the face (into the gap)
    def shift(p,side,d): a=side*ang; return (p[0]+side*-1*d*math.cos(a)*-1*-1, p[1]+d*math.sin(a)*side*-1*-1) if False else (p[0]-side*-d*math.cos(a)*-1, p[1]-side*d*math.sin(a)*-1*-1)
    d=off
    l0=(pL0[0]+d*math.cos(ang), pL0[1]-d*math.sin(ang)); l1=(pL1[0]+d*math.cos(ang), pL1[1]-d*math.sin(ang))
    r0=(pR0[0]-d*math.cos(ang), pR0[1]-d*math.sin(ang)); r1=(pR1[0]-d*math.cos(ang), pR1[1]-d*math.sin(ang))
    c.new_path(); c.move_to(*l0); c.line_to(*l1)
    rb=118-d*1.0          # bulb radius shrinks for inner layers
    cy=CY+2
    c.curve_to(l1[0]+6,l1[1]+40, CX-rb-8,cy-40, CX-rb,cy)
    c.arc_negative(CX,cy,rb,math.pi,0) if False else c.arc_negative(CX,cy,rb,math.pi,0.0)
    c.curve_to(CX+rb+8,cy-40, r1[0]-6,r1[1]+40, r1[0],r1[1])
    c.line_to(*r0)
for i,(col,name) in enumerate(layers):
    screen_path(4+i*5.2); stroke(4.4,col,1)

# ---- flex cable: crosses from one half to the other under the hinge ----
for wdt,col in ((10,(0.55,0.40,0.12)),(6,GOLD)):
    c.new_path(); c.move_to(CX-330,CY+330); c.curve_to(CX-160,CY+330,CX-120,CY+380,CX,CY+380)
    c.curve_to(CX+120,CY+380,CX+160,CY+330,CX+330,CY+330); stroke(wdt,col,1)
# ---- crack zone ----
zx,zy=CX+82,CY+82
rg=cairo.RadialGradient(zx,zy,2,zx,zy,40); rg.add_color_stop_rgba(0,*RED,0.85); rg.add_color_stop_rgba(1,*RED,0)
c.set_source(rg); c.arc(zx,zy,40,0,2*math.pi); c.fill()
c.arc(zx,zy,6,0,2*math.pi); c.set_source_rgb(*RED); c.fill()

# ---- labels: leader lines to the right / left, no crossings ----
c.select_font_face("DejaVu Sans Mono",cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_BOLD)
def tag(px,py,lx,ly,text,col=WHITE,size=20,right=True):
    c.move_to(px,py); c.line_to(lx,ly); c.line_to(lx+(30 if right else -30),ly); stroke(1.1,WHITE,0.4)
    c.arc(px,py,3.5,0,2*math.pi); c.set_source_rgba(*col,1); c.fill()
    c.set_font_size(size); c.set_source_rgba(*col,0.95)
    te=c.text_extents(text); tx=lx+38 if right else lx-38-te.width
    c.move_to(tx,ly+7); c.show_text(text)
p=inner_point(1,330); tag(p[0]-22,p[1],W*0.72,700,"SCREEN: 10+ LAYERS",GOLD)
p=inner_point(-1,520); tag(p[0]-28,p[1],W*0.27,820,"PHONE HALF",WHITE,20,False)
tag(CX+112,CY+10,W*0.72,860,"SCREEN LOOP",WHITE)
tag(bx+bw,by+bh/2,W*0.72,1100,"CENTRE BAR (dropped)",GOLD)
tag(CX+178*math.cos(math.radians(330)),CY+40+178*math.sin(math.radians(330)),W*0.72,960,"CURVED GUIDE RAILS",WHITE)
tag(CX-56,CY+215,W*0.30,1380,"SYNCHRONISING GEARS",WHITE,20,False)
tag(CX+300,CY+215,W*0.72,1250,"TENSION SPRINGS",WHITE)
tag(CX+250,CY+333,W*0.72,1460,"FLEX CABLE",GOLD)
tag(zx,zy,W*0.72,1180,"CRACK ZONE",RED)

c.select_font_face("DejaVu Sans",cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_BOLD)
c.set_font_size(30); c.set_source_rgba(*GOLD,0.95); c.move_to(W*0.07,170); c.show_text("THE HINGE, CLOSE UP")
c.set_font_size(20); c.set_source_rgba(*WHITE,0.7); c.move_to(W*0.07,206); c.show_text("end view, phone closing: the screen bends in a loop,")
c.move_to(W*0.07,234); c.show_text("the centre bar drops below it")
# legend for the layer colours
c.select_font_face("DejaVu Sans Mono",cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_BOLD)
y0=1600
for i,(col,name) in enumerate(layers):
    x=W*0.08+(i%2)*W*0.44; y=y0+(i//2)*40
    c.rectangle(x,y-12,34,8); c.set_source_rgb(*col); c.fill()
    c.set_font_size(18); c.set_source_rgba(*WHITE,0.85); c.move_to(x+46,y); c.show_text(name)
c.set_font_size(15); c.set_source_rgba(*WHITE,0.5); c.move_to(W*0.07,H-60); c.show_text("Based on the iFixit iPhone Duo teardown. Shapes simplified, not measured.")
surf.write_to_png('/tmp/claude-0/-home-claude/799125be-9bd5-56f2-8793-b19dc1429680/scratchpad/hinge/closeup.png')

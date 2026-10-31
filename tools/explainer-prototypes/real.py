import math, numpy as np, cairo
W,H=1080,1920
surf=cairo.ImageSurface(cairo.FORMAT_ARGB32,W,H); c=cairo.Context(surf)
g=cairo.LinearGradient(0,0,0,H); g.add_color_stop_rgb(0,0.07,0.08,0.11); g.add_color_stop_rgb(0.6,0.04,0.045,0.07); g.add_color_stop_rgb(1,0.02,0.02,0.03)
c.set_source(g); c.paint()
rg=cairo.RadialGradient(W/2,900,40,W/2,900,700); rg.add_color_stop_rgba(0,0.22,0.30,0.42,0.40); rg.add_color_stop_rgba(1,0,0,0,0)
c.set_source(rg); c.paint()

yaw,pitch=math.radians(180+22),math.radians(10)
def cam(p):
    x,y,z=p
    x1=x*math.cos(yaw)-z*math.sin(yaw); z1=x*math.sin(yaw)+z*math.cos(yaw)
    y2=y*math.cos(pitch)-z1*math.sin(pitch); z2=y*math.sin(pitch)+z1*math.cos(pitch)
    return np.array([x1,y2,z2])
OX,OY,S=W*0.5,1300,5.4
def P(p): q=cam(p); return (OX+q[0]*S, OY-q[1]*S)

Wd,Ht,T,R=72.0,156.0,5.4,11.0          # one half: width, height, thickness, corner radius (mm)
open_deg=140
a=math.radians((180-open_deg)/2)

def rrect(w,h,r,inset=0.0,n=10):
    """rounded rectangle contour in (s,t), counter-clockwise"""
    w2,h2=w-2*inset,h-2*inset; r=max(0.5,r-inset); pts=[]
    for cx,cy,a0 in ((w2-r,r,-90),(w2-r,h2-r,0),(r,h2-r,90),(r,r,180)):
        for k in range(n+1):
            t=math.radians(a0+90*k/n); pts.append((inset+cx+r*math.cos(t), inset+cy+r*math.sin(t)))
    return pts

def mapper(sign):
    u=np.array([sign*math.cos(a),0,-math.sin(a)])                 # along the width, toward the viewer side
    nb=np.array([sign*math.sin(a),0,math.cos(a)]) * -1              # into the body (away from the screen)
    nb=np.array([-sign*math.sin(a)*-1,0,math.cos(a)])
    def m(s,t,d=0.0):
        # s from the hinge outward
        return u*s+np.array([0,t,0])+nb*d
    return m

def poly2d(pts):
    c.new_path(); c.move_to(*pts[0])
    for p in pts[1:]: c.line_to(*p)
    c.close_path()

halves=[]
for sign in (-1,1):
    m=mapper(sign)
    depth=np.mean([cam(m(Wd/2,Ht/2))[2]])
    halves.append((depth,sign,m))
halves.sort(key=lambda h:-h[0])

# floor shadow and reflection glow
c.save(); c.translate(OX,OY+18); c.scale(1,0.16); c.arc(0,0,360,0,2*math.pi); c.restore()
sh=cairo.RadialGradient(OX,OY+18,10,OX,OY+18,360); sh.add_color_stop_rgba(0,0,0,0,0.85); sh.add_color_stop_rgba(1,0,0,0,0)
c.set_source(sh); c.fill()

def draw_half(sign,m):
    # contour: the half is a rounded rect, but the hinge side is square (it meets the other half)
    cont=rrect(Wd,Ht,R)
    cont=[(s if s>Wd*0.5 else max(0.0,s) if s>R else s, t) for s,t in cont]
    # flatten the hinge-side corners: points with s<R get s=0 for a square hinge edge
    cont=[((0.0 if s<R*0.999 else s),t) for s,t in cont]
    back=[P(m(s,t,T)) for s,t in cont]; front=[P(m(s,t,0)) for s,t in cont]
    # 1. the frame band: silhouette of back + front filled in polished titanium
    hull=back+front
    xs=[p[0] for p in hull]; ys=[p[1] for p in hull]
    for i in range(len(cont)):
        j=(i+1)%len(cont)
        q=[back[i],back[j],front[j],front[i]]
        poly2d(q)
        # light by the facing of this strip
        s0,t0=cont[i]; s1,t1=cont[j]
        nx,ny=t1-t0,-(s1-s0); ln=math.hypot(nx,ny) or 1
        shade=0.45+0.40*max(0,(ny/ln)*-0.6+(nx/ln)*0.5*sign)
        c.set_source_rgb(0.52*shade+0.18,0.54*shade+0.18,0.58*shade+0.2); c.fill()
    # 2. the front face (thin titanium lip around the screen)
    poly2d(front)
    gr=cairo.LinearGradient(min(xs),min(ys),max(xs),max(ys))
    gr.add_color_stop_rgb(0,0.80,0.81,0.84); gr.add_color_stop_rgb(0.5,0.55,0.56,0.60); gr.add_color_stop_rgb(1,0.70,0.71,0.75)
    c.set_source(gr); c.fill()
    # 3. the inner screen: nearly edge to edge, a thin black border, then the lit display
    border=[P(m(s,t,-0.05)) for s,t in [((0.0 if s<R*0.999 else s),t) for s,t in rrect(Wd,Ht,R,inset=1.2)]]
    poly2d(border); c.set_source_rgb(0.01,0.01,0.012); c.fill()
    disp_c=[((0.0 if s<R*0.999 else s),t) for s,t in rrect(Wd,Ht,R,inset=3.0)]
    disp=[P(m(s,t,-0.08)) for s,t in disp_c]
    poly2d(disp)
    # wallpaper: one image across both halves (so the screen reads as ONE folding display)
    gx0,gy0=P(m(Wd,Ht,0)) ; gx1,gy1=P(m(Wd,0,0))
    wp=cairo.LinearGradient(OX,OY-Ht*S*1.05,OX,OY)
    wp.add_color_stop_rgb(0,0.10,0.12,0.38); wp.add_color_stop_rgb(0.45,0.36,0.20,0.62); wp.add_color_stop_rgb(0.8,0.85,0.40,0.45); wp.add_color_stop_rgb(1,0.96,0.62,0.38)
    c.set_source(wp); c.fill_preserve()
    c.save(); c.clip()
    glow=cairo.RadialGradient(OX+60,OY-Ht*S*0.55,10,OX+60,OY-Ht*S*0.55,420)
    glow.add_color_stop_rgba(0,1,0.85,0.75,0.45); glow.add_color_stop_rgba(1,1,1,1,0)
    c.set_source(glow); c.paint()
    # screen reflection: soft diagonal sheen, stronger on the half that faces the light
    sx0=min(p[0] for p in disp); sx1=max(p[0] for p in disp)
    sheen=cairo.LinearGradient(sx0,OY-Ht*S,sx1,OY)
    k=0.16 if sign>0 else 0.08
    for t,al in ((0.0,0),(0.28,k),(0.42,0),(1,0)): sheen.add_color_stop_rgba(t,1,1,1,al)
    c.set_source(sheen); c.paint()
    # the half turned away from the light is a touch darker
    if sign<0:
        c.set_source_rgba(0,0,0,0.18); c.paint()
    c.restore()
    return disp

discs=[]
for depth,sign,m in halves:
    discs.append(draw_half(sign,m))

# the crease: one soft line of light along the fold
top=P((0,Ht-3.0,0)); bot=P((0,3.0,0))
cr=cairo.LinearGradient(top[0]-6,0,top[0]+6,0)
cr.add_color_stop_rgba(0,1,1,1,0); cr.add_color_stop_rgba(0.5,1,1,1,0.28); cr.add_color_stop_rgba(1,1,1,1,0)
c.set_source(cr); c.set_line_width(10); c.move_to(*top); c.line_to(*bot); c.stroke()
# hinge caps at top and bottom of the fold (polished)
for y in (Ht,0):
    x,yy=P((0,y,T*0.6)); c.save(); c.translate(x,yy); c.scale(1,0.5); c.arc(0,0,13,0,2*math.pi); c.restore()
    hc=cairo.RadialGradient(x-4,yy-3,1,x,yy,14); hc.add_color_stop_rgb(0,0.95,0.95,0.97); hc.add_color_stop_rgb(1,0.45,0.46,0.50)
    c.set_source(hc); c.fill()
# status bar and clock on the right half (like a lock screen), set in the screen's plane
m=dict((s,mm) for d,s,mm in halves)[1]
def text_on(m,s,t,txt,size,alpha=0.95,bold=True):
    x,y=P(m(s,t,-0.1)); c.save(); c.translate(x,y)
    u=np.array(P(m(s+10,t,-0.1)))-np.array((x,y))
    if u[0]<0: u=-u
    ang=math.atan2(u[1],u[0]); c.rotate(ang)
    c.scale(1,1); c.select_font_face("DejaVu Sans",cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    c.set_font_size(size); c.set_source_rgba(1,1,1,alpha); c.move_to(0,0); c.show_text(txt); c.restore()
text_on(m,Wd-9,Ht-28,"9:41",58)
text_on(m,Wd-9,Ht-38,"Saturday 31 October",17,0.85,False)
# side buttons on the right half's outer edge
mr=m
for t0,t1 in ((Ht*0.62,Ht*0.70),(Ht*0.50,Ht*0.58)):
    a0=P(mr(Wd+0.6,t0,T*0.5)); a1=P(mr(Wd+0.6,t1,T*0.5))
    c.set_line_cap(cairo.LINE_CAP_ROUND); c.set_source_rgb(0.75,0.76,0.80); c.set_line_width(5); c.move_to(*a0); c.line_to(*a1); c.stroke()

c.select_font_face("DejaVu Sans",cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_BOLD)
c.set_source_rgba(0.96,0.96,0.94,0.95); c.set_font_size(40); c.move_to(W*0.08,200); c.show_text("iPhone Duo")
c.set_source_rgba(0.91,0.77,0.42,0.95); c.set_font_size(22); c.move_to(W*0.08,240); c.show_text("one screen, folding like a book")
surf.write_to_png('/tmp/claude-0/-home-claude/799125be-9bd5-56f2-8793-b19dc1429680/scratchpad/hinge/real.png')

"""Reference sketches of how money and business objects are built (owner direction 2026-10-28).

"Since we know the structures that we need... paste that structure to the API so that it
can generate something like that." The image model draws better from a picture than from
words. These sketches (drawn in code, no cost) show the parts that make each object read: a
coin's reeded edge and rim, a note's border and portrait window, a bank's columns and steps.
When a scene's drawing names one of these objects, its sketch is handed to the line-art
model as a structure reference (shape only; the model keeps our style).
"""

from __future__ import annotations

import math
import random
import re
from pathlib import Path

import cairo

TW, TH = 640, 400
TEAL = (0.43, 0.86, 0.78); GOLD = (0.91, 0.77, 0.42); LINE = (0.93, 0.94, 0.96)
ROSE = (0.94, 0.54, 0.50); BLUE = (0.45, 0.65, 0.98)


def floor(c, y=330, col=TEAL):
    pass


def st(c,col=LINE,w=2.2,a=1): c.set_source_rgba(*col,a); c.set_line_width(w); c.stroke()
def fl(c,col,a): c.set_source_rgba(*col,a); c.fill()
def txt(c, x, y, t, size, col, bold=True, a=1):
    """No text in a structure sketch: the picture model must not copy words or numbers."""


def floor(c,y=330,col=TEAL):
    for i in range(-14,15): c.move_to(320+i*10,y); c.line_to(320+i*70,TH)
    for j in range(1,7): yy=y+(TH-y)*(j/7)**2; c.move_to(0,yy); c.line_to(TW,yy)
    c.set_source_rgba(*col,0.35); c.set_line_width(1); c.stroke()

def coin(c,x=320,y=205,r=95):
    c.save(); c.translate(x,y); c.scale(1,0.92)
    c.arc(0,10,r,0,math.pi); st(c,GOLD,2)                                # thickness
    c.arc(0,0,r,0,2*math.pi); fl(c,GOLD,0.10); c.arc(0,0,r,0,2*math.pi); st(c,GOLD,3)
    for i in range(72):                                                  # reeded edge
        a=i/72*2*math.pi; c.move_to(r*math.cos(a),r*math.sin(a)); c.line_to((r-8)*math.cos(a),(r-8)*math.sin(a))
    st(c,GOLD,1.2,0.8)
    c.arc(0,0,r-18,0,2*math.pi); st(c,GOLD,1.5,0.7)
    c.restore(); txt(c,x,y+22,'5',72,GOLD)
    for k in range(3): c.save(); c.translate(150-k*6,330-k*16); c.scale(1,0.3); c.arc(0,0,50,0,2*math.pi); c.restore(); st(c,GOLD,2,0.8)
def note(c):
    def one(x,y,ang,a):
        c.save(); c.translate(x,y); c.rotate(ang)
        c.rectangle(-170,-80,340,160); fl(c,TEAL,0.08*a); c.rectangle(-170,-80,340,160); st(c,LINE,2.2,a)
        c.rectangle(-158,-68,316,136); st(c,TEAL,1.2,0.6*a)
        c.save(); c.translate(-70,0); c.scale(0.8,1); c.arc(0,0,48,0,2*math.pi); c.restore(); st(c,TEAL,1.5,0.8*a)
        c.arc(-70,-8,16,0,2*math.pi); st(c,LINE,1.2,0.6*a)
        c.move_to(-96,30); c.curve_to(-90,10,-50,10,-44,30); st(c,LINE,1.2,0.6*a)
        c.restore()
    one(300,215,-0.08,0.5); one(330,195,0.04,1.0); txt(c,440,170,'100',30,GOLD); txt(c,178,296,'100',16,GOLD,a=0.8)
    c.move_to(330+120,195+60); c.line_to(330+150,195+60); st(c,TEAL,1)
def bank(c):
    c.move_to(170,150); c.line_to(320,80); c.line_to(470,150); c.close_path(); fl(c,TEAL,0.08)
    c.move_to(170,150); c.line_to(320,80); c.line_to(470,150); c.close_path(); st(c)
    c.rectangle(175,150,290,16); st(c)
    n=6; left,right,cw=190,450,22; gap=(right-left-cw)/(n-1)
    for i in range(n):
        x=left+i*gap
        c.rectangle(x,170,cw,140); st(c,LINE,1.8)
        c.move_to(x+7,172); c.line_to(x+7,308); c.move_to(x+15,172); c.line_to(x+15,308); st(c,LINE,0.8,0.5)
    c.rectangle(160,310,320,12); st(c); c.rectangle(150,322,340,10); st(c)
    txt(c,320,138,'BANK',18,GOLD); c.arc(320,110,10,0,2*math.pi); fl(c,GOLD,0.9)
def shelf(c):
    for y in (120,200,280): c.move_to(140,y); c.line_to(500,y); c.line_to(530,y-15); st(c)
    c.move_to(140,60); c.line_to(140,345); c.move_to(500,60); c.line_to(500,345); c.move_to(530,45); c.line_to(530,330); st(c)
    rnd=random.Random(2)
    for y in (120,200,280):
        x=152
        while x<480:
            w=rnd.choice([22,26,32]); h=rnd.choice([40,52,62])
            if rnd.random()<0.5: c.rectangle(x,y-h,w,h)
            else: c.move_to(x,y); c.line_to(x,y-h*0.7); c.line_to(x+w*0.3,y-h); c.line_to(x+w*0.7,y-h); c.line_to(x+w,y-h*0.7); c.line_to(x+w,y)
            st(c,LINE,1.4); x+=w+6
    c.rectangle(250,288,70,26); fl(c,GOLD,0.25); c.rectangle(250,288,70,26); st(c,GOLD,1.5); txt(c,285,307,'$4.99',14,GOLD)
def card(c):
    c.save(); c.translate(320,200); c.rotate(-0.12)
    c.new_sub_path(); r=14; x,y,w,h=-170,-105,340,210
    c.arc(x+w-r,y+r,r,-math.pi/2,0); c.arc(x+w-r,y+h-r,r,0,math.pi/2); c.arc(x+r,y+h-r,r,math.pi/2,math.pi); c.arc(x+r,y+r,r,math.pi,1.5*math.pi); c.close_path()
    fl(c,BLUE,0.10); c.arc(x+w-r,y+r,r,-math.pi/2,0); c.arc(x+w-r,y+h-r,r,0,math.pi/2); c.arc(x+r,y+h-r,r,math.pi/2,math.pi); c.arc(x+r,y+r,r,math.pi,1.5*math.pi); c.close_path(); st(c)
    c.rectangle(-140,-50,52,40); fl(c,GOLD,0.25); c.rectangle(-140,-50,52,40); st(c,GOLD,1.8)
    for k in (-35,-30): c.move_to(-140,k); c.line_to(-88,k)
    c.move_to(-114,-50); c.line_to(-114,-10); st(c,GOLD,1)
    for k in range(3): c.arc(-60+k*8,-30,4+k*4,-0.8,0.8); st(c,LINE,1.4,0.7)
    txt(c,0,50,'••••  ••••  ••••  4821',20,LINE,False,0.9)
    c.restore()
def market(c):
    c.move_to(80,330); c.line_to(560,330); c.move_to(80,330); c.line_to(80,70); st(c,LINE,1.2,0.5)
    rnd=random.Random(4); y=300; x=100; closes=[]
    for i in range(16):
        o=y; y=max(90,min(310,y+rnd.uniform(-34,16))); hi=min(o,y)-rnd.uniform(5,20); lo=max(o,y)+rnd.uniform(5,20)
        col=TEAL if y<o else ROSE
        c.move_to(x+9,hi); c.line_to(x+9,lo); st(c,col,1.2)
        c.rectangle(x,min(o,y),18,max(3,abs(o-y))); fl(c,col,0.55); closes.append((x+9,y)); x+=28
    avg=[(closes[i][0],sum(p[1] for p in closes[max(0,i-2):i+1])/len(closes[max(0,i-2):i+1])) for i in range(len(closes))]
    c.move_to(*avg[0]); [c.line_to(*p) for p in avg[1:]]; st(c,GOLD,2)
    c.rectangle(80,345,480,30); st(c,TEAL,1,0.6); txt(c,320,366,'NVDA +3.2%     TSLA -1.1%     AAPL +0.6%',14,TEAL,False)
def cart(c):
    c.move_to(150,110); c.line_to(200,110); c.line_to(245,270); c.line_to(450,270); c.line_to(480,150); c.line_to(215,150); st(c)
    for i in range(1,7):
        f=i/7; c.move_to(215+(480-215)*f,150); c.line_to(245+(450-245)*f,270)
    for y in (190,230):
        k=(y-150)/120; c.move_to(215+(245-215)*k,y); c.line_to(480+(450-480)*k,y)
    st(c,LINE,1,0.6)
    for x in (275,420): c.new_path(); c.arc(x,303,18,0,2*math.pi); st(c,GOLD,2.5)
    c.move_to(245,270); c.line_to(255,285); c.line_to(440,285); c.line_to(450,270); st(c,LINE,1.6)
def deal(c):
    c.rectangle(170,70,230,290); fl(c,LINE,0.05); c.rectangle(170,70,230,290); st(c)
    txt(c,285,105,'AGREEMENT',16,LINE); 
    for y in range(130,280,18): c.move_to(195,y); c.line_to(375 if y%54 else 330,y)
    st(c,LINE,1,0.45)
    c.move_to(195,322); c.curve_to(215,296,232,340,256,312); c.curve_to(272,298,282,328,312,314); st(c,GOLD,2)
    c.save(); c.translate(470,240); c.rotate(-0.35); c.rectangle(-10,-110,20,180); st(c,LINE,1.8); c.move_to(-10,70); c.line_to(0,95); c.line_to(10,70); st(c,GOLD,1.8); c.restore()
    c.new_path(); c.arc(360,318,24,0,2*math.pi); st(c,ROSE,2); txt(c,360,322,'SEAL',10,ROSE)



def tag(c):
    c.move_to(250,110); c.line_to(400,110); c.line_to(470,200); c.line_to(400,290); c.line_to(250,290); c.close_path()
    st(c)
    c.new_path(); c.arc(420,200,14,0,2*math.pi); st(c,LINE,2)
    c.move_to(434,200); c.curve_to(480,170,500,120,470,90); st(c,LINE,1.4,0.7)
    txt(c,320,218,'$9.99',44,GOLD)



DRAWERS = {"coin": coin, "banknote": note, "bank": bank, "shelf": shelf, "card": card, "market": market,
           "cart": cart, "contract": deal, "tag": tag}
# Words in a scene's drawing that call for each sketch (first match wins per object).
KEYWORDS = {
    "coin": r"\bcoins?\b",
    "banknote": r"\b(bank ?notes?|notes? of money|cash|bills? of money|dollar bills?|paper money)\b",
    "bank": r"\bbank (building|branch|facade)\b|\b(a|the) bank\b",
    "shelf": r"\b(shelf|shelves|supermarket|grocery)\b",
    "card": r"\b(credit|debit|bank|payment) cards?\b",
    "market": r"\b(candlesticks?|candles chart|stock chart|trading chart)\b",
    "cart": r"\b(shopping )?(cart|trolley)\b",
    "contract": r"\b(contract|agreement|filing|signed document)\b",
    "tag": r"\bprice tags?\b",
}


def sketch(name: str, folder: Path) -> Path:
    """The reference sketch for name as a PNG (white and gold lines on black), cached."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"structure-{name}.png"
    if not path.exists():
        s = cairo.ImageSurface(cairo.FORMAT_RGB24, TW, TH)
        c = cairo.Context(s)
        c.set_source_rgb(0.03, 0.03, 0.04)
        c.paint()
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        DRAWERS[name](c)
        s.write_to_png(str(path))
    return path


def structures_for(drawing: str, folder: Path, limit: int = 2) -> list[Path]:
    """Reference sketches for the money and business objects a scene's drawing names."""
    text = drawing.lower()
    found = [name for name, pattern in KEYWORDS.items() if re.search(pattern, text)]
    return [sketch(name, folder) for name in found[:limit]]

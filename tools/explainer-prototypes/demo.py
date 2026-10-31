import sys, math, subprocess, numpy as np
sys.path.insert(0,'/home/claude/golide-content-engine/src')
from PIL import Image
from golide_engine.vector.render import CaptionRenderer, Layout
from golide_engine.vector.align import TimedLine, Word, caption_chunks
from golide_engine.theme import load_theme
D=__import__('os').path.dirname(__file__) or '.'
SRC={n:open(f'{D}/{n}_anim.py').read() for n in ('real','arch','closeup')}
def draw(name,**kw):
    ns=dict(OUT=False,A=1.0,SHOW_HINGE=False,D=1.0,BAR=1.0,CRACK=0.0); ns.update(kw)
    try: exec(SRC[name],ns)
    except SystemExit: pass
    s=ns['surf']; a=np.ndarray((s.get_height(),s.get_stride()//4,4),np.uint8,s.get_data())[:,:s.get_width(),[2,1,0]]
    return a.astype(np.float32)
ease=lambda x: (lambda u:u*u*(3-2*u))(min(1,max(0,x)))
# script (what the narration would say) and timing
lines=[("Apple's iPhone Duo folds one screen like a book",0.2,4.0,"one screen"),
       ("but that screen is 10 thin layers that all have to bend",4.2,8.4,"10 thin layers"),
       ("and if the centre bar stays up, the fold presses on it",8.6,13.4,"presses")]
tl=[]
for i,(text,a,b,emp) in enumerate(lines):
    ws=text.split(); step=(b-a-0.4)/len(ws)
    words=[Word(w,a+j*step,a+(j+1)*step) for j,w in enumerate(ws)]
    tl.append(TimedLine(i,text,emp,'illustration','','proof',a,b,words,()))
chunks=caption_chunks(tl)
cap=CaptionRenderer(Layout.for_format('short'),load_theme())
mark=cap.wordmark()
DUR,FPS=13.8,30
out='/tmp/claude-0/-home-claude/799125be-9bd5-56f2-8793-b19dc1429680/scratchpad/explainer-short.mp4'
p=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1080x1920','-r',str(FPS),'-i','-',
                    '-c:v','libx264','-pix_fmt','yuv420p','-crf','19',out],stdin=subprocess.PIPE)
def scene(t):
    if t<4.2:
        img=draw('real'); u=t/4.2
        z=1.0+0.07*u; im=Image.fromarray(img.astype(np.uint8)); w,h=im.size
        cw,ch=w/z,h/z; im=im.crop((int((w-cw)/2),int((h-ch)/2),int((w+cw)/2),int((h+ch)/2))).resize((w,h),Image.LANCZOS)
        return np.asarray(im,np.float32)*ease(t/0.6)
    if t<8.6:
        return draw('arch',A=ease((t-4.3)/3.0))
    return draw('closeup',D=ease((t-8.7)/1.6),BAR=1-0.75*ease((t-10.6)/0.9),CRACK=ease((t-11.4)/0.4)*(0.75+0.25*math.sin(t*7)))
prev=None
for k in range(int(DUR*FPS)):
    t=k/FPS
    f=scene(t)
    for edge in (4.2,8.6):                      # short cross-fade at each cut
        if edge-0.25<t<edge: f=f*(edge-t)/0.25
        if edge<=t<edge+0.25: f=f*(t-edge)/0.25
    if t>DUR-0.5: f=f*max(0,(DUR-t)/0.5)
    img=Image.fromarray(np.clip(f,0,255).astype(np.uint8))
    ci=max([i for i,c in enumerate(chunks) if c.start<=t] or [0]); ch=chunks[ci]
    if ch.start<=t<=ch.end+0.3:
        layer=cap.caption(ch,t,min(1.0,(t-ch.start)/0.18+0.2),(233,196,106))
        img.paste(layer,(0,1740),layer)
    img.paste(mark,(1080-mark.width-130,54),mark)
    p.stdin.write(img.tobytes())
p.stdin.close(); p.wait(); print('done')

import subprocess, sys
from pathlib import Path
import numpy as np
from golide_engine.vector.render import VectorRenderer, _load_drawing
from golide_engine.vector.align import TimedLine, Word, group_lines, caption_chunks
from golide_engine.vector.illustrate import SCENES
from golide_engine.vector.figures import render_figure
S=Path(sys.argv[1]); F=S/'fig_dev'
render_figure('layers: names=replaceable cover layer,ultra-thin glass,optical adhesive,polarizer,touch sensor,OLED emitters,thin-film backplane,support plate; title=the inner screen', F/'eng_layers.png',(1024,1536))
render_figure('fold: layers=6; bar=stuck', F/'eng_fold.png',(1024,1536))
scenes=[('product',F/'duo_product.png','grid','rose',"Apple's iPhone Duo folds one screen like a book",'screen'),
        ('stack',F/'eng_layers.png','grid','gold','but that screen is 10 thin layers that all have to bend','layers'),
        ('hinge',F/'eng_fold.png','pedestal','rose',"and if the centre bar stays up the fold presses on it",'presses')]
r=VectorRenderer('short'); SCENES.clear(); lines=[]; t0=0.0; per=4.6
for i,(sid,path,stage,acc,text,emp) in enumerate(scenes):
    d=_load_drawing(path,{'id':sid,'accent':acc,'label':''}); d.stage=stage; SCENES[sid]=d
    ws=text.split(); step=(per-0.6)/len(ws)
    words=[Word(w,t0+0.2+j*step,t0+0.2+(j+1)*step) for j,w in enumerate(ws)]
    lines.append(TimedLine(i,text,emp,'illustration','','proof',t0,t0+per,words,(sid,))); t0+=per
groups=group_lines(lines); chunks=caption_chunks(lines); fps=30
L=r.layout
out=S/'engine-explainer-short.mp4'
p=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{L.width}x{L.height}','-r',str(fps),'-i','-',
    '-c:v','libx264','-pix_fmt','yuv420p','-crf','19',str(out)],stdin=subprocess.PIPE)
for k in range(int(t0*fps)):
    p.stdin.write(np.ascontiguousarray(r.frame(k/fps,groups,chunks,t0)).tobytes())
p.stdin.close(); p.wait(); print('ok',t0)

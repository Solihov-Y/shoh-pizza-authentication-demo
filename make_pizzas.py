"""Create original illustrated pizza images; no third-party media or external requests."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import math, random
ROOT=Path(__file__).resolve().parent/'static'/'assets'
ROOT.mkdir(parents=True,exist_ok=True)
SZ=(920,680)
DEFS=[
 ('pizza_margarita.png',(49,67,52),'margherita',0),
 ('pizza_pepperoni.png',(61,49,39),'pepperoni',1),
 ('pizza_bbq.png',(45,55,57),'bbq',2),
 ('pizza_cheese.png',(65,54,43),'cheese',3),
 ('pizza_veggie.png',(46,64,48),'veggie',4),
 ('pizza_mexicana.png',(69,47,41),'mexicana',5),
]
def rgba(c,a):return tuple(c)+(a,)
for fname,bg,style,seed in DEFS:
 random.seed(1234+seed)
 S=2;w,h=SZ[0]*S,SZ[1]*S
 im=Image.new('RGB',(w,h),bg);d=ImageDraw.Draw(im,'RGBA')
 for i in range(200):
  x=random.randint(0,w);y=random.randint(0,h);r=random.randint(3,75)
  d.ellipse((x-r,y-r,x+r,y+r), fill=(0,0,0,random.randint(2,12)))
 # warm radial ambient
 glow=Image.new('RGBA',(w,h),(0,0,0,0));gd=ImageDraw.Draw(glow)
 for r in range(570,80,-15):
  a=int((1-r/590)*2.7)
  gd.ellipse((w//2-r,h//2-r-35,w//2+r,h//2+r-35), fill=(255,168,86,min(a,9)))
 im=Image.alpha_composite(im.convert('RGBA'),glow)
 # dark elliptical cast shadow
 shadow=Image.new('RGBA',(w,h),(0,0,0,0));sd=ImageDraw.Draw(shadow)
 sd.ellipse((310,130,1585,1360),fill=(0,0,0,150));shadow=shadow.filter(ImageFilter.GaussianBlur(42));im=Image.alpha_composite(im,shadow)
 d=ImageDraw.Draw(im,'RGBA')
 cx=w//2+75;cy=h//2+45;R=520
 # ceramic plate
 d.ellipse((cx-R-45,cy-R-15,cx+R+45,cy+R+85), fill=(239,226,200,255))
 for t in range(8):
  rr=R+36-t*5;d.ellipse((cx-rr,cy-rr-5,cx+rr,cy+rr+12),outline=(255,255,255,25+t*12),width=2)
 # main crust
 pts=[]
 for k in range(260):
  a=2*math.pi*k/260;rx=R-48+random.uniform(-7,7);ry=R-58+random.uniform(-7,7)
  pts.append((cx+math.cos(a)*rx,cy+math.sin(a)*ry))
 d.polygon(pts,fill=(168,83,31,255))
 d.ellipse((cx-R+70,cy-R+65,cx+R-70,cy+R-65),fill=(221,149,60,255))
 d.ellipse((cx-R+100,cy-R+98,cx+R-100,cy+R-105),fill=(190,68,28,255))
 d.ellipse((cx-R+125,cy-R+123,cx+R-125,cy+R-128),fill=(245,191,95,255))
 # dark toasted bits on crust
 for _ in range(420):
  ang=random.random()*2*math.pi;rr=random.uniform(R-108,R-55)
  x=cx+rr*math.cos(ang);y=cy+rr*math.sin(ang)
  r=random.uniform(1.5,8)
  d.ellipse((x-r,y-r,x+r,y+r),fill=random.choice([(118,56,24,90),(255,224,145,150),(226,97,34,75)]))
 # cheese melt freckles
 for _ in range(490):
  angle=random.random()*2*math.pi;rr=random.random()**0.52*(R-135)
  x=cx+rr*math.cos(angle);y=cy+rr*math.sin(angle)
  r=random.uniform(2,13)
  d.ellipse((x-r,y-r,x+r,y+r),fill=random.choice([(255,232,148,130),(187,82,25,75),(244,145,56,65),(255,243,184,90)]))
 # slices etched
 for k in range(8):
  a=math.pi*k/4+0.12
  d.line((cx,cy,cx+int(math.cos(a)*(R-115)),cy+int(math.sin(a)*(R-115))),fill=(124,68,27,78),width=5)
 # ingredient topping logic
 points=[]
 for k in range(58):
  a=random.random()*2*math.pi;rr=random.random()**0.63*(R-178)
  points.append((int(cx+rr*math.cos(a)),int(cy+rr*math.sin(a))))
 if style in ('pepperoni','mexicana'):
  for x,y in points[:36 if style=='pepperoni' else 20]:
   r=random.randint(20,35);d.ellipse((x-r,y-r,x+r,y+r),fill=(129,42,31,242),outline=(231,95,51,238),width=5)
   for k in range(5):
    xx=x+random.randint(-r+4,r-4);yy=y+random.randint(-r+4,r-4)
    d.ellipse((xx-3,yy-3,xx+3,yy+3),fill=(245,161,85,160))
 if style in ('bbq','mexicana'):
  for x,y in points[:37]:
   r=random.randint(13,22)
   d.rounded_rectangle((x-r,y-r//2,x+r,y+r//2),radius=9,fill=(183,93,38,245),outline=(250,171,98,160),width=3)
  # bbq swirls
  if style=='bbq':
   for j in range(7):
    aa=j*2*math.pi/7
    bx=cx+math.cos(aa)*190;by=cy+math.sin(aa)*190
    d.arc((bx-88,by-60,bx+88,by+60),start=30,end=310,fill=(76,33,25,155),width=13)
 if style in ('veggie','margherita','mexicana'):
  for x,y in points[5:27]:
   r=random.randint(9,18);d.ellipse((x-r,y-r,x+r,y+r),fill=(190,48,29,235),outline=(246,139,89,155),width=3)
 if style=='cheese':
  for x,y in points[:24]:
   r=random.randint(12,25);d.ellipse((x-r,y-r//2,x+r,y+r//2),fill=(249,231,193,245),outline=(255,255,236,130),width=2)
  for x,y in points[20:39]:
   r=8;d.ellipse((x-r,y-r,x+r,y+r),fill=(126,134,93,185))
 if style in ('veggie','mexicana'):
  for x,y in points[22:52]:
   r=random.randint(12,23)
   if random.random()<0.6:
    d.arc((x-r,y-r,x+r,y+r),start=20,end=300,fill=(55,98,52,230),width=8)
   else:
    d.ellipse((x-r,y-r,x+r,y+r),outline=(45,39,35,235),width=9)
 # basil leaves on all pizzas
 leaves=18 if style=='margherita' else 12
 for x,y in random.sample(points,leaves):
  angle=random.uniform(0,180);rr=random.randint(13,23)
  # organic leaf polygon
  leaf=[(x-rr,y),(x,y-rr*0.7),(x+rr,y),(x,y+rr*0.45)]
  d.polygon(leaf,fill=(34,94,54,230))
  d.line((x-rr+4,y,x+rr-4,y),fill=(152,186,83,150),width=2)
 # crunchy edge highlights
 for k in range(50):
  a=random.random()*math.pi*2;rr=R-60
  x=cx+rr*math.cos(a);y=cy+rr*math.sin(a)
  r=random.randint(2,7)
  d.ellipse((x-r,y-r,x+r,y+r),fill=(255,232,149,130))
 im=im.convert('RGB').resize(SZ,Image.Resampling.LANCZOS)
 im.save(ROOT/fname,optimize=True,quality=93)
 print(fname)

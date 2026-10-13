import sys
from PIL import Image, ImageDraw, ImageFont
out, scale = sys.argv[1], float(sys.argv[2])
fonts = [a.split("=",1) for a in sys.argv[3:]]
text = ["She said, “I have read *that* book twice — naïve, really.”",
        "abcdefghijklmnopqrstuvwxyz áàâäãåæçéêëíïñóôöøúüß",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789 (fig. 4) [a; b] {c}?!"]
px = int(10*300/72*scale)
W = int(1900*scale); H = int((len(fonts)*(len(text)*1.5+1.2))*px)
img = Image.new("L", (W, H), 255); d = ImageDraw.Draw(img); y = 10
for name, p in fonts:
    lab = ImageFont.truetype(fonts[0][1], int(px*0.5))
    d.text((10, y), name, font=lab, fill=120); y += int(px*0.8)
    f = ImageFont.truetype(p, px)
    for t in text:
        d.text((10, y), t, font=f, fill=0); y += int(px*1.5)
    y += int(px*0.4)
img = img.point(lambda v: (v*15//255)*17)
img.save(out)

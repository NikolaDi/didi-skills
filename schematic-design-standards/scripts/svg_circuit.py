"""确定性原理图图元：图形、端点和预期网络分开记录。仅用于规则校验示意。"""
from pathlib import Path
from html import escape
import json
import math

INK = '#263747'
WIRE = '#226850'
BLUE = '#24518a'
MUTED = '#637586'


class Drawing:
    def __init__(self, number, title, subtitle, width=1120, height=700):
        self.width, self.height = width, height
        self.number, self.title = number, title
        self.items, self.wires, self.pins, self.labels, self.junctions = [], [], [], [], []
        self.texts = []
        self.rect(0, 0, width, height, fill='white', stroke='none')
        self.text(44, 51, f'{number:02d}  {title}', 28, INK, bold=True)
        self.text(44, 82, subtitle, 16, MUTED)
        self.line(44, 104, width-44, 104, '#b9c6ce', 1)
        self.line(44, height-101, width-44, height-101, '#b9c6ce', 1)
        self.text(44, height-26, '通用拓扑与布局校验图 · 逻辑引脚，非封装脚号 · 参数与性能需按实际器件设计', 14, MUTED)

    def text(self, x, y, text, size=17, color=INK, anchor='start', bold=False):
        self.items.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{700 if bold else 400}">{escape(str(text))}</text>')
        self.texts.append(dict(x=x, y=y, text=str(text), size=size, anchor=anchor))

    def line(self, x1, y1, x2, y2, color=INK, width=2):
        self.items.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>')

    def rect(self, x, y, w, h, fill='white', stroke=INK, width=2):
        self.items.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')

    def poly(self, points, fill='none', stroke=INK, width=2, close=False):
        tag = 'polygon' if close else 'polyline'
        ps = ' '.join(f'{x},{y}' for x,y in points)
        self.items.append(f'<{tag} points="{ps}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round"/>')

    def circle(self, x, y, r, fill='white', stroke=INK, width=2):
        self.items.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')

    def wire(self, *points):
        for a,b in zip(points, points[1:]):
            assert a[0] == b[0] or a[1] == b[1], ('导线必须正交', a,b)
            assert a != b, ('零长导线', a)
            self.wires.append([list(a),list(b)])
        ps = ' '.join(f'{x},{y}' for x,y in points)
        self.items.append(f'<polyline data-electrical="wire" points="{ps}" fill="none" stroke="{WIRE}" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>')

    def dot(self, x, y):
        self.junctions.append([x,y])
        self.items.append(f'<circle data-electrical="junction" cx="{x}" cy="{y}" r="3.7" fill="{WIRE}"/>')

    def pin(self, ref, name, p, net):
        assert not any(q['ref']==ref and q['pin']==name for q in self.pins), (ref,name)
        self.pins.append(dict(ref=ref, pin=name, x=p[0], y=p[1], net=net))
        self.items.append(f'<circle data-electrical="pin" data-ref="{escape(ref)}" data-pin="{escape(name)}" cx="{p[0]}" cy="{p[1]}" r="0"/>')

    def label(self, p, net):
        self.labels.append(dict(x=p[0], y=p[1], net=net))
        self.items.append(f'<circle data-electrical="label" data-net="{escape(net)}" cx="{p[0]}" cy="{p[1]}" r="0"/>')

    def port(self, p, net, align='start', display=None):
        self.label(p, net)
        self.circle(*p, 3, fill='white', stroke=WIRE, width=1.6)
        self.text(p[0],p[1]-12,display or net,16,BLUE,align)

    def power(self, p, net):
        self.label(p, net)
        x,y=p
        self.line(x,y,x,y-13,WIRE)
        self.line(x-10,y-13,x+10,y-13,WIRE)
        self.text(x,y-25,net,16,BLUE,'middle')

    def ground(self, p, net='GND', show=False):
        self.label(p, net)
        x,y=p
        self.line(x,y,x,y+12,WIRE)
        for dy,half in [(12,13),(18,9),(24,4)]:
            self.line(x-half,y+dy,x+half,y+dy,WIRE,1.8)
        if net!='GND' or show:
            self.text(x,y+44,net,14,BLUE,'middle')

    def section(self, x, y, title):
        self.text(x,y,title,18,BLUE,bold=True)

    def checks(self, *lines):
        for i,s in enumerate(lines):
            self.text(44,self.height-73+i*24,s,16,INK)

    def passive(self, kind, ref, value, a, b, na, nb, side=1):
        self.pin(ref,'1',a,na); self.pin(ref,'2',b,nb)
        x1,y1=a; x2,y2=b
        assert x1==x2 or y1==y2
        cx,cy=(x1+x2)/2,(y1+y2)/2
        horizontal=y1==y2
        if kind=='R' or kind=='FB':
            if horizontal:
                self.line(x1,y1,cx-23,cy); self.rect(cx-23,cy-9,46,18); self.line(cx+23,cy,x2,y2)
            else:
                self.line(x1,y1,cx,cy-23); self.rect(cx-9,cy-23,18,46); self.line(cx,cy+23,x2,y2)
        elif kind=='C':
            if horizontal:
                self.line(x1,y1,cx-6,cy); self.line(cx+6,cy,x2,y2)
                self.line(cx-6,cy-17,cx-6,cy+17); self.line(cx+6,cy-17,cx+6,cy+17)
            else:
                self.line(x1,y1,cx,cy-6); self.line(cx,cy+6,x2,y2)
                self.line(cx-17,cy-6,cx+17,cy-6); self.line(cx-17,cy+6,cx+17,cy+6)
        elif kind=='L':
            if not horizontal:
                raise ValueError('电感画法使用水平主通路')
            self.line(x1,y1,cx-32,cy); self.line(cx+32,cy,x2,y2)
            self.items.append(f'<path d="M {cx-32} {cy} '+ ' '.join('a 8 10 0 0 1 16 0' for _ in range(4)) + f'" fill="none" stroke="{INK}" stroke-width="2"/>')
        elif kind=='X':
            assert horizontal
            self.line(x1,y1,cx-20,cy); self.line(cx+20,cy,x2,y2)
            self.line(cx-20,cy-20,cx-20,cy+20);self.line(cx+20,cy-20,cx+20,cy+20)
            self.rect(cx-10,cy-25,20,50)
        elif kind=='SW':
            if horizontal:
                self.line(x1,y1,cx-18,cy);self.line(cx+18,cy,x2,y2)
                self.circle(cx-18,cy,3);self.circle(cx+18,cy,3);self.line(cx-18,cy,cx+17,cy-18)
            else:
                self.line(x1,y1,cx,cy-18);self.line(cx,cy+18,x2,y2)
                self.circle(cx,cy-18,3);self.circle(cx,cy+18,3);self.line(cx,cy-18,cx+18,cy+17)
        if horizontal:
            self.text(cx,cy-38 if kind=='X' else cy-25,ref,16,INK,'middle')
            if value:self.text(cx,cy+48 if kind=='X' else cy+34,value,15,MUTED,'middle')
        else:
            xx=cx+24 if side>0 else cx-24
            anc='start' if side>0 else 'end'
            self.text(xx,cy-4,ref,16,INK,anc)
            if value:self.text(xx,cy+20,value,15,MUTED,anc)

    def resistor(self,ref,value,a,b,na,nb,side=1):self.passive('R',ref,value,a,b,na,nb,side)
    def cap(self,ref,value,a,b,na,nb,side=1):self.passive('C',ref,value,a,b,na,nb,side)
    def inductor(self,ref,value,a,b,na,nb):self.passive('L',ref,value,a,b,na,nb)
    def switch(self,ref,a,b,na,nb):self.passive('SW',ref,'',a,b,na,nb)
    def crystal(self,ref,value,a,b,na,nb):self.passive('X',ref,value,a,b,na,nb)

    def diode(self,ref,a,k,na,nk,led=False,side=1):
        self.pin(ref,'A',a,na);self.pin(ref,'K',k,nk)
        cx,cy=(a[0]+k[0])/2,(a[1]+k[1])/2
        dx,dy=k[0]-a[0],k[1]-a[1]
        length=math.hypot(dx,dy); ux,uy=dx/length,dy/length
        def p(t,n=0):return(cx+t*ux-n*uy,cy+t*uy+n*ux)
        self.line(*a,*p(-14));self.line(*p(14),*k)
        self.poly([p(-14,-13),p(12),p(-14,13)],fill='white',close=True)
        self.line(*p(14,-15),*p(14,15))
        if led:
            for t in [-5,10]:
                s=p(t,-20); e=p(t+14,-36)
                self.line(*s,*e)
                self.poly([p(t+8,-36),e,p(t+14,-29)],fill=INK,close=True)
        if dy==0:self.text(cx,cy+48 if led else cy-26,ref,16,INK,'middle')
        else:self.text(cx+side*28,cy+5,ref,16,INK,'start' if side>0 else 'end')

    def ic(self,ref,name,x,y,w,h,pins):
        """pins: (逻辑脚名, L/R/T/B, 沿对应边偏移, 预期网络)；返回外部锚点。"""
        self.rect(x,y,w,h)
        self.text(x,y-16,ref,17,INK,bold=True)
        self.text(x+w/2,y+27,name,17,INK,'middle',True)
        result={}
        for pin,side,off,net in pins:
            if side=='L':
                p=(x-24,y+off);self.line(*p,x,y+off);self.text(x+10,y+off+5,pin,15)
            elif side=='R':
                p=(x+w+24,y+off);self.line(x+w,y+off,*p);self.text(x+w-10,y+off+5,pin,15,anchor='end')
            elif side=='T':
                p=(x+off,y-24);self.line(*p,x+off,y);self.text(x+off,y+48,pin,14,anchor='middle')
            else:
                p=(x+off,y+h+24);self.line(x+off,y+h,*p);self.text(x+off,y+h-10,pin,14,anchor='middle')
            self.pin(ref,pin,p,net);result[pin]=p
        return result

    def opamp(self,ref,cx,cy,nets,comparator=False):
        """引脚 -/+ 左侧，OUT 右侧，V+/V- 上下；nets 为这些名称到网络映射。"""
        self.poly([(cx-60,cy-72),(cx-60,cy+72),(cx+65,cy)],fill='white',close=True)
        p={'-':(cx-90,cy-30),'+':(cx-90,cy+30),'OUT':(cx+95,cy),'V+':(cx,cy-62),'V-':(cx,cy+62)}
        self.line(*p['-'],cx-60,cy-30);self.line(*p['+'],cx-60,cy+30);self.line(cx+65,cy,*p['OUT'])
        self.line(*p['V+'],cx,cy-38);self.line(cx,cy+38,*p['V-'])
        self.text(cx-48,cy-24,'−',22);self.text(cx-48,cy+37,'+',22)
        self.text(cx+8,cy-48,'V+',13);self.text(cx+8,cy+61,'V−',13)
        self.text(cx-30,cy-90,ref,17,INK,'middle',True)
        self.text(cx-18,cy+6,'CMP' if comparator else 'A',15,MUTED)
        for name,point in p.items():self.pin(ref,name,point,nets[name])
        return p

    def transistor(self,ref,cx,cy,ng,nd,ns,bjt=False):
        """三个外部锚点：控制(cx-65,cy)、上端(cx+20,cy-65)、下端(cx+20,cy+65)。"""
        p={'B' if bjt else 'G':(cx-65,cy),'C' if bjt else 'D':(cx+20,cy-65),'E' if bjt else 'S':(cx+20,cy+65)}
        self.line(cx-65,cy,cx-25,cy)
        self.line(cx-25,cy-29,cx-25,cy+29)
        if bjt:
            self.line(cx-25,cy-13,cx+20,cy-42);self.line(cx+20,cy-42,cx+20,cy-65)
            self.line(cx-25,cy+13,cx+20,cy+42);self.line(cx+20,cy+42,cx+20,cy+65)
            self.poly([(cx+18,cy+40),(cx+4,cy+38),(cx+11,cy+28)],fill=INK,close=True)
        else:
            for yy in [-22,0,22]:self.line(cx-12,cy+yy-7,cx-12,cy+yy+7)
            self.poly([(cx-12,cy-22),(cx+20,cy-22),(cx+20,cy-65)])
            self.poly([(cx-12,cy+22),(cx+20,cy+22),(cx+20,cy+65)])
            self.line(cx-12,cy,cx+9,cy);self.line(cx+9,cy,cx+9,cy+22)
            self.poly([(cx-10,cy),(cx-1,cy-5),(cx-1,cy+5)],fill=INK,close=True)
            self.poly([(cx+20,cy-42),(cx+48,cy-42),(cx+48,cy-10)])
            self.poly([(cx+48,cy+10),(cx+48,cy+42),(cx+20,cy+42)])
            self.poly([(cx+39,cy+10),(cx+48,cy-8),(cx+57,cy+10)],fill='white',close=True)
            self.line(cx+37,cy-10,cx+59,cy-10)
        self.text(cx-45,cy-10,'B' if bjt else 'G',14)
        self.text(cx+4,cy-48,'C' if bjt else 'D',14,anchor='end')
        self.text(cx+4,cy+60,'E' if bjt else 'S',14,anchor='end')
        self.text(cx+80,cy-8,ref,17,INK,bold=True)
        self.text(cx+80,cy+18,'NPN' if bjt else 'NMOS',15,MUTED)
        for (name,point),net in zip(p.items(),[ng,nd,ns]):self.pin(ref,name,point,net)
        return p

    def save(self,path):
        meta=dict(number=self.number,title=self.title,pins=self.pins,labels=self.labels,junctions=self.junctions,segments=self.wires,texts=self.texts)
        data=escape(json.dumps(meta,ensure_ascii=False))
        body='\n'.join(self.items)
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}" role="img">\n<title>{escape(self.title)}</title>\n<desc>可编辑矢量原理图；用于布局与连接表达验证。</desc>\n<metadata id="circuit-model">{data}</metadata>\n<g font-family="Noto Sans CJK SC, sans-serif">\n{body}\n</g>\n</svg>\n'
        Path(path).write_text(svg,encoding='utf-8')
        return Path(path)

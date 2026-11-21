"""从 SVG 实际路径重建连通关系，核对预期网络、断线、分支结点和文字占位。

不是原生 EDA ERC，也不验证器件性能。人工查看仍是交付必需步骤。
"""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def on_segment(p,a,b):
    return (a[0]==b[0]==p[0] and min(a[1],b[1])<=p[1]<=max(a[1],b[1])) or (a[1]==b[1]==p[1] and min(a[0],b[0])<=p[0]<=max(a[0],b[0]))


def check(path):
    root=ET.parse(path).getroot()
    metadata=root.find('{*}metadata')
    model=json.loads(metadata.text)
    errors=[];warnings=[]
    segments=[];pins={};labels=[];junctions=[]
    for el in root.iter():
        kind=el.get('data-electrical')
        if kind=='wire':
            points=[tuple(map(float,p.split(','))) for p in el.get('points').split()]
            segments.extend(list(zip(points,points[1:])))
        elif kind in ['pin','label','junction']:
            p=(float(el.get('cx')),float(el.get('cy')))
            if kind=='pin':pins[(el.get('data-ref'),el.get('data-pin'))]=p
            elif kind=='label':labels.append((el.get('data-net'),p))
            else:junctions.append(p)
    expected_segments=[(tuple(a),tuple(b)) for a,b in model['segments']]
    if segments!=expected_segments:errors.append('SVG导线路径与附带记录不一致')
    expected_pins={(p['ref'],p['pin']):(p['x'],p['y']) for p in model['pins']}
    if pins!=expected_pins:errors.append('SVG引脚锚点与预期引脚不一致')
    expected_labels=[(q['net'],(q['x'],q['y'])) for q in model['labels']]
    if labels!=expected_labels:errors.append('SVG标签锚点与记录不一致')
    points=set(pins.values())|{p for _,p in labels}|set(junctions)|{p for s in segments for p in s}
    parent={p:p for p in points}
    def find(p):
        while parent[p]!=p:
            parent[p]=parent[parent[p]];p=parent[p]
        return p
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:parent[b]=a
    for a,b in segments:
        if a[0]!=b[0] and a[1]!=b[1]:errors.append(f'非正交导线 {a}→{b}')
        for p in points:
            if on_segment(p,a,b):union(a,p)
    # 同名标签建立隐式连通；不同地名不会自动合并。
    label_anchor={}
    for net,p in labels:
        if net in label_anchor:union(p,label_anchor[net])
        else:label_anchor[net]=p
    nets={};groups={}
    for pin in model['pins']:
        key=(pin['ref'],pin['pin']);p=pins[key];g=find(p);net=pin['net']
        nets.setdefault(net,set()).add(g)
        groups.setdefault(g,{}).setdefault(net,[]).append('.'.join(key))
    for net,p in labels:
        g=find(p);nets.setdefault(net,set()).add(g)
        groups.setdefault(g,{}).setdefault(net,[]).append('标签:'+net)
    for g,members in groups.items():
        if len(members)>1:errors.append('误并网 '+json.dumps(members,ensure_ascii=False))
    for net,g in nets.items():
        if len(g)>1:errors.append(f'断网 {net}：{len(g)}个分离连接组')
    # 无引脚/标签支撑的自由导线端点，以及未标明的三向以上分支。
    anchors=set(pins.values())|{p for _,p in labels}
    for p in points:
        directions=set()
        for a,b in segments:
            if on_segment(p,a,b):
                for q in [a,b]:
                    if q!=p:directions.add((0 if q[0]==p[0] else (1 if q[0]>p[0] else -1),0 if q[1]==p[1] else (1 if q[1]>p[1] else -1)))
        if len(directions)==1 and p not in anchors:errors.append(f'悬空导线端点 {p}')
        if len(directions)>=3 and p not in junctions:errors.append(f'分支缺少结点 {p}')
        if p in pins.values() and len(directions)==0 and p not in {p for _,p in labels}:errors.append(f'未连接的器件引脚 {p}')
    # 全部文字采用同一字体测量；此检查仅辅助人工渲染检查。
    try:
        from PIL import ImageFont
        fontfile='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
        if not Path(fontfile).exists():raise FileNotFoundError(fontfile)
        boxes=[]
        for t in model['texts']:
            font=ImageFont.truetype(fontfile,int(t['size']))
            w=font.getlength(t['text']);dx=0 if t['anchor']=='start' else (-w/2 if t['anchor']=='middle' else -w)
            bb=font.getbbox(t['text'],anchor='ls')
            box=(t['x']+dx,t['y']+bb[1],t['x']+dx+w,t['y']+bb[3])
            width,height=map(float,root.get('viewBox').split()[2:])
            if box[0]<0 or box[1]<0 or box[2]>width or box[3]>height:errors.append('文字越界 '+t['text'])
            for old,s in boxes:
                iw=min(old[2],box[2])-max(old[0],box[0]);ih=min(old[3],box[3])-max(old[1],box[1])
                if iw>2 and ih>2:errors.append('文字占位重叠 '+s+' / '+t['text'])
            boxes.append((box,t['text']))
    except (ImportError,FileNotFoundError):warnings.append('未执行字体占位检查；需要Pillow与Noto CJK字体')
    return dict(file=path.name,pins=len(pins),segments=len(segments),nets=len(nets),errors=errors,warnings=warnings)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',nargs='?',type=Path,default=Path(__file__).resolve().parents[1]/'assets/examples')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    results=[check(p) for p in sorted(args.directory.glob('*.svg'))]
    if not results:raise SystemExit('没有找到SVG')
    for r in results:
        print(r['file'], '通过' if not r['errors'] else '需修复', f"引脚{r['pins']} 网络{r['nets']}")
        for e in r['errors'][:8]:print('  '+e)
        for w in r['warnings']:print('  '+w)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(1 if any(r['errors'] for r in results) else 0)


if __name__=='__main__':main()

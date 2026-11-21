"""供电与驱动的通用规则校验图；只使用逻辑引脚和用途参数。"""
from pathlib import Path
from svg_circuit import Drawing, INK, MUTED, BLUE


def ldo(out):
    d = Drawing(1, 'LDO：紧凑的供电小系统', '主供电沿水平基线，输入/输出电容就地聚合，使能和指示支路向下展开。')
    d.section(92, 166, '输入与使能')
    d.section(440, 166, '稳压单元')
    d.section(764, 166, '输出与指示')
    p = d.ic('U1', 'LDO', 440, 220, 200, 170,
             [('VIN', 'L', 60, 'VIN'), ('EN', 'L', 130, 'LDO_EN'),
              ('VOUT', 'R', 60, 'VOUT'), ('GND', 'B', 100, 'GND')])
    d.port((100,280), 'VIN')
    d.wire((100,280), p['VIN'])
    d.cap('C_IN', '输入去耦', (240,280), (240,400), 'VIN', 'GND')
    d.dot(240,280);d.ground((240,400))
    d.resistor('R_EN', '上拉', (350,280), (350,350), 'VIN', 'LDO_EN')
    d.dot(350,280);d.dot(350,350)
    d.wire((350,350),p['EN'])
    d.wire((350,350),(350,448));d.port((350,448),'LDO_EN')
    d.wire(p['GND'],(540,450));d.ground((540,450))
    d.wire(p['VOUT'],(1010,280));d.port((1010,280),'VOUT',align='end')
    d.cap('C_OUT','输出去耦',(750,280),(750,400),'VOUT','GND')
    d.dot(750,280);d.ground((750,400))
    d.resistor('R_LED','限流',(940,280),(940,360),'VOUT','LED_A')
    d.dot(940,280);d.wire((940,360),(940,390))
    d.diode('LED1',(940,390),(940,470),'LED_A','GND',led=True,side=-1)
    d.ground((940,470));d.text(875,540,'指示支路按需配置',15,MUTED)
    d.checks('检查：电容分别接在输入与输出节点，VIN / VOUT / GND / EN 就近标明。',
             '使能上拉和输出指示是独立支路；读图不需要追踪跨页回路。')
    return d.save(out/'01-ldo.svg')


def buck(out):
    d = Drawing(2,'Buck：功率主线与反馈分层','通用内置高边开关控制器；外部续流、电感、输出滤波和反馈取样均显式连接。')
    d.section(84,163,'输入')
    d.section(515,163,'开关节点与输出滤波')
    p=d.ic('U1','BUCK 控制',220,215,210,200,
           [('VIN','L',65,'VIN'),('SW','R',65,'SW'),
            ('GND','B',70,'GND'),('FB','B',150,'FB')])
    d.text(325,339,'内置高边开关',15,MUTED,'middle')
    d.port((90,280),'VIN');d.wire((90,280),p['VIN'])
    d.cap('C_IN','输入滤波',(135,280),(135,410),'VIN','GND',side=-1)
    d.dot(135,280);d.ground((135,410))
    d.wire(p['SW'],(600,280));d.dot(520,280)
    d.diode('D_FREE',(520,410),(520,280),'GND','SW')
    d.ground((520,410))
    d.inductor('L1','储能',(600,280),(760,280),'SW','VOUT')
    d.wire((760,280),(1030,280));d.port((1030,280),'VOUT',align='end')
    d.cap('C_OUT','输出滤波',(950,280),(950,410),'VOUT','GND')
    d.dot(950,280);d.ground((950,410))
    d.resistor('R_TOP','反馈上臂',(800,280),(800,390),'VOUT','FB')
    d.resistor('R_BOT','反馈下臂',(800,390),(800,500),'FB','GND')
    d.dot(800,280);d.dot(800,390);d.ground((800,500))
    d.wire((800,390),(740,390),(740,520),(370,520),p['FB'])
    d.wire(p['GND'],(290,470));d.ground((290,470))
    d.text(410,558,'反馈取自电感后的输出节点',16,BLUE)
    d.checks('检查：SW 与 VOUT 不混名；续流二极管阳极接地、阴极接 SW。',
             '输出分压与 FB 的返回路径完整可追踪；本图只校验表达，不提供器件选型。')
    return d.save(out/'02-buck.svg')


def _vertical_inductor(d, ref, x, top, bottom, net_top, net_bottom):
    """纵向负载电感，让主电流通路保持从上到下。"""
    cy=(top+bottom)/2
    d.pin(ref,'1',(x,top),net_top);d.pin(ref,'2',(x,bottom),net_bottom)
    d.line(x,top,x,cy-32);d.line(x,cy+32,x,bottom)
    d.items.append(f'<path d="M {x} {cy-32} '+ ' '.join('a 10 8 0 0 1 0 16' for _ in range(4))+f'" fill="none" stroke="{INK}" stroke-width="2"/>')
    d.text(x-28,cy-5,ref,17,INK,'end')
    d.text(x-28,cy+22,'感性负载',15,MUTED,'end')


def mosfet(out):
    d=Drawing(3,'MOSFET：控制横向、功率纵向','门极电阻与下拉就地放置，负载及续流支路位于功率器件上方。')
    d.section(100,220,'控制输入')
    d.section(830,225,'负载续流')
    q=d.transistor('Q1',570,430,'GATE','LOAD_N','GND')
    d.power((590,160),'VLOAD');d.wire((590,160),(590,200))
    _vertical_inductor(d,'L_LOAD',590,200,290,'VLOAD','LOAD_N')
    d.wire((590,290),q['D'])
    d.diode('D_FREE',(780,330),(780,210),'LOAD_N','VLOAD')
    d.wire((780,210),(780,175),(590,175));d.dot(590,175)
    d.wire((780,330),(590,330));d.dot(590,330)
    d.text(830,300,'阴极 → VLOAD',15,MUTED)
    d.text(830,327,'阳极 → LOAD_N',15,MUTED)
    d.port((100,430),'PWM')
    d.wire((100,430),(180,430))
    d.resistor('R_G','门极串联',(180,430),(320,430),'PWM','GATE')
    d.wire((320,430),q['G']);d.dot(410,430)
    d.resistor('R_GS','关断下拉',(410,430),(410,530),'GATE','GND',side=-1)
    d.wire((410,530),(590,530),q['S']);d.ground((590,530));d.dot(590,530)
    d.checks('检查：G / D / S 靠近引脚；门极下拉回到源极所属参考地。',
             '续流支路跨接真实负载两端，控制网 GATE 与功率网 LOAD_N 保持分离。')
    return d.save(out/'03-mosfet-driver.svg')


def bjt(out):
    d=Drawing(4,'三极管：明确 B / C / E 与支路归属','以 NPN 低边驱动 LED 示意；基极限流、关断偏置、负载限流各有对应位置。')
    d.section(100,218,'逻辑控制')
    d.section(760,218,'负载电流路径')
    q=d.transistor('Q1',570,440,'BASE','LED_C','GND',bjt=True)
    d.power((590,150),'VLED');d.wire((590,150),(590,170))
    d.resistor('R_LED','LED 限流',(590,170),(590,260),'VLED','LED_A')
    d.wire((590,260),(590,280))
    d.diode('LED1',(590,280),(590,350),'LED_A','LED_C',led=True,side=-1)
    d.wire((590,350),q['C'])
    d.port((100,440),'LED_EN')
    d.wire((100,440),(180,440))
    d.resistor('R_B','基极限流',(180,440),(320,440),'LED_EN','BASE')
    d.wire((320,440),q['B']);d.dot(410,440)
    d.resistor('R_BE','关断偏置',(410,440),(410,535),'BASE','GND',side=-1)
    d.wire((410,535),(590,535),q['E']);d.ground((590,535));d.dot(590,535)
    d.text(760,282,'供电 → 限流 → LED',17,BLUE)
    d.text(760,315,'→ 集电极 → 发射极 → 地',17,BLUE)
    d.checks('检查：基极与集电极支路在空间上分开，B / C / E 身份可直接读取。',
             'R_B、R_BE、R_LED 的职责不混淆；具体阻值须按工作条件计算。')
    return d.save(out/'04-bjt-driver.svg')


def build(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    return [ldo(out),buck(out),mosfet(out),bjt(out)]


if __name__=='__main__':
    for p in build(Path(__file__).resolve().parents[1]/'assets'/'examples'):
        print(p)

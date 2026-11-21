"""数字与接口类通用图例。几何布局和预期网络均通过统一图元记录。"""
from pathlib import Path
from svg_circuit import Drawing, MUTED, BLUE


def mcu_core(out):
    d = Drawing(8, 'MCU：供电、复位、时钟与接口',
                '按功能组织引脚；局部外围连续连线；电源去耦保留器件归属。', height=900)
    d.section(70, 136, '复位：上拉与局部 RC')
    u = d.ic('U1', 'MCU · 逻辑单元', 470, 240, 240, 280, [
        ('NRST', 'L', 80, 'RESET_N'), ('OSC_IN', 'L', 180, 'OSC_IN'),
        ('OSC_OUT', 'L', 230, 'OSC_OUT'), ('VDD', 'T', 80, '+3V3'),
        ('VSS', 'B', 120, 'GND'), ('SCK', 'R', 80, 'SPI1_SCK'),
        ('MOSI', 'R', 120, 'SPI1_MOSI'), ('MISO', 'R', 160, 'SPI1_MISO'),
        ('SWDIO', 'R', 200, 'SWDIO'), ('SWCLK', 'R', 240, 'SWCLK')])
    d.power((550, 190), '+3V3'); d.wire((550, 190), u['VDD'])
    d.wire(u['VSS'], (590, 580)); d.ground((590, 580))
    d.power((200, 200), '+3V3'); d.wire((200, 200), (200, 220))
    d.resistor('R1', '上拉', (200, 220), (200, 300), '+3V3', 'RESET_N')
    d.wire((200, 300), (200, 320)); d.dot(200, 320)
    d.wire((100, 320), u['NRST'])
    d.wire((100, 320), (100, 380))
    d.switch('SW1', (100, 380), (100, 460), 'RESET_N', 'GND'); d.ground((100, 460))
    d.wire((300, 320), (300, 380)); d.dot(300, 320)
    d.cap('C1', '复位滤波', (300, 380), (300, 460), 'RESET_N', 'GND')
    d.ground((300, 460))
    d.section(750, 138, 'U1 的电源去耦')
    for ref,x in [('C2',790), ('C3',960)]:
        d.power((x, 195), '+3V3'); d.wire((x,195), (x,215))
        # 保留地符号与下方接口标签之间的留白。
        d.cap(ref, '去耦', (x,215), (x,260), '+3V3', 'GND'); d.ground((x,260))
    for name,net in [('SCK','SPI1_SCK'), ('MOSI','SPI1_MOSI'), ('MISO','SPI1_MISO'),
                     ('SWDIO','SWDIO'), ('SWCLK','SWCLK')]:
        p=u[name]; d.wire(p,(1020,p[1])); d.port((1020,p[1]),net,'end')
    d.section(70, 548, '时钟：晶体与负载电容')
    d.wire(u['OSC_IN'], (390,420), (390,560), (130,560), (130,620))
    d.wire(u['OSC_OUT'], (420,470), (420,650), (330,650), (330,620))
    d.crystal('X1', '晶体', (130,620), (330,620), 'OSC_IN', 'OSC_OUT')
    d.cap('C4', '负载', (130,620), (130,710), 'OSC_IN', 'GND'); d.dot(130,620)
    d.cap('C5', '负载', (330,650), (330,710), 'OSC_OUT', 'GND'); d.dot(330,650)
    d.ground((130,710)); d.ground((330,710))
    d.text(720,610,'同一芯片的不同功能可以分区，',17,MUTED)
    d.text(720,640,'器件身份和供电归属保持明确。',17,MUTED)
    d.text(720,680,'外围参数取决于选定 MCU。',16,MUTED)
    d.checks('检查：复位支路紧凑；晶体两端分别连接；通信引脚按组有序扇出。',
             '边界：这里只展示逻辑单元，实际器件的全部电源脚和约束须另行核对。')
    return d.save(out/'08-mcu-core.svg')


def i2c_interface(out):
    d = Drawing(9, 'I²C：双线总线与集中上拉',
                '两根信号按同一顺序展开；结点表示分支；无结点的跨线不连接。', height=760)
    master=d.ic('U1','I²C 主机',130,270,230,230,[
        ('SCL','R',80,'I2C1_SCL'),('SDA','R',140,'I2C1_SDA'),
        ('VDD','T',115,'+3V3'),('VSS','B',115,'GND')])
    target=d.ic('U2','I²C 外设',770,270,230,230,[
        ('SCL','L',80,'I2C1_SCL'),('SDA','L',140,'I2C1_SDA'),
        ('VDD','T',115,'+3V3'),('GND','B',115,'GND')])
    d.wire(master['SCL'],target['SCL']); d.wire(master['SDA'],target['SDA'])
    for x,ref,net,y in [(500,'R1','I2C1_SCL',350),(620,'R2','I2C1_SDA',410)]:
        d.power((x,160),'+3V3');d.wire((x,160),(x,185))
        d.resistor(ref,'上拉',(x,185),(x,285),'+3V3',net)
        d.wire((x,285),(x,y));d.dot(x,y)
    d.text(405,338,'I2C1_SCL',16,BLUE); d.text(405,398,'I2C1_SDA',16,BLUE)
    for pins,gnd in [(master,'VSS'),(target,'GND')]:
        p=pins['VDD'];d.power((p[0],210),'+3V3');d.wire((p[0],210),p)
        p=pins[gnd];d.wire(p,(p[0],560));d.ground((p[0],560))
    for x,ref in [(490,'C1'),(650,'C2')]:
        d.power((x,475),'+3V3');d.wire((x,475),(x,500))
        d.cap(ref,'去耦',(x,500),(x,575),'+3V3','GND');d.ground((x,575))
    d.text(490,632,'U1 去耦',15,MUTED,'middle');d.text(650,632,'U2 去耦',15,MUTED,'middle')
    d.checks('检查：一组上拉服务同一总线；SCL 与 SDA 未在交叉处误连接。',
             '设计时另核对电平、地址、总线电容和上拉值；本图不规定具体参数。')
    return d.save(out/'09-i2c-interface.svg')


def spi_uart(out):
    d=Drawing(10,'SPI / UART：接口顺序与两端身份',
              '按协议功能安排逻辑引脚；串联元件两侧使用不同网络；明确 TX/RX 所属端。',height=900)
    d.section(70,143,'SPI：时钟、数据与片选')
    a=d.ic('U1A','SPI 主机',100,180,260,230,[
        ('SCK','R',70,'SPI_SCK_SRC'),('MOSI','R',110,'SPI_MOSI'),
        ('MISO','R',150,'SPI_MISO'),('CS_N','R',190,'SPI_CS_N'),('GND','B',130,'GND')])
    b=d.ic('U2A','SPI 外设',760,180,260,230,[
        ('SCK','L',70,'SPI_SCK'),('SDI','L',110,'SPI_MOSI'),
        ('SDO','L',150,'SPI_MISO'),('CS_N','L',190,'SPI_CS_N'),('GND','B',130,'GND')])
    d.wire(a['SCK'],(440,250));d.resistor('R1','串联',(440,250),(560,250),'SPI_SCK_SRC','SPI_SCK')
    d.wire((560,250),b['SCK'])
    for pa,pb in [('MOSI','SDI'),('MISO','SDO'),('CS_N','CS_N')]:d.wire(a[pa],b[pb])
    for pins in [a,b]:
        p=pins['GND'];d.wire(p,(p[0],455));d.ground((p[0],455))
    d.section(70,523,'UART：主机 TX 对端 RX，主机 RX 对端 TX')
    a=d.ic('U1B','UART 主机',100,560,260,170,[
        ('TX','R',60,'UART_HOST_TX'),('RX','R',110,'UART_PEER_TX'),('GND','B',130,'GND')])
    b=d.ic('U3','UART 对端',760,560,260,170,[
        ('RX','L',60,'UART_TX_LINE'),('TX','L',110,'UART_PEER_TX'),('GND','B',130,'GND')])
    d.wire(a['TX'],(440,620));d.resistor('R2','串联',(440,620),(560,620),'UART_HOST_TX','UART_TX_LINE')
    d.wire((560,620),b['RX']);d.wire(a['RX'],b['TX'])
    for pins in [a,b]:d.ground(pins['GND'])
    d.checks('检查：SPI 信号次序一致；UART 端口命名参照端明确；串联元件没有被同名标签旁路。',
             '图中为接口逻辑单元；省略的供电单元须在实际工程中完整表达。')
    return d.save(out/'10-spi-uart.svg')


def multichannel(out):
    d=Drawing(11,'多通道：同构布局与独立采样节点',
              '四路共享供电和参考地；每路信号保持独立；选配差异就地标注。',height=940)
    for index,(dx,dy) in enumerate([(0,0),(550,0),(0,360),(550,360)],start=1):
        raw,adc=f'SENS{index}_RAW',f'SENS{index}_ADC'
        d.section(70+dx,145+dy,f'通道 {index}' + (' · C4 不装' if index==4 else ''))
        u=d.ic(f'U{index}','传感器',90+dx,240+dy,115,110,[
            ('OUT','R',60,raw),('VDD','T',60,'+3V3'),('GND','B',60,'GND')])
        d.power((150+dx,200+dy),'+3V3');d.wire((150+dx,200+dy),u['VDD'])
        d.wire(u['GND'],(150+dx,405+dy));d.ground((150+dx,405+dy))
        d.wire(u['OUT'],(280+dx,300+dy))
        d.resistor(f'R{index}','串联',(280+dx,300+dy),(380+dx,300+dy),raw,adc)
        d.wire((380+dx,300+dy),(530+dx,300+dy));d.port((530+dx,300+dy),adc,'end')
        d.wire((450+dx,300+dy),(450+dx,350+dy));d.dot(450+dx,300+dy)
        d.cap(f'C{index}','DNP' if index==4 else '滤波',(450+dx,350+dy),(450+dx,425+dy),adc,'GND')
        d.ground((450+dx,425+dy))
    d.checks('检查：各通道器件位置对应；SENS1_ADC 至 SENS4_ADC 互不并网；+3V3 / GND 真实共享。',
             'C4 标记为不安装，焊盘网络仍保留；不得把 DNP 等同于引脚未连接。')
    return d.save(out/'11-multichannel.svg')


def buttons_indicators(out):
    d=Drawing(13,'按键与指示灯：主线与辅助支路',
              '按键上拉、开关和滤波形成局部单元；LED 与限流电阻保持连续通路。',height=760)
    d.section(70,135,'低有效按键')
    d.power((250,190),'+3V3');d.wire((250,190),(250,220))
    d.resistor('R1','上拉',(250,220),(250,300),'+3V3','KEY_N')
    d.wire((250,300),(250,340));d.dot(250,340)
    d.wire((100,340),(480,340));d.port((480,340),'KEY_N','end')
    d.wire((100,340),(100,390))
    d.switch('SW1',(100,390),(100,470),'KEY_N','GND');d.ground((100,470))
    # 上拉与滤波支路错开，避免同一位置形成四向接点。
    d.wire((330,340),(330,390));d.dot(330,340)
    d.cap('C1','滤波',(330,390),(330,470),'KEY_N','GND')
    d.ground((330,470))
    d.text(100,555,'开关与电容各自接在 KEY_N 和 GND 之间。',16,MUTED)
    d.section(620,135,'高有效指示灯')
    d.port((620,300),'LED_DRV');d.wire((620,300),(690,300))
    d.resistor('R2','限流',(690,300),(790,300),'LED_DRV','LED_A')
    d.wire((790,300),(850,300))
    d.diode('D1',(850,300),(950,300),'LED_A','GND',led=True)
    d.wire((950,300),(1000,300),(1000,420));d.ground((1000,420))
    d.text(620,500,'GPIO 输出能力与 LED 电流另行计算。',16,MUTED)
    d.text(620,530,'功能名称、有效电平和元件身份就地可见。',16,MUTED)
    d.checks('检查：按键主节点清楚；上拉和到地支路上下分层；LED 没有绕过限流电阻。',
             '错落来自功能关系；不为对称交换端子、扩大支路间距或删去元件。')
    return d.save(out/'13-buttons-indicators.svg')


def build(out: Path) -> list[Path]:
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    return [mcu_core(out),i2c_interface(out),spi_uart(out),multichannel(out),buttons_indicators(out)]


if __name__=='__main__':
    import sys
    target=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'assets'/'examples'
    for path in build(target):print(path)

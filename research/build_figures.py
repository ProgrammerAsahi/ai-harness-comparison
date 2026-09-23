#!/usr/bin/env python3
"""Author conceptual SVG diagrams; no third-party images or remote assets."""
import pathlib,html
D=pathlib.Path(__file__).resolve().parent.parent/'report/figures';D.mkdir(exist_ok=True)
def frame(title,w,h,body):
 return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title)}"><title>{html.escape(title)}</title><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="none" stroke="#508984" stroke-width="1.3"/></marker></defs><style>text{{font-family:system-ui,-apple-system,'PingFang SC','Microsoft YaHei',sans-serif}}.title{{font-size:19px;font-weight:600;fill:#142e39}}.label{{font-size:15px;fill:#233e48}}.small{{font-size:13px;fill:#59717a}}.edge{{fill:none;stroke:#508984;stroke-width:1.7;marker-end:url(#arrow)}}</style><rect width="100%" height="100%" rx="16" fill="#f3f7f6"/>{body}</svg>'''
def box(x,y,w,h,lines,accent=False):
 fill='#dceee9' if accent else '#fff';stroke='#85b8aa' if accent else '#cadbd8'
 s=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}"/>'
 start=y+h/2-(len(lines)-1)*11+5
 for i,line in enumerate(lines):s+=f'<text class="label" x="{x+w/2}" y="{start+i*22}" text-anchor="middle">{html.escape(line)}</text>'
 return s
def arrow(d,label=None,x=0,y=0):
 return f'<path class="edge" d="{d}"/>'+('' if not label else f'<text class="small" x="{x}" y="{y}" text-anchor="middle">{html.escape(label)}</text>')
def title(s):return f'<text class="title" x="24" y="34">{s}</text>'
b=title('一次任务：模型提出行动，运行时执行并核对')
for x,y,lines,a in [(30,70,['用户目标','与验收条件'],False),(260,70,['Harness','组织上下文'],True),(490,70,['模型','提出下一步'],False),(720,70,['权限','与执行检查'],False),(720,225,['文件、终端','浏览器等工具'],False),(490,225,['观察结果','记录状态'],True),(260,225,['验证结果','是否达标'],False),(30,225,['交付','可检查的成果'],False)]:b+=box(x,y,190,72,lines,a)
for d in ['M220 106 H258','M450 106 H488','M680 106 H718','M815 142 V223','M720 261 H682','M490 261 H452','M260 261 H222']:b+=arrow(d)
b+=arrow('M585 225 V182 H355 V144','继续工作',452,172)
b+='<text class="small" x="30" y="331">文件、历史、规则和检索材料按需进入上下文；交付前还要检验真实结果。</text>'
(D/'01-task-loop.svg').write_text(frame('任务执行循环',940,355,b))
b=title('一套代理方案可以分层选择')
labels=[['交互入口','终端、编辑器、网页、消息渠道'],['组织层','单代理、子任务、团队、固定流程'],['上下文与状态','规则、历史、检索、记忆、检查点'],['运行核心','模型调用、工具执行、纠错、停止'],['执行边界','权限、沙箱、容器、远程工作机'],['工具与数据','文件、浏览器、终端、业务应用']]
for i,ls in enumerate(labels):
 y=68+i*102;b+=box(35,y,530,76,ls,i in [2,3]);
 if i<5:b+=arrow(f'M300 {y+76} V{y+100}')
b+=box(615,340,255,110,['模型接口','Provider、协议、型号'],True)+arrow('M565 378 H613')+arrow('M615 414 H567')
b+='<text class="small" x="625" y="500">界面变化，不一定意味着</text><text class="small" x="625" y="522">代理核心或模型也变化。</text>'
(D/'02-layers.svg').write_text(frame('代理方案的分层结构',900,696,b))
b=title('上下文：不是全搬进去，而是按本轮需要组织')
b+=box(30,168,210,80,['原始材料','与完整历史'])
for y,ls in [(66,['检索的相关片段']),(154,['稳定的项目规则']),(242,['当前任务检查点']),(330,['近期工具交换'])]:
 b+=box(325,y,235,58,ls,True);b+=arrow(f'M240 208 H282 V{y+29} H323');b+=arrow(f'M560 {y+29} H602 V208 H645')
b+=box(648,168,235,80,['本轮模型上下文','决定下一步'])
b+='<text class="small" x="31" y="435">任务结果写回材料与检查点，供后续检索或恢复；磁盘里存在不等于模型本轮已经看到。</text>'
(D/'03-context.svg').write_text(frame('上下文组织',914,462,b))
b=title('多代理：交付仍要经过统一集成与验证')
b+=box(322,64,290,66,['主代理','统一需求与接口'],True)
for x,ls in [(25,['A：只读调查依赖','交回证据与结论']),(322,['B：独立工作树','实现后端']),(619,['C：按固定接口','实现前端'])]:
 b+=box(x,190,290,76,ls);b+=arrow(f'M467 130 V156 H{x+145} V188');b+=arrow(f'M{x+145} 266 V302 H467 V333')
b+=box(322,335,290,66,['主代理检查证据','合并变更'],True)
b+=box(322,447,290,66,['统一测试与审查','形成可交付结果'])+arrow('M467 401 V445')
b+='<text class="small" x="26" y="550">接口不清或多人争改同一文件时，增加代理可能增加返工。每个分支也会产生调用成本。</text>'
(D/'04-agents.svg').write_text(frame('多代理任务结构',940,578,b))
b=title('数据路径：本地界面不等于全链路本地')
b+=box(25,164,235,82,['本地文件','或企业资料'])+box(336,164,245,82,['Harness','实际运行位置'],True)+arrow('M260 205 H334')
for y,ls in [(60,['模型推理服务']),(176,['工具与连接器']),(292,['日志、会话与记忆'])]:
 b+=box(690,y,255,65,ls);b+=arrow(f'M581 205 H634 V{y+32} H688')
b+='<text class="small" x="28" y="410">每条路径都可能位于本机、内网或云端。自托管 Harness 只回答了其中一个位置问题。</text>'
(D/'05-data-flow.svg').write_text(frame('数据流向',975,442,b))
print('Authored 5 general SVG diagrams; profile diagrams are built by build_profiles.py')

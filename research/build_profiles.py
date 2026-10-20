#!/usr/bin/env python3
"""Assemble consistently structured, individually authored tool profiles."""
from pathlib import Path
import re, html, json
from editorial import read_baseline
from profile_expansions import PROFILES, AUTHORED_BASE
import profile_expansions_b
import profile_expansions_c
import profile_expansions_d
from profile_models import ROUTES
from profile_deepdives import DEEP
from profile_diagrams import draw_special
from profile_architecture import detail_markdown, build_detail
from profile_tiers import is_focus, headings

ROOT=Path(__file__).resolve().parent.parent
BASE=ROOT/'research/editorial-baseline'
OUT=ROOT/'report'
FIG=OUT/'figures/profiles'
FIG.mkdir(parents=True, exist_ok=True)
SHORT_NOTE='*简档：保留定位、总体结构和能力边界；上手命令、试用任务和模型路线不再随事实刷新维护，选型请参考[第 05 章的场景表](05-按场景选择组合.md)与[第 06 章的集中表](06-模型搭配与成本.md)。*'

def diagram(key, name, p):
    special=draw_special(key,name)
    if special:
        (FIG/(key+'.svg')).write_text(special)
        return
    def esc(s):return html.escape(s,quote=True)
    body=[]
    positions=[(30,75),(347,75),(664,75),(30,305),(347,305),(664,305)]
    for i,((x,y),label) in enumerate(zip(positions,p['flow'])):
        lines=label.split('\n')
        assert len(lines)==2,(key,label)
        assert all(len(s)<=24 for s in lines),(key,label)
        fill='#dceee9' if i in (1,3) else '#ffffff'
        body.append(f'<rect x="{x}" y="{y}" width="265" height="86" rx="10" fill="{fill}" stroke="#adc9bf"/>')
        for j,line in enumerate(lines):
            body.append(f'<text x="{x+132.5}" y="{y+35+j*25}" text-anchor="middle" font-size="15" fill="#24453c">{esc(line)}</text>')
    for d in ['M295 118 H344','M612 118 H661','M796 161 V302','M664 348 H615','M347 348 H298','M162 305 V238 H479 V164']:
        body.append(f'<path d="{d}" fill="none" stroke="#508984" stroke-width="1.7" marker-end="url(#arrow)"/>')
    body.append('<text x="255" y="225" font-size="13" fill="#58756b">结果回到当前任务</text>')
    kind='公开接口与文档中的责任分工' if p['kind'] in ('public','docs') else '公开源码与文档中的关键责任分工'
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 472" role="img" aria-label="{esc(key+' '+name+' 架构示意')}"><title>{esc(key+' '+name+' 架构示意')}</title><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="none" stroke="#508984" stroke-width="1.3"/></marker></defs><style>text{{font-family:system-ui,-apple-system,'PingFang SC','Microsoft YaHei',sans-serif}}</style><rect width="960" height="472" rx="16" fill="#f3f7f6"/><text x="30" y="35" font-size="19" font-weight="600" fill="#163d34">{esc(key+' · '+name)}</text>{''.join(body)}<text x="30" y="437" font-size="13" fill="#60796f">{kind}；图中能力不表示每种入口与安装方式都默认开放。</text></svg>'''
    (FIG/(key+'.svg')).write_text(svg)

def clean(s):
    s=re.sub(r'^\*\*[^*]+[。．]\*\*\s*','',s)
    return s.strip()

def split_baseline(key, body):
    body=body.split('\n---')[0].strip()
    if key=='A17':
        parts=dict(re.findall(r'^### (.+)\n([\s\S]*?)(?=^### |\Z)',body,re.M))
        intro=parts['定位、理念与源码血缘'].strip()
        arch=re.sub(r'```mermaid[\s\S]*?```\s*','',parts['一条任务怎样执行']).strip()
        # A17 is a short profile: the detailed capability notes (versions, commands, settings) stay in the
        # editorial baseline for traceability but are not rendered; profile_expansions.py carries the summary table.
        capabilities=''
        tail=parts['怎样开始，以及模型应该怎么配']
        model=tail[tail.index('**原生首选'):].strip().replace('第六章 Step 专项','第六章的模型与成本比较')
        return intro,arch,capabilities,'',model
    paragraphs=body.split('\n\n')
    intro=clean(paragraphs[0]);arch=[];how=[];model=[];mode='arch'
    for para in paragraphs[1:]:
        if para.startswith('下一步') or para.startswith('下一章'):continue
        if re.match(r'\*\*(怎样上手|怎样使用|使用方式|架构与使用)',para):mode='how'
        elif re.match(r'\*\*(模型|使用与模型|上手与模型)',para):mode='model'
        elif para.startswith('**'):mode='arch'
        {'arch':arch,'how':how,'model':model}[mode].append(clean(para))
    return intro,'\n\n'.join(arch),'','\n\n'.join(how),'\n\n'.join(model)

def assemble(key,title,body):
    p=PROFILES[key];name=title.split('：')[0];focus=is_focus(key)
    diagram(key,name,p)
    if focus:build_detail(key)
    intro,arch,caps,how,model=split_baseline(key,body)
    sections=[]
    sections.append(intro+'\n\n'+p['principle'])
    boundary='下图依据官方公开接口整理，表示责任分工，不代表已审计闭源内部实现。' if p['kind']=='public' else ('下图依据所引公开文档概括职责，不代表完整源码审计或对现有服务可用性的确认。' if p['kind']=='docs' else '下图结合所引源码与文档，画出本工具的主要责任分工；为便于理解，省略次要模块与错误分支。')
    sections.append(boundary+f'\n\n![{key} {name}：工作原理与责任分工](figures/profiles/{key}.svg)\n\n'+(arch.strip()+'\n\n' if arch.strip() else '')+p['mechanism']+('\n\n'+detail_markdown(key) if focus else ''))
    if p['rows']:
        table='| 观察项 | 实际机制／公开能力 | 对使用者意味着什么 |\n|---|---|---|\n'+'\n'.join('| '+' | '.join(r)+' |' for r in p['rows'])
        caps=(caps+'\n\n'+table).strip()
    sections.append(caps+('\n\n**把机制放进实际工作。**\n\n'+DEEP[key] if focus and key in DEEP else ''))
    if focus:
        sections+=operational_sections(key,p,model)
    sections.append(references(key,p,body,focus))
    assert all(s.strip() for s in sections),(key,[bool(s.strip()) for s in sections])
    lead='' if focus else SHORT_NOTE+'\n\n'
    return '<a id="'+key.lower()+'"></a>\n\n## '+key+' '+title+'\n\n'+lead+'\n\n'.join('### '+h+'\n\n'+s.strip() for h,s in zip(headings(key),sections))+'\n\n'

def operational_sections(key,p,model):
    sections=[]
    usage='\n\n'.join(f'{i}. {s}' for i,s in enumerate(p['steps'],1))
    sections.append(usage+'\n\n下面是启动命令或操作路线；路径、认证与功能入口请按自己的版本调整。\n\n```'+p['command']+'\n```')
    sections.append('下面是一份**可直接改写使用的试用任务**，属于本报告设计的验收示例，并非已完成的运行测试。\n\n> '+p['task']+'\n\n'+p['acceptance'])
    model_table='| 选择路线 | 候选组合 | 怎样决定 |\n|---|---|---|\n'+'\n'.join('| '+' | '.join(r)+' |' for r in ROUTES[key])
    if '{{m:' in model_table:
        model_table+='\n\n*表中具体型号核实于 {{date:facts}}；各家族的完整型号与限制见[第 06 章的集中表](06-模型搭配与成本.md)。*'
    sections.append((model+'\n\n'+model_table+'\n\n'+p['tradeoff']).strip())
    return sections

def references(key,p,body,focus):
    urls=[]
    for label,url in re.findall(r'\[([^\]]+)\]\((https?://[^)]+)\)',body+'\n'+p['sources']):
        if url not in [u for _,u in urls]:urls.append((label,url))
    selected=urls[:1]+urls[1:3]+urls[-1:] if len(urls)>3 else urls
    refs='、'.join(f'[{a}]({b})' for a,b in selected)
    scope='完整商业运行时未公开，结构判断以官方可见行为和接口为限。' if p['kind']=='public' else ('此处主要依据公开说明与维护声明，未重新安装验证旧版本的全部功能。' if p['kind']=='docs' else '源码链接指向固定提交；关键实现分析不等于对整个项目和依赖逐行审计。')
    tail='上面的流程建议与取舍是依据这些材料给出的选型判断；具体型号、权限和菜单以实际安装与账户为准。' if focus else '上面的结构与边界依据这些材料整理；当前安装方式、型号和菜单以官方最新文档为准。'
    return refs+'。\n\n'+scope+tail

def insert_authored(text,letter):
    # Profiles added after the baseline was frozen go after the group's last baseline profile.
    for key in sorted(k for k in AUTHORED_BASE if k[0]==letter):
        title,body=AUTHORED_BASE[key]
        last=list(re.finditer(r'^## '+letter+r'\d{2} .+$',text,re.M))[-1]
        nxt=re.compile(r'^(## |---)',re.M).search(text,last.end())
        at=nxt.start() if nxt else len(text)
        text=text[:at]+'## '+key+' '+title+'\n\n'+body+'\n\n'+text[at:]
    return text

counts=[]
for file in sorted(BASE.glob('03*.md')):
    text=read_baseline(file);focus_here=[]
    if file.name.startswith('03D'):
        text=re.sub(r'### Aider 为什么仍值得读[\s\S]*?(?=## 另外三种)',profile_expansions_d.HISTORY_BASE+'\n\n',text)
    text=insert_authored(text,file.name[2])
    def replace(m):
        key,title,body=m[1],m[2],m[3]
        if key not in PROFILES:return m[0]
        result=assemble(key,title,body)
        if is_focus(key):focus_here.append(key+' '+title.split('：')[0])
        counts.append({'id':key,'tier':'focus' if is_focus(key) else 'short','chinese_characters':len(re.findall('[\u4e00-\u9fff]',result))})
        return result
    text=re.sub(r'^## ([ABCDH]\d{2}) (.+)\n([\s\S]*?)(?=^## |\Z)',replace,text,flags=re.M)
    group=('本组的重点档案是 '+'、'.join(focus_here)+'，其余为简档。') if focus_here else '本组均为简档。'
    note='\n\n**档案读法：** 工具档案分两层。重点档案是作者自己日常使用、会持续复查的工具，按七个维度完整展开，包括下一层架构图、上手步骤、试用任务和模型路线；简档保留定位、总体结构和能力边界。分层只反映本报告的维护范围，不代表产品优劣或推荐强度。'+group+'代码块是命令或操作示例，不表示本报告已经运行全部工具。\n'
    first=text.index('\n<a id="')
    text=text[:first]+note+text[first:]
    (OUT/file.name).write_text(text)
(ROOT/'research/profile-coverage.json').write_text(json.dumps(counts,ensure_ascii=False,indent=2))
print(json.dumps({'expanded':len(counts),'min_characters':min(x['chinese_characters'] for x in counts),'max_characters':max(x['chinese_characters'] for x in counts)},ensure_ascii=False))

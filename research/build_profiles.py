#!/usr/bin/env python3
"""Assemble consistently structured, individually authored tool profiles."""
from pathlib import Path
import re, html, json
from profile_expansions import PROFILES
import profile_expansions_b
import profile_expansions_c
import profile_expansions_d
from profile_models import ROUTES
from profile_deepdives import DEEP
from profile_diagrams import draw_special

ROOT=Path(__file__).resolve().parent.parent
BASE=ROOT/'research/editorial-baseline'
OUT=ROOT/'report'
FIG=OUT/'figures/profiles'
FIG.mkdir(parents=True, exist_ok=True)
HEADINGS=['定位与设计理念','工作原理与架构图','能力、状态与边界','从安装到完成第一个任务','典型任务与验收方法','模型搭配、适用方向与取舍','资料依据与继续阅读']

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
        capabilities='\n\n'.join('**'+k+'。**\n\n'+parts[k].strip() for k in ['上下文、记录与长期工作','子代理、workflow、goal 和 cron 各自负责什么','权限、隔离与数据路径','扩展、迁移与静态网页交付'])
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
    p=PROFILES[key];name=title.split('：')[0]
    diagram(key,name,p)
    intro,arch,caps,how,model=split_baseline(key,body)
    sections=[]
    sections.append(intro+'\n\n'+p['principle'])
    boundary='下图依据官方公开接口整理，表示责任分工，不代表已审计闭源内部实现。' if p['kind']=='public' else ('下图依据所引公开文档概括职责，不代表完整源码审计或对现有服务可用性的确认。' if p['kind']=='docs' else '下图结合所引源码与文档，画出本工具的主要责任分工；为便于理解，省略次要模块与错误分支。')
    sections.append(boundary+f'\n\n![{key} {name}：工作原理与责任分工](figures/profiles/{key}.svg)\n\n'+arch+'\n\n'+p['mechanism'])
    if p['rows']:
        table='| 观察项 | 实际机制／公开能力 | 对使用者意味着什么 |\n|---|---|---|\n'+'\n'.join('| '+' | '.join(r)+' |' for r in p['rows'])
        caps=(caps+'\n\n'+table).strip()
    sections.append(caps+('\n\n**把机制放进实际工作。**\n\n'+DEEP[key] if key in DEEP else ''))
    usage='\n\n'.join(f'{i}. {s}' for i,s in enumerate(p['steps'],1))
    sections.append(usage+'\n\n下面是启动命令或操作路线；路径、认证与功能入口请按自己的版本调整。\n\n```'+p['command']+'\n```')
    sections.append('下面是一份**可直接改写使用的试用任务**，属于本报告设计的验收示例，并非已完成的运行测试。\n\n> '+p['task']+'\n\n'+p['acceptance'])
    model_table='| 选择路线 | 候选组合 | 怎样决定 |\n|---|---|---|\n'+'\n'.join('| '+' | '.join(r)+' |' for r in ROUTES[key])
    sections.append((model+'\n\n'+model_table+'\n\n'+p['tradeoff']).strip())
    urls=[]
    for label,url in re.findall(r'\[([^\]]+)\]\((https?://[^)]+)\)',body+'\n'+p['sources']):
        if url not in [u for _,u in urls]:urls.append((label,url))
    selected=urls[:1]+urls[1:3]+urls[-1:] if len(urls)>3 else urls
    refs='、'.join(f'[{a}]({b})' for a,b in selected)
    scope='完整商业运行时未公开，结构判断以官方可见行为和接口为限。' if p['kind']=='public' else ('此处主要依据公开说明与维护声明，未重新安装验证旧版本的全部功能。' if p['kind']=='docs' else '源码链接指向固定提交；关键实现分析不等于对整个项目和依赖逐行审计。')
    sections.append(refs+'。\n\n'+scope+'上面的流程建议与取舍是依据这些材料给出的选型判断；具体型号、权限和菜单以实际安装与账户为准。')
    assert all(s.strip() for s in sections),(key,[bool(s.strip()) for s in sections])
    return '<a id="'+key.lower()+'"></a>\n\n## '+key+' '+title+'\n\n'+'\n\n'.join('### '+h+'\n\n'+s.strip() for h,s in zip(HEADINGS,sections))+'\n\n'

counts=[]
for file in sorted(BASE.glob('03*.md')):
    text=file.read_text()
    if file.name.startswith('03D'):
        text=re.sub(r'### Aider 为什么仍值得读[\s\S]*?(?=## 另外三种)',profile_expansions_d.HISTORY_BASE+'\n\n',text)
    def replace(m):
        key,title,body=m[1],m[2],m[3]
        if key not in PROFILES:return m[0]
        result=assemble(key,title,body)
        counts.append({'id':key,'chinese_characters':len(re.findall('[\u4e00-\u9fff]',result))})
        return result
    text=re.sub(r'^## ([ABCDH]\d{2}) (.+)\n([\s\S]*?)(?=^## |\Z)',replace,text,flags=re.M)
    note='\n\n**档案读法：** 每个工具均按七个相同维度展开。架构图用于理解责任分工；上手步骤与任务卡用于实际试用。代码块是命令或操作示例，不表示本报告已经运行全部工具。\n'
    first=text.index('\n<a id="')
    text=text[:first]+note+text[first:]
    (OUT/file.name).write_text(text)
(ROOT/'research/profile-coverage.json').write_text(json.dumps(counts,ensure_ascii=False,indent=2))
print(json.dumps({'expanded':len(counts),'min_characters':min(x['chinese_characters'] for x in counts),'max_characters':max(x['chinese_characters'] for x in counts)},ensure_ascii=False))

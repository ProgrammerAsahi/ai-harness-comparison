"""Tailored structural diagrams for architectures not captured by one local loop."""
from html import escape

def draw_special(key,name):
    nodes=[];edges=[];notes=[];extra='';height=600
    def node(x,y,a,b,accent=False):
        nodes.append((x,y,a,b,accent))
    def edge(d):edges.append(d)
    if key in ['B06','B17','B18','C05']:
        front={'B06':'Zed 编辑器','B17':'Neovim／Avante','B18':'Neovim／CodeCompanion','C05':'Cherry 桌面'}[key]
        direct={'B06':'Zed 自有 Agent','B17':'Lua 直接模型路线','B18':'HTTP Adapter 路线','C05':'普通对话 Provider'}[key]
        external='Agent 驱动路线' if key=='C05' else 'ACP 外部代理路线'
        node(30,75,front,'用户、文件与会话')
        node(347,75,'宿主界面与会话管理','统一展示与输入',True)
        node(30,270,direct,'模型及对应工具能力')
        node(347,270,external,'连接完整执行后端',True)
        node(664,270,'后端自己的配置','认证、模型与权限')
        node(347,455,'结果回到宿主','展示、审阅与后续工作',True)
        for d in ['M295 118 H344','M400 161 V220 H162 V267','M479 161 V267','M612 313 H661','M162 356 V498 H344','M796 356 V498 H615']:edge(d)
        notes=['两条路线可以共享界面，但不自动共享认证、工具、历史恢复和计费。']
    elif key=='C02':
        node(30,75,'手机／桌面／消息渠道','身份、配对与输入')
        node(347,75,'Gateway','连接与会话路由',True)
        node(664,75,'会话队列','顺序、取消与运行所有权')
        node(347,270,'选定代理运行时','模型与工具循环',True)
        node(30,270,'模型服务','按后端配置')
        node(664,270,'工具与工作空间','宿主或显式沙箱')
        node(347,455,'历史与记忆持久化','确认当前运行可写回',True)
        for d in ['M295 118 H344','M612 118 H661','M796 161 V215 H479 V267','M347 313 H298','M612 313 H661','M479 356 V452','M347 498 H15 V205 H430 V164']:edge(d)
        notes=['持续连接、代理执行与状态写入是不同责任；自托管不自动提供工具隔离。']
    elif key in ['D01','D02','C09']:
        label={'D01':'应用输入／API','D02':'事件／计划／Webhook','C09':'工作空间资料与问题'}[key]
        main={'D01':'Workflow 图执行','D02':'业务工作流引擎','C09':'Agent／Flow 入口'}[key]
        node(30,75,label,'带明确输入与变量')
        node(347,75,main,'顺序、分支与任务状态',True)
        node(664,75,'输出或下一节点','交付、人工处理或结束')
        node(30,270,'模型与检索服务','提供判断及相关材料')
        node(347,270,'需要自治的局部步骤','模型与工具往返',True)
        node(664,270,'业务／资料工具','查询、计算与操作')
        node(347,455,'执行结果与错误状态','返回外层流程',True)
        for d in ['M295 118 H344','M612 118 H661','M479 161 V267','M347 313 H298','M612 313 H661','M796 356 V498 H615','M479 455 V359','M612 520 H945 V210 H545 V164']:edge(d)
        notes=['外层流程管理固定步骤；局部 Agent 处理需要探索的部分，二者不应混为一层。']
    elif key in ['A15','B03','B13','B20']:
        height=665
        front={'A15':'Canvas／CLI／调用方','B03':'Desktop／云端任务入口','B13':'Replit 需求与项目入口','B20':'GitHub／Jules／API'}[key]
        environment={'A15':'工作空间：本机／容器／集群','B03':'本地／托管／Outposts 环境','B13':'平台托管的应用环境','B20':'云端虚拟机环境'}[key]
        extra=f'<rect x="325" y="205" width="615" height="253" rx="14" fill="#edf4f0" stroke="#8ab2a1" stroke-dasharray="6 5"/><text x="640" y="430" font-size="13" fill="#4e7465">{escape(environment)}</text>'
        node(30,75,front,'任务与用户反馈')
        node(347,75,'会话与环境管理','准备、启动与跟踪',True)
        node(664,75,'模型服务或代理后端','按产品／运行时配置')
        node(347,280,'执行代理','使用当前项目与任务',True)
        node(664,280,'文件、进程与工具','依赖、运行及检查')
        node(347,520,'持久保存的成果','补丁、日志、文件与审查',True)
        for d in ['M295 118 H344','M479 161 V277','M796 161 V190 H560 V277','M612 323 H661','M479 366 V517','M347 563 H162 V164']:edge(d)
        notes=['回收工作环境前保存成果；界面、模型与工作机可以位于不同位置。']
    elif key in ['B08','C06']:
        height=655
        front='Auggie／IDE／其他代理' if key=='B08' else '用户与网页入口'
        knowledge='代码仓库及相关项目' if key=='B08' else '工作空间资料与知识库'
        context='Context Engine 检索' if key=='B08' else '后端权限与检索组织'
        node(30,75,knowledge,'材料范围与更新')
        node(347,75,'索引与相关材料检索','找到本次需要的片段',True)
        node(664,75,front,'问题与身份')
        node(347,275,context,'按范围提供上下文',True)
        node(664,275,'模型／执行代理','理解材料并决定行动')
        node(30,275,'可用项目或业务工具','按部署启用')
        node(347,505,'回答、引用或代码产物','核对来源与实际结果',True)
        for d in ['M295 118 H344','M664 118 H615','M479 161 V272','M612 318 H661','M664 340 H635 V460 H15 V318 H27','M162 361 V548 H344','M796 361 V548 H615']:edge(d)
        notes=['检索质量与执行能力分别评价；资料已入库，不表示关键片段一定进入本轮上下文。']
    else:return None
    body=[extra]
    for x,y,a,b,accent in nodes:
        fill='#dceee9' if accent else '#fff'
        body.append(f'<rect x="{x}" y="{y}" width="265" height="86" rx="10" fill="{fill}" stroke="#adc9bf"/>')
        for i,line in enumerate([a,b]):body.append(f'<text x="{x+132.5}" y="{y+35+i*25}" text-anchor="middle" font-size="15" fill="#24453c">{escape(line)}</text>')
    for d in edges:body.append(f'<path d="{d}" fill="none" stroke="#508984" stroke-width="1.7" marker-end="url(#arrow)"/>')
    body.append(f'<text x="30" y="{height-23}" font-size="13" fill="#60796f">{escape(notes[0])}</text>')
    label=escape(key+' · '+name)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {height}" role="img" aria-label="{label} 架构示意"><title>{label} 架构示意</title><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="none" stroke="#508984" stroke-width="1.3"/></marker></defs><style>text{{font-family:system-ui,-apple-system,\'PingFang SC\',\'Microsoft YaHei\',sans-serif}}</style><rect width="960" height="{height}" rx="16" fill="#f3f7f6"/><text x="30" y="35" font-size="19" font-weight="600" fill="#163d34">{label}</text>{"".join(body)}</svg>'

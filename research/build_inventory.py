#!/usr/bin/env python3
import pathlib,json,csv
ROOT=pathlib.Path(__file__).resolve().parent.parent
R=ROOT/'research'
rows=[]
for p in sorted((R/'repos').iterdir()):
 if not (p/'manifest.json').exists():continue
 m=json.loads((p/'manifest.json').read_text());a=json.loads((p/'metadata.json').read_text())
 rows.append({'id':p.name,'repository':m['repo'],'sha':m['sha'],'retrieved_at':m['retrieved_at'],'stars':a['stargazers_count'],'pushed_at':a['pushed_at'],'archived':a['archived'],'license_metadata':(a.get('license') or {}).get('spdx_id','unknown'),'inventory_files':len(json.loads((p/'tree.json').read_text())),'captured_files':len(m['files']),'url':'https://github.com/'+m['repo']})
with (R/'repository-snapshot.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(R/'repository-snapshot.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
catalog=[
('A01','Claude Code','claude-code','模型原生代理；商业核心未完整公开'),('A02','Codex','codex','公开 Rust 核心＋不同产品入口'),('A03','Gemini CLI','gemini-cli','Gemini 原生终端代理'),('A04','Qwen Code','qwen-code','Qwen 原生＋多协议'),('A05','Kimi Code','kimi-code','当前 TypeScript 核心，区别于旧 kimi-cli'),('A06','MiMo Code','mimo-code','模型特定工具与任务状态'),('A07','DeepSeek Harness','deepseek-harness','开发者预览；插件化执行核心'),('A08','OpenCode','opencode','多模型、多入口的开放代理'),('A09','Pi','pi','可扩展核心；默认无内置权限系统'),('A10','Cline','cline','扩展／CLI／SDK；团队能力按入口区分'),('A11','Kilo Code','kilo','当前核心具有 OpenCode 结构'),('A12','Goose','goose','工具扩展中心；仓库已迁移'),('A13','Crush','crush','Go 实现的终端代理'),('A14','Mistral Vibe','vibe','Mistral 官方代理；厂商生态补充'),('A15','OpenHands','openhands','主仓库为 Canvas，执行 SDK 另列'),('A16','Grok Build','grok-build','公开 Rust 运行时；内部大仓同步'),
('A17','Step Code','step-code','Pi 派生、Step 原生；用户指定新发布候选，成熟度待验证'),
('B01','Cursor','https://cursor.com/docs/agent/overview','编辑器、Agent 与后台工作'),('B02','GitHub Copilot','https://docs.github.com/en/copilot','IDE／CLI／云端入口分别评估'),('B03','Devin／Devin Desktop','https://docs.devin.ai/','Windsurf 文档已迁入；本地与云端分开'),('B04','Kiro','https://kiro.dev/docs/how-kiro-works/','Spec 与统一跨界面 Harness'),('B05','JetBrains Junie','https://junie.jetbrains.com/','IDE 代码理解与任务执行'),('B06','Zed','zed','开放编辑器＋自有／外部代理'),('B07','TRAE／SOLO','https://www.trae.ai/','商业产品，不等于 trae-agent 研究仓库'),('B08','Augment／Auggie','https://docs.augmentcode.com/','项目上下文与跨仓库检索'),('B09','Amp','https://ampcode.com/docs','档位、专家分工与远程环境'),('B10','Factory Droid','https://docs.factory.ai/','Droid 与 Missions'),('B11','Warp／Automation Platform','https://docs.warp.dev/','终端、原生代理、平台三层'),('B12','Google Antigravity','https://www.antigravity.google/docs/agent','代码、浏览器、产物与任务'),('B13','Replit Agent','https://docs.replit.com/replitai/agent','托管应用开发与部署'),('B14','Qoder','https://docs.qoder.com/','项目知识、Quest 与多模型'),('B15','CodeBuddy','https://www.codebuddy.cn/docs/','中文生态；地区与入口需区分'),('B16','ZCode','https://zcode.z.ai/en/docs/agents','GLM 原生长任务；生态补充候选'),
('B17','Avante.nvim','avante','Neovim：直接模型与 ACP 代理'),('B18','CodeCompanion.nvim','codecompanion','Neovim：HTTP 模型／ACP 代理双路径'),('B19','Tabnine Agent','https://docs.tabnine.com/main/getting-started/tabnine-agent','企业开发助手、工具权限和模型治理'),('B20','Google Jules','https://jules.google/docs','云端异步编码；当前文档标记实验性质'),
('C01','Hermes Agent','hermes','会话检索、记忆、Skills 与自动化'),('C02','OpenClaw','openclaw','Gateway、渠道、设备与持续服务'),('C03','Agent Zero','agent-zero','通用计算环境与上下级代理'),('C04','Chatbox AI','chatbox','聊天＋工作模式；商业与社区版区分'),('C05','Cherry Studio','cherry-studio','桌面工作台＋多种代理驱动'),('C06','Open WebUI','open-webui','自托管门户、知识与可选执行能力'),('C07','LibreChat','librechat','共享对话产品＋Agent Builder'),('C08','LobeHub','lobehub','有状态的 Agent 与协作工作台'),('C09','AnythingLLM','anythingllm','资料工作空间、检索与 Flow'),
('D01','Dify','dify','相邻：AI 应用与工作流'),('D02','n8n','n8n','相邻：业务自动化与 Agent 节点'),('D03','mini-SWE-agent','mini-swe-agent','相邻：研究与评测'),('D04','SWE-agent','swe-agent','转移重点：官方建议新用 mini'),('D05','Oh My OpenAgent／OmO','oh-my-openagent','相邻：叠加编排与扩展体系')]
byid={x['id']:x for x in rows}
paths={'A':'03A-终端与开放编程代理.md','B':'03B-编辑器与托管工作台.md','C':'03C-个人助理与知识工作台.md','D':'03D-相邻路线与维护观察.md'}
head='''# 02｜全景清单：哪些值得纳入，哪些需要保留判断

本报告建立了 **46 个核心工具／产品家族的档案**，另列 **5 个相邻或转移开发重点的项目**，以及 **4 个维护观察／历史项目**。它是一份有明确范围的主流候选地图，不宣称已经穷尽全网，也不把同一产品的 IDE、CLI、桌面端重复计数。

## 2.1 怎样判断“主流且在维护”

对有公开仓库的项目，优先看社区关注度、近期开发、当前文档与维护者声明。约五千以上 GitHub 星数、近九十天有活动是有用的初筛线索，但不是机械门槛：Mistral Vibe 属于明确的模型厂商官方路线；新 SDK 的低星数也不代表其所服务的整个产品缺少用户。

**星数是关注度，不是活跃用户数。** 本报告没有各产品月活、付费用户或留存的统一可比数据。对于商业产品，以持续开放的官方产品、文档、更新与开发生态作为候选依据；未能独立核验用户规模的产品，不能据此声称与最大平台同量级。ZCode 等厂商生态产品纳入是为了补全路线，不是在认证市场份额。

维护判断的优先顺序是：**明确维护声明／迁移说明 → 实际代码与版本活动 → 最后推送时间**。单纯“昨天有 push”可能只是文档或归档准备；反过来，旧仓库归档也可能是迁移。

Step Code 为 9 月 23 日应用户要求补充的新发布官方产品；目前关注规模未达到上述常用初筛线，不据此认定已拥有大量稳定用户。原有产品保留 9 月 22 日基线，本次未全面重新抓取。

## 2.2 核心清单

以下星数、推送日期是抓取时的快照，日期为 UTC。它们没有经过热度加权，也没有拿来计算产品质量总分。商业产品的“未核验”表示没有统一公开使用量证据，不等于用户少。每组详情链接内有对应编号。
'''
parts=[head]
for group,title in [('A','终端与开放编程代理'),('B','编辑器与托管工作台'),('C','个人助理与知识工作台'),('D','相邻路线与转移重点')]:
 parts.append(f'\n### {group}｜{title}\n\n[阅读本组详细档案]({paths[group]})\n\n| 编号 | 工具／产品家族 | 关注度与活动证据 | 定位与当前边界 |\n|---|---|---|---|\n')
 for code,name,key,note in catalog:
  if not code.startswith(group):continue
  if key in byid:
   r=byid[key];url=r['url'];ev=f"{r['stars']:,} ★；推送 {r['pushed_at'][:10]}"
  else:url=key;ev='官方产品与文档；使用量未独立核验'
  parts.append(f'| {code} | [{name}]({url}) | {ev} | {note} |\n')
parts.append('''
## 2.3 维护观察与历史条目

| 项目 | 本次状态 | 是否作为新用户的活跃首选 |
|---|---|---|
| Continue | README 明确不再积极维护，最终 2.0.0；元数据仍有近期推送 | 否 |
| Roo Code | 仓库归档，官方 README 写扩展已关闭 | 否 |
| Aider | 未归档；快照最后推送 2026-05-22 | 维护观察，先核实当前适配 |
| bytedance/trae-agent | 快照最后推送 2026-02-05；不等于商业 TRAE | 研究参考，不当作商业产品现状 |

[维护声明与架构价值详见 03D](03D-相邻路线与维护观察.md)。所有仓库的完整提交、精确时间、许可证元数据与目录规模保存在[CSV](../research/repository-snapshot.csv)和[JSON](../research/repository-snapshot.json)。

## 2.4 容易被重复计数或混淆的名字

| 名称关系 | 本报告处理方式 |
|---|---|
| Codex CLI、应用、编辑器入口 | 作为产品家族，逐项提醒能力和权限差异 |
| Copilot 补全、IDE Agent、CLI、云端代理 | 不能当同一运行环境；合并介绍，分场景比较 |
| Windsurf／Devin Desktop／Cascade | 按当前迁移后的文档辨认，不重复当独立市场份额 |
| Kimi CLI 旧仓库与 Kimi Code | 以新仓库为当前架构依据 |
| OpenHands 主仓库与 SDK | 两者均采集；前者不能代替引擎审查 |
| Pi 旧组织与当前组织 | 使用重定向后的正式仓库 |
| Pi 与 Step Code | Step Code 明确派生自 Pi；产品配置、权限与默认模型分别研究 |
| Cline／Roo／Kilo 的历史关系 | 仅作为历史，不假定今天的核心和功能完全相同 |
| Chatbox／Cherry 的聊天模式与代理模式 | 分开理解，避免用旧版能力否定当前执行能力 |

## 2.5 本报告没有做成同等级深读的范围

原生托管办公与研究产品、特定写作客户端、纯模型服务工具和开发框架，在相关章节作为相邻路线说明。没有充分公开证据或运行时未开放的产品，不编造内部架构；已停止维护的小项目也不为凑数量收进主推荐表。

因此，这份清单适合建立主流选型地图和找到下一步验证对象。若目标是采购、组织级迁移或完整安全审计，还需要针对短名单补充实际测试、合同／账户条件与部署检查。
''')
(ROOT/'report/02-全景清单.md').write_text(''.join(parts))
(R/'catalog.json').write_text(json.dumps([{'id':a,'name':b,'source':c,'note':d,'chapter':paths[a[0]]} for a,b,c,d in catalog],ensure_ascii=False,indent=2))
print('repositories',len(rows),'catalog',len(catalog))

#!/usr/bin/env python3
"""MIT. Original method diagrams; all numerical examples are synthetic."""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "studies/harness-quantification/figures"
OUT.mkdir(parents=True, exist_ok=True)


class Diagram:
    def __init__(self, name, title, subtitle, height=550):
        self.name, self.height = name, height
        self.parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {height}" role="img" aria-labelledby="{name}-title {name}-desc">
<title id="{name}-title">{escape(title)}</title><desc id="{name}-desc">{escape(subtitle)}</desc>
<style>
text{{font-family:system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;fill:var(--figure-ink,#203e3a)}}
.bg{{fill:var(--figure-bg,#f5f9f8)}}.box{{fill:var(--figure-box,#e5efed);stroke:var(--figure-line,#547870);stroke-width:1.5}}
.accent{{fill:var(--figure-accent,#145f55)}}.accent-text{{fill:var(--figure-on-accent,#fff)}}
.muted{{fill:var(--figure-muted,#536a64)}}.line{{stroke:var(--figure-line,#547870);stroke-width:2;fill:none}}
.warm{{fill:var(--figure-warm,#f4e7cf)}}.dash{{stroke-dasharray:7 6}}
</style><rect class="bg" width="1000" height="{height}" rx="18"/>
<defs><marker id="{name}-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="accent" d="M0 0 L10 5 L0 10Z"/></marker></defs>''']
        self.text(34, 48, title, 27, bold=True)
        self.text(34, 82, subtitle, 17, css="muted")

    def text(self, x, y, value, size=19, css="", anchor="start", bold=False):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" class="{css}" text-anchor="{anchor}" font-weight="{700 if bold else 400}">{escape(value)}</text>')

    def box(self, x, y, w, h, title, lines=(), accent=False):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="13" class="{"accent" if accent else "box"}"/>')
        css = "accent-text" if accent else ""
        self.text(x + 18, y + 33, title, 21, css=css, bold=True)
        for i, line in enumerate(lines):
            self.text(x + 18, y + 65 + i * 28, line, 17, css=css)

    def line(self, x1, y1, x2, y2, arrow=True, dash=False):
        marker = f' marker-end="url(#{self.name}-arrow)"' if arrow else ""
        self.parts.append(f'<path class="line{" dash" if dash else ""}" d="M{x1} {y1} L{x2} {y2}"{marker}/>')

    def circle(self, x, y, label, radius=21):
        self.parts.append(f'<circle class="accent" cx="{x}" cy="{y}" r="{radius}"/>')
        self.text(x, y + 7, label, 18, css="accent-text", anchor="middle", bold=True)

    def save(self):
        (OUT / f"{self.name}.svg").write_text("\n".join(self.parts) + "\n</svg>\n", encoding="utf-8")


d = Diagram("01-three-questions", "三种问题，三张地图", "架构接近、适合任务和实际做得好，需要不同输入与验证。", 540)
for x, title, inputs, outputs in [
    (35, "结构相似", ["组件、控制、状态", "权限、上下文、扩展"], ["差异矩阵与近邻", "解释机制哪里相同"]),
    (360, "场景适合", ["任务需求与硬约束", "用户效用与偏好"], ["候选集与取舍", "解释为何值得试用"]),
    (685, "运行表现", ["固定环境和任务", "模型、预算与重复运行"], ["效果、成本与失败", "说明在哪些条件下成立"]),
]:
    d.box(x, 120, 280, 128, title, inputs)
    d.line(x + 140, 250, x + 140, 292)
    d.box(x, 305, 280, 127, "得到的结果", outputs, accent=True)
d.text(500, 489, "关联三张地图，分别保留证据与解释。", 22, anchor="middle", bold=True)
d.save()

d = Diagram("02-feature-hierarchy", "大维度分预算，小字段给证据", "示意：九组等权时每组占 1/9；拆字段不会增加整组权重。", 570)
d.box(335, 113, 330, 81, "架构比较：总预算 100%")
d.line(500, 194, 245, 243)
d.line(500, 194, 745, 243)
d.box(45, 253, 400, 99, "状态与恢复：1/9", ["持久化、恢复控制、状态范围、回退"])
d.box(555, 253, 400, 99, "其余八组：合计 8/9", ["控制、边界、调用、上下文等"])
for x, label in [(45, "F17"), (150, "F18"), (255, "F19"), (360, "F20")]:
    d.line(245, 352, x + 43, 392)
    d.box(x, 403, 85, 73, label)
d.text(245, 511, "每项 1/36 → 每项都关联具体证据", 19, anchor="middle")
d.text(748, 416, "若一组拆成八项", 22, anchor="middle", bold=True)
d.text(748, 455, "每项可分 1/72，组预算仍为 1/9", 19, anchor="middle")
d.save()

d = Diagram("03-missing-range", "未知不会消失：它扩大可确定的范围", "虚构例子：四项等权，三项已知；已知部分差异约 0.333。", 490)
d.box(35, 117, 290, 118, "已知贡献", ["0.25 × (0 + 0.5 + 0.5)", "= 0.25"])
d.box(355, 117, 290, 118, "未知重量", ["1 − 0.75 = 0.25", "可能贡献 0 到 0.25"])
d.box(675, 117, 290, 118, "完整差异范围", ["最小 0.25，最大 0.50", "这是逻辑边界，不是置信区间"], accent=True)
d.line(100, 335, 900, 335, arrow=False)
for value in (0, 0.25, 0.5, 0.75, 1):
    x = 100 + 800 * value
    d.line(x, 327, x, 343, arrow=False)
    d.text(x, 376, str(value), 19, anchor="middle")
d.parts.append('<rect class="warm" x="300" y="306" width="200" height="18" rx="8"/>')
d.circle(300, 335, "", 7)
d.circle(500, 335, "", 7)
d.text(500, 432, "覆盖率 75% 与差异值必须一起呈现。", 22, anchor="middle", bold=True)
d.save()

d = Diagram("04-axis-limit", "三个等距对象，不能无损压成一条直线", "示意距离均为 1；一维展示需要说明横轴的具体含义。", 565)
for a, b in [((160, 155), (65, 318)), ((160, 155), (255, 318)), ((65, 318), (255, 318))]:
    d.line(*a, *b, arrow=False)
for x, y, label in [(160, 155, "甲"), (65, 318, "乙"), (255, 318, "丙")]:
    d.circle(x, y, label)
d.text(79, 231, "1")
d.text(239, 231, "1")
d.text(160, 352, "1", anchor="middle")
d.text(160, 397, "二维可表示等边关系", 18, anchor="middle")
d.line(430, 270, 895, 270, arrow=False)
for x, label in [(430, "甲"), (662, "乙"), (895, "丙")]:
    d.circle(x, 270, label)
d.text(546, 237, "1", anchor="middle")
d.text(779, 237, "1", anchor="middle")
d.text(662, 329, "两端距离变成 2", 23, anchor="middle", bold=True)
d.text(662, 372, "不可能同时让三对距离都保持为 1", 19, anchor="middle")
d.box(35, 442, 930, 87, "可用的一维轴", ["场景效用分数 ｜ 到选定参照的距离 ｜ 标明误差的一维近似投影"])
d.save()

d = Diagram("05-joint-system", "组合的有效能力，需要整条链路成立", "规格描述可行性；任务轨迹和验收才提供行为与效果证据。", 600)
d.box(35, 121, 280, 126, "H：Harness 配置", ["控制、状态与工具", "选定版本和开启机制"])
d.box(360, 121, 280, 126, "K：适配层", ["协议转换、错误处理", "哪些能力被保留或降级"])
d.box(685, 121, 280, 126, "M：模型端点", ["型号、渠道与参数", "接口能力与调用限制"])
d.line(315, 181, 355, 181)
d.line(680, 181, 645, 181)
d.line(500, 248, 500, 299)
d.box(245, 310, 510, 104, "T：任务、环境、预算与验收", ["共同决定这次组合运行的条件"])
d.line(500, 414, 500, 455)
d.box(245, 466, 510, 96, "Y：结果与过程", ["产物、成功、费用、耗时、恢复与失败"], accent=True)
d.save()

d = Diagram("06-interaction", "搭配优势可以交叉", "全部为虚构数据：示意同一个 Harness 对不同模型的优势不相同。", 560)
d.text(175, 139, "模型甲", 20, anchor="middle", bold=True)
d.text(455, 139, "模型乙", 20, anchor="middle", bold=True)
points = [(175, 195, "80%"), (455, 345, "50%"), (175, 295, "60%"), (455, 220, "75%")]
d.line(175, 195, 455, 345, arrow=False)
d.line(175, 295, 455, 220, arrow=False, dash=True)
for x, y, label in points:
    d.circle(x, y, "", 6)
    d.text(x, y - 16, label, 20, anchor="middle")
d.text(308, 405, "实线：Harness A　虚线：Harness B", 18, anchor="middle")
d.box(580, 145, 385, 145, "先有可比的组合矩阵", ["同任务、环境与预算规则", "足够交叉与重复运行", "缺测格子保持缺测"])
d.box(580, 324, 385, 134, "再估计交互与不确定性", ["用交叉实验识别搭配效应", "用运行结果估计成功率"], accent=True)
d.text(500, 514, "这是方法示意，不是产品排名或实测趋势。", 21, anchor="middle", bold=True)
d.save()
print(f"Built {len(list(OUT.glob('*.svg')))} original method diagrams")

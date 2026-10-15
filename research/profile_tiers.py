"""Profile tiers: which tools keep a full, maintained profile.

Focus profiles are the tools wired into the author's daily agent workflow; they keep
all seven sections and the lower-level architecture diagrams. Every other tool gets a
short profile. Generator data for the omitted sections stays in place, so promoting a
tool is a one-line change here (refresh its commands, task and model route first).
"""
FOCUS=('A01','A02','A05','A06','A07','A08','B12')
FULL_HEADINGS=['定位与设计理念','工作原理与架构图','能力、状态与边界','从安装到完成第一个任务','典型任务与验收方法','模型搭配、适用方向与取舍','资料依据与继续阅读']
SHORT_HEADINGS=['定位与设计理念','工作原理与架构图','能力、状态与边界','资料依据与继续阅读']

def is_focus(key):return key in FOCUS
def headings(key):return FULL_HEADINGS if is_focus(key) else SHORT_HEADINGS

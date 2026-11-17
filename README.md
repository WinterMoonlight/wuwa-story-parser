# 鸣潮剧情解析

从 FModel 导出的 ConfigDB 还原任务对白，生成按任务和章节组织的 JSON 与 TXT 基础语料。解析器保留文本来源、选择、说话人和缺口，阅读版支持女漂泊者与统一玩家名“漂泊者”。

[快速开始](#快速开始) · [当前状态](#当前状态) · [命令参考](docs/commands.md) · [项目架构](docs/architecture.md) · [开发与换机](docs/handoff.md)

## 快速开始

需要 Python 3.10+。运行时使用标准库，当前数据验证环境为 Windows / Python 3.13。

```powershell
git clone https://github.com/WinterMoonlight/wuwa-story-parser.git
cd wuwa-story-parser
```

将同版本完整 `ConfigDB/` 放到项目根目录，保留 `zh-Hans/` 与 `Misc/` 子目录。外部数据库可通过环境变量配置。

```powershell
$env:WUWA_CONFIG_DB = 'D:\GameData\ConfigDB'

# 按章节生成全部任务、覆盖报告和阻塞清单
python run.py export-reading-batch

# 单任务阅读草稿
python run.py export-recap --quest-id 139000027 --output outputs/sample
```

批量结果位于 `outputs/主线批量/<批次>/覆盖阅读版/`，每任务一份 JSON 和同名 TXT。输入结构见[数据库说明](docs/database-guide.md)。

## 当前状态

下列结果对应 3.8.11 本地快照，最近语料批次为 `20261117_132957_607004`。

|项目|结果|
|---|---:|
|任务记录|135|
|有文字的记录|132|
|所选路线 / 部分有序|12 / 1|
|回顾草稿 / 候选材料|60 / 62|
|回顾解析阻塞|16任务、27处|
|严格整任务导出通过|2|
|最近解析回归测试|304项通过|

三项连续阅读样本《万象新声·上》《万象新声·下》《嘤鸣初相召》评为“带明确缺口可阅读”。模拟领域1505仍有14条候选对白待确认顺序。路线中断、缺口和阅读验收采用不同统计口径，详见[当前进度](progress.md)和[验收标准](docs/reading-acceptance.md)。

下一步先汇总任务路线与回顾区段的全部阻塞，优先处理现有配置能够验证且影响较多任务的问题。项目当前聚焦解析器和基础语料。

## 输出内容

- JSON 保存原文、文本ID、动作和条件、身份来源、所选路线与验证状态。
- TXT 展示对白、选择、小游戏文本与简短缺口说明，未定位内容带有范围说明。
- 姓名按配置关联。明确空名称显示“无署名”，匿名人物保留问号。
- 阅读顺序来自回顾或明确调用证据。原始数据库以只读方式访问。
- 原始数据、生成语料、临时研究文件及本地技能由 `.gitignore` 排除，换机时单独恢复。

格式定义见[语料格式](docs/corpus-format.md)，当前工具能力和限制见[架构](docs/architecture.md)。

## 开发

```powershell
# 安装后也可使用 wuwa-story 命令
python -m pip install -e .

# 结构、文档链接、Python语法检查
python scripts/check_project.py

# 完整测试需要同版本ConfigDB
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
```

## 目录

```text
run.py                  源码运行入口
src/wuwa_story/         解析、关联、阅读渲染与命令行实现
tests/                  单元与本地快照回归测试
scripts/                项目维护工具
docs/                   当前使用、架构和开发指南
  research/             专题取证与历次阅读验收报告
  reviews/              绑定源文件哈希的阅读审查记录
  history/              完整历史规划、发现与进度
task_plan.md            当前目标与下一步
progress.md             当前验证状态
findings.md             继续开发所需的关键结论
ConfigDB/               本地原始数据
outputs/                本地生成语料
work/                   临时探查、日志与缓存
```

[文档目录](docs/README.md)收录当前指南与历史研究入口。[仓库管理说明](docs/repository.md)说明提交范围。

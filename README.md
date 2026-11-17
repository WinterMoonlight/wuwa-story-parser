# 鸣潮剧情解析 · Wuwa Story Parser

[![Source checks](https://github.com/WinterMoonlight/wuwa-story-parser/actions/workflows/ci.yml/badge.svg)](https://github.com/WinterMoonlight/wuwa-story-parser/actions/workflows/ci.yml)

把本地 ConfigDB 中分散的任务、对白、人物和回顾配置，整理为**每任务一份 JSON 与 TXT**的剧情基础语料。

[快速开始](#快速开始) · [当前进度](#当前进度) · [命令参考](docs/commands.md) · [开发指南](docs/handoff.md)

> [!NOTE]
> 本仓库提供解析器和文档，不附带游戏数据库、客户端脚本、资产或完整剧情语料。你需要自行准备同一版本的 ConfigDB。示例中的文字为虚构内容。

## 可以做什么

- 关联任务、剧情回顾、流程状态、说话人和语言文本，按章节批量导出。
- 输出可阅读的对白、选择与简短缺口说明；JSON保留原始引用、条件、动作与证据。
- 优先使用任务调用关系，结合已核查的回顾、实体和玩法关联恢复顺序。
- 统一玩家名为“漂泊者”，选择女性属性；身份无法确认时保留问号。
- 区分完整的有序草稿、带缺口草稿、局部片段和暂无有序正文，避免把提取成功当作顺序正确。

项目当前聚焦解析器与基础语料。知识库、知识图谱和剧情推理不在本仓库当前范围内。

## 快速开始

需要 **Python 3.10+**，解析运行时仅使用标准库。

```shell
git clone https://github.com/WinterMoonlight/wuwa-story-parser.git
cd wuwa-story-parser
python run.py --help
```

把同一版本的数据库放到项目根目录 `ConfigDB/`，保留 `zh-Hans/`、`Misc/` 子目录。也可以在 PowerShell 中指定外部目录：

```powershell
$env:WUWA_CONFIG_DB = 'D:\GameData\ConfigDB'

# 导出单个任务
python run.py export-recap --quest-id 168850009 --output outputs/sample

# 按章节导出并生成覆盖、顺序和阅读报告
python run.py export-reading-batch
```

可选安装命令入口：`python -m pip install -e .`，之后可使用 `wuwa-story` 替代 `python run.py`。

数据库清单和字段关系见[数据库说明](docs/database-guide.md)。其他系统的环境变量设置方式见[开发指南](docs/handoff.md)。

## 输出长什么样

```text
outputs/主线批量/<批次>/覆盖阅读版/
├─ Type1/<章节>/<幕>/
│  ├─ <任务ID>_<任务名>.json
│  └─ <任务ID>_<任务名>.txt
├─ Type15/...
├─ 主线阅读报告.md
└─ 覆盖报告.json
```

TXT便于阅读；JSON适合继续加工，并可追溯每段内容的来源和排序依据。查看[虚构TXT示例](examples/minimal-story.txt)、[简化JSON示例](examples/minimal-story.json)和[完整字段说明](docs/corpus-format.md)。

## 当前进度

以下是本地 **3.8.11快照**的验证结果，不代表其他游戏版本或全部分支都已支持。

|主线阅读状态|任务记录数|
|---|---:|
|有序草稿|44|
|有序草稿，含明确缺口或略过过程|29|
|仅局部有序|11|
|暂无有序正文|1|
|合计|85|

另外导出50条Type15记录。最近完整回归为**479项测试通过**。最新解析修复将《梦枢心相由心生·后日谈》的三个正常流程按关联回顾顺序接回，阅读内容由51条增至127条。

> [!IMPORTANT]
> 有序草稿不等于游戏运行时复现或人工验收通过。缺少证据的顺序继续保留说明；视频和演出内部内容、复杂活动的小分支暂时后置。

12条整体顺序待恢复的主线、已解决问题和下一步见[当前状态](docs/status.md)。

## 开发与验证

```shell
# 不需要游戏数据库
python scripts/check_project.py
python -m unittest discover -s tests/unit -v

# 需要本地同版本数据库；从源码运行时先配置 PYTHONPATH=src
python -m unittest discover -s tests -v
```

未安装项目时，PowerShell使用 `$env:PYTHONPATH='src'`；Linux/macOS使用 `export PYTHONPATH=src`。GitHub Actions只运行无数据库检查，完整解析回归在本地执行。

```text
src/wuwa_story/     解析、排序、渲染与命令入口
tests/unit/        无数据库测试
tests/             数据库回归与通用规则测试
scripts/audits/    导出结果对照检查
docs/              使用指南、当前状态与研究证据
examples/          不含游戏原文的格式示例
ConfigDB/          本地输入，不提交
outputs/、work/    本地产物和临时文件，不提交
```

[项目架构](docs/architecture.md) · [阅读验收标准](docs/reading-acceptance.md) · [仓库与数据管理](docs/repository.md)

# 鸣潮剧情解析

从 FModel 导出的游戏配置中还原任务对白，生成**每个任务一个 JSON 和 TXT**，为剧情阅读、检索和后续知识图谱准备可追溯的原文。

[快速开始](#快速开始) · [当前进度](#当前进度) · [输出与解析原则](#输出与解析原则) · [开发与换机](#开发与换机) · [数据库说明](docs/database-guide.md)

> [!IMPORTANT]
> 项目处于解析规则验证阶段。能够导出文件不代表整个任务已完整还原。未知身份、缺失资源、未确认顺序均保留标记，不用猜测补齐。
>
> 仓库包含源码、测试和研究文档；**不包含原始数据库、游戏资产、批量语料或本地 `.codex/` 配置**。克隆后需要自行恢复同版本 `ConfigDB` 才能运行数据解析和完整测试。

## 当前进度

以下为 **2026-11-17、3.8.11 数据快照**的本地验证结果；更换数据后需重新验证。

| 指标 | 结果 |
|---|---:|
| 自动化测试 | 155 项通过 |
| 批量任务记录 | 135（Type1：85，Type15：50） |
| 可提取到文字 | 132 |
| 所选配置路线 / 部分有序 | 12 / 1 |
| 回顾主干草稿 / 仅候选材料 | 60 / 62 |
| 仍有回顾解析阻塞 | 31 个任务、68 处 |
| 严格导出通过 | 2 |

这些分类不是完整率；同名任务和不同类型记录可能对应相关剧情。最新批次标识为 `20261117_023233_327940`，本地产物在 `outputs/主线批量/<批次>/覆盖阅读版/`。

最近完成：

- [配置动作与角色绑定](docs/parallel-review-validation.md)：支持已核验的场景、模型动作；无演员绑定时，仅按明确的对白说话人读取，不猜匿名身份。
- [变量与左右路线](docs/capture-dream-variables-validation.md)：《捕梦于神秘园中》按选择值筛选回顾分支，避免左右混排；保留“变量未被其他交互改写”的假设。

仍待处理：变量跨节点传播、复杂条件、状态结束与跳转、QTE、部分界面与镜头参数，以及无回顾任务的可靠排序。资产完整性后置。下一步以[任务计划](task_plan.md)为准，历史验证见[进度记录](progress.md)。AI 总结、向量知识库和知识图谱尚未实现。

## 快速开始

需要 **Python 3.10+**，当前在 Windows / Python 3.13 验证。运行时只使用标准库，不需要模型、API Key 或第三方服务。

以下命令在项目根目录的 PowerShell 中执行。

先克隆私有仓库（需要相应 GitHub 访问权限）：

```powershell
git clone https://github.com/WinterMoonlight/wuwa-story-parser.git
cd wuwa-story-parser
```

### 1. 恢复数据库

将 FModel 导出的整个同版本 `ConfigDB` 放到项目根目录，保留中文分库：

```text
ConfigDB/
├─ db_QuestData.db
├─ db_QuestNodeData.db
├─ db_PlotHandBook.db
├─ db_flowState.db
├─ db_speaker.db
├─ …
├─ zh-Hans/
│  ├─ lang_multi_text.db
│  ├─ lang_multi_text_1sthalf.db
│  └─ …
└─ Misc/
   ├─ BuildInfo.txt
   └─ ConfigVersion.txt
```

这里只展示部分文件，**不能只复制上述几张表或只复制 zh-Hans**。完整数据关联见[数据库说明](docs/database-guide.md)。也可以指定外部目录：

```powershell
$env:WUWA_CONFIG_DB = 'D:\GameData\ConfigDB'
```

### 2. 导出阅读版

```powershell
# 按章节批量生成任务 JSON/TXT、覆盖报告和缺口清单
python run.py export-reading-batch

# 单独查看一个回顾主干样本
$env:PYTHONPATH = 'src'
python -m wuwa_story.recap_backbone --quest-id 147000002
```

批量结果位于 `outputs/主线批量/<运行时间>/覆盖阅读版/`；单任务回顾位于 `outputs/回顾主干验证/`。默认使用女漂泊者文本，玩家名统一为“漂泊者”。

《捕梦》默认选择左路，右路的选择文件及复现命令见[条件路线验证](docs/capture-dream-variables-validation.md)。每条配置阅读路线仍会标明适用假设和未验证内容。

### 3. 运行严格样本和测试

```powershell
# 已验证的严格样本；其他任务可能因未知机制而停止
python run.py export-task --quest-id 880000013

# 需要完整的本地数据库快照
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
```

测试包含真实数据集成验证，空仓库或不同快照不能复现上述通过数字。

## 输出与解析原则

```text
任务与回顾配置 → 流程、选项、文本、说话人关联 → 有序正文与待核验材料
                                             ├─ JSON：原文、引用、证据、缺口
                                             └─ TXT：对白、选择、简短说明
```

- **JSON** 保留文本 ID、原始模板、来源、条件与选择、身份关联证据、技术记录和验证状态。
- **TXT** 保留可阅读对白、玩家选择、小游戏正文与必要缺失说明；候选、失败和无法定位的内容单列。
- 姓名只按配置关联，无法确定时保留问号；问号标签不作为全局人物 ID。
- 顺序依赖回顾或明确配置证据，不按文件名、节点编号猜测；配置顺序不等于实际运行时完成顺序。
- 原始数据库只读。重新导出会生成新批次或覆盖同名样本，不修改游戏数据。

字段细节见[语料格式](docs/corpus-format.md)，批量分类见[覆盖阅读版](docs/coverage-reading.md)。研究文档中指向 `outputs/` 或 `work/` 的链接是本地产物，GitHub 上不可用，需恢复数据后重新生成。

## 其他命令

| 命令 | 用途 |
|---|---|
| `python run.py export-mainline` | 严格批量导出与失败清单 |
| `python run.py scan-mainline` | 结构扫描及后续阻塞诊断 |
| `python run.py inspect` | 查看核心表结构与样例 |
| `python run.py inventory` | 数据库清单与解析缓存 |
| `python run.py index` | 基于 inventory 缓存整理索引 |
| `python run.py refresh-reading` | 更新已有导出文件的阅读呈现 |

换快照后需重建缓存。`export-task --allow-incomplete` 可生成带缺口草稿，但不保证任意结构都能解析。

## 开发与换机

```text
src/wuwa_story/   解析、数据关联、阅读渲染与批量报告
tests/           纯逻辑测试和真实数据库回归
docs/            架构、数据组织、案例证据与恢复说明
run.py           无需安装的命令入口
pyproject.toml   Python 包定义
task_plan.md     当前目标、验收标准、下一步
findings.md      研究结论
progress.md      历史验证记录
```

克隆后先读[任务计划](task_plan.md) → [换机指南](docs/handoff.md) → [项目架构](docs/architecture.md)。恢复数据库后运行测试；不要把历史测试结果当作新环境验证。

| 环境变量 | 默认值 |
|---|---|
| `WUWA_PROJECT_ROOT` | 源码所在项目根目录 |
| `WUWA_CONFIG_DB` | `ConfigDB` |
| `WUWA_WORK_DIR` | `work` |
| `WUWA_OUTPUT_DIR` | `outputs` |

后三项相对路径以项目根目录为基准。可选安装：`python -m pip install -e .`；开发时也可直接使用 `run.py` 或设置 `PYTHONPATH=src`。当前以 Windows 为验证平台，其他系统需重新测试。

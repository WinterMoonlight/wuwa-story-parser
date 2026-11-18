# 鸣潮剧情解析

[![Source checks](https://github.com/WinterMoonlight/wuwa-story-parser/actions/workflows/ci.yml/badge.svg)](https://github.com/WinterMoonlight/wuwa-story-parser/actions/workflows/ci.yml)

从本地《鸣潮》ConfigDB 读取任务、对白、说话人和剧情回顾，生成按章幕组织的 **TXT 阅读稿、JSON 语料和主线连读索引**。TXT 适合从序幕连续读，JSON 保存每段对白的来源、选项和排序依据。

[快速开始](#快速开始) · [文档](docs/README.md) · [虚构输出示例](examples/minimal-story.txt) · [报告问题](https://github.com/WinterMoonlight/wuwa-story-parser/issues)

> [!NOTE]
> 仓库提供源码、文档和虚构示例。运行解析需要自行准备同一版本的 ConfigDB。数据库、客户端文件和完整剧情产物保存在本地。

## 快速开始

需要 **Python 3.10 或更高版本**。解析器使用 Python 标准库。

```shell
git clone https://github.com/WinterMoonlight/wuwa-story-parser.git
cd wuwa-story-parser
python run.py --help
```

将同版本数据放入 `ConfigDB/`，保留 `zh-Hans/` 和 `Misc/` 等原有目录。也可用 `WUWA_CONFIG_DB` 指定数据路径。核心库清单见[数据库说明](docs/database-guide.md)。

```shell
python run.py export-reading-batch
python run.py export-recap --quest-id 139000025 --output outputs/sample
```

第一条命令生成完整批次。第二条命令只导出指定任务，适合先试跑。执行 `python -m pip install -e .` 后也可使用 `wuwa-story`。选项覆盖、路径变量和审查版的用法见[命令参考](docs/commands.md)。

## 从哪里开始读

打开终端输出的批次目录，再进入 `覆盖阅读版/`。

```text
覆盖阅读版/
  主线连读索引.md
  主线阅读报告.md / .json
  覆盖报告.md / .json
  Type1/<章>/<幕>/<任务ID>_<任务名>.txt
  Type1/<章>/<幕>/<任务ID>_<任务名>.json
  Type15/...
```

- **主线连读索引** 从《万象新声》开始。顺序依据是任务前置、已核对的章节回顾和章节树，待核的位置会注明。
- **TXT 阅读稿** 保留选中的对白和选项。视频、交互或无法定位的过程会有简短标记。
- **JSON 语料** 适合程序读取，包含原始动作和引用、候选材料、阅读顺序以及指回原事件的路径。可先看[简化 JSON 示例](examples/minimal-story.json)和[字段说明](docs/corpus-format.md)。

## 解析范围

本地 **3.8.11 快照**的 85 条 Type1 记录都有可读主干。连读索引串起 44 幕的 80 条任务，另附追月节 4 条和乘霄山总回顾。另有 50 条 Type15 补充记录单独导出。

阅读稿采用一条配置支持的路线。实机时序、部分分支及素材内部内容仍有待核验，细节见[当前状态](docs/status.md)和[任务节点与对白选择](docs/selection.md)。

## 开发检查

```shell
python scripts/check_project.py
python -m unittest discover -s tests/unit -v
```

这两项检查可在无游戏数据的克隆中运行。[运行架构](docs/architecture.md)说明程序从数据读取到导出的过程。修改解析规则前可参考[贡献指南](CONTRIBUTING.md)和[仓库与本地数据管理](docs/repository.md)。

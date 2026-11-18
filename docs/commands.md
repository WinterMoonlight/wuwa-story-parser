# 命令参考

在源码根目录运行 `python run.py`。安装后可用 `wuwa-story`，设置 `PYTHONPATH=src` 后可用 `python -m wuwa_story`。

## 日常导出

| 命令 | 输出与用途 |
|---|---|
| `export-reading-batch` | 读取当前快照，生成章幕目录、每任务 TXT 和 JSON、主线连读索引以及覆盖和缺口报告 |
| `export-recap --quest-id 139000025 --output outputs/sample` | 导出单任务阅读稿和证据 |
| `export-task --quest-id 880000013` | 单任务解析，适合检查受支持的任务路线 |
| `export-task --quest-id 139000026 --allow-incomplete` | 启用已支持的待核验任务投影 |
| `export-mainline` | 严格批量检查，输出成功任务和首次失败清单 |
| `refresh-reading` | 用现有 JSON 重建配置的输出目录中的 TXT |
| `scan-mainline` | 检查任务结构、动作和外部内容引用 |
| `inspect`、`inventory`、`index` | 查看数据表、生成中间资料和查找配置引用 |

批量输出的位置、所含任务和统计口径见[批量导出](batch-export.md)。

## 覆盖对白选项

先生成单任务 JSON，再从任务或相应回顾片段的 `route.choices` 复制 `choice_key`。以下是虚构格式示例，实际键以 JSON 为准。

```json
{
  "示例流程_1_1:3": 1
}
```

值从 0 开始，`1` 表示第二个选项。将文件保存为 `choices.json` 后运行下面的命令。

```shell
python run.py export-recap --quest-id 139000025 --choices choices.json --output outputs/alternate
```

备用路径以及控制动作的限制见[任务节点与对白选择](selection.md)。

## 更新已有批次的连读索引

安装项目或设置 `PYTHONPATH=src` 后，可对已有批次重新生成索引。

```shell
python -m wuwa_story.chapter_reading_index "outputs/主线批量/<批次>/覆盖阅读版"
```

将 `<批次>` 换成实际目录名。此命令只写入 `主线连读索引.md`。只有本地章节树数据库哈希与该批次一致时，才使用章节树连接补充任务前置关系。

## 生成阅读审查版

```shell
python run.py export-review --batch outputs/my-batch/覆盖阅读版 --review review.json --output outputs/review
```

将路径换成实际批次和审查文件。审查记录绑定源 JSON、TXT 的 SHA-256，源文件变化后需重新核验。见[阅读验收](reading-acceptance.md)。

## 路径配置

| 环境变量 | 默认值 |
|---|---|
| `WUWA_PROJECT_ROOT` | 源码运行时定位到项目根目录 |
| `WUWA_CONFIG_DB` | `ConfigDB` |
| `WUWA_OUTPUT_DIR` | `outputs` |
| `WUWA_WORK_DIR` | `work` |

环境变量中的相对路径以项目根目录为基准。显式命令行路径以当前工作目录为基准。

```powershell
$env:WUWA_CONFIG_DB = 'D:\GameData\ConfigDB'
$env:PYTHONPATH = 'src'
python run.py export-reading-batch
```

Linux 和 macOS 可用 `export WUWA_CONFIG_DB=/path/to/ConfigDB` 和 `export PYTHONPATH=src`。

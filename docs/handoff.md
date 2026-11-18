# 开发与验证

## 搭建开发环境

克隆仓库并使用 Python 3.10 或更高版本。可在项目根目录用 `python run.py`，也可用 `python -m pip install -e .` 安装命令入口。如果要测试真实任务，请恢复同一版本的完整 ConfigDB，或设定 `WUWA_CONFIG_DB`。目录和参数见[命令参考](commands.md#路径配置)。

## 验证改动

| 检查 | 命令 | 是否需要 ConfigDB |
|---|---|---|
| 语法与文档链接 | `python scripts/check_project.py` | 否 |
| 无数据测试 | `python -m unittest discover -s tests/unit -v` | 否 |
| 完整解析回归 | `python -m unittest discover -s tests -v` | 是 |
| 生成对照批次 | `python run.py export-reading-batch` | 是 |

未安装项目时，先在 PowerShell 中运行 `$env:PYTHONPATH='src'`，或在 POSIX shell 中运行 `export PYTHONPATH=src`。GitHub Actions 在 Linux 和 Windows 上检查无数据库测试、打包和 CLI 帮助。真实 ConfigDB 的完整回归在本地运行。

## 对照导出

修复前后使用同一快照。先对照数据库哈希，再检查原有对白、选择、引用和 TXT 的变化。新增段落应有明确的前后锚点，未改动的任务可逐文件比较。专项校验工具位于 `scripts/audits/`，各脚本针对的批次和范围见其参数说明。

关于代码布局和证据要求，分别见[运行架构](architecture.md)与[任务节点与对白选择](selection.md)。需要复用旧审查记录时，先核对该记录绑定的源文件哈希。

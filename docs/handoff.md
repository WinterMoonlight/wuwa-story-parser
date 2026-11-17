# 开发与换机

## 恢复项目

1. 克隆源码，先看[当前状态](status.md)和根目录`task_plan.md`。
2. 安装Python 3.10+；当前完整数据验证环境为Windows / Python 3.13。
3. 单独恢复同版本ConfigDB，或设置`WUWA_CONFIG_DB`。数据库、输出、客户端脚本和`.codex`不随Git克隆。
4. 如需复查历史阅读结论，另行恢复相应批次；审查记录绑定旧文件哈希，不能套用到新导出。

```powershell
python -m pip install -e .
python scripts/check_project.py
python -m unittest discover -s tests/unit -v

$env:WUWA_CONFIG_DB = 'D:\GameData\ConfigDB'
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python run.py export-reading-batch
```

Linux/macOS可用`export WUWA_CONFIG_DB=/path/to/ConfigDB`和`export PYTHONPATH=src`设置环境变量。

## 修改规则

- 原始数据库只读；不得把清洗结果写回输入库。
- 先用明确案例取证，再实现可复用规则和反例测试。
- 任务调用关系优先；回顾补充顺序，不能使用节点ID、文件名或数据库行号猜测顺序。
- TXT面向阅读，JSON保留证据。未知身份、未确认顺序和未取得内容保持可区分。
- 修复后对照旧批次，检查原正文、选择、重复、来源指针及未修改任务；局部顺序不计整任务完整。

## 测试分层

`tests/unit/`可在没有数据库的干净克隆中运行。其他测试覆盖真实配置和通用解析规则，部分模块导入时会建立文本索引，因此完整测试需要数据库，不能把未运行的测试算作通过。

GitHub Actions检查语法、文档链接、无数据库测试、打包和CLI帮助；它不下载游戏数据，也不替代本地完整回归。

`scripts/audits/`保存结果核对脚本。运行时设置`PYTHONPATH=src`，先查看脚本的参数说明；历史专项脚本可能只适用于对应修复前后的批次。

## 接着做什么

当前重点是12条尚无整体顺序的主线，详见[状态与待办](status.md)。先从现有数据库寻找明确的调用、完成条件、关联回顾或去重依据。缺少新证据的案例记清原因，避免反复使用相同假设。

既有脚本继续使用`wuwa_story.*`导入路径。当前结构调整不重命名解析模块，不改变导出行为。研究记录见[研究目录](research/README.md)，更早的规划见`history/`；根目录三份规划文件只保留当前工作入口。

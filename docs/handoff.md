# 开发与换机

## 恢复工作环境

1. 克隆仓库并阅读根目录`task_plan.md`、`progress.md`和`findings.md`。
2. 安装Python 3.10+，当前验证使用Python 3.13。
3. 单独恢复完整同版本ConfigDB，或者设置`WUWA_CONFIG_DB`。
4. 核对Misc中的快照信息，再运行结构检查和测试。

```powershell
python scripts/check_project.py
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python run.py export-recap --quest-id 139000026 --output outputs/sample
```

源码仓库包含程序、测试、指南、研究报告及审查记录。数据库、outputs、work和本地.codex配置由使用者另行恢复。完整测试读取本机快照，当前预期快照为3.8.11。

## 当前状态

最近解析批次为20261117_132957_607004。135任务记录中132有文字，12所选路线、1部分有序、60回顾草稿、62候选材料。回顾阻塞16任务27处，严格整任务通过2。三任务连续阅读评为带明确缺口可阅读。最新实测和结构整理结果见[进度](../progress.md)。

## 接手顺序

先汇总任务路线中断和回顾区段阻塞的统一清单，按影响任务数和可验证性选择代表问题。每轮规则修复后运行相关测试、全量回归及批量比较，再记录可读范围和缺口。

模拟领域1505的14条候选已有详细触发证据。8/3多调用、8/8完成条件引用及37至成功节点3的关系需要新执行证据。现有研究见[第五轮阅读验收](research/reading-acceptance-005.md)。

## 维护约定

- 现有`wuwa_story.*`模块路径继续兼容，公共命令集中到`cli.py`。
- 新专题结论放`docs/research/`，当前接口说明放顶层docs指南。
- 人工审查记录放`docs/reviews/`，生成文件进入outputs。
- 当前规划三文件保持简洁，已完成的长历史可追加到`docs/history/`。
- 可使用`python scripts/check_project.py`检查语法与可见本地Markdown链接。

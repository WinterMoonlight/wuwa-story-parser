# 私有 GitHub 仓库与数据管理

## 默认提交内容

源代码、tests、docs、README、run.py、pyproject.toml、Git 配置文件，以及根目录 task_plan.md、findings.md、progress.md。GitHub 私有仓库：[WinterMoonlight/wuwa-story-parser](https://github.com/WinterMoonlight/wuwa-story-parser)，默认分支 `main`。

`.gitignore` 默认排除 ConfigDB、所有 SQLite 数据库、outputs、work、根目录 `.codex/`、虚拟环境和缓存。因此，默认提交是可复现解析工具与文档，不包含完整客户端数据库、剧情正文或本地 Codex 配置与技能。

这是仓库组织的默认选择，不是禁止在私有环境保留数据。以后如需把数据一起备份，应单独决定版本化方式，并显式选择需要跟踪的目录。普通 ZIP 打包不会自动遵守 `.gitignore`；直接压缩整个项目会包含数据库与工作缓存。

## 为什么把原始数据与生成结果分开

- 原始快照体积较大，更新时二进制差异难审阅。
- outputs 和 work 可以重新生成，不宜每次运行都产生大量提交变化。
- work/reference.py 是下载的第三方研究参考，不是当前项目的正式实现。
- 私有仓库可见性与源码许可是不同问题。本项目暂未添加开源许可证，后续发布或复用第三方代码时再明确许可和归属。

## 发布前本地检查

初始化后检查待提交清单，确认 ConfigDB、outputs、work 没有意外进入跟踪。已跟踪文件不会因为后来添加 .gitignore 自动退出跟踪。

建议从干净源码 checkout 验证：

```powershell
python -m pip install -e .
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
```

测试包含真实数据库读取；未配置数据库时，不能保证测试模块可导入或测试通过。要验证真实解析，设置 `WUWA_CONFIG_DB` 指向快照，再执行全部测试和样本导出。

## 数据迁移与快照

当前路径以源码项目根目录为基准，可通过环境变量覆盖，避免写入个人机器绝对路径。

更换快照应同时保留同一版本根目录配置和语言目录，不能只更新中文文本。先记录 Misc 中的构建信息，再重新生成 inventory、index 和样本。当前缓存不自动校验版本，重建是必要步骤。

后续建议采用独立快照目录与 manifest（构建号、文件哈希、导出时间、解析器版本）。这部分是规划，当前没有自动快照管理或云端备份功能。

## 规划文件与换机

规划文件不在 .gitignore 排除范围，应与源码一起提交。仅克隆无法恢复被忽略的数据与成果；步骤见[换机恢复指南](../handoff.md)。.codex 继续忽略，planning-with-files 技能可在新机单独安装，三份普通 Markdown 不依赖技能运行。

当前批量清单已有核心源库 SHA-256 与 BuildInfo；自动管理快照、全输入 manifest 和远程备份尚未实现。

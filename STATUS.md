# 当前状态

更新时间：2026-10-13

- 已从 `instant-ai-finance/services/sunmao-ai-community` 提取为独立 Git 仓库，并保留社区相关提交历史归档。
- 公开远端仓库 `wangbaocheng123-hash/sunmao-ai-community` 已创建；`main` 和 `production` 均已建立。
- 远端 30 个文件已和本地 Git 内容逐项核对，差异仅为 GitHub 网页上传不保留 4 个脚本的可执行位；服务器安装器会明确安装为 `0755`。
- 发布脚本已改为从独立仓库根目录读取，生产分支为 `production`。
- 线上网站仍正常运行，当前发布源暂时仍是旧仓库的 `sunmao-production`；尚未切换服务器 Git 来源。
- 线上社区进程、端口、数据库和域名不需要迁移，留言数据不会因仓库拆分而移动。
- 当前自动化测试：16 项。

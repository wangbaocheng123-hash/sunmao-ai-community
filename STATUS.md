# 当前状态

更新时间：2026-10-13

- 已从 `instant-ai-finance/services/sunmao-ai-community` 提取为独立本地 Git 仓库，并保留社区相关提交历史。
- 独立仓库远端预定为 `wangbaocheng123-hash/sunmao-ai-community`，当前等待 GitHub 登录后创建与首次推送。
- 发布脚本已改为从独立仓库根目录读取，生产分支改为 `production`。
- 线上网站仍正常运行，当前发布源暂时仍是旧仓库的 `sunmao-production`；尚未切换服务器 Git 来源。
- 线上社区进程、端口、数据库和域名不需要迁移，留言数据不会因仓库拆分而移动。
- 当前自动化测试：16 项。

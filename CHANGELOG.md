# 变更记录

## 2026-10-13：独立仓库上线

- 服务器发布源已切换到 `sunmao-ai-community` 的 `production` 分支，线上提交为 `6de54e5`。
- 交流区主屏、尺寸型入口、右侧榫卯 108 道导航及 34 条抖音跳转链接通过公网验收。
- 保留原留言数据库、域名和独立服务；北京博主采集器保持原版本运行。

- 把榫卯 AI 社区从 `instant-ai-finance` 子目录提取为独立仓库。
- 把生产发布分支从 `sunmao-production` 简化为独立仓库的 `production`。
- 发布器改为验证和解包仓库根目录，不再依赖 `services/sunmao-ai-community` 子树。
- 增加独立仓库的项目章程、状态、路线图、任务和 Codex 工作规则。

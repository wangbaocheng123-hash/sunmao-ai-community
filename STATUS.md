# 当前状态

更新时间：2026-10-13

- 已从 `instant-ai-finance/services/sunmao-ai-community` 提取为独立 Git 仓库，并保留社区相关提交历史归档。
- 公开远端仓库 `wangbaocheng123-hash/sunmao-ai-community` 已创建；`main` 和 `production` 均已建立。
- 远端 30 个文件已和本地 Git 内容逐项核对，差异仅为 GitHub 网页上传不保留 4 个脚本的可执行位；服务器安装器会明确安装为 `0755`。
- 发布脚本已改为从独立仓库根目录读取，生产分支为 `production`。
- 2026-10-13 17:18（北京时间）已完成服务器发布源切换，Git origin 指向独立仓库，生产分支为 `production`。
- 最近已验收的线上版本：`0.2.0`；部署提交：`6de54e56b3dbaac1a3bbeb13ced32dccd6dcb0b4`；代码树：`c8969e09921debb65dc2fdfb278a4f7096b4ed7e`。
- 公网已验收交流区主屏、底部三个导航入口及 34 条抖音视频链接；尺寸型等待提供首批资料。
- 社区进程、端口、域名和数据库路径保持原配置；数据库 inode `408317` 未改变。博主采集器仍运行原提交 `10fdb3a313f8851c8e7963fb29bc2935dfb164ae`。
- 首次迁移备份：`/var/lib/sunmao-community/git-deploy/migration-object-20261013T091825Z`。首次发布通过固定提交压缩包及 Git 内容指纹核验完成。
- 开发版本已推进到 `0.3.0`：新增 `/admin/` 管理入口、第一方匿名访问统计、趋势、栏目、来源、设备和最近访客；当前尚未发布。
- 统计使用随机浏览器编号，不保存 IP 地址或完整 User-Agent；统计从新版本正式上线后开始，不包含历史访问。
- 后台默认关闭，发布时需把密码摘要安全写入社区自己的 `/var/lib/sunmao-community/admin-password.hash`，不得进入 Git。
- 后台、会员、收费与广告的渐进框架记录在 `docs/ADMIN_AND_MONETIZATION_PLAN.md`；架构决策见 ADR-0002。
- 所有者已明确授权发布本次访问统计与管理后台；当前阻塞是实际连接能力，不是等待再次口头批准。不增加定时发布，后续仍由所有者的发布指令触发。
- GitHub 连接已获仅针对社区仓库的授权，真实 `git push` 成功：功能提交 `7dd09ff67baa119d672738a822c5a77ddd8fe297` 已进入远端 `main`。此前的代码写入 403 已解决，恢复工作时不要默认要求重复登录或重新安装连接应用。
- `production` 仍指向 `6de54e56b3dbaac1a3bbeb13ced32dccd6dcb0b4`；本次未推进生产分支、未操作线上服务，也未改动北京博主采集器。
- 当前 `/workspace` 执行环境没有已配置的服务器身份、VPN 或 TCP 目标授权，且不存在原新加坡环境的 `beijing-admin` 入口。原项目 ADR-0047 记录了可复用的新加坡到北京的长期连接，但尚未在当前任务中接通或验证；不得把旧文档记录当作当前连接成功。
- 仓库当前没有 GitHub Actions 发布工作流。现有发布脚本推进 `production` 后，仍需在服务器触发一次 `sunmao-community-git-deploy.service`；推送 `main` 不等于网站上线。当前连接也无权查询仓库 Actions 密钥或自托管运行器，不能据此断言它们不存在。
- 当前云端经 HTTPS 代理访问社区健康接口返回上游连接失败 503，尚不能据此判断公网网站是否故障。下一步先接通已有服务器管理路径，再配置后台密码摘要、按现有流程发布，并核验 `/health/version` 与后台登录。
- 当前自动化测试：22 项。

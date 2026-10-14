# 当前状态

更新时间：2026-10-14

- 已从 `instant-ai-finance/services/sunmao-ai-community` 提取为独立 Git 仓库，并保留社区相关提交历史归档。
- 公开远端仓库 `wangbaocheng123-hash/sunmao-ai-community` 已创建；`main` 和 `production` 均已建立。
- 远端 30 个文件已和本地 Git 内容逐项核对，差异仅为 GitHub 网页上传不保留 4 个脚本的可执行位；服务器安装器会明确安装为 `0755`。
- 发布脚本已改为从独立仓库根目录读取，生产分支为 `production`。
- 2026-10-13 17:18（北京时间）已完成服务器发布源切换，Git origin 指向独立仓库，生产分支为 `production`。
- 最近已验收的线上版本：`0.3.0`；部署提交：`a54a95a0bbca1765447e656347c88a8c1f4e1838`；代码树：`996d626c2114aa33da92649b50d1c7854f7a28ff`。
- 公网已验收交流区主屏、底部三个导航入口及 34 条抖音视频链接；尺寸型等待提供首批资料。
- 社区进程、端口、域名和数据库路径保持原配置；发布后数据库 inode 仍为 `408317`。社区、博主采集器和模型下载器服务均为 `active`，本次只触发社区发布器，没有停止或重启另外两项业务。
- 首次迁移备份：`/var/lib/sunmao-community/git-deploy/migration-object-20261013T091825Z`。首次发布通过固定提交压缩包及 Git 内容指纹核验完成。
- `0.3.0` 已正式上线：新增 `/admin/` 管理入口、第一方匿名访问统计、趋势、栏目、来源、设备和最近访客。
- 统计使用随机浏览器编号，不保存 IP 地址或完整 User-Agent；统计从新版本正式上线后开始，不包含历史访问。
- 后台密码摘要已安全写入社区自己的 `/var/lib/sunmao-community/admin-password.hash`，属主为 `sunmaocommunity:sunmaocommunity`、权限 `0600`；初始明文临时文件在登录验收后已删除，凭据未进入 Git 或服务日志。
- 后台、会员、收费与广告的渐进框架记录在 `docs/ADMIN_AND_MONETIZATION_PLAN.md`；架构决策见 ADR-0002。
- 所有者已明确授权并完成本次访问统计与管理后台发布。没有增加定时发布，后续仍由所有者的发布指令触发。
- GitHub 连接已获仅针对社区仓库的授权，真实 `git push` 成功：功能提交 `7dd09ff67baa119d672738a822c5a77ddd8fe297` 已进入远端 `main`。此前的代码写入 403 已解决，恢复工作时不要默认要求重复登录或重新安装连接应用。
- `0.3.0` 发布时，本地桌面曾经新加坡 `/home/compassdev/bin/beijing-admin` 人工触发北京固定发布器。该路径现只保留为首次基础设施安装与故障维护，不是手机 Codex Cloud 日常修改或发布的前置。
- 当前固定发布入口为在独立仓库运行 `deploy/beijing/publish-via-git.sh <完整提交SHA>`：它只安全快进 `production`并等待公网精确版本。GitHub 签名 Webhook 自动通知北京，不再要求云端或所有者登录任何服务器。
- 手机 Codex Cloud 只需选择社区独立仓库；它直接修改、测试并推送 GitHub。普通 `main` 不上线；收到所有者固定发布指令后推进 `production`，北京即按事件自行发布。
- 仓库没有 GitHub Actions 发布工作流；现使用仓库 Webhook 和北京社区固定发布器。密钥不进入 Git，服务器不启用 Git 定时轮询。
- 公网 `/admin/` 返回 200 和 `X-Robots-Tag: noindex, nofollow`；密码登录返回 200，带会话读取统计看板返回 200。发布验收写入 1 条明确标记的测试访问，统计显示 1 位访客、1 次访问、1 次浏览，并返回趋势、栏目、来源、设备和最近访客数据结构。
- 当前自动化测试：27 项；功能提交发布前在 Linux 环境全部通过，服务器固定发布器完成验证和原子切换。
- `0.3.1` 开发候选已将未来日常发布改为 GitHub `production` push 事件驱动：社区进程验证 HMAC-SHA256 签名、精确仓库、分支和提交号，再写入短暂触发文件，systemd path 仅启动社区固定发布器。不增加 Git 轮询 timer，不要求云端 Codex 连接新加坡或北京 SSH。
- 引导发布中实测发现北京到 `github.com` 的 Git TLS 偶发中断；候选发布器已新增45秒有界 Git 尝试，以及 GitHub 官方 API 快进验证和按不可变提交 codeload 的安全备用下载，避免单次网络波动丢失事件发布。
- `0.3.1` 首次引导上线时使用 GitHub API/codeload 备用链路发布了 `e39b903160fa01f3dfe9bdcd06f729beca4aac11`。Git 外密钥为 `root:sunmaocommunity 0640`，事件 path 为 `active/enabled`，Git 轮询 timer 不存在；无效签名返回403。
- GitHub 仓库 Webhook `697357007` 已启用且只订阅 push，创建后的签名 ping 返回 HTTP 200。真实 `production` push 于 `2026-10-14T00:44:05Z` 完成，GitHub 于 `00:44:06Z` 收到 HTTP 202，北京 systemd 在同秒自动启动发布器，并于 `00:45:57Z` 上线 `abceb04d1eb6ffe8b9913f58cdb559a8702f8a8a`。该次验收未执行任何新加坡或北京启动命令。
- 后续验收记录提交同样只通过 `production` 事件自动上线；实际线上完整提交始终以公网 `/health/version` 为准。

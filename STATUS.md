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
- `production` 已从 `6de54e56b3dbaac1a3bbeb13ced32dccd6dcb0b4` 安全快进到 `a54a95a0bbca1765447e656347c88a8c1f4e1838`。服务器固定发布器返回成功，`current`、服务器远端生产引用、回环和公网 `/health/version` 均精确指向目标提交。
- 本次实际运行环境是本地桌面社区独立仓库，经既有新加坡维护服务器进入 `/home/compassdev/bin/beijing-admin`，再连接北京 `singaporecodex` 管理入口；该链路已实际核验完整 sudo，没有重新生成、覆盖或导出 SSH 私钥。
- 固定发布入口为：在独立仓库运行 `deploy/beijing/publish-via-git.sh <完整提交SHA>`；脚本进入等待后，通过上述北京管理连接执行一次 `systemctl start --no-block sunmao-community-git-deploy.service`。推送 `main` 或 `production` 本身不等于网站上线。
- 其他手机/云端 Codex 窗口不会自动继承本窗口或新加坡服务器的连接。只有任务实际运行在含 `/home/compassdev/bin/beijing-admin` 的既有新加坡环境时，才能直接复用该入口；当前工具不能把另一个已存在的云端窗口跨窗口绑定到这条连接，不能把本次本地发布成功写成那个窗口也已接通。
- 仓库当前没有 GitHub Actions 发布工作流。现有发布脚本推进 `production` 后，仍需在服务器触发一次 `sunmao-community-git-deploy.service`；推送 `main` 不等于网站上线。当前连接也无权查询仓库 Actions 密钥或自托管运行器，不能据此断言它们不存在。
- 公网 `/admin/` 返回 200 和 `X-Robots-Tag: noindex, nofollow`；密码登录返回 200，带会话读取统计看板返回 200。发布验收写入 1 条明确标记的测试访问，统计显示 1 位访客、1 次访问、1 次浏览，并返回趋势、栏目、来源、设备和最近访客数据结构。
- 当前自动化测试：22 项；功能提交发布前在 Linux 环境全部通过，服务器固定发布器完成验证和原子切换。
- `0.3.1` 开发候选已将未来日常发布改为 GitHub `production` push 事件驱动：社区进程验证 HMAC-SHA256 签名、精确仓库、分支和提交号，再写入短暂触发文件，systemd path 仅启动社区固定发布器。不增加 Git 轮询 timer，不要求云端 Codex 连接新加坡或北京 SSH。
- 引导发布中实测发现北京到 `github.com` 的 Git TLS 偶发中断；候选发布器已新增45秒有界 Git 尝试，以及 GitHub 官方 API 快进验证和按不可变提交 codeload 的安全备用下载，避免单次网络波动丢失事件发布。
- `0.3.1` 已使用 GitHub API/codeload 备用链路完成首次引导上线，当前公网与回环提交为 `e39b903160fa01f3dfe9bdcd06f729beca4aac11`。Git 外密钥为 `root:sunmaocommunity 0640`，事件 path 为 `active/enabled`，Git 轮询 timer 不存在；无效签名返回403。
- GitHub 仓库 Webhook `697357007` 已启用且只订阅 push，创建后的签名 ping 返回 HTTP 200。本提交将作为第一个真实 `production` push 事件验收目标；在公网精确切换至本提交前，仍不得将端到端验收标为完成。

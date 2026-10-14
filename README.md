# 榫卯 AI 社区

这是榫卯 AI 社区的独立代码仓库，不是北京博主采集器的页面、目录或子模块。

两者可以部署在同一台北京服务器，但永久保持并列：

- GitHub 仓库：`wangbaocheng123-hash/sunmao-ai-community`
- 社区源码：仓库根目录
- 社区进程：`sunmao-ai-community.service`
- 回环端口：`127.0.0.1:18808`
- 运行数据库：`/var/lib/sunmao-community/community.sqlite3`
- 原子发布目录：`/opt/sunmao-community/`
- 生产分支：`production`
- 公网域名：`https://阿木爷爷.com/`

北京博主采集器继续使用自己的目录、`blogger-collector.service`、端口 `18797`、数据目录和 `beijing-production`；发布社区不得重启或改写采集器。

## 本地运行

```powershell
cd sunmao-ai-community
python -m unittest discover -s tests -p "test_*.py"
python -m sunmao_community --host 127.0.0.1 --port 4173 --database .runtime/community.sqlite3
```

## 管理后台与访问统计

开发版本提供 `/admin/` 管理入口。第一版可查看今日与累计匿名访客、访问次数、浏览量、近 7～90 日趋势、栏目、来源域名、设备和最近访客。访客以浏览器随机编号显示；系统不保存 IP 地址或完整 User-Agent。

后台默认关闭。密码摘要只存运行数据目录，不进入 Git。生成摘要：

```powershell
python -m scripts.generate_admin_password_hash
```

生产环境把输出以 `0600` 权限保存为 `/var/lib/sunmao-community/admin-password.hash`，属主设为 `sunmaocommunity:sunmaocommunity`，再重启社区服务。也可通过 `SUNMAO_ADMIN_PASSWORD_HASH` 或 `SUNMAO_ADMIN_PASSWORD_HASH_FILE` 指定，但不得把值写进仓库。具体架构与商业化顺序见 `docs/ADMIN_AND_MONETIZATION_PLAN.md`，隐私与认证决策见 `docs/decisions/ADR-0002-first-party-analytics-and-admin.md`。

## 发布规则

普通 `main` 推送只保存开发检查点，不上线。所有者明确说“更新并发布榫卯AI社区：<具体需求>”后，才允许把已验收提交安全快进到 `production`。GitHub 随后发送带 HMAC-SHA256 签名的 push Webhook；北京社区进程验证仓库、分支、提交号和签名后，通过 systemd path 一次性启动 `sunmao-community-git-deploy.service`。该发布只切换 `/opt/sunmao-community/current` 并重启社区进程。

服务器已于 2026-10-13 切换到本独立仓库。当前网站由独立社区进程提供；普通社区功能发布不重启博主采集器。修改 `main` 或在手机云端完成任务不等于网站已发布：仍须经授权推进 `production`，由 GitHub 事件触发北京固定发布器，最后核对只读部署探针 `/health/version` 的提交号。服务器不进行每分钟或其他周期的 Git 轮询。

当前 `阿木爷爷.com` 从北京服务器自身访问正常，但从部分外部网络会被阿里云备案边缘拦截。为区分“代码未部署”和“域名被拦截”，机器验收可读取 `http://47.93.214.76/health/version`；该 IP 入口只开放版本 JSON，其他路径返回404。它不是面向用户的网站替代地址，正式域名仍需完成备案或迁移到经确认的境外入口。

## 手机云端 Codex

新建云端任务时只选择 `sunmao-ai-community` 仓库和默认环境。任务描述写清“只修改榫卯 AI 社区；完成后运行全部测试；未经‘更新并发布榫卯AI社区’指令不得推进 `production`”。手机上的 Codex Cloud 直接操作 GitHub 仓库，不需要连接或运行在新加坡服务器。正式发布由 `production` 事件触发北京社区固定发布器。

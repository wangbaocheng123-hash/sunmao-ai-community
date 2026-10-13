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

## 发布规则

普通 `main` 推送只保存开发检查点，不上线。所有者明确说“更新并发布榫卯AI社区：<具体需求>”后，才允许把已验收提交安全快进到 `production`，再触发固定的一次性 `sunmao-community-git-deploy.service`。该发布只切换 `/opt/sunmao-community/current` 并重启社区进程。

服务器已于 2026-10-13 切换到本独立仓库，并完成公网验收。当前网站由独立社区进程提供；普通社区功能发布不修改 Caddy，也不重启博主采集器。修改 `main` 或在手机云端完成任务不等于网站已发布：仍须经授权推进 `production`，在服务器触发上述发布服务，最后核对公网 `/health/version` 的提交号。

## 手机云端 Codex

新建云端任务时只选择 `sunmao-ai-community` 仓库和默认环境。任务描述写清“只修改榫卯 AI 社区；完成后运行全部测试；未经‘更新并发布榫卯AI社区’指令不得推进 `production`”。这样手机端不会把其他系统的代码带进任务上下文。

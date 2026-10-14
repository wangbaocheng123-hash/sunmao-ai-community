# ADR-0003：GitHub 事件驱动的社区发布通道

- 状态：已接受并完成生产验收
- 日期：2026-10-14

## 背景

手机上的 Codex Cloud 已能直接检出社区独立仓库、修改和测试代码并推送 GitHub。它不是新加坡服务器内的 Codex，也不应持有北京服务器的 SSH 身份。原流程在推进 `production` 后还要从新加坡或桌面环境人工执行一次 `systemctl start`，这成为手机云端发布的最后阻塞。

北京服务器同时运行其他模型与采集任务。为了不增加周期轮询，不采用每分钟 Git 检查。

## 决策

1. Codex Cloud 只直接操作 `wangbaocheng123-hash/sunmao-ai-community`：日常修改推送 `main`，所有者明确说“更新并发布榫卯AI社区：<具体需求>”后才能安全快进 `production`。
2. GitHub 仅在 `production` 收到 push 时向社区自身的 `/api/deploy/github` 发送 Webhook。`main` 和其他事件不发布。
3. 社区进程使用 GitHub HMAC-SHA256 签名校验，严格核对仓库、`refs/heads/production`和40位提交号。密钥只存于 GitHub Webhook 配置与北京 `/etc/sunmao-community/github-webhook.secret`，不进入 Git、聊天或日志。
4. 验签成功后只能在 `/run/sunmao-community/` 写入一个触发文件。systemd path 单元据此启动已有的 `sunmao-community-git-deploy.service`；公网请求不能选择命令、参数或其他服务。
5. 不安装 Git 轮询 timer，systemd path 平时没有用户态常驻进程。只有正式分支改变时才运行现有发布器和隔离测试。
6. 新加坡 `/home/compassdev/bin/beijing-admin` 只在首次安装或故障维护时作为管理通道，不再参与日常修改和发布。
7. `0.3.2` 增加 GitHub Actions 只读验收：在生产分支 push 后等待公网精确提交并检查公开页面资源，用于云端 HTTPS 代理无法访问网站时提供独立验证。工作流只有仓库读取权限，不持有服务器凭据，也不能触发或改变发布；发布通道仍是上述签名 Webhook。

## 安全与故障边界

- Webhook 签名错误、仓库错误、分支错误或提交号非法均不产生触发文件。
- 重复投递最多再次启动固定发布器；发布器自身有锁、已验收提交检查和失败提交抑制，不会重复切换。
- 发布器仍只拉取独立仓库 `production`，只重启 `sunmao-ai-community.service`，不修改、停止或重启博主采集器和模型下载器。
- Webhook 失效时，网站继续运行已验收版本；故障修复可用现有维护通道手动启动同一固定发布服务。

## 生产验收

- GitHub Webhook `697357007` 仅订阅 push，签名 ping 返回200，无签名请求返回403。
- `production` 在 `2026-10-14T00:44:05Z` 安全快进至 `abceb04d1eb6ffe8b9913f58cdb559a8702f8a8a`；GitHub 于 `00:44:06Z` 收到202，北京 systemd 在同秒自动启动发布器，`00:45:57Z` 完成发布。该过程未执行新加坡或北京启动命令。
- 事件 path 为 active/enabled，Git 轮询 timer 不存在，社区、博主采集器和模型下载器均为 active。

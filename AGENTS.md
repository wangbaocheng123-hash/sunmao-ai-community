# 榫卯 AI 社区仓库规则

## 每次开始

按顺序阅读：

1. `PROJECT_CHARTER.md`
2. `STATUS.md`
3. `ROADMAP.md`
4. `TASKS.md`
5. 最近相关的 `docs/decisions/`

## 永久边界

- 本仓库只维护榫卯 AI 社区。
- 北京博主采集器是同一台服务器上的并列系统，不属于本仓库。
- 社区服务固定为 `sunmao-ai-community.service`，端口 `127.0.0.1:18808`，数据库 `/var/lib/sunmao-community/community.sqlite3`。
- 不得修改、停止或重启 `blogger-collector.service`，不得读写其数据目录。
- `main` 是开发分支；`production` 是生产发布分支。
- 未收到所有者明确指令“更新并发布榫卯AI社区：<具体需求>”，不得推进 `production` 或操作线上服务。
- 留言数据库属于运行数据，不进入 Git。

## 验证与收尾

- 修改后运行：`python -m unittest discover -s tests -p "test_*.py"`。
- 架构、发布方式或永久路径变化时新增 ADR。
- 状态变化时更新 `STATUS.md`、`TASKS.md` 和 `CHANGELOG.md`。
- 结束前检查 `git status --short`，不得提交密钥、令牌、`.env`、数据库、日志或备份。

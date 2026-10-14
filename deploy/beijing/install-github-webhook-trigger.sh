#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

readonly SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly SECRET_DIR="/etc/sunmao-community"
readonly SECRET_TARGET="${SECRET_DIR}/github-webhook.secret"
readonly APP_SERVICE_TARGET="/etc/systemd/system/sunmao-ai-community.service"
readonly DEPLOY_SERVICE_TARGET="/etc/systemd/system/sunmao-community-git-deploy.service"
readonly PATH_UNIT_TARGET="/etc/systemd/system/sunmao-community-deploy-trigger.path"
readonly APP_USER="sunmaocommunity"

fail() { printf 'sunmao-webhook-install: ERROR %s\n' "$*" >&2; exit 1; }
cleanup() { [[ -z "${secret_stage:-}" ]] || rm -f -- "${secret_stage}"; }
trap cleanup EXIT

[[ "$(id -u)" -eq 0 ]] || fail "installer must run as root"
[[ $# -eq 0 ]] || fail "installer accepts the webhook secret only on standard input"
for file in sunmao-ai-community.service sunmao-community-git-deploy.service sunmao-community-deploy-trigger.path; do
  [[ -f "${SOURCE_DIR}/${file}" ]] || fail "missing reviewed file ${file}"
done
id "${APP_USER}" >/dev/null 2>&1 || fail "community service user is missing"
systemctl is-active --quiet sunmao-ai-community.service || fail "community service must be healthy"
systemctl is-active --quiet blogger-collector.service || fail "collector must remain healthy"

IFS= read -r webhook_secret || fail "webhook secret was not supplied on standard input"
[[ ${#webhook_secret} -ge 32 && ${#webhook_secret} -le 1024 ]] || fail "webhook secret length is invalid"
[[ "${webhook_secret}" =~ ^[A-Za-z0-9_-]+$ ]] || fail "webhook secret contains an invalid character"

install -d -o root -g "${APP_USER}" -m 0750 "${SECRET_DIR}"
secret_stage="$(mktemp "${SECRET_DIR}/.github-webhook.secret.XXXXXX")"
printf '%s\n' "${webhook_secret}" >"${secret_stage}"
chown root:"${APP_USER}" "${secret_stage}"
chmod 0640 "${secret_stage}"
if [[ -e "${SECRET_TARGET}" ]] && ! cmp -s -- "${secret_stage}" "${SECRET_TARGET}"; then
  fail "an existing webhook secret differs; refusing an uncoordinated rotation"
fi
mv -f -- "${secret_stage}" "${SECRET_TARGET}"
secret_stage=""

install -o root -g root -m 0644 "${SOURCE_DIR}/sunmao-ai-community.service" "${APP_SERVICE_TARGET}"
install -o root -g root -m 0644 "${SOURCE_DIR}/sunmao-community-git-deploy.service" "${DEPLOY_SERVICE_TARGET}"
install -o root -g root -m 0644 "${SOURCE_DIR}/sunmao-community-deploy-trigger.path" "${PATH_UNIT_TARGET}"
systemctl daemon-reload
systemctl restart sunmao-ai-community.service
systemctl enable --now sunmao-community-deploy-trigger.path >/dev/null

systemctl is-active --quiet sunmao-ai-community.service || fail "community service did not recover"
systemctl is-active --quiet sunmao-community-deploy-trigger.path || fail "event trigger path is inactive"
systemctl is-active --quiet blogger-collector.service || fail "collector changed during installation"
printf '%s\n' 'sunmao_github_webhook_trigger_installed=true'
printf '%s\n' 'trigger_mode=event_driven_no_timer'

from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEPLOY_ROOT = PROJECT_ROOT / "deploy" / "beijing"


class IndependentDeploymentContractTests(unittest.TestCase):
    def read(self, name: str) -> str:
        return (DEPLOY_ROOT / name).read_text(encoding="utf-8")

    def test_service_has_its_own_identity_port_and_data_root(self) -> None:
        service = self.read("sunmao-ai-community.service")
        self.assertIn("User=sunmaocommunity", service)
        self.assertIn("127.0.0.1 --port 18808", service)
        self.assertIn("/var/lib/sunmao-community/community.sqlite3", service)
        self.assertIn("/opt/sunmao-community/current", service)
        self.assertNotIn("bloggeragent", service)
        self.assertNotIn("18797", service)

    def test_publisher_uses_only_the_standalone_community_repository(self) -> None:
        publisher = self.read("sunmao-community-git-deploy")
        self.assertIn("wangbaocheng123-hash/sunmao-ai-community.git", publisher)
        self.assertIn("refs/remotes/origin/production", publisher)
        self.assertNotIn("SUBTREE=", publisher)
        self.assertNotIn("instant-ai-finance", publisher)
        self.assertIn('SERVICE_NAME="sunmao-ai-community.service"', publisher)
        self.assertIn("merge-base --is-ancestor", publisher)
        self.assertIn("api.github.com/repos/wangbaocheng123-hash/sunmao-ai-community", publisher)
        self.assertIn("codeload.github.com/wangbaocheng123-hash/sunmao-ai-community/tar.gz", publisher)
        self.assertIn("production branch is not a verified fast-forward", publisher)
        self.assertIn("special codeload object rejected", publisher)
        self.assertIn("--retry-all-errors", publisher)
        self.assertIn("timeout --signal=TERM 45s", publisher)
        self.assertIn("flock -n", publisher)
        self.assertIn("validate_release_path", publisher)
        self.assertIn("release marker mismatch", publisher)
        self.assertNotIn("beijing-production", publisher)
        self.assertNotIn("systemctl restart blogger-collector", publisher)
        self.assertNotIn("/var/lib/blogger-agent", publisher)

    def test_publisher_does_not_reference_a_local_in_its_declaration(self) -> None:
        publisher = self.read("sunmao-community-git-deploy")
        self.assertIn('local source_dir="$1"\n', publisher)
        self.assertIn('local output_file="${source_dir}/.test-output" count', publisher)
        self.assertNotIn(
            'local source_dir="$1" output_file="${source_dir}/.test-output"',
            publisher,
        )

    def test_caddy_proxies_directly_to_the_peer_service(self) -> None:
        caddy = self.read("sunmao-community.Caddyfile.example")
        apply_script = self.read("apply-caddy.sh")
        self.assertIn("reverse_proxy 127.0.0.1:18808", caddy)
        self.assertIn("http://47.93.214.76", caddy)
        self.assertIn("path /health/version", caddy)
        self.assertIn("# BEGIN SUNMAO COMMUNITY", caddy)
        self.assertIn("# END SUNMAO COMMUNITY", caddy)
        self.assertNotIn("rewrite * /community", caddy)
        self.assertNotIn("18797", caddy)
        self.assertIn("restore_previous_config", apply_script)
        self.assertIn("http://127.0.0.1:18808/health", apply_script)
        self.assertIn("begin_marker", apply_script)
        self.assertIn("http://47.93.214.76/health/version", apply_script)
        self.assertNotIn("systemctl restart blogger-collector", apply_script)

    def test_release_trigger_is_independent(self) -> None:
        script = self.read("publish-via-git.sh")
        self.assertIn("wangbaocheng123-hash/sunmao-ai-community.git", script)
        self.assertIn("refs/heads/production", script)
        self.assertNotIn("refs/heads/beijing-production", script)
        self.assertNotIn("blogger-collector-git-deploy.service", script)
        self.assertIn("SUNMAO_GITHUB_WEBHOOK_TRIGGER_SENT", script)
        self.assertIn("DEPLOYMENT_PROBE_URL", script)
        self.assertIn("http://47.93.214.76/health/version", script)
        self.assertNotIn("remote_command=systemctl", script)

    def test_installer_keeps_collector_running_and_adds_no_timer(self) -> None:
        installer = self.read("install-independent-service.sh")
        self.assertIn("blogger-collector.service", installer)
        self.assertIn("collector must remain healthy", installer)
        self.assertIn("disable --now sunmao-community-git-deploy.timer", installer)
        self.assertIn("enable sunmao-ai-community.service", installer)
        self.assertNotIn("systemctl stop blogger-collector", installer)
        self.assertNotIn("systemctl restart blogger-collector", installer)

    def test_event_trigger_is_signed_scoped_and_has_no_resident_poller(self) -> None:
        path_unit = self.read("sunmao-community-deploy-trigger.path")
        webhook_installer = self.read("install-github-webhook-trigger.sh")
        app_service = self.read("sunmao-ai-community.service")
        deploy_service = self.read("sunmao-community-git-deploy.service")
        webhook_module = (PROJECT_ROOT / "sunmao_community" / "deploy_webhook.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("PathExists=/run/sunmao-community/deploy.trigger", path_unit)
        self.assertIn("Unit=sunmao-community-git-deploy.service", path_unit)
        self.assertNotIn("OnUnitActiveSec", path_unit)
        self.assertNotIn("OnCalendar", path_unit)
        self.assertIn("github-webhook.secret", webhook_installer)
        self.assertIn("standard input", webhook_installer)
        self.assertIn("blogger-collector.service", webhook_installer)
        self.assertNotIn("systemctl restart blogger-collector", webhook_installer)
        self.assertIn("RuntimeDirectory=sunmao-community", app_service)
        self.assertIn("ExecStartPre=-/usr/bin/rm -f /run/sunmao-community/deploy.trigger", deploy_service)
        self.assertIn("-/run/sunmao-community", deploy_service)
        self.assertIn("Restart=on-failure", deploy_service)
        self.assertIn("StartLimitBurst=3", deploy_service)
        self.assertIn('EXPECTED_REPOSITORY = "wangbaocheng123-hash/sunmao-ai-community"', webhook_module)
        self.assertIn('EXPECTED_REF = "refs/heads/production"', webhook_module)
        self.assertIn("hmac.compare_digest", webhook_module)


if __name__ == "__main__":
    unittest.main()

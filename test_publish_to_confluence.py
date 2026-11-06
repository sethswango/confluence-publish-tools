import contextlib
import io
import os
import unittest
from pathlib import Path
from unittest import mock

import publish_to_confluence as p

REQUIRED = [__file__, "--space-id", "1", "--parent-id", "2"]


def parse(argv, env):
    """parse_args under exactly this environment; returns (args or None, exit code or None, stderr)."""
    err = io.StringIO()
    with mock.patch.dict(os.environ, env, clear=True), contextlib.redirect_stderr(err):
        try:
            return p.parse_args(argv), None, err.getvalue()
        except SystemExit as e:
            return None, e.code, err.getvalue()


class TokenComesOnlyFromEnvironmentTest(unittest.TestCase):
    def test_token_read_from_environment(self):
        args, code, _ = parse(REQUIRED, {"CONFLUENCE_EMAIL": "fake@example.com", "CONFLUENCE_TOKEN": "env-token"})
        self.assertIsNone(code)
        self.assertEqual(args.token, "env-token")
        self.assertEqual(args.email, "fake@example.com")

    def test_token_flag_refused_without_echoing_it(self):
        env = {"CONFLUENCE_EMAIL": "fake@example.com", "CONFLUENCE_TOKEN": "env-token"}
        for argv in (REQUIRED + ["--token", "fake-token-123"], REQUIRED + ["--token=fake-token-123"],
                     REQUIRED + ["--tok", "fake-token-123"]):
            args, code, err = parse(argv, env)
            self.assertIsNone(args)
            self.assertEqual(code, 2)
            self.assertIn("CONFLUENCE_TOKEN", err)
            self.assertNotIn("fake-token-123", err)

    def test_missing_environment_token_is_an_error(self):
        args, code, err = parse(REQUIRED + ["--email", "fake@example.com"], {})
        self.assertIsNone(args)
        self.assertEqual(code, 2)
        self.assertIn("CONFLUENCE_TOKEN", err)

    def test_help_does_not_offer_token(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit) as cm:
                p.parse_args(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertNotIn("--token", out.getvalue())


class AuthStaysOffArgvTest(unittest.TestCase):
    def test_authorization_never_in_curl_argv(self):
        auth = p.auth_header("fake@example.com", "fake-token-123")
        calls = []

        def fake_run(args, **kwargs):
            calls.append((args, kwargs))
            out = '{"id": "1", "version": {"number": 1}}' if "-w" not in args else "200"
            return mock.Mock(stdout=out, stderr="", returncode=0)

        with mock.patch.object(p.subprocess, "run", side_effect=fake_run):
            p.upload_attachment("1", Path("diagram_1.png"), auth)
            p.create_page("s", "parent", "t", "<p/>", auth)
            p.get_page_version("1", auth)
            p.update_page("1", "t", "<p/>", 2, auth)

        self.assertEqual(len(calls), 4)
        for args, kwargs in calls:
            argv = " ".join(args)
            self.assertNotIn(auth, argv)
            self.assertNotIn("fake-token-123", argv)
            self.assertNotIn("Authorization", argv)
            self.assertIn(f"Authorization: Basic {auth}", kwargs["input"])


if __name__ == "__main__":
    unittest.main()

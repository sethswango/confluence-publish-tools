import unittest
from pathlib import Path
from unittest import mock

import publish_to_confluence as p


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

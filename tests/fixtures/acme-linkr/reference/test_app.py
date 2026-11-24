"""The builder's own unit tests for the reference build. They pass, and they never try a javascript address."""
import unittest

import app


class SchemeTests(unittest.TestCase):
    def test_https_is_accepted(self):
        self.assertTrue(app.valid_scheme("https://example.com/a"))

    def test_ftp_is_refused(self):
        self.assertFalse(app.valid_scheme("ftp://example.com/a"))


if __name__ == "__main__":
    unittest.main()

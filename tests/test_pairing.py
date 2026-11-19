import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lan import token_for

class PairingTests(unittest.TestCase):
    def test_repeatable_code(self):
        self.assertEqual(token_for("1234"), token_for("1234"))
    def test_different_codes(self):
        self.assertNotEqual(token_for("1234"), token_for("4321"))
    def test_reject_short_code(self):
        with self.assertRaises(ValueError):
            token_for("123")

if __name__ == "__main__":
    unittest.main()

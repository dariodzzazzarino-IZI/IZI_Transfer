import json
import unittest
from unittest.mock import patch
from discovery import Discovery, MAGIC

class DiscoveryTests(unittest.TestCase):
    def test_defaults(self):
        d = Discovery("Studio", lambda _: None)
        self.assertEqual(d.receive_port, 8765)
        self.assertEqual(d.devices, {})
        self.assertFalse(d.running)

    def test_magic(self):
        self.assertEqual(json.loads(json.dumps({"magic": MAGIC}))["magic"], MAGIC)

if __name__ == "__main__":
    unittest.main()

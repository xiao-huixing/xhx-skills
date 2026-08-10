import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.feature_flags import enabled


class FeatureFlagsTest(unittest.TestCase):
    def test_beta_search_is_enabled_by_default(self):
        self.assertTrue(enabled("beta_search"))


if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from decimal import Decimal
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pricing import total


class PricingTest(unittest.TestCase):
    def test_total_preserves_amount(self):
        self.assertEqual(Decimal("12.345"), total(Decimal("12.345")))


if __name__ == "__main__":
    unittest.main()

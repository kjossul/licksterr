import unittest
from src.guitar import Guitar


class TestGuitar(unittest.TestCase):
    def test(self):
        guitar = Guitar()
        self.assertEqual("{1: 'E', 2: 'B', 3: 'G', 4: 'D', 5: 'A', 6: 'E'}", str(guitar))


if __name__ == '__main__':
    unittest.main()

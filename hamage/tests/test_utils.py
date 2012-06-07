import unittest

class TestUtilFunctions(unittest.TestCase):


    def test_shorten_line(self):
        from hamage.filter import shorten_line
        self.assertEqual(shorten_line(''), '')
        self.assertEqual(shorten_line('okay really'), 'okay really')
        self.assertEqual(
            shorten_line("this can play until it gets really super dark, bu that's what happens normally"),
            "this can play until it gets really super dark, bu that's what happens ...")


if __name__ == '__main__':
    unittest.main()

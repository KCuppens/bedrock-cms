"""Simple test to verify Django test infrastructure works."""

from django.test import TestCase


class SimpleTest(TestCase):
    """Simple test case to verify testing works."""

    def test_basic_math(self):
        """Test that basic math works."""
        self.assertEqual(1 + 1, 2)

    def test_string_operations(self):
        """Test string operations."""
        self.assertEqual("hello" + " " + "world", "hello world")

    def test_list_operations(self):
        """Test list operations."""
        test_list = [1, 2, 3]
        test_list.append(4)
        self.assertEqual(len(test_list), 4)
        self.assertEqual(test_list[-1], 4)

import unittest
from blast import AlignmentPart


class TestAlignmentPart(unittest.TestCase):
    def setUp(self):
        self.alignment_part = AlignmentPart()

    def test_default_values(self):
        self.assertEqual(self.alignment_part.start, 0)
        self.assertEqual(self.alignment_part.end, 0)
        self.assertEqual(self.alignment_part.strand, "+")
        self.assertEqual(self.alignment_part.sequence, "")

    def test_setting_values(self):
        self.alignment_part.start = 10
        self.alignment_part.end = 20
        self.alignment_part.strand = "-"
        self.alignment_part.sequence = "ATCG"

        self.assertEqual(self.alignment_part.start, 10)
        self.assertEqual(self.alignment_part.end, 20)
        self.assertEqual(self.alignment_part.strand, "-")
        self.assertEqual(self.alignment_part.sequence, "ATCG")

    def test_as_dict(self):
        self.alignment_part.start = 10
        self.alignment_part.end = 20
        self.alignment_part.strand = "-"
        self.alignment_part.sequence = "ATCG"

        expected_dict = {
            "start": 10,
            "end": 20,
            "strand": "-",
            "sequence": "ATCG"
        }

        self.assertEqual(self.alignment_part.as_dict(), expected_dict)


if __name__ == '__main__':
    unittest.main()
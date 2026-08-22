import contextlib
import io
import unittest
from pathlib import Path

from csv_snapshot_demo import CSVSnapshotSession, generate_sample_files

TEST_DATA = Path(__file__).parent / "test_data"


class CSVSnapshotDemoTests(unittest.TestCase):
    def test_generated_sample_detects_all_four_change_types(self) -> None:
        before, after, sql = generate_sample_files(TEST_DATA, rows=100)
        session = CSVSnapshotSession()
        commit_output = io.StringIO()
        with contextlib.redirect_stdout(commit_output):
            first = session.commit_csv(
                before,
                table="users",
                primary_key="id",
                message="before",
            )
            second = session.commit_csv(
                after,
                table="users",
                primary_key="id",
                message="after",
                sql_file=sql,
            )

        diff_output = io.StringIO()
        with contextlib.redirect_stdout(diff_output):
            changed = session.show_diff(first, second)

        self.assertNotIn("Diff v1 -> v2", commit_output.getvalue())
        self.assertIn("Diff v1 -> v2", diff_output.getvalue())
        self.assertEqual(
            changed,
            ["users:10", "users:101", "users:50", "users:90"],
        )
        self.assertIn("UPDATE users", session.commit_metadata[2]["sql_text"])
        self.assertEqual(session.commit_metadata[1]["commit_mode"], "full import")
        self.assertEqual(
            session.commit_metadata[2]["commit_mode"], "incremental batch"
        )
        self.assertEqual(session.db.commit_stats[2].changed_keys, 4)
        self.assertNotEqual(
            session.db.versions[first], session.db.versions[second]
        )

    def test_duplicate_primary_key_is_rejected(self) -> None:
        path = TEST_DATA / "duplicate.csv"
        path.write_text("id,name\n1,Asha\n1,Ravi\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "duplicate primary key"):
            CSVSnapshotSession.load_csv(path, "users", "id")

    def test_missing_primary_key_column_is_rejected(self) -> None:
        path = TEST_DATA / "missing.csv"
        path.write_text("name,status\nAsha,active\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "not found"):
            CSVSnapshotSession.load_csv(path, "users", "id")


if __name__ == "__main__":
    unittest.main()

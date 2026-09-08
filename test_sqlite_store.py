import contextlib
import io
import sqlite3
import unittest
from pathlib import Path

from csv_snapshot_demo import CSVSnapshotSession, generate_sample_files
from sqlite_store import RevonIntegrityError, SQLiteRevonRepository

TEST_DATA = Path(__file__).parent / "test_data" / "sqlite"


class SQLiteRevonRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        TEST_DATA.mkdir(parents=True, exist_ok=True)
        for name in (
            "history.revon.db",
            "atomic.revon.db",
            "tampered.revon.db",
            "csv-history.revon.db",
        ):
            path = TEST_DATA / name
            if path.exists():
                path.unlink()
            journal = Path(str(path) + "-journal")
            if journal.exists():
                journal.unlink()

    def test_reopen_reproduces_history_checkout_diff_and_metrics(self) -> None:
        path = TEST_DATA / "history.revon.db"
        initial = {
            "a": {"value": 1},
            "b": {"value": 2},
            "nullable": None,
        }
        with SQLiteRevonRepository.create(path) as repository:
            root_v1 = repository.commit(initial, message="initial")
            root_v2 = repository.apply_changes(
                root_v1,
                puts={"a": {"value": 9}, "added": None},
                deletes={"b"},
                message="mixed batch",
            )
            commit_hashes = dict(repository.version_commits)
            self.assertEqual(repository.verify_integrity().versions, 2)

        with SQLiteRevonRepository.open(path) as reopened:
            self.assertEqual(reopened.head, 2)
            self.assertEqual(reopened.versions, {1: root_v1, 2: root_v2})
            self.assertEqual(reopened.version_commits, commit_hashes)
            self.assertEqual(reopened.checkout(1), initial)
            self.assertEqual(
                reopened.checkout(2),
                {"a": {"value": 9}, "nullable": None, "added": None},
            )
            self.assertEqual(
                reopened.diff_versions(1, 2, strategy="log"),
                reopened.diff_versions(1, 2, strategy="merkle"),
            )
            self.assertEqual(
                [entry.message for entry in reopened.log()],
                ["mixed batch", "initial"],
            )
            self.assertEqual(reopened.commit_stats[2].changed_keys, 3)
            report = reopened.verify_integrity()
            self.assertEqual(report.commits, 2)
            self.assertEqual(report.changesets, 2)
            self.assertEqual(report.head_hash, commit_hashes[2])

    def test_failed_transaction_restores_in_memory_head(self) -> None:
        path = TEST_DATA / "atomic.revon.db"
        with SQLiteRevonRepository.create(path) as repository:
            root = repository.commit({"a": 1}, message="durable")
            durable_head = repository.head_hash
            repository._connection.execute(
                """
                CREATE TRIGGER reject_new_version
                BEFORE INSERT ON versions
                BEGIN
                    SELECT RAISE(ABORT, 'injected transaction failure');
                END
                """
            )

            with self.assertRaisesRegex(
                sqlite3.DatabaseError, "injected transaction failure"
            ):
                repository.apply_changes(root, puts={"b": 2})

            self.assertEqual(repository.head, 1)
            self.assertEqual(repository.head_hash, durable_head)
            self.assertEqual(repository.checkout(1), {"a": 1})
            self.assertEqual(repository.verify_integrity().versions, 1)

        with SQLiteRevonRepository.open(path) as reopened:
            self.assertEqual(reopened.head, 1)
            self.assertEqual(reopened.checkout(1), {"a": 1})

    def test_tampered_payload_is_rejected_on_open(self) -> None:
        path = TEST_DATA / "tampered.revon.db"
        with SQLiteRevonRepository.create(path) as repository:
            repository.commit({"a": 1})
            node_hash = repository.versions[1]

        connection = sqlite3.connect(path)
        connection.execute(
            "UPDATE objects SET payload = ? WHERE hash = ?",
            (b"{}", node_hash),
        )
        connection.commit()
        connection.close()

        with self.assertRaisesRegex(RevonIntegrityError, "hash mismatch"):
            SQLiteRevonRepository.open(path)

    def test_csv_session_continues_after_repository_reopen(self) -> None:
        before, after, sql = generate_sample_files(TEST_DATA, rows=100)
        path = TEST_DATA / "csv-history.revon.db"

        with SQLiteRevonRepository.create(path) as repository:
            session = CSVSnapshotSession(repository)
            with contextlib.redirect_stdout(io.StringIO()):
                first = session.commit_csv(
                    before,
                    table="users",
                    primary_key="id",
                    message="before",
                )

        with SQLiteRevonRepository.open(path) as repository:
            session = CSVSnapshotSession(repository)
            with contextlib.redirect_stdout(io.StringIO()):
                second = session.commit_csv(
                    after,
                    table="users",
                    primary_key="id",
                    message="after",
                    sql_file=sql,
                )

        with SQLiteRevonRepository.open(path) as repository:
            self.assertEqual((first, second), (1, 2))
            self.assertEqual(len(repository.checkout(1)), 100)
            self.assertEqual(len(repository.checkout(2)), 100)
            self.assertEqual(
                [entry.key for entry in repository.diff_versions(1, 2)],
                ["users:10", "users:101", "users:50", "users:90"],
            )
            self.assertEqual(repository.verify_integrity().versions, 2)


if __name__ == "__main__":
    unittest.main()

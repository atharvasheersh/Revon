import unittest

from versioned_db import VersionedDatabase


class VersionedDatabaseTests(unittest.TestCase):
    def test_same_state_has_same_root_and_is_fully_reused(self) -> None:
        db = VersionedDatabase()
        state = {"a": 1, "b": 2}
        first = db.commit(state)
        second = db.commit(dict(reversed(list(state.items()))))

        self.assertEqual(first, second)
        self.assertEqual(db.commit_stats[2].new_nodes, 0)
        self.assertEqual(db.commit_stats[2].shared_percent, 100.0)

    def test_diff_finds_added_removed_and_updated_keys(self) -> None:
        db = VersionedDatabase()
        first = db.commit({"removed": 1, "updated": "old", "same": True})
        second = db.commit({"added": 2, "updated": "new", "same": True})

        self.assertEqual(db.diff(first, second), ["added", "removed", "updated"])
        self.assertGreater(db.last_diff_stats.matching_subtrees_skipped, 0)

    def test_diff_of_identical_roots_stops_at_root(self) -> None:
        db = VersionedDatabase()
        root = db.commit({"a": 1, "b": 2})

        self.assertEqual(db.diff(root, root), [])
        self.assertEqual(db.last_diff_stats.nodes_compared, 1)
        self.assertEqual(db.last_diff_stats.matching_subtrees_skipped, 1)

    def test_small_change_reuses_most_nodes(self) -> None:
        db = VersionedDatabase()
        state = {f"key-{i:04d}": i for i in range(1_000)}
        first = db.commit(state)
        state["key-0500"] = "changed"
        second = db.commit(state)

        self.assertNotEqual(first, second)
        self.assertEqual(db.diff(first, second), ["key-0500"])
        self.assertGreater(db.commit_stats[2].shared_percent, 95.0)

    def test_versions_map_to_roots(self) -> None:
        db = VersionedDatabase()
        first = db.commit({"a": 1})
        second = db.commit({"a": 2})

        self.assertEqual(db.versions, {1: first, 2: second})

    def test_rejects_invalid_data_without_creating_version(self) -> None:
        db = VersionedDatabase()

        with self.assertRaises(TypeError):
            db.commit({"bad": object()})
        self.assertEqual(db.versions, {})


if __name__ == "__main__":
    unittest.main()


import random
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


class IncrementalBatchTests(unittest.TestCase):
    def test_batch_matches_full_rebuild_and_creates_one_version(self) -> None:
        state = {f"key-{index:05d}": index for index in range(2_000)}
        db = VersionedDatabase()
        first = db.commit(state, message="base")
        nodes_before = len(db.node_store)

        puts = {
            "key-00010": "changed",
            "key-01000": None,
            "new-key": {"status": "new"},
        }
        second = db.apply_changes(
            first,
            puts=puts,
            deletes={"key-01999"},
            message="one atomic batch",
        )

        expected = dict(state)
        expected.update(puts)
        del expected["key-01999"]
        rebuilt = VersionedDatabase()
        self.assertEqual(second, rebuilt.commit(expected))
        self.assertEqual(db.materialize(second), expected)
        self.assertEqual(len(db.versions), 2)
        self.assertEqual(db.commit_stats[2].changed_keys, 4)
        self.assertLessEqual(
            len(db.node_store) - nodes_before,
            4 * (db.tree_depth + 1),
        )

    def test_get_reads_one_version_and_missing_key_fails(self) -> None:
        db = VersionedDatabase()
        root = db.commit({"present": {"value": 7}})

        self.assertEqual(db.get(root, "present"), {"value": 7})
        with self.assertRaises(KeyError):
            db.get(root, "missing")

    def test_invalid_delete_is_atomic(self) -> None:
        db = VersionedDatabase()
        root = db.commit({"a": 1})
        node_count = len(db.node_store)

        with self.assertRaises(KeyError):
            db.apply_changes(root, puts={"b": 2}, deletes={"missing"})

        self.assertEqual(len(db.versions), 1)
        self.assertEqual(len(db.node_store), node_count)

    def test_no_op_batch_reuses_root_and_records_empty_changeset(self) -> None:
        db = VersionedDatabase()
        first = db.commit({"a": 1})
        second = db.apply_changes(first, puts={"a": 1})

        self.assertEqual(first, second)
        self.assertEqual(db.commit_stats[2].new_nodes, 0)
        self.assertEqual(db.commit_stats[2].changed_keys, 0)

    def test_non_head_write_is_rejected_until_branching_exists(self) -> None:
        db = VersionedDatabase()
        first = db.commit({"a": 1})
        db.apply_changes(first, puts={"a": 2})

        with self.assertRaisesRegex(ValueError, "target HEAD"):
            db.apply_changes(first, puts={"branch": True})

    def test_structural_sharing_is_exact_reachable_node_overlap(self) -> None:
        db = VersionedDatabase()
        first = db.commit({f"key-{index:05d}": index for index in range(5_000)})
        second = db.apply_changes(first, puts={"key-02500": "changed"})

        sharing = db.structural_sharing(first, second)
        self.assertEqual(sharing.shared_nodes, sharing.right_nodes - 5)
        self.assertGreater(sharing.right_shared_percent, 99.0)

    def test_random_batch_sequence_matches_canonical_full_rebuilds(self) -> None:
        random_source = random.Random(20260821)
        state = {f"key-{index:04d}": index for index in range(300)}
        db = VersionedDatabase()
        root = db.commit(state)

        for round_number in range(25):
            existing = sorted(state)
            deletes = set(random_source.sample(existing, 2))
            update_keys = random_source.sample(
                [key for key in existing if key not in deletes], 4
            )
            puts = {
                key: {"round": round_number, "value": random_source.randrange(10_000)}
                for key in update_keys
            }
            puts.update(
                {
                    f"new-{round_number:03d}-{index}": random_source.randrange(10_000)
                    for index in range(3)
                }
            )

            root = db.apply_changes(root, puts=puts, deletes=deletes)
            state.update(puts)
            for key in deletes:
                del state[key]

            rebuilt = VersionedDatabase()
            self.assertEqual(root, rebuilt.commit(state))
            self.assertEqual(db.materialize(root), state)

        self.assertEqual(
            db.diff_versions(1, db.head, strategy="log"),
            db.diff_versions(1, db.head, strategy="merkle"),
        )


class ContentAddressedCommitTests(unittest.TestCase):
    def test_commit_and_changeset_are_addressed_and_parented_by_hash(self) -> None:
        db = VersionedDatabase()
        first_root = db.commit({"a": 1}, message="base")
        first = db.commits[1]
        db.apply_changes(first_root, puts={"a": 2}, message="change")
        second = db.commits[2]

        self.assertIn(first.commit_hash, db.commit_store)
        self.assertIn(second.commit_hash, db.commit_store)
        self.assertIn(second.changeset_hash, db.changeset_store)
        self.assertEqual(second.parent, 1)
        self.assertEqual(second.parent_hash, first.commit_hash)
        self.assertEqual(db.head_hash, second.commit_hash)
        self.assertEqual(
            second.commit_hash,
            db._content_hash("commit", db.commit_store[second.commit_hash]),
        )


class HybridDiffTests(unittest.TestCase):
    def _database(self, threshold: int = 128) -> VersionedDatabase:
        db = VersionedDatabase(hybrid_log_threshold=threshold)
        root = db.commit({"same": True, "updated": 1, "deleted": None})
        root = db.apply_changes(
            root,
            puts={"updated": 2, "added": None},
            deletes={"deleted"},
        )
        db.apply_changes(root, puts={"temporary": 1})
        db.apply_changes(db.versions[3], deletes={"temporary"})
        return db

    def test_structured_merkle_diff_preserves_change_types_and_nulls(self) -> None:
        db = self._database()
        entries = db.diff_versions(1, 2, strategy="merkle")
        by_key = {entry.key: entry for entry in entries}

        self.assertEqual(by_key["updated"].change_type, "modified")
        self.assertEqual(by_key["updated"].old_value, 1)
        self.assertEqual(by_key["updated"].new_value, 2)
        self.assertEqual(by_key["added"].change_type, "added")
        self.assertIsNone(by_key["added"].new_value)
        self.assertEqual(by_key["deleted"].change_type, "deleted")
        self.assertIsNone(by_key["deleted"].old_value)

    def test_log_and_merkle_modes_return_identical_results(self) -> None:
        db = self._database()
        log_entries = db.diff_versions(1, 4, strategy="log")
        merkle_entries = db.diff_versions(1, 4, strategy="merkle")

        self.assertEqual(log_entries, merkle_entries)
        self.assertNotIn("temporary", [entry.key for entry in log_entries])

    def test_hybrid_selects_log_for_short_history(self) -> None:
        db = self._database(threshold=10)
        db.diff_versions(1, 2, strategy="hybrid")

        self.assertEqual(db.last_diff_stats.strategy, "log")
        self.assertEqual(db.last_diff_stats.log_operations_examined, 3)

    def test_hybrid_selects_merkle_above_threshold(self) -> None:
        db = self._database(threshold=1)
        db.diff_versions(1, 2, strategy="hybrid")

        self.assertEqual(db.last_diff_stats.strategy, "merkle")
        self.assertGreater(db.last_diff_stats.nodes_compared, 0)

    def test_reverse_log_diff_reverses_added_and_deleted(self) -> None:
        db = self._database()
        entries = db.diff_versions(2, 1, strategy="log")
        by_key = {entry.key: entry for entry in entries}

        self.assertEqual(by_key["added"].change_type, "deleted")
        self.assertEqual(by_key["deleted"].change_type, "added")


if __name__ == "__main__":
    unittest.main()

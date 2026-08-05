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


class IncrementalUpdateTests(unittest.TestCase):
    """put()/delete() must land on exactly the hash a full rebuild would."""

    def test_put_matches_full_rebuild_on_random_mutations(self) -> None:
        random_source = random.Random(20260804)
        trials = 0
        for starting_size in (1, 5, 50, 500):
            state = {f"key-{i:05d}": i for i in range(starting_size)}
            db = VersionedDatabase()
            root = db.commit(state)

            for _ in range(6):
                trials += 1
                if random_source.random() < 0.5:
                    # Overwrite an existing key.
                    key = random_source.choice(sorted(state))
                    value = f"changed-{random_source.randrange(10_000)}"
                else:
                    # Insert a brand new key.
                    key = f"new-{random_source.randrange(10_000_000):08d}"
                    value = random_source.randrange(10_000)

                incremental_root = db.put(root, key, value)
                expected_state = dict(state)
                expected_state[key] = value

                rebuilt = VersionedDatabase()
                rebuilt_root = rebuilt.commit(expected_state)

                self.assertEqual(incremental_root, rebuilt_root)
                self.assertEqual(db.materialize(incremental_root), expected_state)
                state = expected_state
                root = incremental_root

        self.assertGreaterEqual(trials, 20)

    def test_delete_matches_full_rebuild_including_emptied_buckets(self) -> None:
        random_source = random.Random(7)
        for starting_size in (2, 40, 400):
            state = {f"key-{i:05d}": i for i in range(starting_size)}
            db = VersionedDatabase()
            root = db.commit(state)

            for _ in range(min(8, starting_size)):
                key = random_source.choice(sorted(state))
                incremental_root = db.delete(root, key)
                expected_state = {k: v for k, v in state.items() if k != key}

                rebuilt = VersionedDatabase()
                self.assertEqual(incremental_root, rebuilt.commit(expected_state))
                self.assertEqual(db.materialize(incremental_root), expected_state)
                state = expected_state
                root = incremental_root

    def test_deleting_every_key_collapses_to_the_empty_root(self) -> None:
        """Cascading empties, all the way up to a bare root node."""
        db = VersionedDatabase()
        state = {f"key-{i:03d}": i for i in range(25)}
        root = db.commit(state)
        for key in sorted(state):
            root = db.delete(root, key)

        empty = VersionedDatabase()
        self.assertEqual(root, empty.commit({}))
        self.assertEqual(db.materialize(root), {})

    def test_put_touches_only_the_routed_path(self) -> None:
        db = VersionedDatabase()
        root = db.commit({f"key-{i:06d}": i for i in range(100_000)})
        nodes_before = len(db.node_store)

        for index, key in enumerate(("key-000001", "key-050000", "key-099999")):
            root = db.put(root, key, f"changed-{index}")

        created = len(db.node_store) - nodes_before
        self.assertLessEqual(created, 3 * (db.tree_depth + 1))
        self.assertEqual(db.materialize(root)["key-050000"], "changed-1")

    def test_delete_of_absent_key_is_rejected(self) -> None:
        db = VersionedDatabase()
        root = db.commit({"a": 1})

        with self.assertRaises(KeyError):
            db.delete(root, "missing")

    def test_put_rejects_unserializable_value_without_creating_version(self) -> None:
        db = VersionedDatabase()
        root = db.commit({"a": 1})

        with self.assertRaises(TypeError):
            db.put(root, "b", object())
        self.assertEqual(list(db.versions), [1])


class CommitGraphTests(unittest.TestCase):
    def test_log_walks_parents_back_from_head(self) -> None:
        db = VersionedDatabase()
        db.commit({"a": 1}, message="first")
        db.commit({"a": 2}, message="second")
        db.commit({"a": 3}, message="third")

        history = db.log()
        self.assertEqual([entry.version for entry in history], [3, 2, 1])
        self.assertEqual(
            [entry.message for entry in history], ["third", "second", "first"]
        )
        self.assertEqual([entry.parent for entry in history], [2, 1, None])
        self.assertEqual(db.head, 3)

    def test_put_and_delete_record_commits_parented_on_head(self) -> None:
        db = VersionedDatabase()
        root = db.commit({"a": 1}, message="base")
        root = db.put(root, "b", 2, message="add b")
        db.delete(root, "a", message="drop a")

        history = db.log()
        self.assertEqual(
            [entry.message for entry in history], ["drop a", "add b", "base"]
        )
        self.assertEqual([entry.parent for entry in history], [2, 1, None])

    def test_checkout_returns_earlier_state_after_later_commits(self) -> None:
        db = VersionedDatabase()
        original = {"a": 1, "b": 2}
        db.commit(original, message="v1")
        db.commit({"a": 99, "b": 2}, message="v2")
        db.commit({"a": 99, "b": 2, "c": 3}, message="v3")

        self.assertEqual(db.checkout(1), original)
        self.assertEqual(db.checkout(2), {"a": 99, "b": 2})
        self.assertEqual(db.checkout(3), {"a": 99, "b": 2, "c": 3})

    def test_checkout_of_unknown_version_is_rejected(self) -> None:
        db = VersionedDatabase()
        db.commit({"a": 1})

        with self.assertRaises(KeyError):
            db.checkout(2)


if __name__ == "__main__":
    unittest.main()


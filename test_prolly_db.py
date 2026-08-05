import random
import statistics
import unittest

from prolly_db import ProllyStore


class ChunkingTests(unittest.TestCase):
    def test_same_keys_give_same_root_regardless_of_insert_order(self) -> None:
        """History independence: the defining property of a Prolly tree."""
        state = {f"key-{i:05d}": i for i in range(500)}
        shuffled = list(state.items())
        random.Random(11).shuffle(shuffled)

        first = ProllyStore().commit(state)
        second = ProllyStore().commit(dict(shuffled))

        self.assertEqual(first, second)

    def test_incremental_inserts_reach_the_same_root_as_a_bulk_commit(self) -> None:
        """Order of arrival must not matter, even one key at a time."""
        state = {f"key-{i:05d}": i for i in range(300)}
        bulk = ProllyStore().commit(state)

        incremental = ProllyStore()
        root = incremental.commit({})
        keys = list(state)
        random.Random(4).shuffle(keys)
        for key in keys:
            root = incremental.put(root, key, state[key])

        self.assertEqual(root, bulk)

    def test_chunk_size_stays_near_target_at_every_scale(self) -> None:
        """The property the fixed-fanout trie does not have."""
        for rows in (1_000, 10_000, 50_000):
            store = ProllyStore(target_chunk_size=32)
            root = store.commit({f"key-{i:08d}": i for i in range(rows)})
            mean = statistics.mean(store.chunk_sizes(root))
            # Geometric around the target; generous bounds, but crucially
            # they do not widen as the dataset grows.
            self.assertGreater(mean, 8, f"{rows} rows")
            self.assertLess(mean, 96, f"{rows} rows")

    def test_tree_grows_deeper_rather_than_fatter(self) -> None:
        small = ProllyStore()
        deep = ProllyStore()
        small_root = small.commit({f"key-{i:08d}": i for i in range(500)})
        deep_root = deep.commit({f"key-{i:08d}": i for i in range(200_000)})

        self.assertGreater(deep.depth(deep_root), small.depth(small_root))

    def test_target_chunk_size_must_be_a_power_of_two(self) -> None:
        with self.assertRaises(ValueError):
            ProllyStore(target_chunk_size=30)


class IncrementalTests(unittest.TestCase):
    def test_put_matches_full_rebuild_on_random_mutations(self) -> None:
        source = random.Random(20260805)
        for size in (1, 40, 400):
            state = {f"key-{i:05d}": i for i in range(size)}
            store = ProllyStore()
            root = store.commit(state)

            for _ in range(10):
                if source.random() < 0.5:
                    key = source.choice(sorted(state))
                    value = f"changed-{source.randrange(9999)}"
                else:
                    key = f"key-{source.randrange(99999):05d}"
                    value = source.randrange(9999)

                root = store.put(root, key, value)
                state[key] = value

                self.assertEqual(root, ProllyStore().commit(state))
                self.assertEqual(store.materialize(root), state)

    def test_delete_matches_full_rebuild(self) -> None:
        source = random.Random(99)
        for size in (2, 60, 500):
            state = {f"key-{i:05d}": i for i in range(size)}
            store = ProllyStore()
            root = store.commit(state)

            for _ in range(min(12, size)):
                key = source.choice(sorted(state))
                root = store.delete(root, key)
                del state[key]

                self.assertEqual(root, ProllyStore().commit(state))
                self.assertEqual(store.materialize(root), state)

    def test_deleting_every_key_collapses_to_the_empty_root(self) -> None:
        store = ProllyStore()
        state = {f"key-{i:04d}": i for i in range(60)}
        root = store.commit(state)
        for key in sorted(state):
            root = store.delete(root, key)

        self.assertEqual(root, ProllyStore().commit({}))
        self.assertEqual(store.materialize(root), {})

    def test_delete_of_absent_key_is_rejected(self) -> None:
        store = ProllyStore()
        root = store.commit({"a": 1})

        with self.assertRaises(KeyError):
            store.delete(root, "missing")

    def test_edit_touches_only_a_local_neighbourhood(self) -> None:
        store = ProllyStore()
        root = store.commit({f"key-{i:06d}": i for i in range(20_000)})
        leaves_before = len(store.chunk_sizes(root))
        nodes_before = len(store.node_store)

        root = store.put(root, "key-010000", "changed")

        # A handful of new nodes, not a rebuilt tree.
        self.assertLess(len(store.node_store) - nodes_before, 60)
        self.assertLessEqual(abs(len(store.chunk_sizes(root)) - leaves_before), 2)


class ReadTests(unittest.TestCase):
    def test_range_scan_matches_sorted_slice(self) -> None:
        store = ProllyStore()
        state = {f"key-{i:05d}": i for i in range(2_000)}
        root = store.commit(state)

        expected = [
            (key, value)
            for key, value in sorted(state.items())
            if "key-00500" <= key < "key-00700"
        ]
        self.assertEqual(store.range_scan(root, "key-00500", "key-00700"), expected)

    def test_range_scan_on_empty_and_open_ranges(self) -> None:
        store = ProllyStore()
        root = store.commit({f"key-{i:03d}": i for i in range(50)})

        self.assertEqual(store.range_scan(root, "zzz", "zzzz"), [])
        self.assertEqual(len(store.range_scan(root, "", "zzz")), 50)

    def test_get_finds_keys_and_rejects_missing_ones(self) -> None:
        store = ProllyStore()
        root = store.commit({f"key-{i:04d}": i * 2 for i in range(500)})

        self.assertEqual(store.get(root, "key-0250"), 500)
        with self.assertRaises(KeyError):
            store.get(root, "nope")

    def test_checkout_and_log_track_history(self) -> None:
        store = ProllyStore()
        original = {"a": 1, "b": 2}
        root = store.commit(original, message="v1")
        root = store.put(root, "a", 99, message="v2")
        store.delete(root, "b", message="v3")

        self.assertEqual(store.checkout(1), original)
        self.assertEqual(store.checkout(3), {"a": 99})
        self.assertEqual([c.message for c in store.log()], ["v3", "v2", "v1"])
        self.assertEqual([c.parent for c in store.log()], [2, 1, None])


class DiffTests(unittest.TestCase):
    def test_diff_matches_brute_force_on_random_edits(self) -> None:
        source = random.Random(5)
        for _ in range(10):
            left = {f"key-{i:05d}": source.randrange(100) for i in range(400)}
            right = dict(left)
            for _ in range(source.randrange(1, 15)):
                choice = source.random()
                if choice < 0.4:
                    right[source.choice(sorted(right))] = "edited"
                elif choice < 0.7:
                    del right[source.choice(sorted(right))]
                else:
                    right[f"new-{source.randrange(99999):05d}"] = 1

            store = ProllyStore()
            left_root = store.commit(left)
            right_root = store.commit(right)

            expected = sorted(
                key
                for key in set(left) | set(right)
                if left.get(key, object()) != right.get(key, object())
            )
            self.assertEqual(store.diff(left_root, right_root), expected)

    def test_diff_of_identical_roots_stops_at_the_root(self) -> None:
        store = ProllyStore()
        root = store.commit({f"key-{i:04d}": i for i in range(100)})

        self.assertEqual(store.diff(root, root), [])
        self.assertEqual(store.last_diff_stats.nodes_compared, 1)
        self.assertEqual(store.last_diff_stats.matching_subtrees_skipped, 1)

    def test_diff_skips_matching_subtrees(self) -> None:
        store = ProllyStore()
        state = {f"key-{i:05d}": i for i in range(5_000)}
        left = store.commit(state)
        right = store.put(left, "key-02500", "changed")

        self.assertEqual(store.diff(left, right), ["key-02500"])
        self.assertGreater(store.last_diff_stats.matching_subtrees_skipped, 0)


if __name__ == "__main__":
    unittest.main()

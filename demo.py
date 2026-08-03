"""Run the one-flow Chronos demo."""

from versioned_db import VersionedDatabase


def main() -> None:
    db = VersionedDatabase(branching_factor=8, tree_depth=4)
    state = {f"key-{number:04d}": f"value-{number}" for number in range(1_000)}

    root_v1 = db.commit(state)
    print(db.commit_stats[1])
    print(f"  root: {root_v1[:16]}...")

    state["key-0010"] = "changed-value"
    state["key-0500"] = "changed-value"
    state["key-0900"] = "changed-value"
    root_v2 = db.commit(state)
    print(db.commit_stats[2])
    print(f"  root: {root_v2[:16]}...")

    changed_keys = db.diff(root_v1, root_v2)
    print(f"diff v1 -> v2: {changed_keys}")
    print(f"  {db.last_diff_stats}")


if __name__ == "__main__":
    main()


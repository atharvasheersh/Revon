"""Run the one-flow Chronos demo."""

from versioned_db import VersionedDatabase


def main() -> None:
    db = VersionedDatabase(branching_factor=8, tree_depth=4)
    state = {f"key-{number:04d}": f"value-{number}" for number in range(1_000)}

    root_v1 = db.commit(state)
    print(db.commit_stats[1])
    print(f"  root: {root_v1[:16]}...")

    root_v2 = db.apply_changes(
        root_v1,
        puts={
            "key-0010": "changed-value",
            "key-0500": "changed-value",
            "key-0900": "changed-value",
        },
        message="change three records",
    )
    print(db.commit_stats[2])
    print(f"  root: {root_v2[:16]}...")
    sharing = db.structural_sharing(root_v1, root_v2)
    print(
        f"  exact structural sharing: {sharing.shared_nodes}/"
        f"{sharing.right_nodes} nodes ({sharing.right_shared_percent:.1f}%)"
    )

    changes = db.diff_versions(1, 2, strategy="hybrid")
    print(f"diff v1 -> v2: {[entry.key for entry in changes]}")
    print(f"  {db.last_diff_stats}")


if __name__ == "__main__":
    main()

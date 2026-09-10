import subprocess
import sys
import unittest
from pathlib import Path


TEST_DATABASE = (
    Path(__file__).parent / "test_data" / "sqlite" / "cli-demo.revon.db"
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RevonSQLiteDemoTests(unittest.TestCase):
    def test_cli_closes_and_reopens_in_child_process(self) -> None:
        TEST_DATABASE.parent.mkdir(parents=True, exist_ok=True)
        process = subprocess.run(
            [
                sys.executable,
                "-m",
                "examples.revon_sqlite_demo",
                "--database",
                str(TEST_DATABASE),
                "--rows",
                "100",
                "--reset",
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn("PASS  separate Python process reopened", process.stdout)
        self.assertIn("PASS  v1/v2 checkout", process.stdout)


if __name__ == "__main__":
    unittest.main()

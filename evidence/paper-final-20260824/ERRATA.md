# Original paper run errata

This bundle is retained unchanged as a record of the August 2026 run. Its
333 CSV rows are **executions**, comprising 74 warm-ups and 259 measured runs.
The primary five-system evaluation contains 175 measured runs, including 35
measured Dolt runs. The remaining 84 measured runs are selector calibration.

The original Dolt adapter checked successful execution of `dolt diff` and exact
initial and final historical checkout states. It did **not** parse or compare
the contents of Dolt's diff. Consequently, the 45 Dolt rows' `correctness=True`
flags do not establish semantic diff correctness. Their `changed_keys` values
were copied from the workload oracle and are **not measured Dolt counts**.
Do not use those fields as observations or cite this bundle as a fully
semantically validated comparison.

The later schema-version-2 run in `../paper-corrected-20260923/` uses parsed
JSON Dolt diffs and observed changed-key counts. Its diff latency includes
JSON formatting and parsing, so its timing protocol differs from this bundle.

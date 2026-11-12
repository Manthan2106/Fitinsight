# Evidence index

| Evidence ID | Reproducible command | Source | Result artifacts | Status |
| --- | --- | --- | --- | --- |
| P1-DATA-AUDIT | `python src/data_audit.py` | `data/raw/*.csv` (11 files) | `reports/evidence/P1/dataset_audit.csv`, `column_inventory.csv`, `run_manifest.json` (source hashes, timestamp, Python version, commit, daily quality flags) | PASS; 7 standard-library tests pass, including malformed rows, missing keys, and duplicate detection |
| P2-REPRODUCIBLE-PREPROCESSING | `python src/preprocess.py`; `python -m unittest discover -s tests -v` | 11 raw source CSVs; six committed `data/processed/` references | `reports/evidence/P2/run_manifest.json`, per-table `metrics.json`, and key-alignment proofs | PASS; six generated outputs have zero reference mismatches; 22 tests pass; originals preserved |

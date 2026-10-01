---
applyTo: "tools/serumfile.py"
---

- **Round-trip checks apply only to rewriting commands**: `read_editable` refuses a preset whose body does not re-encode byte for byte, because rewriting it would change more than the edit. Read-only commands (`verify`, `dump`, `matrix`, `rowcurves`, `diff`, `curve`, and `meta` with no `FIELD=VALUE`) never write a file, so they must not require a round-trip; `meta` without assignments only checks that the file is a preset. Do not suggest adding round-trip validation to read-only paths.
- **The canonical matrix order is defined and tested**: `matrix_key` and `MATRIX_GROUPS` define the destination-first order documented in `docs/SERUM-FILE-FORMAT.md`, and `sort_matrix` keeps every row, moves empty slots last, and changes nothing outside the matrix. The scrut tests check the order, idempotence, and that nothing else changes. When flagging `sortmatrix`, name the input or rows that sort incorrectly rather than asking for the serialization to be fixed in general.

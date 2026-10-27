"""Describe a SQLite world: tables, columns, row counts, sample rows, and date ranges.

    python inspect_sqlite.py <db> [--samples 3]

Read-only (opens the file in read-only mode). Use it before writing planters and oracles.
"""

from __future__ import annotations

import argparse
import sqlite3


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("db")
    parser.add_argument("--samples", type=int, default=3)
    args = parser.parse_args()

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    for table in tables:
        cols = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        fks = conn.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()
        print(f"\n## {table}  ({count} rows)")
        print("  columns: " + ", ".join(f"{c[1]} {c[2]}{' PK' if c[5] else ''}" for c in cols))
        for fk in fks:
            print(f"  fk: {fk[3]} -> {fk[2]}.{fk[4]}")
        for c in cols:
            name, ctype = c[1], (c[2] or "").upper()
            lname = name.lower()
            datelike = any(k in lname for k in ("date", "departure", "arrival", "scheduled"))
            if datelike or lname.endswith(("_at", "_time")) or "DATE" in ctype or "TIMESTAMP" in ctype:
                lo, hi = conn.execute(f'SELECT MIN("{name}"), MAX("{name}") FROM "{table}"').fetchone()
                print(f"  range {name}: {lo} .. {hi}")
        for row in conn.execute(f'SELECT * FROM "{table}" LIMIT {args.samples}'):
            print("  ", tuple(str(v)[:40] for v in row))


if __name__ == "__main__":
    main()

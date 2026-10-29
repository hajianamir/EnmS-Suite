#!/usr/bin/env python3
import re
import sys

CLAUSE_REGEX = re.compile(r"^ISO-50001:(4\.[1-4]|5\.[1-3]|6\.[1-3]|7\.[1-5]|8\.[1-3]|9\.[1-3]|10\.[1-3])$")
AC_REGEX = re.compile(r"^AC-[0-9]{2}[a-z]$")

def main():
    file_path = "docs/blueprint/17-traceability.md"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        sys.exit(1)

    clauses_found = set()
    ac_found = set()

    lines = content.split("\n")
    for line in lines:
        if line.startswith("| **ISO-50001:"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 6:
                clause = parts[0].replace("**", "")
                ac_id = parts[5]
                
                if CLAUSE_REGEX.match(clause):
                    clauses_found.add(clause)
                else:
                    print(f"Invalid Clause ID format: {clause}")
                
                if AC_REGEX.match(ac_id):
                    ac_found.add(ac_id)
                else:
                    print(f"Invalid AC ID format: {ac_id}")

    expected_clauses = [
        "ISO-50001:4.1", "ISO-50001:4.2", "ISO-50001:4.3", "ISO-50001:4.4",
        "ISO-50001:5.1", "ISO-50001:5.2", "ISO-50001:5.3",
        "ISO-50001:6.1", "ISO-50001:6.2", "ISO-50001:6.3",
        "ISO-50001:7.1", "ISO-50001:7.2", "ISO-50001:7.3", "ISO-50001:7.4", "ISO-50001:7.5",
        "ISO-50001:8.1", "ISO-50001:8.2", "ISO-50001:8.3",
        "ISO-50001:9.1", "ISO-50001:9.2", "ISO-50001:9.3",
        "ISO-50001:10.1", "ISO-50001:10.2", "ISO-50001:10.3"
    ]

    missing = set(expected_clauses) - clauses_found
    if missing:
        print(f"FAILED: Missing ISO clauses: {sorted(list(missing))}")
        sys.exit(1)

    print(f"SUCCESS: All {len(clauses_found)} required ISO 50001:2018 clauses validated against regex!")
    print(f"Validated AC IDs: {sorted(list(ac_found))}")
    sys.exit(0)

if __name__ == "__main__":
    main()

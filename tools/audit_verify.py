#!/usr/bin/env python3
import hashlib
import json
import sys

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

def calculate_record_hash(record, prev_hash):
    # Payload format for SHA-256 calculation
    raw_data = f"{record['id']}|{record['tenant_id']}|{record['entity_type']}|{record['entity_id']}|{record['action_type']}|{prev_hash}"
    return hashlib.sha256(raw_data.encode("utf-8")).hexdigest()

def verify_audit_chain(records):
    prev_hash = GENESIS_HASH
    for idx, record in enumerate(records):
        if record["previous_hash"] != prev_hash:
            print(f"TAMPER_DETECTED: Chain broken at record index {idx} (ID: {record['id']}). Previous hash mismatch.")
            return False
        
        calc_hash = calculate_record_hash(record, prev_hash)
        if record["cryptographic_hash"] != calc_hash:
            print(f"TAMPER_DETECTED: Record hash mismatch at index {idx} (ID: {record['id']}). Expected {calc_hash}, got {record['cryptographic_hash']}.")
            return False
        
        prev_hash = calc_hash
    
    print(f"SUCCESS: Audit trail verification passed for {len(records)} records. Hash chain intact.")
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: audit_verify.py <path_to_audit_records.json>")
        sys.exit(1)
        
    try:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            records = json.load(f)
        
        if verify_audit_chain(records):
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"Error reading audit file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

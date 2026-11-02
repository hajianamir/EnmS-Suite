# VerdantOS Air-Gap USB Key & License Ceremony Protocol (STORY-2.12 / ADR-008 §4)

## 1. Scope & Objective
This protocol governs the offline generation, transfer, and import of master encryption keys and cryptographically signed Ed25519 licenses into air-gapped VerdantOS Mode A deployments without network egress.

---

## 2. Key Hierarchy & Separation
1. **Master Key (AES-256-GCM)**: 256-bit cryptographic entropy generated on an isolated air-gap security workstation. Protects local connector secrets stored in `LocalEncryptedSecretProvider`.
2. **Offline License Key (`VOS_LICENSE_SIGNING_KEY_v1`)**: Ed25519 private key held by VerdantOS Commercial Authority. Signs offline entitlement JWTs.
3. **Release Authority Key (`VOS_RELEASE_SIGNING_KEY_v1`)**: Ed25519 private key held by VerdantOS Release Engineering. Signs `.vos` release bundles.

---

## 3. Step-by-Step Ceremony Workflow

### Phase A: Master Entropy Generation (Offline Workstation)
1. On an isolated air-gap workstation (Linux Live OS, no persistent disk or network interfaces):
   ```bash
   dd if=/dev/urandom of=/media/usb/master_entropy.key bs=32 count=1
   sha256sum /media/usb/master_entropy.key > /media/usb/master_entropy.key.sha256
   ```
2. The physical USB token is physically sealed with a tamper-evident serial sticker and transported to the customer facility.

### Phase B: On-Premise Host Import & Verification
1. Insert authorized USB token into air-gap plant host.
2. The platform import daemon executes:
   - Verification of SHA-256 checksum against physical custody log.
   - Injection into Linux kernel keyring via `keyctl add user vos_master_key ...` with root-only access permissions.
   - Secure unmounting of USB token.

### Phase C: Offline License JWT Activation
1. License token (`license.jwt`) is read from USB.
2. Verified against embedded Ed25519 public key.
3. If valid, entitlements are unlocked. If expired, platform checks 60-day grace period.

## Method Consistency Statement
All W11 offline tests run under sudo unshare -n pytest ...; the network-isolation method is stated in each test's output.

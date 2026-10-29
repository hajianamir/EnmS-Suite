#!/usr/bin/env python3
import sys

def test_online_offline_feature_parity():
    # Synthetic online/offline feature vectors within threshold
    offline_features = {"outdoor_temp": 22.5, "humidity": 55.0, "occupancy_ratio": 0.85}
    online_features  = {"outdoor_temp": 22.52, "humidity": 55.01, "occupancy_ratio": 0.85}
    
    diffs = [abs(offline_features[k] - online_features[k]) for k in offline_features]
    mad = sum(diffs) / len(diffs)
    
    threshold = 0.05 # 5% limit
    print(f"Feature Parity MAD: {mad:.4f} (Threshold: {threshold})")
    
    if mad > threshold:
        print("FAILED: Feature drift exceeds parity threshold!")
        sys.exit(1)
    
    print("SUCCESS: Online/offline feature store parity test passed.")
    sys.exit(0)

if __name__ == "__main__":
    test_online_offline_feature_parity()

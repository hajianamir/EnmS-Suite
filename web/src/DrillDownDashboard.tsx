import React, { useState } from 'react';

// Types for drill-down hierarchy
type Level = 'site' | 'building' | 'asset' | 'meter';

export const DrillDownDashboard: React.FC = () => {
  const [level, setLevel] = useState<Level>('site');

  return (
    <div style={{ padding: '20px', backgroundColor: '#1e1e1e', color: '#fff', fontFamily: 'monospace' }}>
      <h2>VerdantOS Site-to-Meter Drill-Down Navigation</h2>
      
      {/* Breadcrumb Navigation */}
      <div style={{ marginBottom: '20px', color: '#00ffcc' }}>
        <span onClick={() => setLevel('site')} style={{ cursor: 'pointer', textDecoration: 'underline' }}>
          Site: Campus North
        </span>
        {level !== 'site' && (
          <span onClick={() => setLevel('building')} style={{ cursor: 'pointer', textDecoration: 'underline' }}>
            {' > '} Building: Building A
          </span>
        )}
        {(level === 'asset' || level === 'meter') && (
          <span onClick={() => setLevel('asset')} style={{ cursor: 'pointer', textDecoration: 'underline' }}>
            {' > '} Asset: AHU-01
          </span>
        )}
        {level === 'meter' && <span>{' > '} Meter: Active Power Meter</span>}
      </div>

      {/* Drill-down View Panels */}
      {level === 'site' && (
        <div>
          <h3>Site Level View: Campus North</h3>
          <p>Total Energy (30 Days): 412.8 MWh | Active Buildings: 4</p>
          <button onClick={() => setLevel('building')} style={{ padding: '8px 16px', background: '#0066cc', color: '#fff' }}>
            Drill Down to Building A ->
          </button>
        </div>
      )}

      {level === 'building' && (
        <div>
          <h3>Building Level View: Building A</h3>
          <p>Total Energy (30 Days): 182.4 MWh | Assets Monitored: 12</p>
          <button onClick={() => setLevel('asset')} style={{ padding: '8px 16px', background: '#0066cc', color: '#fff' }}>
            Drill Down to Asset: AHU-01 ->
          </button>
        </div>
      )}

      {level === 'asset' && (
        <div>
          <h3>Asset Level View: Air Handling Unit #01 (AHU-01)</h3>
          <p>Brick Class: brick:Air_Handling_Unit | Active Power: 42.8 kW</p>
          <p style={{ color: '#ff3333' }}>[ACTIVE ANOMALY] Baseload Excess (+40.4 kW above expected 45.0 kW)</p>
          <button onClick={() => setLevel('meter')} style={{ padding: '8px 16px', background: '#0066cc', color: '#fff' }}>
            Drill Down to Physical Meter (Point UUID: 44444444...) ->
          </button>
        </div>
      )}

      {level === 'meter' && (
        <div>
          <h3>Meter Level View: Point 44444444-4444-4444-4444-444444444444</h3>
          <p>Point Type: active_power | Unit: kW | Sampling: 60s</p>
          <p>Latest Reading: 85.4 kW | Quality Flag: GOOD</p>
          <button onClick={() => setLevel('site')} style={{ padding: '8px 16px', background: '#339933', color: '#fff' }}>
            <- Return to Site Overview
          </button>
        </div>
      )}
    </div>
  );
};

export default DrillDownDashboard;

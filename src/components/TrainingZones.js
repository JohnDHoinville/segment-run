import React from 'react';
import './TrainingZones.css';

const TrainingZones = ({ zones }) => {
  console.log("TrainingZones component received zones:", zones);
  if (!zones) return null;

  // Helper function to safely display HR ranges
  const formatHRRange = (zoneData) => {
    if (!zoneData.hr_range || !Array.isArray(zoneData.hr_range)) {
      return null;
    }
    return `${zoneData.hr_range[0]}-${zoneData.hr_range[1]} bpm`;
  };

  return (
    <div className="training-zones">
      <h3>Heart Rate Training Zones</h3>
      <div className="zones-grid">
        {Object.entries(zones).map(([zoneName, zoneData]) => (
          <div 
            key={zoneName} 
            className="zone-card"
            style={{ borderLeft: `4px solid ${zoneData.color}` }}
          >
            <div className="zone-header">
              <h4>{zoneName} - {zoneData.name}</h4>
              <span className="zone-ranges">
                <div className="zone-range hrr">
                  {Math.round(zoneData.range[0] * 100)}-{Math.round(zoneData.range[1] * 100)}% HRR
                </div>
                {formatHRRange(zoneData) && (
                  <div className="zone-range bpm">
                    {formatHRRange(zoneData)}
                  </div>
                )}
              </span>
            </div>
            <div className="zone-stats">
              <div className="zone-percentage">
                {Math.round(zoneData.percentage)}%
                <div 
                  className="percentage-bar" 
                  style={{ 
                    width: `${zoneData.percentage}%`,
                    backgroundColor: zoneData.color 
                  }} 
                />
              </div>
              <div className="zone-time">
                {Math.floor(zoneData.time_spent)}:{((zoneData.time_spent % 1) * 60).toFixed(0).padStart(2, '0')}
              </div>
            </div>
            <p className="zone-description">{zoneData.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TrainingZones; 
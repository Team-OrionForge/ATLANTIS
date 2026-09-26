import React from 'react';
import { Sliders } from 'lucide-react';

interface ThresholdSlidersProps {
  confThreshold: number;
  setConfThreshold: (v: number) => void;
  iouThreshold: number;
  setIouThreshold: (v: number) => void;
  altitudeM: number;
  setAltitudeM: (v: number) => void;
}

export const ThresholdSliders: React.FC<ThresholdSlidersProps> = ({
  confThreshold,
  setConfThreshold,
  iouThreshold,
  setIouThreshold,
  altitudeM,
  setAltitudeM,
}) => {
  return (
    <div className="bg-[#121e36] border border-slate-700/60 rounded-lg p-3 text-slate-200">
      <h3 className="text-xs font-semibold text-cyan-400 uppercase tracking-wide flex items-center gap-1.5 mb-3">
        <Sliders className="w-3.5 h-3.5" /> Sensor & Model Tuning Controls
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        <div>
          <div className="flex justify-between text-slate-300 mb-1">
            <span>Confidence Threshold</span>
            <span className="font-mono text-cyan-400">{confThreshold.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0.20"
            max="0.95"
            step="0.05"
            value={confThreshold}
            onChange={(e) => setConfThreshold(parseFloat(e.target.value))}
            className="w-full accent-cyan-400 bg-slate-800 h-1.5 rounded cursor-pointer"
          />
        </div>

        <div>
          <div className="flex justify-between text-slate-300 mb-1">
            <span>IoU Threshold</span>
            <span className="font-mono text-cyan-400">{iouThreshold.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0.10"
            max="0.80"
            step="0.05"
            value={iouThreshold}
            onChange={(e) => setIouThreshold(parseFloat(e.target.value))}
            className="w-full accent-cyan-400 bg-slate-800 h-1.5 rounded cursor-pointer"
          />
        </div>

        <div>
          <div className="flex justify-between text-slate-300 mb-1">
            <span>Towfish Altitude (H)</span>
            <span className="font-mono text-amber-400">{altitudeM.toFixed(1)} m</span>
          </div>
          <input
            type="range"
            min="2.0"
            max="25.0"
            step="0.5"
            value={altitudeM}
            onChange={(e) => setAltitudeM(parseFloat(e.target.value))}
            className="w-full accent-amber-400 bg-slate-800 h-1.5 rounded cursor-pointer"
          />
        </div>
      </div>
    </div>
  );
};

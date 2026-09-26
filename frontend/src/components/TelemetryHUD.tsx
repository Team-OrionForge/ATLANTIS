import React from 'react';
import { Activity, ShieldAlert, Target, Compass } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Detection, ProcessSonarResponse } from '../types';

interface TelemetryHUDProps {
  result: ProcessSonarResponse | null;
  filteredDetections: Detection[];
  selectedDetection: Detection | null;
}

const TIER_COLORS: Record<string, string> = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  MODERATE: '#f59e0b',
  LOW: '#10b981',
};

export const TelemetryHUD: React.FC<TelemetryHUDProps> = ({
  result,
  filteredDetections,
  selectedDetection,
}) => {
  if (!result) {
    return (
      <div className="bg-[#121e36] border border-slate-700/60 rounded-lg p-6 text-center text-slate-400">
        <Activity className="w-8 h-8 text-slate-600 mx-auto mb-2" />
        <p className="text-xs uppercase font-mono tracking-wider">No Active Mission Telemetry</p>
      </div>
    );
  }

  const chartData = [
    { tier: 'CRITICAL', count: result.critical_count },
    { tier: 'HIGH', count: result.high_count },
    { tier: 'MODERATE', count: result.moderate_count },
    { tier: 'LOW', count: result.low_count },
  ];

  return (
    <div className="bg-[#121e36] border border-slate-700/60 rounded-lg p-4 text-slate-200">
      <h3 className="text-xs font-semibold text-cyan-400 uppercase tracking-wide flex items-center gap-2 mb-3">
        <Activity className="w-4 h-4" /> Telemetry HUD & Hazard Priority Index (HPI)
      </h3>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="bg-slate-900/60 border border-slate-800 p-3 rounded">
          <div className="text-[11px] text-slate-400 uppercase font-mono flex items-center gap-1">
            <Target className="w-3.5 h-3.5 text-cyan-400" /> Total Targets
          </div>
          <div className="text-2xl font-bold font-mono text-cyan-400 mt-1">
            {filteredDetections.length}
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 p-3 rounded">
          <div className="text-[11px] text-slate-400 uppercase font-mono flex items-center gap-1">
            <ShieldAlert className="w-3.5 h-3.5 text-red-400" /> Critical Risk
          </div>
          <div className="text-2xl font-bold font-mono text-red-400 mt-1">
            {result.critical_count}
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 p-3 rounded">
          <div className="text-[11px] text-slate-400 uppercase font-mono flex items-center gap-1">
            <Compass className="w-3.5 h-3.5 text-amber-400" /> Selected Height
          </div>
          <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
            {selectedDetection ? `${selectedDetection.estimated_elevation_m}m` : '--'}
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 p-3 rounded">
          <div className="text-[11px] text-slate-400 uppercase font-mono flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 text-emerald-400" /> Target Area
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
            {selectedDetection ? `${selectedDetection.area_m2}m²` : '--'}
          </div>
        </div>
      </div>

      {/* Recharts HPI Distribution Bar Chart */}
      <div className="bg-slate-950 p-3 rounded border border-slate-800">
        <span className="text-[11px] font-mono text-slate-400 uppercase block mb-2">
          Hazard Tier Distribution Breakdown
        </span>
        <div className="h-36">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <XAxis dataKey="tier" stroke="#94a3b8" fontSize={10} tickLine={false} />
              <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={TIER_COLORS[entry.tier] || '#00f0ff'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { Eye, Layers } from 'lucide-react';
import { ProcessSonarResponse } from '../types';

interface PreprocessCompareViewProps {
  result: ProcessSonarResponse;
}

export const PreprocessCompareView: React.FC<PreprocessCompareViewProps> = ({ result }) => {
  const [showProcessed, setShowProcessed] = useState<boolean>(true);

  return (
    <div className="bg-[#121e36] border border-slate-700/60 rounded-lg p-4 text-slate-200">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-cyan-400 uppercase tracking-wide flex items-center gap-2">
          <Layers className="w-4 h-4" /> Acoustic Waterfall Channel Split (Nadir Auto-Detected)
        </h3>
        <button
          onClick={() => setShowProcessed((prev) => !prev)}
          className="flex items-center gap-1.5 px-3 py-1 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded border border-slate-600 transition-colors"
        >
          <Eye className="w-3.5 h-3.5" />
          {showProcessed ? 'Showing CLAHE + Denoised' : 'Showing Raw Waterfall'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Port Channel */}
        <div className="bg-slate-950 p-2 rounded border border-slate-800">
          <div className="flex justify-between items-center text-xs font-mono text-cyan-400 mb-1 px-1">
            <span>PORT CHANNEL (LEFT)</span>
            <span className="text-slate-500">
              {showProcessed ? 'CLAHE clip=2.8' : 'Raw acoustic return'}
            </span>
          </div>
          <div className="aspect-[4/3] bg-black flex items-center justify-center overflow-hidden rounded">
            <img
              src={showProcessed ? result.preprocessed_port_b64 : result.raw_port_b64}
              alt="Port Channel"
              className="w-full h-full object-contain filter contrast-125"
            />
          </div>
        </div>

        {/* Starboard Channel */}
        <div className="bg-slate-950 p-2 rounded border border-slate-800">
          <div className="flex justify-between items-center text-xs font-mono text-amber-400 mb-1 px-1">
            <span>STARBOARD CHANNEL (RIGHT)</span>
            <span className="text-slate-500">
              {showProcessed ? 'CLAHE clip=2.8' : 'Raw acoustic return'}
            </span>
          </div>
          <div className="aspect-[4/3] bg-black flex items-center justify-center overflow-hidden rounded">
            <img
              src={showProcessed ? result.preprocessed_starboard_b64 : result.raw_starboard_b64}
              alt="Starboard Channel"
              className="w-full h-full object-contain filter contrast-125"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

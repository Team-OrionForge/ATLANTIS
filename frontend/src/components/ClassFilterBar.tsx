import React from 'react';
import { TargetClass } from '../types';
import { Filter } from 'lucide-react';

interface ClassFilterBarProps {
  enabledClasses: Record<TargetClass, boolean>;
  onToggle: (cls: TargetClass) => void;
}

const CLASS_CONFIG: Record<TargetClass, { label: string; color: string; border: string }> = {
  shipwreck: { label: 'Shipwreck', color: 'bg-red-500/20 text-red-400', border: 'border-red-500' },
  ghost_net: { label: 'Ghost Net', color: 'bg-amber-500/20 text-amber-400', border: 'border-amber-500' },
  chemical_container: { label: 'Chemical Cont.', color: 'bg-orange-500/20 text-orange-400', border: 'border-orange-500' },
  metal_debris: { label: 'Metal Debris', color: 'bg-cyan-500/20 text-cyan-400', border: 'border-cyan-500' },
  pipeline: { label: 'Pipeline', color: 'bg-purple-500/20 text-purple-400', border: 'border-purple-500' },
  marine_plastic: { label: 'Marine Plastic', color: 'bg-emerald-500/20 text-emerald-400', border: 'border-emerald-500' },
};

export const ClassFilterBar: React.FC<ClassFilterBarProps> = ({ enabledClasses, onToggle }) => {
  return (
    <div className="flex items-center gap-2 bg-[#121e36] border border-slate-700/60 rounded-lg p-2.5 overflow-x-auto">
      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5 mr-1">
        <Filter className="w-3.5 h-3.5 text-cyan-400" /> Taxonomy:
      </span>
      {(Object.keys(CLASS_CONFIG) as TargetClass[]).map((cls) => {
        const isEnabled = enabledClasses[cls];
        const cfg = CLASS_CONFIG[cls];
        return (
          <button
            key={cls}
            onClick={() => onToggle(cls)}
            className={`px-2.5 py-1 text-xs font-medium rounded-full border transition-all ${
              isEnabled
                ? `${cfg.color} ${cfg.border} shadow-sm`
                : 'bg-slate-900/40 text-slate-500 border-slate-800 opacity-60'
            }`}
          >
            {cfg.label}
          </button>
        );
      })}
    </div>
  );
};

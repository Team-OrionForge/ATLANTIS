import React, { useRef, useEffect, useState } from 'react';
import { Target, Info } from 'lucide-react';
import { Detection, ProcessSonarResponse, TargetClass } from '../types';

interface DetectionOverlayProps {
  result: ProcessSonarResponse;
  filteredDetections: Detection[];
  selectedDetection: Detection | null;
  onSelectDetection: (d: Detection | null) => void;
}

const CLASS_COLORS: Record<TargetClass, string> = {
  shipwreck: '#ef4444',
  ghost_net: '#f59e0b',
  chemical_container: '#f97316',
  metal_debris: '#06b6d4',
  pipeline: '#a855f7',
  marine_plastic: '#10b981',
};

export const DetectionOverlay: React.FC<DetectionOverlayProps> = ({
  result,
  filteredDetections,
  selectedDetection,
  onSelectDetection,
}) => {
  const [activeChannel, setActiveChannel] = useState<'starboard' | 'port'>('starboard');
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const channelImgB64 =
    activeChannel === 'starboard' ? result.preprocessed_starboard_b64 : result.preprocessed_port_b64;

  const channelDetections = filteredDetections.filter((d) => d.channel === activeChannel);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.src = channelImgB64;
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0);

      // Render polygon bounding overlays
      channelDetections.forEach((det) => {
        const color = CLASS_COLORS[det.class_name] || '#00f0ff';
        const isSelected = selectedDetection?.detection_id === det.detection_id;

        ctx.strokeStyle = color;
        ctx.lineWidth = isSelected ? 4 : 2;
        ctx.fillStyle = `${color}33`; // 20% opacity fill

        if (det.polygon && det.polygon.length > 2) {
          ctx.beginPath();
          ctx.moveTo(det.polygon[0][0], det.polygon[0][1]);
          for (let i = 1; i < det.polygon.length; i++) {
            ctx.lineTo(det.polygon[i][0], det.polygon[i][1]);
          }
          ctx.closePath();
          ctx.fill();
          ctx.stroke();
        } else {
          // Bounding box fallback
          const [x, y, w, h] = det.bbox;
          ctx.fillRect(x, y, w, h);
          ctx.strokeRect(x, y, w, h);
        }

        // Render target label tag
        const [x, y] = det.bbox;
        ctx.font = 'bold 12px monospace';
        ctx.fillStyle = color;
        const labelText = `${det.class_name.toUpperCase()} (${(det.confidence * 100).toFixed(0)}%)`;
        ctx.fillRect(x, Math.max(0, y - 16), ctx.measureText(labelText).width + 8, 16);
        ctx.fillStyle = '#0b1325';
        ctx.fillText(labelText, x + 4, Math.max(12, y - 4));
      });
    };
  }, [channelImgB64, channelDetections, selectedDetection]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    const clickX = (e.clientX - rect.left) * scaleX;
    const clickY = (e.clientY - rect.top) * scaleY;

    // Check if clicked inside any bounding box
    const clickedDet = channelDetections.find((d) => {
      const [x, y, w, h] = d.bbox;
      return clickX >= x && clickX <= x + w && clickY >= y && clickY <= y + h;
    });

    onSelectDetection(clickedDet || null);
  };

  return (
    <div className="bg-[#121e36] border border-slate-700/60 rounded-lg p-4 text-slate-200">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-cyan-400 uppercase tracking-wide flex items-center gap-2">
          <Target className="w-4 h-4" /> Multi-Class Target Detection Overlay
        </h3>
        <div className="flex gap-2">
          <button
            onClick={() => setActiveChannel('port')}
            className={`px-3 py-1 text-xs font-mono font-medium rounded transition-all ${
              activeChannel === 'port'
                ? 'bg-cyan-500 text-slate-950 font-bold'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            PORT ({filteredDetections.filter((d) => d.channel === 'port').length})
          </button>
          <button
            onClick={() => setActiveChannel('starboard')}
            className={`px-3 py-1 text-xs font-mono font-medium rounded transition-all ${
              activeChannel === 'starboard'
                ? 'bg-amber-500 text-slate-950 font-bold'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            STARBOARD ({filteredDetections.filter((d) => d.channel === 'starboard').length})
          </button>
        </div>
      </div>

      <div className="relative bg-black rounded border border-slate-800 flex items-center justify-center p-2">
        <canvas
          ref={canvasRef}
          onClick={handleCanvasClick}
          className="max-w-full max-h-[500px] object-contain cursor-crosshair rounded"
        />
      </div>

      {selectedDetection && (
        <div className="mt-3 p-3 bg-slate-900/80 border border-cyan-500/40 rounded flex items-start gap-3">
          <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
          <div className="text-xs grid grid-cols-2 md:grid-cols-4 gap-2 w-full font-mono">
            <div>
              <span className="text-slate-400">Class:</span>{' '}
              <span className="text-cyan-300 font-bold uppercase">{selectedDetection.class_name}</span>
            </div>
            <div>
              <span className="text-slate-400">Confidence:</span>{' '}
              <span className="text-emerald-400">{(selectedDetection.confidence * 100).toFixed(1)}%</span>
            </div>
            <div>
              <span className="text-slate-400">HPI Risk:</span>{' '}
              <span className="text-amber-400">{selectedDetection.hpi_score} ({selectedDetection.hpi_tier})</span>
            </div>
            <div>
              <span className="text-slate-400">Elevation:</span>{' '}
              <span className="text-slate-200">{selectedDetection.estimated_elevation_m} m</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

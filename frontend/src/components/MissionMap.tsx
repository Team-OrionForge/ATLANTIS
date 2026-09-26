import React from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { MapPin, Download, FileSpreadsheet } from 'lucide-react';
import { api } from '../lib/api';
import { Detection, TargetClass } from '../types';

interface MissionMapProps {
  detections: Detection[];
  selectedDetection: Detection | null;
  onSelectDetection: (d: Detection | null) => void;
  jobId?: string;
}

const CLASS_COLORS: Record<TargetClass, string> = {
  shipwreck: '#ef4444',
  ghost_net: '#f59e0b',
  chemical_container: '#f97316',
  metal_debris: '#06b6d4',
  pipeline: '#a855f7',
  marine_plastic: '#10b981',
};

function createCustomIcon(class_name: TargetClass, isSelected: boolean) {
  const color = CLASS_COLORS[class_name] || '#00f0ff';
  const size = isSelected ? 24 : 16;
  const html = `
    <div style="
      width: ${size}px;
      height: ${size}px;
      background-color: ${color};
      border: 2px solid #ffffff;
      border-radius: 50%;
      box-shadow: 0 0 8px ${color};
      transform: translate(-50%, -50%);
    "></div>
  `;
  return L.divIcon({
    html,
    className: 'custom-sonar-marker',
    iconSize: [size, size],
  });
}

export const MissionMap: React.FC<MissionMapProps> = ({
  detections,
  selectedDetection,
  onSelectDetection,
  jobId,
}) => {
  const centerLat = detections.length > 0 ? detections[0].lat : 25.7617;
  const centerLon = detections.length > 0 ? detections[0].lon : -80.1918;

  return (
    <div className="bg-[#121e36] border border-slate-700/60 rounded-lg p-4 text-slate-200">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-cyan-400 uppercase tracking-wide flex items-center gap-2">
          <MapPin className="w-4 h-4" /> Geotagged Target Map (WGS84 Coordinates)
        </h3>
        {jobId && (
          <div className="flex gap-2">
            <a
              href={api.getGeoJsonExportUrl(jobId)}
              download
              className="flex items-center gap-1 px-2.5 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded border border-slate-600 transition-colors"
            >
              <Download className="w-3.5 h-3.5" /> GeoJSON
            </a>
            <a
              href={api.getCsvExportUrl(jobId)}
              download
              className="flex items-center gap-1 px-2.5 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-emerald-300 rounded border border-slate-600 transition-colors"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" /> CSV Mission Log
            </a>
          </div>
        )}
      </div>

      <div className="h-[360px] w-full rounded overflow-hidden border border-slate-800">
        <MapContainer
          center={[centerLat, centerLon]}
          zoom={14}
          scrollWheelZoom={true}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {detections.map((det) => {
            const isSelected = selectedDetection?.detection_id === det.detection_id;
            return (
              <Marker
                key={det.detection_id}
                position={[det.lat, det.lon]}
                icon={createCustomIcon(det.class_name, isSelected)}
                eventHandlers={{
                  click: () => onSelectDetection(det),
                }}
              >
                <Popup>
                  <div className="text-xs font-sans text-slate-900 font-medium">
                    <div className="font-bold uppercase text-cyan-700">{det.class_name}</div>
                    <div>HPI Score: <b>{det.hpi_score}</b> ({det.hpi_tier})</div>
                    <div>Confidence: <b>{(det.confidence * 100).toFixed(0)}%</b></div>
                    <div>Elevation: <b>{det.estimated_elevation_m}m</b></div>
                    <div className="text-[10px] text-slate-500 font-mono mt-1">
                      {det.lat.toFixed(6)}, {det.lon.toFixed(6)}
                    </div>
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
};

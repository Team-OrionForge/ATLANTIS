import { Waves, Database, Compass, AlertCircle } from 'lucide-react';
import { useMissionState } from './hooks/useMissionState';
import { UploadPanel } from './components/UploadPanel';
import { ClassFilterBar } from './components/ClassFilterBar';
import { ThresholdSliders } from './components/ThresholdSliders';
import { PreprocessCompareView } from './components/PreprocessCompareView';
import { DetectionOverlay } from './components/DetectionOverlay';
import { TelemetryHUD } from './components/TelemetryHUD';
import { MissionMap } from './components/MissionMap';
import { BatchDatasetView } from './components/BatchDatasetView';

export function App() {
  const {
    sonarResult,
    setSonarResult,
    selectedDetection,
    setSelectedDetection,
    loading,
    setLoading,
    error,
    setError,
    viewMode,
    setViewMode,
    enabledClasses,
    toggleClass,
    confThreshold,
    setConfThreshold,
    iouThreshold,
    setIouThreshold,
    altitudeM,
    setAltitudeM,
    filteredDetections,
  } = useMissionState();

  return (
    <div className="min-h-screen bg-[#0b1325] text-slate-100 flex flex-col font-sans">
      {/* Main Header Toolbar */}
      <header className="bg-[#121e36] border-b border-slate-700/60 px-6 py-3 flex flex-col md:flex-row items-center justify-between gap-3 shadow-md">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-cyan-500/20 border border-cyan-500/50 rounded-lg text-cyan-400">
            <Waves className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h1 className="text-base font-extrabold tracking-wide uppercase text-slate-100 flex items-center gap-2">
              Project Atlantis <span className="text-xs px-2 py-0.5 bg-cyan-950 text-cyan-400 border border-cyan-500/40 rounded">v1.0 Hackathon MVP</span>
            </h1>
            <p className="text-[11px] text-slate-400 font-mono">
              Autonomous Dual-Channel Side-Scan Sonar Target & Debris Detection
            </p>
          </div>
        </div>

        {/* Mode Switcher */}
        <div className="flex gap-2 bg-slate-900/80 p-1 rounded border border-slate-800">
          <button
            onClick={() => setViewMode('single')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-medium rounded transition-all ${
              viewMode === 'single'
                ? 'bg-cyan-500 text-slate-950 font-bold shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Compass className="w-3.5 h-3.5" /> Single Inspection
          </button>
          <button
            onClick={() => setViewMode('batch')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-medium rounded transition-all ${
              viewMode === 'batch'
                ? 'bg-amber-500 text-slate-950 font-bold shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Database className="w-3.5 h-3.5" /> Batch Dataset Engine (500+)
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-4 md:p-6 max-w-[1600px] w-full mx-auto space-y-4">
        {error && (
          <div className="p-3 bg-red-950/60 border border-red-500/50 rounded-lg text-xs text-red-300 flex items-center gap-2 font-mono">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            {error}
          </div>
        )}

        {viewMode === 'single' ? (
          <div className="space-y-4">
            {/* Top Toolbar Controls */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-1">
                <UploadPanel
                  onSuccess={(res) => {
                    setSonarResult(res);
                    if (res.detections.length > 0) {
                      setSelectedDetection(res.detections[0]);
                    }
                  }}
                  loading={loading}
                  setLoading={setLoading}
                  setError={setError}
                  confThreshold={confThreshold}
                  iouThreshold={iouThreshold}
                  altitudeM={altitudeM}
                />
              </div>
              <div className="lg:col-span-2 space-y-3">
                <ClassFilterBar enabledClasses={enabledClasses} onToggle={toggleClass} />
                <ThresholdSliders
                  confThreshold={confThreshold}
                  setConfThreshold={setConfThreshold}
                  iouThreshold={iouThreshold}
                  setIouThreshold={setIouThreshold}
                  altitudeM={altitudeM}
                  setAltitudeM={setAltitudeM}
                />
              </div>
            </div>

            {/* Middle Inspection Row */}
            {sonarResult && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <PreprocessCompareView result={sonarResult} />
                <DetectionOverlay
                  result={sonarResult}
                  filteredDetections={filteredDetections}
                  selectedDetection={selectedDetection}
                  onSelectDetection={setSelectedDetection}
                />
              </div>
            )}

            {/* Bottom Row: Telemetry HUD & Geotagged Map */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <TelemetryHUD
                result={sonarResult}
                filteredDetections={filteredDetections}
                selectedDetection={selectedDetection}
              />
              <MissionMap
                detections={filteredDetections}
                selectedDetection={selectedDetection}
                onSelectDetection={setSelectedDetection}
                jobId={sonarResult?.job_id}
              />
            </div>
          </div>
        ) : (
          /* Batch Mode View */
          <BatchDatasetView />
        )}
      </main>

      {/* Footer Status Bar */}
      <footer className="bg-[#121e36] border-t border-slate-700/60 px-6 py-2 text-[11px] text-slate-500 font-mono flex justify-between items-center">
        <span>Project Atlantis • Production-Grade Marine Debris Detection</span>
        <span>Dual-Branch Physics Engine Active • WGS84 Geodetic Correction</span>
      </footer>
    </div>
  );
}
export default App;

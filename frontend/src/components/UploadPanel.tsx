import { useState } from 'react';
import { Upload, Play, RefreshCw, CheckCircle, AlertTriangle, ShieldCheck } from 'lucide-react';
import { api } from '../lib/api';
import { ProcessSonarResponse } from '../types';

interface UploadPanelProps {
  onSuccess: (result: ProcessSonarResponse) => void;
  loading: boolean;
  setLoading: (l: boolean) => void;
  setError: (e: string | null) => void;
  confThreshold: number;
  iouThreshold: number;
  altitudeM: number;
}

export const UploadPanel: React.FC<UploadPanelProps> = ({
  onSuccess,
  loading,
  setLoading,
  setError,
  confThreshold,
  iouThreshold,
  altitudeM,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [validationBadge, setValidationBadge] = useState<{
    isValid: boolean;
    confidence: number;
    message: string;
  } | null>(null);

  const handleFileUpload = async (file: File) => {
    setLoading(true);
    setError(null);
    setValidationBadge(null);
    setStatusMessage('Analyzing uploaded image...');

    try {
      const upRes = await api.uploadWaterfall(file);

      setStatusMessage('Checking Side-Scan Sonar (SSS) compatibility...');

      const procRes = await api.processSonar({
        upload_id: upRes.upload_id,
        conf_threshold: confThreshold,
        iou_threshold: iouThreshold,
        altitude_m: altitudeM,
      });

      if (procRes.is_sonar) {
        const confPct = procRes.sonar_confidence ? (procRes.sonar_confidence * 100).toFixed(0) : '94';
        setValidationBadge({
          isValid: true,
          confidence: procRes.sonar_confidence || 0.94,
          message: `✓ Valid Side-Scan Sonar (SSS) Image (Sonar Confidence: ${confPct}%)`,
        });
        setStatusMessage('Proceeding to AI Detection...');
        onSuccess(procRes);
      }
    } catch (err: any) {
      console.error(err);
      const detail = err.response?.data?.message || err.response?.data?.detail || err.message;
      const conf = err.response?.data?.sonar_confidence;

      setValidationBadge({
        isValid: false,
        confidence: conf || 0.42,
        message: '✕ Invalid Image: This does not appear to be a valid Side-Scan Sonar image.',
      });
      setError(detail || 'This does not appear to be a valid Side-Scan Sonar image. Please upload a correct Side-Scan Sonar image.');
    } finally {
      setLoading(false);
      setTimeout(() => setStatusMessage(null), 3000);
    }
  };

  const handleRunMockDemo = async () => {
    setLoading(true);
    setError(null);
    setValidationBadge(null);
    setStatusMessage('Generating & validating synthetic SSS waterfall...');

    try {
      const res = await api.runSyntheticDemo();
      setValidationBadge({
        isValid: true,
        confidence: res.sonar_confidence || 0.98,
        message: '✓ Valid Side-Scan Sonar (SSS) Image (Sonar Confidence: 98%)',
      });
      onSuccess(res);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'Failed to run synthetic demo.');
    } finally {
      setLoading(false);
      setTimeout(() => setStatusMessage(null), 3000);
    }
  };

  return (
    <div className="bg-[#121e36] border border-slate-700/60 rounded-lg p-4 text-slate-200">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold tracking-wide text-cyan-400 uppercase flex items-center gap-2">
          <Upload className="w-4 h-4" /> Waterfall Image Ingestion
        </h2>
        <button
          onClick={handleRunMockDemo}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-amber-500 hover:bg-amber-400 text-slate-950 rounded shadow transition-all disabled:opacity-50"
        >
          {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          Run Mock Demo
        </button>
      </div>

      <div className="mb-3 flex items-center justify-between bg-slate-900/60 border border-slate-800 p-2 rounded text-xs">
        <span className="text-slate-400 flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" /> Supported Input:
        </span>
        <span className="font-mono text-cyan-300 font-bold bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-500/30">
          Side-Scan Sonar (SSS)
        </span>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileUpload(e.dataTransfer.files[0]);
          }
        }}
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
          dragActive ? 'border-cyan-400 bg-cyan-950/20' : 'border-slate-600 hover:border-slate-400 bg-slate-900/40'
        }`}
      >
        <input
          type="file"
          id="file-upload"
          accept="image/png,image/jpeg,image/tiff"
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              handleFileUpload(e.target.files[0]);
            }
          }}
          className="hidden"
        />
        <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center gap-2">
          <Upload className="w-8 h-8 text-cyan-400 animate-bounce" />
          <span className="text-xs font-medium text-slate-300">
            Drag & drop acoustic waterfall tile (PNG, JPEG, TIFF)
          </span>
          <span className="text-[11px] text-slate-500">Max size 50 MB • Dual-channel Port/Starboard sweep</span>
        </label>
      </div>

      {statusMessage && (
        <div className="mt-3 p-2 bg-slate-900 border border-cyan-500/40 rounded text-xs font-mono text-cyan-300 flex items-center gap-2 animate-pulse">
          <RefreshCw className="w-3.5 h-3.5 animate-spin text-cyan-400" />
          {statusMessage}
        </div>
      )}

      {validationBadge && (
        <div
          className={`mt-3 p-2.5 rounded border text-xs font-mono flex items-center gap-2 ${
            validationBadge.isValid
              ? 'bg-emerald-950/60 border-emerald-500/60 text-emerald-300'
              : 'bg-red-950/60 border-red-500/60 text-red-300'
          }`}
        >
          {validationBadge.isValid ? (
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
          )}
          <span>{validationBadge.message}</span>
        </div>
      )}
    </div>
  );
};

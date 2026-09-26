import React, { useState, useEffect } from 'react';
import { Database, FolderOpen, Play, RefreshCw, Download, FileSpreadsheet, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { api } from '../lib/api';
import { BatchReport, BatchStatusResponse } from '../types';

const CLASS_COLORS: Record<string, string> = {
  shipwreck: '#ef4444',
  ghost_net: '#f59e0b',
  chemical_container: '#f97316',
  metal_debris: '#06b6d4',
  pipeline: '#a855f7',
  marine_plastic: '#10b981',
};

export const BatchDatasetView: React.FC = () => {
  const [folderPath, setFolderPath] = useState<string>('');
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [batchStatus, setBatchStatus] = useState<BatchStatusResponse | null>(null);
  const [batchReport, setBatchReport] = useState<BatchReport | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState<number>(1);
  const pageSize = 10;

  const handleStartBatch = async () => {
    setLoading(true);
    setError(null);
    setBatchReport(null);
    try {
      const upRes = await api.uploadBatchDataset(folderPath || undefined);
      setActiveBatchId(upRes.batch_id);

      await api.startBatchRun(upRes.batch_id, upRes.dataset_path);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'Failed to start batch processing run.');
      setLoading(false);
    }
  };

  // Poll batch status every 1.5 seconds
  useEffect(() => {
    if (!activeBatchId) return;

    const interval = setInterval(async () => {
      try {
        const st = await api.getBatchStatus(activeBatchId);
        setBatchStatus(st);

        if (st.status === 'done') {
          clearInterval(interval);
          const rep = await api.getBatchReport(activeBatchId);
          setBatchReport(rep);
          setLoading(false);
        } else if (st.status === 'failed') {
          clearInterval(interval);
          setError('Batch processing run failed.');
          setLoading(false);
        }
      } catch (err) {
        console.error(err);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeBatchId]);

  const classChartData = batchReport
    ? Object.entries(batchReport.detections_by_class).map(([cls, count]) => ({ class: cls, count }))
    : [];

  const paginatedResults = batchReport
    ? batchReport.per_image_results.slice((page - 1) * pageSize, page * pageSize)
    : [];

  const totalPages = batchReport ? Math.ceil(batchReport.per_image_results.length / pageSize) : 1;

  return (
    <div className="space-y-4 text-slate-200">
      {/* Dataset Folder Ingestion Box */}
      <div className="bg-[#121e36] border border-slate-700/60 rounded-lg p-4">
        <h2 className="text-sm font-semibold tracking-wide text-cyan-400 uppercase flex items-center gap-2 mb-3">
          <Database className="w-4 h-4" /> Real Dataset Batch Ingestion Engine (500+ Waterfall Images)
        </h2>

        <div className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <FolderOpen className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              type="text"
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
              placeholder="Enter local dataset path (e.g. C:/Users/.../Dataset) or leave blank to use workspace Dataset/"
              className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-700 rounded text-xs text-slate-200 focus:outline-none focus:border-cyan-400 font-mono"
            />
          </div>
          <button
            onClick={handleStartBatch}
            disabled={loading}
            className="flex items-center justify-center gap-2 px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold rounded shadow transition-all disabled:opacity-50"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Start Batch Processing
          </button>
        </div>

        {error && (
          <div className="mt-3 p-3 bg-red-950/60 border border-red-500/50 rounded text-xs text-red-300 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
            {error}
          </div>
        )}

        {/* Progress Bar */}
        {batchStatus && batchStatus.status === 'running' && (
          <div className="mt-4 p-3 bg-slate-900/80 rounded border border-slate-800 space-y-2">
            <div className="flex justify-between text-xs font-mono text-cyan-300">
              <span>Processing Dataset...</span>
              <span>
                {batchStatus.completed} / {batchStatus.total} ({((batchStatus.completed / (batchStatus.total || 1)) * 100).toFixed(0)}%)
              </span>
            </div>
            <div className="w-full bg-slate-800 h-2 rounded overflow-hidden">
              <div
                className="bg-cyan-400 h-full transition-all duration-300"
                style={{ width: `${(batchStatus.completed / (batchStatus.total || 1)) * 100}%` }}
              ></div>
            </div>
          </div>
        )}
      </div>

      {/* Aggregate Batch Report */}
      {batchReport && (
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-[#121e36] border border-slate-700/60 rounded-lg p-3">
            <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wide">
              Batch Summary: {batchReport.batch_id} ({batchReport.processing_time_s}s elapsed)
            </span>
            <div className="flex gap-2">
              <a
                href={api.getBatchGeoJsonExportUrl(batchReport.batch_id)}
                download
                className="flex items-center gap-1.5 px-3 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded border border-slate-600 transition-colors"
              >
                <Download className="w-3.5 h-3.5" /> Export Batch GeoJSON
              </a>
              <a
                href={api.getBatchCsvExportUrl(batchReport.batch_id)}
                download
                className="flex items-center gap-1.5 px-3 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-emerald-300 rounded border border-slate-600 transition-colors"
              >
                <FileSpreadsheet className="w-3.5 h-3.5" /> Export Batch CSV
              </a>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-[#121e36] border border-slate-700/60 p-3 rounded">
              <div className="text-[11px] text-slate-400 font-mono">TOTAL IMAGES</div>
              <div className="text-2xl font-bold font-mono text-cyan-400 mt-1">{batchReport.total_images}</div>
            </div>
            <div className="bg-[#121e36] border border-slate-700/60 p-3 rounded">
              <div className="text-[11px] text-slate-400 font-mono">SUCCEEDED</div>
              <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">{batchReport.succeeded}</div>
            </div>
            <div className="bg-[#121e36] border border-slate-700/60 p-3 rounded">
              <div className="text-[11px] text-slate-400 font-mono">FAILED</div>
              <div className="text-2xl font-bold font-mono text-red-400 mt-1">{batchReport.failed}</div>
            </div>
            <div className="bg-[#121e36] border border-slate-700/60 p-3 rounded">
              <div className="text-[11px] text-slate-400 font-mono">ESTIMATED GEOLOCATION</div>
              <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
                {batchReport.flagged_estimated_geolocation_count}
              </div>
            </div>
          </div>

          {/* Recharts Aggregate Class Distribution */}
          <div className="bg-[#121e36] border border-slate-700/60 p-4 rounded-lg">
            <h3 className="text-xs font-semibold text-cyan-400 uppercase tracking-wide mb-3">
              Aggregate Target Counts by Taxonomy Class across Dataset
            </h3>
            <div className="h-44">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={classChartData}>
                  <XAxis dataKey="class" stroke="#94a3b8" fontSize={10} tickLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {classChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={CLASS_COLORS[entry.class] || '#00f0ff'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Per-Image Results Virtualized/Paginated Table */}
          <div className="bg-[#121e36] border border-slate-700/60 rounded-lg p-4">
            <h3 className="text-xs font-semibold text-cyan-400 uppercase tracking-wide mb-3">
              Per-Image Analysis Results ({batchReport.per_image_results.length} total)
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="p-2">Filename</th>
                    <th className="p-2">Status</th>
                    <th className="p-2">Target Count</th>
                    <th className="p-2">Geolocation Flag</th>
                    <th className="p-2">Details / Error</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {paginatedResults.map((r, i) => (
                    <tr key={i} className="hover:bg-slate-900/40">
                      <td className="p-2 font-semibold text-slate-200">{r.filename}</td>
                      <td className="p-2">
                        {r.status === 'done' ? (
                          <span className="text-emerald-400 flex items-center gap-1">
                            <CheckCircle className="w-3.5 h-3.5" /> Done
                          </span>
                        ) : (
                          <span className="text-red-400 flex items-center gap-1">
                            <XCircle className="w-3.5 h-3.5" /> Failed
                          </span>
                        )}
                      </td>
                      <td className="p-2 text-cyan-300 font-bold">{r.detection_count}</td>
                      <td className="p-2">
                        {r.geolocation_estimated ? (
                          <span className="text-amber-400 text-[10px] bg-amber-950/60 border border-amber-500/40 px-1.5 py-0.5 rounded">
                            Estimated (No Meta)
                          </span>
                        ) : (
                          <span className="text-emerald-400 text-[10px]">Exact Meta</span>
                        )}
                      </td>
                      <td className="p-2 text-slate-400 text-[11px]">
                        {r.error ? (
                          <span className="text-red-400">{r.error}</span>
                        ) : (
                          <span>{r.detections.map((d) => d.class_name).join(', ') || 'No targets'}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div className="flex items-center justify-between mt-3 text-xs font-mono text-slate-400">
              <span>
                Page {page} of {totalPages}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                  className="px-3 py-1 bg-slate-900 border border-slate-800 rounded disabled:opacity-40"
                >
                  Prev
                </button>
                <button
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                  className="px-3 py-1 bg-slate-900 border border-slate-800 rounded disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

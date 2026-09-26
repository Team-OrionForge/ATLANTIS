import axios from 'axios';
import {
  BatchReport,
  BatchStatusResponse,
  BatchUploadResponse,
  HealthResponse,
  ProcessSonarResponse,
  UploadResponse,
} from '../types';

const API_BASE = '/api';

export const api = {
  async checkHealth(): Promise<HealthResponse> {
    const res = await axios.get<HealthResponse>(`${API_BASE}/health`);
    return res.data;
  },

  async uploadWaterfall(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await axios.post<UploadResponse>(`${API_BASE}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  async processSonar(params: {
    upload_id: string;
    towfish_lat?: number;
    towfish_lon?: number;
    towfish_heading_deg?: number;
    altitude_m?: number;
    conf_threshold?: number;
    iou_threshold?: number;
  }): Promise<ProcessSonarResponse> {
    const res = await axios.post<ProcessSonarResponse>(`${API_BASE}/process-sonar`, params);
    return res.data;
  },

  async runSyntheticDemo(): Promise<ProcessSonarResponse> {
    const res = await axios.post<ProcessSonarResponse>(`${API_BASE}/demo/run-synthetic`);
    return res.data;
  },

  async uploadBatchDataset(datasetPath?: string, files?: File[]): Promise<BatchUploadResponse> {
    const formData = new FormData();
    if (datasetPath) {
      formData.append('dataset_path', datasetPath);
    }
    if (files && files.length > 0) {
      files.forEach((f) => formData.append('files', f));
    }
    const res = await axios.post<BatchUploadResponse>(`${API_BASE}/batch/upload-dataset`, formData);
    return res.data;
  },

  async startBatchRun(batchId: string, datasetPath?: string, conf?: number, iou?: number): Promise<{ batch_id: string; status_url: string }> {
    const res = await axios.post(`${API_BASE}/batch/${batchId}/run`, {
      dataset_path: datasetPath,
      conf_threshold: conf,
      iou_threshold: iou,
    });
    return res.data;
  },

  async getBatchStatus(batchId: string): Promise<BatchStatusResponse> {
    const res = await axios.get<BatchStatusResponse>(`${API_BASE}/batch/${batchId}/status`);
    return res.data;
  },

  async getBatchReport(batchId: string): Promise<BatchReport> {
    const res = await axios.get<BatchReport>(`${API_BASE}/batch/${batchId}/report`);
    return res.data;
  },

  getGeoJsonExportUrl(jobId: string): string {
    return `${API_BASE}/export-geojson/${jobId}`;
  },

  getCsvExportUrl(jobId: string): string {
    return `${API_BASE}/export-csv/${jobId}`;
  },

  getBatchGeoJsonExportUrl(batchId: string): string {
    return `${API_BASE}/batch/${batchId}/export-geojson`;
  },

  getBatchCsvExportUrl(batchId: string): string {
    return `${API_BASE}/batch/${batchId}/export-csv`;
  },
};

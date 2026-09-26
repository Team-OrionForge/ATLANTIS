/**
 * Project Atlantis Frontend Type Definitions.
 * Hand-synchronized with backend Pydantic v2 schemas in api/schemas.py.
 */

export type TargetClass =
  | 'ghost_net'
  | 'metal_debris'
  | 'chemical_container'
  | 'pipeline'
  | 'marine_plastic'
  | 'shipwreck';

export type HPITier = 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';

export type ShadowVerdict = 'PROTRUSION_CONFIRMED' | 'BENTHIC_DRAPED' | 'DISCARDED_SEABED';

export interface Detection {
  detection_id: string;
  class_name: TargetClass;
  confidence: number;
  bbox: [number, number, number, number]; // [x, y, w, h]
  polygon: [number, number][]; // [[x, y], ...]
  shadow_verdict: ShadowVerdict;
  shadow_intensity: number;
  estimated_elevation_m: number;
  area_m2: number;
  span_m: number;
  hpi_score: number;
  hpi_tier: HPITier;
  lat: number;
  lon: number;
  channel: 'port' | 'starboard';
  components?: Record<string, number>;
}

export interface NadirMetadata {
  nadir_start: number;
  nadir_end: number;
  nadir_width: number;
  image_width: number;
  image_height: number;
  fallback_split: boolean;
}

export interface ProcessSonarResponse {
  success?: boolean;
  is_sonar?: boolean;
  sonar_confidence?: number;
  message?: string | null;
  job_id: string;
  upload_id: string;
  preprocessed_port_b64: string;
  preprocessed_starboard_b64: string;
  raw_port_b64: string;
  raw_starboard_b64: string;
  detections: Detection[];
  total_detections: number;
  critical_count: number;
  high_count: number;
  moderate_count: number;
  low_count: number;
  nadir_metadata: NadirMetadata;
}

export interface UploadResponse {
  upload_id: string;
  filename: string;
  file_path: string;
  size_bytes: number;
}

export interface HealthResponse {
  status: string;
  model_loaded: boolean;
  degraded_mode: boolean;
  version: string;
  uptime_seconds: number;
}

export interface BatchUploadResponse {
  batch_id: string;
  image_count: number;
  dataset_path: string;
}

export interface BatchStatusResponse {
  batch_id: string;
  status: 'queued' | 'running' | 'done' | 'failed';
  completed: number;
  total: number;
  succeeded: number;
  failed: number;
}

export interface BatchImageResult {
  filename: string;
  status: 'done' | 'failed';
  detection_count: number;
  geolocation_estimated: boolean;
  detections: Detection[];
  error?: string | null;
}

export interface BatchReport {
  batch_id: string;
  total_images: number;
  succeeded: number;
  failed: number;
  processing_time_s: number;
  detections_by_class: Record<string, number>;
  hpi_tier_breakdown: Record<string, number>;
  flagged_estimated_geolocation_count: number;
  per_image_results: BatchImageResult[];
}

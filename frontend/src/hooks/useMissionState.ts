import { useState, useCallback } from 'react';
import { ProcessSonarResponse, Detection, TargetClass } from '../types';

export function useMissionState() {
  const [sonarResult, setSonarResult] = useState<ProcessSonarResponse | null>(null);
  const [selectedDetection, setSelectedDetection] = useState<Detection | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'single' | 'batch'>('single');

  // Active taxonomy class filter chips
  const [enabledClasses, setEnabledClasses] = useState<Record<TargetClass, boolean>>({
    ghost_net: true,
    metal_debris: true,
    chemical_container: true,
    pipeline: true,
    marine_plastic: true,
    shipwreck: true,
  });

  // Slider tuning parameters
  const [confThreshold, setConfThreshold] = useState<number>(0.65);
  const [iouThreshold, setIouThreshold] = useState<number>(0.45);
  const [altitudeM, setAltitudeM] = useState<number>(8.0);

  const toggleClass = useCallback((cls: TargetClass) => {
    setEnabledClasses((prev) => ({ ...prev, [cls]: !prev[cls] }));
  }, []);

  const filteredDetections = sonarResult
    ? sonarResult.detections.filter((d) => enabledClasses[d.class_name])
    : [];

  return {
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
  };
}

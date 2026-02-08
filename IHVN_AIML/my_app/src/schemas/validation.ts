import { z } from 'zod';

// Patient selection schema
export const patientSelectionSchema = z.object({
  patient_uuid: z.string().min(1, 'Patient UUID is required'),
});

// Feature input schema for prediction
export const predictionFeaturesSchema = z.object({
  // Demographic features
  age: z.number().min(0).max(120).optional(),
  gender: z.enum(['M', 'F', 'Other']).optional(),
  
  // Clinical features
  cd4_count: z.number().min(0).optional(),
  viral_load: z.number().min(0).optional(),
  art_duration_months: z.number().min(0).optional(),
  
  // Adherence features
  missed_appointments_last_6m: z.number().min(0).max(100).optional(),
  medication_pickup_adherence: z.number().min(0).max(100).optional(),
  
  // Social features
  distance_to_facility_km: z.number().min(0).optional(),
  has_phone: z.boolean().optional(),
  has_support_system: z.boolean().optional(),
  
  // Treatment features
  current_regimen: z.string().optional(),
  regimen_changes_count: z.number().min(0).optional(),
  
  // Visit features
  last_visit_days_ago: z.number().min(0).optional(),
  next_visit_scheduled: z.boolean().optional(),
});

// Combined prediction request schema
export const predictionRequestSchema = z.object({
  patient_uuid: z.string().min(1, 'Patient UUID is required'),
  features: predictionFeaturesSchema,
});

export type PredictionFeaturesData = z.infer<typeof predictionFeaturesSchema>;
export type PredictionRequestData = z.infer<typeof predictionRequestSchema>;
export type PatientSelectionData = z.infer<typeof patientSelectionSchema>;

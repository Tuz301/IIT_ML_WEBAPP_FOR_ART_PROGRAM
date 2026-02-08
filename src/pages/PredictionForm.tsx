import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Loader,
  Search,
  ArrowRight
} from 'lucide-react';
import { toast } from 'react-toastify';
import { useApi } from '../contexts/ApiContext';
import { PredictionFeaturesData } from '../schemas/validation';

interface PredictionResult {
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  features_used: Record<string, any>;
  model_version: string;
  prediction_timestamp: string;
}

const PredictionForm = () => {
  const navigate = useNavigate();
  const { getPatients, createPrediction } = useApi();
  
  // Form state
  const [step, setStep] = useState<'select' | 'features' | 'result'>('select');
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [patients, setPatients] = useState<any[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<any>(null);
  
  // Feature inputs
  const [features, setFeatures] = useState<PredictionFeaturesData>({});
  const [predictionResult, setPredictionResult] = useState<PredictionResult | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Load patients on mount
  useEffect(() => {
    loadPatients();
  }, []);

  const loadPatients = async () => {
    try {
      const response = await getPatients(0, 50, searchQuery);
      if (response.data?.patients) {
        setPatients(response.data.patients);
      }
    } catch (error) {
      console.error('Failed to load patients:', error);
    }
  };

  // Search patients
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      loadPatients();
    }, 500);
    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  const handlePatientSelect = (patient: any) => {
    setSelectedPatient(patient);
    setStep('features');
  };

  const handleFeatureChange = (field: string, value: any) => {
    setFeatures(prev => ({ ...prev, [field]: value }));
    // Clear error for this field
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const validateFeatures = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    // Simple validation
    if (features.age !== undefined && (features.age < 0 || features.age > 120)) {
      newErrors.age = 'Age must be between 0 and 120';
    }
    if (features.missed_appointments_last_6m !== undefined && 
        (features.missed_appointments_last_6m < 0 || features.missed_appointments_last_6m > 100)) {
      newErrors.missed_appointments_last_6m = 'Value must be between 0 and 100';
    }
    if (features.medication_pickup_adherence !== undefined && 
        (features.medication_pickup_adherence < 0 || features.medication_pickup_adherence > 100)) {
      newErrors.medication_pickup_adherence = 'Value must be between 0 and 100';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handlePredict = async () => {
    if (!selectedPatient) {
      toast.error('Please select a patient first');
      return;
    }

    if (!validateFeatures()) {
      toast.error('Please fix the validation errors');
      return;
    }

    setLoading(true);
    try {
      const response = await createPrediction({
        patient_uuid: selectedPatient.patient_uuid,
        features: features
      });

      if (response.data) {
        setPredictionResult(response.data as PredictionResult);
        setStep('result');
        toast.success('Prediction completed successfully!');
      }
    } catch (error) {
      console.error('Prediction failed:', error);
      toast.error('Failed to generate prediction. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setStep('select');
    setSelectedPatient(null);
    setFeatures({});
    setPredictionResult(null);
    setErrors({});
    setSearchQuery('');
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'low': return 'from-green-400 to-emerald-500';
      case 'medium': return 'from-yellow-400 to-amber-500';
      case 'high': return 'from-orange-400 to-red-500';
      case 'critical': return 'from-red-500 to-pink-600';
      default: return 'from-gray-400 to-gray-500';
    }
  };

  const getRiskIcon = (level: string) => {
    switch (level) {
      case 'low': return CheckCircle;
      case 'medium': return Activity;
      case 'high': return AlertTriangle;
      case 'critical': return AlertTriangle;
      default: return Activity;
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center space-y-2"
      >
        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          Treatment Risk Prediction
        </h1>
        <p className="text-gray-600">
          Use machine learning to predict patient treatment interruption risk
        </p>
      </motion.div>

      {/* Step Indicator */}
      <div className="flex items-center justify-center space-x-4">
        {['Select Patient', 'Enter Features', 'View Result'].map((label, index) => (
          <div key={label} className="flex items-center">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
              (step === 'select' && index === 0) ||
              (step === 'features' && index === 1) ||
              (step === 'result' && index === 2)
                ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white'
                : 'bg-gray-200 text-gray-600'
            }`}>
              {index + 1}
            </div>
            {index < 2 && (
              <div className={`w-16 h-1 ${index < (step === 'select' ? 0 : step === 'features' ? 1 : 2) ? 'bg-blue-500' : 'bg-gray-200'}`} />
            )}
            <span className={`ml-2 text-sm ${index < (step === 'select' ? 0 : step === 'features' ? 1 : 2) ? 'text-blue-600 font-medium' : 'text-gray-400'}`}>
              {label}
            </span>
          </div>
        ))}
      </div>

      {/* Step 1: Select Patient */}
      {step === 'select' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl shadow-xl p-6 border border-gray-100"
        >
          <h2 className="text-xl font-bold text-gray-800 mb-4">Select Patient</h2>
          
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search patients by name or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div className="space-y-2 max-h-96 overflow-y-auto">
            {patients.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No patients found. Try a different search term.
              </div>
            ) : (
              patients.map((patient) => (
                <motion.button
                  key={patient.patient_uuid}
                  whileHover={{ scale: 1.01 }}
                  onClick={() => handlePatientSelect(patient)}
                  className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-blue-50 rounded-xl border border-gray-200 hover:border-blue-300 transition-all"
                >
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold">
                      {patient.given_name?.[0] || '?'}
                    </div>
                    <div className="text-left">
                      <div className="font-semibold text-gray-800">
                        {patient.given_name} {patient.family_name}
                      </div>
                      <div className="text-sm text-gray-500">
                        ID: {patient.datim_id || patient.pepfar_id || patient.patient_uuid.slice(0, 8)}
                      </div>
                    </div>
                  </div>
                  <ArrowRight className="w-5 h-5 text-gray-400" />
                </motion.button>
              ))
            )}
          </div>
        </motion.div>
      )}

      {/* Step 2: Enter Features */}
      {step === 'features' && selectedPatient && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl shadow-xl p-6 border border-gray-100"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-800">
              Patient: {selectedPatient.given_name} {selectedPatient.family_name}
            </h2>
            <button
              onClick={() => setStep('select')}
              className="text-blue-600 hover:text-blue-800 text-sm font-medium"
            >
              Change Patient
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Demographic Features */}
            <div className="space-y-4">
              <h3 className="font-semibold text-gray-700 border-b pb-2">Demographics</h3>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Age</label>
                <input
                  type="number"
                  value={features.age || ''}
                  onChange={(e) => handleFeatureChange('age', parseInt(e.target.value) || 0)}
                  className={`w-full px-4 py-2 border rounded-lg ${errors.age ? 'border-red-500' : 'border-gray-300'}`}
                  placeholder="Enter age"
                />
                {errors.age && <p className="text-red-500 text-xs mt-1">{errors.age}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Gender</label>
                <select
                  value={features.gender || ''}
                  onChange={(e) => handleFeatureChange('gender', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="">Select gender</option>
                  <option value="M">Male</option>
                  <option value="F">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>

            {/* Clinical Features */}
            <div className="space-y-4">
              <h3 className="font-semibold text-gray-700 border-b pb-2">Clinical</h3>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">CD4 Count</label>
                <input
                  type="number"
                  value={features.cd4_count || ''}
                  onChange={(e) => handleFeatureChange('cd4_count', parseInt(e.target.value) || 0)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                  placeholder="CD4 count"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Viral Load</label>
                <input
                  type="number"
                  value={features.viral_load || ''}
                  onChange={(e) => handleFeatureChange('viral_load', parseInt(e.target.value) || 0)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                  placeholder="Viral load"
                />
              </div>
            </div>

            {/* Adherence Features */}
            <div className="space-y-4">
              <h3 className="font-semibold text-gray-700 border-b pb-2">Adherence</h3>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Missed Appointments (Last 6 months)
                </label>
                <input
                  type="number"
                  value={features.missed_appointments_last_6m || ''}
                  onChange={(e) => handleFeatureChange('missed_appointments_last_6m', parseInt(e.target.value) || 0)}
                  className={`w-full px-4 py-2 border rounded-lg ${errors.missed_appointments_last_6m ? 'border-red-500' : 'border-gray-300'}`}
                  placeholder="Number of missed appointments"
                />
                {errors.missed_appointments_last_6m && <p className="text-red-500 text-xs mt-1">{errors.missed_appointments_last_6m}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Medication Pickup Adherence (%)
                </label>
                <input
                  type="number"
                  value={features.medication_pickup_adherence || ''}
                  onChange={(e) => handleFeatureChange('medication_pickup_adherence', parseInt(e.target.value) || 0)}
                  className={`w-full px-4 py-2 border rounded-lg ${errors.medication_pickup_adherence ? 'border-red-500' : 'border-gray-300'}`}
                  placeholder="Adherence percentage"
                  min="0"
                  max="100"
                />
                {errors.medication_pickup_adherence && <p className="text-red-500 text-xs mt-1">{errors.medication_pickup_adherence}</p>}
              </div>
            </div>

            {/* Social Features */}
            <div className="space-y-4">
              <h3 className="font-semibold text-gray-700 border-b pb-2">Social</h3>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Distance to Facility (km)
                </label>
                <input
                  type="number"
                  value={features.distance_to_facility_km || ''}
                  onChange={(e) => handleFeatureChange('distance_to_facility_km', parseFloat(e.target.value) || 0)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                  placeholder="Distance in km"
                />
              </div>

              <div className="flex items-center space-x-4">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={features.has_phone || false}
                    onChange={(e) => handleFeatureChange('has_phone', e.target.checked)}
                    className="rounded text-blue-600"
                  />
                  <span className="text-sm text-gray-700">Has Phone</span>
                </label>

                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={features.has_support_system || false}
                    onChange={(e) => handleFeatureChange('has_support_system', e.target.checked)}
                    className="rounded text-blue-600"
                  />
                  <span className="text-sm text-gray-700">Has Support System</span>
                </label>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex justify-between mt-6 pt-6 border-t">
            <button
              onClick={() => setStep('select')}
              className="px-6 py-3 border border-gray-300 rounded-xl text-gray-700 hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={handlePredict}
              disabled={loading}
              className="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl font-semibold hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {loading ? (
                <>
                  <Loader className="w-5 h-5 animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <Activity className="w-5 h-5" />
                  <span>Generate Prediction</span>
                </>
              )}
            </button>
          </div>
        </motion.div>
      )}

      {/* Step 3: Result */}
      {step === 'result' && predictionResult && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100"
        >
          <div className="text-center space-y-6">
            <h2 className="text-2xl font-bold text-gray-800">Prediction Result</h2>
            
            {/* Risk Score Display */}
            <div className={`w-48 h-48 mx-auto rounded-full bg-gradient-to-br ${getRiskColor(predictionResult.risk_level)} flex items-center justify-center shadow-2xl`}>
              <div className="text-center text-white">
                <div className="text-5xl font-bold">{predictionResult.risk_score}</div>
                <div className="text-sm opacity-90">Risk Score</div>
              </div>
            </div>

            {/* Risk Level */}
            <div className="space-y-2">
              <div className={`inline-flex items-center px-6 py-3 rounded-full text-lg font-bold bg-gradient-to-r ${getRiskColor(predictionResult.risk_level)} text-white shadow-lg`}>
                {(() => {
                  const Icon = getRiskIcon(predictionResult.risk_level);
                  return <Icon className="w-6 h-6 mr-2" />;
                })()}
                {predictionResult.risk_level.toUpperCase()} RISK
              </div>
              <p className="text-gray-600">
                Confidence: <span className="font-semibold">{(predictionResult.confidence * 100).toFixed(1)}%</span>
              </p>
            </div>

            {/* Recommendations */}
            <div className="bg-blue-50 rounded-xl p-6 text-left max-w-md mx-auto">
              <h3 className="font-semibold text-blue-800 mb-3">Recommendations</h3>
              <ul className="space-y-2 text-blue-700">
                {predictionResult.risk_level === 'low' && (
                  <>
                    <li>• Continue regular monitoring</li>
                    <li>• Maintain current treatment plan</li>
                    <li>• Schedule routine follow-up</li>
                  </>
                )}
                {predictionResult.risk_level === 'medium' && (
                  <>
                    <li>• Increase monitoring frequency</li>
                    <li>• Assess adherence barriers</li>
                    <li>• Provide additional support resources</li>
                  </>
                )}
                {predictionResult.risk_level === 'high' && (
                  <>
                    <li>• Immediate intervention required</li>
                    <li>• Conduct home visit if possible</li>
                    <li>• Engage family support system</li>
                    <li>• Consider treatment regimen review</li>
                  </>
                )}
                {predictionResult.risk_level === 'critical' && (
                  <>
                    <li>• URGENT: Direct outreach needed</li>
                    <li>• Emergency case management</li>
                    <li>• Multi-disciplinary team involvement</li>
                    <li>• Daily monitoring until stabilized</li>
                  </>
                )}
              </ul>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-center space-x-4">
              <button
                onClick={handleReset}
                className="px-6 py-3 border border-gray-300 rounded-xl text-gray-700 hover:bg-gray-50"
              >
                New Prediction
              </button>
              <button
                onClick={() => navigate('/patients')}
                className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700"
              >
                View Patient Details
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default PredictionForm;

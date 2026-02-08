import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Edit, Calendar, MapPin, Phone, User, Activity, FileText, Clock } from 'lucide-react';
import { apiService, Patient } from '../services/api';

const PatientDetail: React.FC = () => {
  const { patientUuid } = useParams<{ patientUuid: string }>();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (patientUuid) {
      fetchPatient();
    }
  }, [patientUuid]);

  const fetchPatient = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getPatient(patientUuid!);
      setPatient(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch patient');
    } finally {
      setLoading(false);
    }
  };

  const calculateAge = (birthdate: string | undefined) => {
    if (!birthdate) return 'N/A';
    const birth = new Date(birthdate);
    const today = new Date();
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--;
    }
    return age;
  };

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatDateTime = (dateString: string | undefined) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error || !patient) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-4">
          <Link
            to="/patients"
            className="flex items-center text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            Back to Patients
          </Link>
        </div>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <p className="text-red-800 dark:text-red-400">{error || 'Patient not found'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link
            to="/patients"
            className="flex items-center text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            Back to Patients
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              {patient.given_name && patient.family_name
                ? `${patient.given_name} ${patient.family_name}`
                : patient.given_name || patient.family_name || 'Patient Details'
              }
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Patient ID: {patient.datim_id || patient.pepfar_id || patient.patient_uuid.slice(0, 8)}
            </p>
          </div>
        </div>
        <Link
          to={`/patients/${patient.patient_uuid}/edit`}
          className="flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
        >
          <Edit className="w-4 h-4 mr-2" />
          Edit Patient
        </Link>
      </div>

      {/* Patient Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center">
            <User className="w-8 h-8 text-indigo-600 dark:text-indigo-400" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Age</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {calculateAge(patient.birthdate)}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
              <span className="text-blue-600 dark:text-blue-400 font-semibold">
                {patient.gender === 'M' ? 'M' : patient.gender === 'F' ? 'F' : '?'}
              </span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Gender</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {patient.gender === 'M' ? 'Male' : patient.gender === 'F' ? 'Female' : patient.gender || 'N/A'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center">
            <MapPin className="w-8 h-8 text-green-600 dark:text-green-400" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Location</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">
                {patient.state_province || 'N/A'}
              </p>
              {patient.city_village && (
                <p className="text-sm text-gray-600 dark:text-gray-400">{patient.city_village}</p>
              )}
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center">
            <Phone className="w-8 h-8 text-purple-600 dark:text-purple-400" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Phone</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">
                {patient.phone_number || 'N/A'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="flex space-x-8 px-6">
            {[
              { id: 'overview', label: 'Overview', icon: User },
              { id: 'visits', label: 'Visits', icon: Calendar },
              { id: 'encounters', label: 'Encounters', icon: Activity },
              { id: 'observations', label: 'Observations', icon: FileText },
              { id: 'history', label: 'History', icon: Clock },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                <tab.icon className="w-4 h-4 mr-2" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Patient Information</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Patient UUID</label>
                      <p className="mt-1 text-sm text-gray-900 dark:text-white font-mono">{patient.patient_uuid}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">DATIM ID</label>
                      <p className="mt-1 text-sm text-gray-900 dark:text-white">{patient.datim_id || 'N/A'}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">PEPFAR ID</label>
                      <p className="mt-1 text-sm text-gray-900 dark:text-white">{patient.pepfar_id || 'N/A'}</p>
                    </div>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Date of Birth</label>
                      <p className="mt-1 text-sm text-gray-900 dark:text-white">{formatDate(patient.birthdate)}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Created</label>
                      <p className="mt-1 text-sm text-gray-900 dark:text-white">{formatDateTime(patient.created_at)}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Last Updated</label>
                      <p className="mt-1 text-sm text-gray-900 dark:text-white">{formatDateTime(patient.updated_at)}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'visits' && (
            <div className="text-center py-12">
              <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Visit History</h3>
              <p className="text-gray-600 dark:text-gray-400">Visit data will be displayed here</p>
            </div>
          )}

          {activeTab === 'encounters' && (
            <div className="text-center py-12">
              <Activity className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Encounter History</h3>
              <p className="text-gray-600 dark:text-gray-400">Encounter data will be displayed here</p>
            </div>
          )}

          {activeTab === 'observations' && (
            <div className="text-center py-12">
              <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Clinical Observations</h3>
              <p className="text-gray-600 dark:text-gray-400">Observation data will be displayed here</p>
            </div>
          )}

          {activeTab === 'history' && (
            <div className="text-center py-12">
              <Clock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Change History</h3>
              <p className="text-gray-600 dark:text-gray-400">Patient change history will be displayed here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PatientDetail;

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Search, Filter, Plus, Download, Upload, Trash2, ChevronLeft, ChevronRight, User, Phone, MapPin, Calendar, X } from 'lucide-react';
import { apiService, PatientListResponse, Patient } from '../services/api';

const PatientList: React.FC = () => {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(50);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  // Filters
  const [filters, setFilters] = useState({
    gender: '',
    state_province: '',
    has_phone: '',
    age_min: '',
    age_max: '',
  });

  useEffect(() => {
    fetchPatients();
  }, [currentPage, searchQuery, filters]);

  const fetchPatients = async () => {
    try {
      setLoading(true);
      setError(null);

      const params: any = {
        page: currentPage,
        page_size: pageSize,
        search: searchQuery || undefined,
      };

      // Add filters
      if (filters.gender) params.gender = filters.gender;
      if (filters.state_province) params.state_province = filters.state_province;
      if (filters.has_phone) params.has_phone = filters.has_phone === 'true';
      if (filters.age_min) params.age_min = parseInt(filters.age_min);
      if (filters.age_max) params.age_max = parseInt(filters.age_max);

      const response: PatientListResponse = await apiService.getPatients(params);
      // Ensure patients is always an array, even if response is malformed
      setPatients(Array.isArray(response?.patients) ? response.patients : []);
      setTotal(response?.total ?? 0);
      setTotalPages(response?.total_pages ?? 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch patients');
      // Set empty arrays on error to prevent undefined errors
      setPatients([]);
      setTotal(0);
      setTotalPages(0);
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleDeletePatient = async (patientUuid: string) => {
    if (!confirm('Are you sure you want to delete this patient? This action cannot be undone.')) {
      return;
    }

    try {
      await apiService.deletePatient(patientUuid);
      fetchPatients(); // Refresh the list
    } catch (err) {
      alert('Failed to delete patient: ' + (err instanceof Error ? err.message : 'Unknown error'));
    }
  };

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setCurrentPage(1); // Reset to first page when filters change
  };

  const clearFilters = () => {
    setFilters({
      gender: '',
      state_province: '',
      has_phone: '',
      age_min: '',
      age_max: '',
    });
    setCurrentPage(1);
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
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Patient Management</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Manage patient records, search, filter, and perform bulk operations
          </p>
        </div>
        <div className="flex space-x-3">
          <button className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
            <Upload className="w-4 h-4 mr-2" />
            Import
          </button>
          <button className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            <Download className="w-4 h-4 mr-2" />
            Export
          </button>
          <Link
            to="/patients/new"
            className="flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Patient
          </Link>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex-1 max-w-md">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search patients by name, ID, or phone..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              />
            </div>
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 dark:text-white"
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
          </button>
        </div>

        {/* Filter Panel */}
        {showFilters && (
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Gender
                </label>
                <select
                  value={filters.gender}
                  onChange={(e) => handleFilterChange('gender', e.target.value)}
                  className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 dark:bg-gray-700 dark:text-white"
                >
                  <option value="">All</option>
                  <option value="M">Male</option>
                  <option value="F">Female</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  State/Province
                </label>
                <input
                  type="text"
                  value={filters.state_province}
                  onChange={(e) => handleFilterChange('state_province', e.target.value)}
                  placeholder="Enter state/province"
                  className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 dark:bg-gray-700 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Has Phone
                </label>
                <select
                  value={filters.has_phone}
                  onChange={(e) => handleFilterChange('has_phone', e.target.value)}
                  className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 dark:bg-gray-700 dark:text-white"
                >
                  <option value="">All</option>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Min Age
                </label>
                <input
                  type="number"
                  value={filters.age_min}
                  onChange={(e) => handleFilterChange('age_min', e.target.value)}
                  placeholder="0"
                  min="0"
                  max="120"
                  className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 dark:bg-gray-700 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Max Age
                </label>
                <input
                  type="number"
                  value={filters.age_max}
                  onChange={(e) => handleFilterChange('age_max', e.target.value)}
                  placeholder="120"
                  min="0"
                  max="120"
                  className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 dark:bg-gray-700 dark:text-white"
                />
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={clearFilters}
                className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
              >
                Clear Filters
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Results Summary */}
      <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
        <span>
          Showing {patients?.length ?? 0} of {total ?? 0} patients
        </span>
        <span>
          Page {currentPage} of {totalPages ?? 0}
        </span>
      </div>

      {/* Patient Cards */}
      {loading ? (
        <div className="flex justify-center items-center h-64">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            className="w-12 h-12 border-4 border-indigo-200 border-t-indigo-600 rounded-full"
          />
        </div>
      ) : error ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-red-50 border border-red-200 rounded-2xl p-8 text-center"
        >
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <X className="w-8 h-8 text-red-600" />
          </div>
          <h3 className="text-lg font-semibold text-red-800 mb-2">Error Loading Patients</h3>
          <p className="text-red-600 mb-6">{error}</p>
          <button
            onClick={fetchPatients}
            className="px-6 py-3 bg-red-600 text-white rounded-xl font-semibold hover:bg-red-700 transition-all shadow-lg hover:shadow-xl"
          >
            Try Again
          </button>
        </motion.div>
      ) : (
        <>
          {/* Patient Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {patients?.map((patient, index) => (
              <motion.div
                key={patient.patient_uuid}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="bg-white rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-100 overflow-hidden group"
              >
                {/* Card Header */}
                <div className="bg-gradient-to-r from-blue-500 to-purple-600 p-4">
                  <div className="flex items-center justify-between">
                    <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                      <User className="w-6 h-6 text-white" />
                    </div>
                    <div className="text-right">
                      <div className="text-white/80 text-xs font-medium">ID</div>
                      <div className="text-white font-bold text-sm">
                        {patient.datim_id || patient.pepfar_id || patient.patient_uuid.slice(0, 8)}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card Content */}
                <div className="p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-2">
                    {patient.given_name && patient.family_name
                      ? `${patient.given_name} ${patient.family_name}`
                      : patient.given_name || patient.family_name || 'Unknown Patient'
                    }
                  </h3>

                  <div className="space-y-3">
                    <div className="flex items-center text-gray-600">
                      <Calendar className="w-4 h-4 mr-2 text-blue-500" />
                      <span className="text-sm">
                        Age: <span className="font-semibold">{calculateAge(patient.birthdate)}</span>
                      </span>
                    </div>

                    <div className="flex items-center text-gray-600">
                      <User className="w-4 h-4 mr-2 text-purple-500" />
                      <span className="text-sm">
                        Gender: <span className="font-semibold">
                          {patient.gender === 'M' ? 'Male' : patient.gender === 'F' ? 'Female' : patient.gender || 'N/A'}
                        </span>
                      </span>
                    </div>

                    {patient.phone_number && (
                      <div className="flex items-center text-gray-600">
                        <Phone className="w-4 h-4 mr-2 text-green-500" />
                        <span className="text-sm font-mono">{patient.phone_number}</span>
                      </div>
                    )}

                    {(patient.state_province || patient.city_village) && (
                      <div className="flex items-center text-gray-600">
                        <MapPin className="w-4 h-4 mr-2 text-orange-500" />
                        <span className="text-sm">
                          {patient.state_province || 'N/A'}
                          {patient.city_village && `, ${patient.city_village}`}
                        </span>
                      </div>
                    )}

                    <div className="text-xs text-gray-500 pt-2 border-t border-gray-100">
                      Created: {formatDate(patient.created_at)}
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex space-x-2 mt-6">
                    <Link
                      to={`/patients/${patient.patient_uuid}`}
                      className="flex-1 bg-gradient-to-r from-blue-500 to-blue-600 text-white py-2 px-4 rounded-xl font-semibold text-center hover:from-blue-600 hover:to-blue-700 transition-all shadow-md hover:shadow-lg"
                    >
                      View
                    </Link>
                    <Link
                      to={`/patients/${patient.patient_uuid}/edit`}
                      className="flex-1 bg-gradient-to-r from-gray-500 to-gray-600 text-white py-2 px-4 rounded-xl font-semibold text-center hover:from-gray-600 hover:to-gray-700 transition-all shadow-md hover:shadow-lg"
                    >
                      Edit
                    </Link>
                    <button
                      onClick={() => handleDeletePatient(patient.patient_uuid)}
                      className="bg-gradient-to-r from-red-500 to-red-600 text-white p-2 rounded-xl hover:from-red-600 hover:to-red-700 transition-all shadow-md hover:shadow-lg"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 mt-8"
            >
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-600">
                  Showing <span className="font-semibold">{(currentPage - 1) * pageSize + 1}</span> to{' '}
                  <span className="font-semibold">{Math.min(currentPage * pageSize, total)}</span> of{' '}
                  <span className="font-semibold">{total}</span> patients
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="p-2 rounded-xl border border-gray-200 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>

                  <div className="flex space-x-1">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      const pageNum = Math.max(1, Math.min(totalPages - 4, currentPage - 2)) + i;
                      if (pageNum > totalPages) return null;

                      return (
                        <button
                          key={pageNum}
                          onClick={() => handlePageChange(pageNum)}
                          className={`px-4 py-2 rounded-xl font-semibold transition-all ${
                            pageNum === currentPage
                              ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg'
                              : 'border border-gray-200 hover:bg-gray-50'
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                  </div>

                  <button
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="p-2 rounded-xl border border-gray-200 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </>
      )}
    </div>
  );
};

export default PatientList;

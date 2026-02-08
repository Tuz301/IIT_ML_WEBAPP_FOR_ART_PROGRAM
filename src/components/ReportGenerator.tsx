import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  FileText,
  Download,
  FileSpreadsheet,
  File,
  Calendar,
  Filter,
  Settings,
  CheckCircle,
  Loader
} from 'lucide-react';

interface ReportConfig {
  type: 'pdf' | 'excel' | 'csv';
  dateRange: { start: string; end: string };
  filters: {
    riskLevel?: string[];
    departments?: string[];
    ageRange?: { min: number; max: number };
  };
  includeCharts: boolean;
  includeRawData: boolean;
}

interface ReportGeneratorProps {
  reportType: string;
  onGenerate: (config: ReportConfig) => Promise<void>;
}

const ReportGenerator: React.FC<ReportGeneratorProps> = ({ reportType, onGenerate }) => {
  // Use reportType for component logic or display
  console.log('Report type:', reportType);
  const [config, setConfig] = useState<ReportConfig>({
    type: 'pdf',
    dateRange: { start: '', end: '' },
    filters: {},
    includeCharts: true,
    includeRawData: false
  });

  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setProgress(0);

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return prev;
          }
          return prev + 10;
        });
      }, 200);

      await onGenerate(config);
      setProgress(100);

      setTimeout(() => {
        setIsGenerating(false);
        setProgress(0);
      }, 1000);
    } catch (error) {
      console.error('Report generation failed:', error);
      setIsGenerating(false);
      setProgress(0);
    }
  };

  const exportFormats = [
    {
      id: 'pdf',
      name: 'PDF Report',
      description: 'Formatted report with charts and tables',
      icon: FileText,
      color: 'from-red-500 to-pink-500'
    },
    {
      id: 'excel',
      name: 'Excel Spreadsheet',
      description: 'Raw data with calculations and pivot tables',
      icon: FileSpreadsheet,
      color: 'from-green-500 to-emerald-500'
    },
    {
      id: 'csv',
      name: 'CSV Data Export',
      description: 'Comma-separated values for data analysis',
      icon: File,
      color: 'from-blue-500 to-cyan-500'
    }
  ];

  const riskLevels = ['Low', 'Medium', 'High', 'Critical'];
  const departments = ['Cardiology', 'Oncology', 'Neurology', 'Emergency', 'General Medicine'];

  return (
    <div className="space-y-6">
      {/* Export Format Selection */}
      <div className="bg-white rounded-2xl p-6 shadow-xl border border-gray-100">
        <h3 className="text-xl font-bold text-gray-800 mb-6">Export Format</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {exportFormats.map((format) => (
            <motion.div
              key={format.id}
              whileHover={{ scale: 1.02 }}
              className={`relative p-4 rounded-xl border-2 cursor-pointer transition-all ${
                config.type === format.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
              onClick={() => setConfig(prev => ({ ...prev, type: format.id as ReportConfig['type'] }))}
            >
              <div className="flex items-center space-x-3 mb-3">
                <div className={`w-10 h-10 bg-gradient-to-br ${format.color} rounded-lg flex items-center justify-center`}>
                  <format.icon className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-800">{format.name}</h4>
                </div>
              </div>
              <p className="text-sm text-gray-600">{format.description}</p>
              {config.type === format.id && (
                <div className="absolute top-4 right-4">
                  <CheckCircle className="w-5 h-5 text-blue-500" />
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </div>

      {/* Date Range */}
      <div className="bg-white rounded-2xl p-6 shadow-xl border border-gray-100">
        <h3 className="text-xl font-bold text-gray-800 mb-6 flex items-center">
          <Calendar className="w-5 h-5 mr-3 text-blue-600" />
          Date Range
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Start Date</label>
            <input
              type="date"
              value={config.dateRange.start}
              onChange={(e) => setConfig(prev => ({
                ...prev,
                dateRange: { ...prev.dateRange, start: e.target.value }
              }))}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">End Date</label>
            <input
              type="date"
              value={config.dateRange.end}
              onChange={(e) => setConfig(prev => ({
                ...prev,
                dateRange: { ...prev.dateRange, end: e.target.value }
              }))}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl p-6 shadow-xl border border-gray-100">
        <h3 className="text-xl font-bold text-gray-800 mb-6 flex items-center">
          <Filter className="w-5 h-5 mr-3 text-purple-600" />
          Filters
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Risk Levels */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">Risk Levels</label>
            <div className="space-y-2">
              {riskLevels.map((level) => (
                <label key={level} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={config.filters.riskLevel?.includes(level) || false}
                    onChange={(e) => {
                      const current = config.filters.riskLevel || [];
                      const updated = e.target.checked
                        ? [...current, level]
                        : current.filter(l => l !== level);
                      setConfig(prev => ({
                        ...prev,
                        filters: { ...prev.filters, riskLevel: updated }
                      }));
                    }}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">{level}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Departments */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">Departments</label>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {departments.map((dept) => (
                <label key={dept} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={config.filters.departments?.includes(dept) || false}
                    onChange={(e) => {
                      const current = config.filters.departments || [];
                      const updated = e.target.checked
                        ? [...current, dept]
                        : current.filter(d => d !== dept);
                      setConfig(prev => ({
                        ...prev,
                        filters: { ...prev.filters, departments: updated }
                      }));
                    }}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">{dept}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Age Range */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">Age Range</label>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Min Age</label>
                <input
                  type="number"
                  min="0"
                  max="120"
                  value={config.filters.ageRange?.min || ''}
                  onChange={(e) => setConfig(prev => ({
                    ...prev,
                    filters: {
                      ...prev.filters,
                      ageRange: {
                        min: parseInt(e.target.value) || 0,
                        max: prev.filters.ageRange?.max || 120
                      }
                    }
                  }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Max Age</label>
                <input
                  type="number"
                  min="0"
                  max="120"
                  value={config.filters.ageRange?.max || ''}
                  onChange={(e) => setConfig(prev => ({
                    ...prev,
                    filters: {
                      ...prev.filters,
                      ageRange: {
                        min: prev.filters.ageRange?.min || 0,
                        max: parseInt(e.target.value) || 120
                      }
                    }
                  }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Options */}
      <div className="bg-white rounded-2xl p-6 shadow-xl border border-gray-100">
        <h3 className="text-xl font-bold text-gray-800 mb-6 flex items-center">
          <Settings className="w-5 h-5 mr-3 text-green-600" />
          Report Options
        </h3>

        <div className="space-y-4">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={config.includeCharts}
              onChange={(e) => setConfig(prev => ({ ...prev, includeCharts: e.target.checked }))}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="ml-3 text-sm text-gray-700">Include charts and visualizations</span>
          </label>

          <label className="flex items-center">
            <input
              type="checkbox"
              checked={config.includeRawData}
              onChange={(e) => setConfig(prev => ({ ...prev, includeRawData: e.target.checked }))}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="ml-3 text-sm text-gray-700">Include raw data tables</span>
          </label>
        </div>
      </div>

      {/* Generation Progress */}
      {isGenerating && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl p-6 shadow-xl border border-gray-100"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-gray-800">Generating Report...</h3>
            <span className="text-sm text-gray-500">{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <motion.div
              className="bg-gradient-to-r from-blue-500 to-purple-600 h-2 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          <div className="flex items-center mt-4 text-sm text-gray-600">
            <Loader className="w-4 h-4 mr-2 animate-spin" />
            Processing data and generating {config.type.toUpperCase()} file...
          </div>
        </motion.div>
      )}

      {/* Generate Button */}
      <div className="flex justify-center">
        <button
          onClick={handleGenerate}
          disabled={isGenerating || !config.dateRange.start || !config.dateRange.end}
          className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-8 py-4 rounded-2xl font-bold hover:from-blue-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-3 shadow-lg hover:shadow-xl"
        >
          {isGenerating ? (
            <>
              <Loader className="w-6 h-6 animate-spin" />
              <span>Generating...</span>
            </>
          ) : (
            <>
              <Download className="w-6 h-6" />
              <span>Generate {config.type.toUpperCase()} Report</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default ReportGenerator;

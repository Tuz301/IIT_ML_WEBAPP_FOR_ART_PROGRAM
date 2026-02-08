import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Calendar,
  Clock,
  Mail,
  FileText,
  Plus,
  Edit,
  Trash2,
  Play,
  Pause,
  CheckCircle,
  AlertCircle
} from 'lucide-react';

interface ScheduledReport {
  id: string;
  name: string;
  type: string;
  frequency: string;
  nextRun: string;
  status: 'active' | 'paused' | 'completed' | 'failed';
  recipients: string[];
  lastRun?: string;
  createdAt: string;
}

const ScheduledReports: React.FC = () => {
  const [reports, setReports] = useState<ScheduledReport[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingReport, setEditingReport] = useState<ScheduledReport | null>(null);

  // Mock data - replace with actual API calls
  useEffect(() => {
    const mockReports: ScheduledReport[] = [
      {
        id: '1',
        name: 'Weekly Risk Summary',
        type: 'risk_summary',
        frequency: 'weekly',
        nextRun: '2024-01-15T09:00:00Z',
        status: 'active',
        recipients: ['admin@ihvn.org', 'manager@ihvn.org'],
        lastRun: '2024-01-08T09:00:00Z',
        createdAt: '2024-01-01T10:00:00Z'
      },
      {
        id: '2',
        name: 'Monthly Intervention Report',
        type: 'intervention_report',
        frequency: 'monthly',
        nextRun: '2024-02-01T09:00:00Z',
        status: 'active',
        recipients: ['clinical@ihvn.org'],
        lastRun: '2024-01-01T09:00:00Z',
        createdAt: '2024-01-01T10:00:00Z'
      }
    ];
    setReports(mockReports);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'paused':
        return <Pause className="w-5 h-5 text-yellow-500" />;
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'paused':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleCreateReport = () => {
    setShowCreateForm(true);
    setEditingReport(null);
  };

  const handleEditReport = (report: ScheduledReport) => {
    setEditingReport(report);
    setShowCreateForm(true);
  };

  const handleDeleteReport = (reportId: string) => {
    setReports(reports.filter(r => r.id !== reportId));
  };

  const handleToggleStatus = (reportId: string) => {
    setReports(reports.map(r =>
      r.id === reportId
        ? { ...r, status: r.status === 'active' ? 'paused' : 'active' as any }
        : r
    ));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Scheduled Reports</h2>
          <p className="text-gray-600">Automate report generation and delivery</p>
        </div>
        <button
          onClick={handleCreateReport}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center"
        >
          <Plus className="w-5 h-5 mr-2" />
          Schedule Report
        </button>
      </div>

      {/* Reports List */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Active Schedules</h3>
        </div>

        <div className="divide-y divide-gray-200">
          {reports.map((report) => (
            <div key={report.id} className="px-6 py-4 hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  {getStatusIcon(report.status)}
                  <div>
                    <h4 className="text-sm font-medium text-gray-900">{report.name}</h4>
                    <div className="flex items-center space-x-4 mt-1">
                      <span className="text-sm text-gray-500 flex items-center">
                        <Calendar className="w-4 h-4 mr-1" />
                        {report.frequency}
                      </span>
                      <span className="text-sm text-gray-500 flex items-center">
                        <Clock className="w-4 h-4 mr-1" />
                        Next: {new Date(report.nextRun).toLocaleDateString()}
                      </span>
                      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(report.status)}`}>
                        {report.status}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleToggleStatus(report.id)}
                    className="p-1 text-gray-400 hover:text-gray-600"
                    title={report.status === 'active' ? 'Pause' : 'Resume'}
                  >
                    {report.status === 'active' ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => handleEditReport(report)}
                    className="p-1 text-gray-400 hover:text-gray-600"
                    title="Edit"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDeleteReport(report.id)}
                    className="p-1 text-gray-400 hover:text-red-600"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="mt-2 flex items-center space-x-4 text-sm text-gray-500">
                <span className="flex items-center">
                  <Mail className="w-4 h-4 mr-1" />
                  {report.recipients.length} recipients
                </span>
                {report.lastRun && (
                  <span>
                    Last run: {new Date(report.lastRun).toLocaleDateString()}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        {reports.length === 0 && (
          <div className="px-6 py-12 text-center">
            <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-sm font-medium text-gray-900 mb-1">No scheduled reports</h3>
            <p className="text-sm text-gray-500 mb-4">Get started by scheduling your first automated report.</p>
            <button
              onClick={handleCreateReport}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              Schedule Report
            </button>
          </div>
        )}
      </div>

      {/* Create/Edit Form Modal */}
      {showCreateForm && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-white rounded-lg p-6 w-full max-w-md"
          >
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              {editingReport ? 'Edit Scheduled Report' : 'Schedule New Report'}
            </h3>

            <form className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Report Name
                </label>
                <input
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., Weekly Risk Summary"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Report Type
                </label>
                <select className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option>Risk Summary</option>
                  <option>Intervention Report</option>
                  <option>Performance Dashboard</option>
                  <option>Compliance Report</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Frequency
                </label>
                <select className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option>Daily</option>
                  <option>Weekly</option>
                  <option>Monthly</option>
                  <option>Quarterly</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Recipients
                </label>
                <input
                  type="email"
                  multiple
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="email@example.com"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  {editingReport ? 'Update' : 'Schedule'}
                </button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </div>
  );
};

export default ScheduledReports;

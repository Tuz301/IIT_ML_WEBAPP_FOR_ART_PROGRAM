import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  FileText,
  BarChart3,
  PieChart,
  TrendingUp,
  LayoutDashboard,
  Timer
} from 'lucide-react';
import ReportGenerator from '../components/ReportGenerator';
import ScheduledReports from '../components/ScheduledReports';
import CustomDashboard from '../components/CustomDashboard';

const Reports: React.FC = () => {
  const [activeTab, setActiveTab] = useState('reports');

  const tabs = [
    { id: 'reports', label: 'Reports', icon: FileText },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'dashboards', label: 'Dashboards', icon: LayoutDashboard },
    { id: 'scheduled', label: 'Scheduled', icon: Timer }
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Reports & Analytics</h1>
          <p className="text-gray-600">Generate comprehensive reports and analyze IIT risk trends</p>
        </div>

        {/* Tab Navigation */}
        <div className="mb-8">
          <nav className="flex space-x-8" aria-label="Tabs">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center px-1 py-2 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className="w-5 h-5 mr-2" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="space-y-6">
          {activeTab === 'reports' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <ReportGenerator
                reportType="general"
                onGenerate={async (config) => {
                  console.log('Generating report with config:', config);
                  // Mock implementation
                  await new Promise(resolve => setTimeout(resolve, 1000));
                }}
              />
            </motion.div>
          )}

          {activeTab === 'analytics' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-semibold mb-4">Advanced Analytics</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <BarChart3 className="w-8 h-8 text-blue-600 mb-2" />
                    <h3 className="font-medium">Risk Distribution</h3>
                    <p className="text-sm text-gray-600">Analyze risk levels across patient populations</p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <TrendingUp className="w-8 h-8 text-green-600 mb-2" />
                    <h3 className="font-medium">Trend Analysis</h3>
                    <p className="text-sm text-gray-600">Track IIT risk trends over time</p>
                  </div>
                  <div className="bg-purple-50 p-4 rounded-lg">
                    <PieChart className="w-8 h-8 text-purple-600 mb-2" />
                    <h3 className="font-medium">Intervention Effectiveness</h3>
                    <p className="text-sm text-gray-600">Measure success of intervention programs</p>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'dashboards' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <CustomDashboard />
            </motion.div>
          )}

          {activeTab === 'scheduled' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <ScheduledReports />
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Reports;

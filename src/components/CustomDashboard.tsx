import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart3,
  PieChart,
  TrendingUp,
  AlertTriangle,
  Settings,
  X,
  Edit,
  Save,
  Trash2,
  GripVertical
} from 'lucide-react';

interface DashboardWidget {
  id: string;
  type: 'chart' | 'metric' | 'table' | 'alert';
  title: string;
  size: 'small' | 'medium' | 'large';
  position: { x: number; y: number };
  config: any;
}

interface CustomDashboardProps {
  dashboardId?: string;
}

const CustomDashboard: React.FC<CustomDashboardProps> = ({ dashboardId }) => {
  const [widgets, setWidgets] = useState<DashboardWidget[]>([]);
  const [isEditMode, setIsEditMode] = useState(false);
  const [selectedWidget, setSelectedWidget] = useState<string | null>(null);
  const [dashboardName, setDashboardName] = useState('My Custom Dashboard');

  // Mock data - in real app, this would come from API
  const mockWidgets: DashboardWidget[] = [
    {
      id: '1',
      type: 'metric',
      title: 'Total Patients',
      size: 'small',
      position: { x: 0, y: 0 },
      config: { value: 1247, change: '+12%', trend: 'up' }
    },
    {
      id: '2',
      type: 'chart',
      title: 'Risk Distribution',
      size: 'medium',
      position: { x: 1, y: 0 },
      config: { type: 'pie', data: [35, 45, 20] }
    },
    {
      id: '3',
      type: 'alert',
      title: 'High Risk Alerts',
      size: 'small',
      position: { x: 0, y: 1 },
      config: { count: 23, severity: 'high' }
    },
    {
      id: '4',
      type: 'table',
      title: 'Recent Predictions',
      size: 'large',
      position: { x: 1, y: 1 },
      config: { rows: 5 }
    }
  ];

  useEffect(() => {
    // Load dashboard data
    setWidgets(mockWidgets);
  }, [dashboardId]);

  const addWidget = (type: DashboardWidget['type']) => {
    const newWidget: DashboardWidget = {
      id: Date.now().toString(),
      type,
      title: `New ${type.charAt(0).toUpperCase() + type.slice(1)} Widget`,
      size: 'medium',
      position: { x: 0, y: Math.max(...widgets.map(w => w.position.y)) + 1 },
      config: {}
    };
    setWidgets([...widgets, newWidget]);
  };

  const removeWidget = (widgetId: string) => {
    setWidgets(widgets.filter(w => w.id !== widgetId));
  };

  const updateWidget = (widgetId: string, updates: Partial<DashboardWidget>) => {
    setWidgets(widgets.map(w => w.id === widgetId ? { ...w, ...updates } : w));
  };

  const saveDashboard = () => {
    // Mock save - in real app, this would call API
    console.log('Saving dashboard:', { name: dashboardName, widgets });
    setIsEditMode(false);
  };

  const renderWidget = (widget: DashboardWidget) => {
    const sizeClasses = {
      small: 'col-span-1',
      medium: 'col-span-2',
      large: 'col-span-3'
    };

    return (
      <motion.div
        key={widget.id}
        layout
        className={`${sizeClasses[widget.size]} bg-white rounded-2xl p-6 shadow-lg border border-gray-100 relative group`}
        whileHover={{ scale: isEditMode ? 1 : 1.02 }}
      >
        {isEditMode && (
          <div className="absolute top-4 right-4 flex space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={() => setSelectedWidget(widget.id)}
              className="p-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 transition-colors"
            >
              <Edit className="w-4 h-4" />
            </button>
            <button
              onClick={() => removeWidget(widget.id)}
              className="p-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            <div className="p-2 bg-gray-100 text-gray-600 rounded-lg cursor-move">
              <GripVertical className="w-4 h-4" />
            </div>
          </div>
        )}

        <h3 className="text-lg font-bold text-gray-800 mb-4">{widget.title}</h3>

        {widget.type === 'metric' && (
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600 mb-2">
              {widget.config.value?.toLocaleString() || '0'}
            </div>
            <div className="flex items-center justify-center space-x-2">
              <TrendingUp className={`w-4 h-4 ${widget.config.trend === 'up' ? 'text-green-500' : 'text-red-500'}`} />
              <span className={`text-sm font-medium ${widget.config.trend === 'up' ? 'text-green-600' : 'text-red-600'}`}>
                {widget.config.change}
              </span>
            </div>
          </div>
        )}

        {widget.type === 'chart' && (
          <div className="h-48 flex items-center justify-center bg-gray-50 rounded-xl">
            {widget.config.type === 'pie' ? (
              <PieChart className="w-16 h-16 text-blue-500" />
            ) : (
              <BarChart3 className="w-16 h-16 text-green-500" />
            )}
            <span className="ml-4 text-gray-500">Chart visualization</span>
          </div>
        )}

        {widget.type === 'alert' && (
          <div className="flex items-center space-x-4">
            <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
              widget.config.severity === 'high' ? 'bg-red-100' : 'bg-yellow-100'
            }`}>
              <AlertTriangle className={`w-6 h-6 ${
                widget.config.severity === 'high' ? 'text-red-600' : 'text-yellow-600'
              }`} />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-800">{widget.config.count}</div>
              <div className="text-sm text-gray-500">Active alerts</div>
            </div>
          </div>
        )}

        {widget.type === 'table' && (
          <div className="overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-gray-600">Patient</th>
                  <th className="px-4 py-2 text-left text-gray-600">Risk Level</th>
                  <th className="px-4 py-2 text-left text-gray-600">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {Array.from({ length: widget.config.rows || 3 }).map((_, i) => (
                  <tr key={i}>
                    <td className="px-4 py-2">Patient {i + 1}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        i % 3 === 0 ? 'bg-red-100 text-red-700' :
                        i % 3 === 1 ? 'bg-yellow-100 text-yellow-700' :
                        'bg-green-100 text-green-700'
                      }`}>
                        {i % 3 === 0 ? 'High' : i % 3 === 1 ? 'Medium' : 'Low'}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-gray-500">
                      {new Date(Date.now() - i * 86400000).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </motion.div>
    );
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          {isEditMode ? (
            <input
              type="text"
              value={dashboardName}
              onChange={(e) => setDashboardName(e.target.value)}
              className="text-3xl font-bold text-gray-800 bg-transparent border-b-2 border-blue-500 focus:outline-none"
            />
          ) : (
            <h1 className="text-3xl font-bold text-gray-800">{dashboardName}</h1>
          )}
        </div>

        <div className="flex items-center space-x-3">
          {isEditMode ? (
            <>
              <button
                onClick={() => addWidget('metric')}
                className="bg-blue-100 text-blue-700 px-4 py-2 rounded-lg font-medium hover:bg-blue-200 transition-colors"
              >
                Add Metric
              </button>
              <button
                onClick={() => addWidget('chart')}
                className="bg-green-100 text-green-700 px-4 py-2 rounded-lg font-medium hover:bg-green-200 transition-colors"
              >
                Add Chart
              </button>
              <button
                onClick={() => addWidget('table')}
                className="bg-purple-100 text-purple-700 px-4 py-2 rounded-lg font-medium hover:bg-purple-200 transition-colors"
              >
                Add Table
              </button>
              <button
                onClick={saveDashboard}
                className="bg-green-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-green-700 transition-colors flex items-center space-x-2"
              >
                <Save className="w-4 h-4" />
                <span>Save</span>
              </button>
            </>
          ) : (
            <button
              onClick={() => setIsEditMode(true)}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors flex items-center space-x-2"
            >
              <Settings className="w-4 h-4" />
              <span>Customize</span>
            </button>
          )}
        </div>
      </div>

      {/* Dashboard Grid */}
      <div className="grid grid-cols-3 gap-6">
        {widgets.map(renderWidget)}
      </div>

      {/* Widget Configuration Modal */}
      {selectedWidget && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-2xl p-6 max-w-md w-full mx-4"
          >
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-gray-800">Configure Widget</h3>
              <button
                onClick={() => setSelectedWidget(null)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {(() => {
              const widget = widgets.find(w => w.id === selectedWidget);
              if (!widget) return null;

              return (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Title</label>
                    <input
                      type="text"
                      value={widget.title}
                      onChange={(e) => updateWidget(widget.id, { title: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Size</label>
                    <select
                      value={widget.size}
                      onChange={(e) => updateWidget(widget.id, { size: e.target.value as DashboardWidget['size'] })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="small">Small</option>
                      <option value="medium">Medium</option>
                      <option value="large">Large</option>
                    </select>
                  </div>

                  <div className="flex justify-end space-x-3 pt-4">
                    <button
                      onClick={() => setSelectedWidget(null)}
                      className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => setSelectedWidget(null)}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      Apply
                    </button>
                  </div>
                </div>
              );
            })()}
          </motion.div>
        </div>
      )}
    </div>
  );
};

export default CustomDashboard;

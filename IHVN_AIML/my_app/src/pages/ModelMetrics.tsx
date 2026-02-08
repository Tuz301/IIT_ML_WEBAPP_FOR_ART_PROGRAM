// src/pages/ModelMetrics.tsx - COMPLETELY REDESIGNED
import { motion } from 'framer-motion';
import { 
  TrendingUp, 
  Target,
  Zap,
  Activity,
  Eye,
  Shield,
  Database,
  Calendar,
  RefreshCw
} from 'lucide-react';

export const ModelMetrics = () => {
  const metrics = [
    { 
      name: 'AUC Score', 
      value: '85.0%', 
      description: 'Area Under Curve',
      icon: TrendingUp,
      color: 'from-blue-500 to-cyan-500'
    },
    { 
      name: 'Precision', 
      value: '78.0%', 
      description: 'Positive Predictive Value',
      icon: Target,
      color: 'from-green-500 to-emerald-500'
    },
    { 
      name: 'Recall', 
      value: '82.0%', 
      description: 'Sensitivity',
      icon: Zap,
      color: 'from-purple-500 to-pink-500'
    },
    { 
      name: 'F1 Score', 
      value: '80.0%', 
      description: 'Balance Score',
      icon: Activity,
      color: 'from-orange-500 to-amber-500'
    },
    { 
      name: 'Sensitivity', 
      value: '82.0%', 
      description: 'True Positive Rate',
      icon: Eye,
      color: 'from-indigo-500 to-blue-500'
    },
    { 
      name: 'Specificity', 
      value: '88.0%', 
      description: 'True Negative Rate',
      icon: Shield,
      color: 'from-red-500 to-pink-500'
    },
  ];

  const confusionMatrix = {
    trueNegative: 894,
    falsePositive: 67,
    falseNegative: 53,
    truePositive: 233,
  };

  const modelInfo = [
    { label: 'Model Version', value: 'v2.1.0 - Treatment Interruption Predictor', icon: Database },
    { label: 'Training Date', value: 'October 15, 2024', icon: Calendar },
    { label: 'Algorithm', value: 'XGBoost Classifier', icon: Activity },
    { label: 'Training Dataset', value: '12,345 patient records', icon: Database },
    { label: 'Last Updated', value: '3 days ago', icon: RefreshCw },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center space-y-4"
      >
        <h1 className="text-4xl font-bold text-gray-800 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          Model Performance Metrics
        </h1>
        <p className="text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed">
          Real-time insights into the ML model's prediction accuracy
        </p>
      </motion.div>

      {/* Metrics Grid */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-2 lg:grid-cols-3 gap-6"
      >
        {metrics.map((metric, index) => {
          const Icon = metric.icon;
          return (
            <motion.div
              key={metric.name}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 + index * 0.1 }}
              className="bg-white rounded-2xl p-6 shadow-xl border border-gray-100 hover:shadow-2xl transition-all duration-300 group cursor-pointer"
            >
              <div className="flex items-start justify-between mb-4">
                <div className={`w-12 h-12 bg-gradient-to-br ${metric.color} rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-gray-800">{metric.value}</div>
                  <div className="text-xs text-gray-500 mt-1">{metric.description}</div>
                </div>
              </div>
              <h3 className="text-lg font-semibold text-gray-800">{metric.name}</h3>
            </motion.div>
          );
        })}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Confusion Matrix */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-2xl shadow-xl border border-gray-100 p-6"
        >
          <h2 className="text-2xl font-semibold text-gray-800 mb-6">Confusion Matrix</h2>
          
          <div className="overflow-hidden rounded-xl border border-gray-200">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-4 text-left text-sm font-semibold text-gray-700 uppercase">
                    Actual \ Predicted
                  </th>
                  <th scope="col" className="px-6 py-4 text-center text-sm font-semibold text-gray-700 uppercase">
                    Negative
                  </th>
                  <th scope="col" className="px-6 py-4 text-center text-sm font-semibold text-gray-700 uppercase">
                    Positive
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                <tr>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900 bg-red-50">
                    Actual Negative
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center bg-green-50 border-r border-gray-200">
                    <div className="text-2xl font-bold text-green-700">{confusionMatrix.trueNegative}</div>
                    <div className="text-sm text-green-600 font-medium">True Negative</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center bg-red-50">
                    <div className="text-2xl font-bold text-red-700">{confusionMatrix.falsePositive}</div>
                    <div className="text-sm text-red-600 font-medium">False Positive</div>
                  </td>
                </tr>
                <tr>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900 bg-green-50">
                    Actual Positive
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center bg-red-50 border-r border-gray-200">
                    <div className="text-2xl font-bold text-red-700">{confusionMatrix.falseNegative}</div>
                    <div className="text-sm text-red-600 font-medium">False Negative</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center bg-green-50">
                    <div className="text-2xl font-bold text-green-700">{confusionMatrix.truePositive}</div>
                    <div className="text-sm text-green-600 font-medium">True Positive</div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Matrix Explanation */}
          <div className="mt-6 p-4 bg-blue-50 rounded-xl border border-blue-200">
            <h4 className="font-semibold text-blue-800 mb-3 text-lg">Understanding the Matrix</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span className="text-blue-700"><strong>True Negative:</strong> Correctly predicted non-risk</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <span className="text-blue-700"><strong>False Positive:</strong> Incorrectly flagged as high-risk</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <span className="text-blue-700"><strong>False Negative:</strong> Missed high-risk patients</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span className="text-blue-700"><strong>True Positive:</strong> Correctly identified high-risk</span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Model Information */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
          className="space-y-6"
        >
          <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-6">
            <h2 className="text-2xl font-semibold text-gray-800 mb-6">Model Information</h2>
            
            <div className="space-y-4">
              {modelInfo.map((info, index) => {
                const Icon = info.icon;
                return (
                  <motion.div
                    key={info.label}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 + index * 0.1 }}
                    className="flex items-center justify-between p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                        <Icon className="w-5 h-5 text-blue-600" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-600">{info.label}</div>
                        <div className="text-lg font-semibold text-gray-800">{info.value}</div>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>

          {/* Performance Chart Placeholder */}
          <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-6">
            <h3 className="text-xl font-semibold text-gray-800 mb-4">Performance Trends</h3>
            <div className="h-48 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl flex items-center justify-center border-2 border-dashed border-gray-300">
              <div className="text-center">
                <Activity className="w-12 h-12 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-500 font-medium">Performance chart visualization</p>
                <p className="text-sm text-gray-400">AUC, Precision, Recall over time</p>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Additional Metrics */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-6"
      >
        <div className="bg-gradient-to-br from-blue-500 to-cyan-500 text-white rounded-2xl p-6 text-center shadow-lg">
          <div className="text-3xl font-bold mb-2">94.2%</div>
          <div className="text-blue-100 font-medium">Overall Accuracy</div>
        </div>
        <div className="bg-gradient-to-br from-green-500 to-emerald-500 text-white rounded-2xl p-6 text-center shadow-lg">
          <div className="text-3xl font-bold mb-2">12.3K</div>
          <div className="text-green-100 font-medium">Total Predictions</div>
        </div>
        <div className="bg-gradient-to-br from-purple-500 to-pink-500 text-white rounded-2xl p-6 text-center shadow-lg">
          <div className="text-3xl font-bold mb-2">99.1%</div>
          <div className="text-purple-100 font-medium">Uptime</div>
        </div>
      </motion.div>
    </div>
  );
};

export default ModelMetrics;
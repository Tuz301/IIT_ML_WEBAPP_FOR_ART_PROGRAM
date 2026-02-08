// src/pages/Dashboard.tsx - VIBRANT REDESIGN WITH REAL API INTEGRATION
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { useState, useEffect } from 'react';
import {
  TrendingUp,
  Users,
  AlertTriangle,
  BarChart3,
  Clock,
  User,
  ArrowRight,
  Download,
  Activity,
  Heart
} from 'lucide-react';
import { toast } from 'react-toastify';
import StatCard from '../components/StatCard';
import { useApi } from '../contexts/ApiContext';

interface DashboardStats {
  totalPredictions: number;
  highRiskPatients: number;
  anyRiskCases: number;
  predictionsToday: number;
}

interface RecentPrediction {
  id: string;
  time: string;
  risk: string;
}

interface RiskDistribution {
  level: string;
  patients: number;
  percentage: number;
  color: string;
}

export const Dashboard = () => {
  const { getPredictionAnalytics, getRiskDistribution, getPredictions } = useApi();
  const [stats, setStats] = useState<DashboardStats>({
    totalPredictions: 0,
    highRiskPatients: 0,
    anyRiskCases: 0,
    predictionsToday: 0
  });
  const [recentPredictions, setRecentPredictions] = useState<RecentPrediction[]>([]);
  const [riskDistribution, setRiskDistribution] = useState<RiskDistribution[]>([]);

  // Fetch dashboard data on component mount
  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      // Fetch analytics data
      const analyticsResponse = await getPredictionAnalytics(30);
      if (analyticsResponse.data) {
        // Process analytics data to extract stats
        const analytics = analyticsResponse.data;
        setStats({
          totalPredictions: analytics.total_predictions || 0,
          highRiskPatients: analytics.high_risk_count || 0,
          anyRiskCases: analytics.medium_risk_count || 0,
          predictionsToday: analytics.predictions_today || 0
        });
      }

      // Fetch risk distribution
      const riskResponse = await getRiskDistribution();
      if (riskResponse.data) {
        const riskData = riskResponse.data;
        setRiskDistribution([
          { level: 'Low Risk', patients: riskData.low_risk || 0, percentage: riskData.low_risk_percentage || 0, color: 'from-green-400 to-emerald-500' },
          { level: 'Medium Risk', patients: riskData.medium_risk || 0, percentage: riskData.medium_risk_percentage || 0, color: 'from-yellow-400 to-amber-500' },
          { level: 'High Risk', patients: riskData.high_risk || 0, percentage: riskData.high_risk_percentage || 0, color: 'from-orange-400 to-red-500' },
          { level: 'Critical Risk', patients: riskData.critical_risk || 0, percentage: riskData.critical_risk_percentage || 0, color: 'from-red-500 to-pink-600' }
        ]);
      }

      // Fetch recent predictions
      const predictionsResponse = await getPredictions();
      if (predictionsResponse.data?.predictions) {
        const recent = predictionsResponse.data.predictions.slice(0, 4).map((pred: any) => ({
          id: `P-${pred.id}`,
          time: formatTimeAgo(new Date(pred.prediction_timestamp)),
          risk: pred.risk_level.charAt(0).toUpperCase() + pred.risk_level.slice(1)
        }));
        setRecentPredictions(recent);
      }

    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      toast.error('Failed to load dashboard data');
      // Set fallback data
      setStats({
        totalPredictions: 0,
        highRiskPatients: 0,
        anyRiskCases: 0,
        predictionsToday: 0
      });
      setRiskDistribution([
        { level: 'Low Risk', patients: 0, percentage: 0, color: 'from-green-400 to-emerald-500' },
        { level: 'Medium Risk', patients: 0, percentage: 0, color: 'from-yellow-400 to-amber-500' },
        { level: 'High Risk', patients: 0, percentage: 0, color: 'from-orange-400 to-red-500' },
        { level: 'Critical Risk', patients: 0, percentage: 0, color: 'from-red-500 to-pink-600' }
      ]);
      setRecentPredictions([]);
    }
  };

  const formatTimeAgo = (date: Date): string => {
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));

    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes} min ago`;

    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`;

    const diffInDays = Math.floor(diffInHours / 24);
    return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`;
  };



  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center space-y-4"
      >
        <h1 className="text-4xl font-bold text-gray-800 bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
          Predict Patient Treatment Risk
        </h1>
        <p className="text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed">
          Use machine learning to identify patients at risk of treatment interruption. 
          Early intervention saves lives and improves retention rates.
        </p>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column - Main Action & Stats */}
        <div className="lg:col-span-2 space-y-6">
          {/* Main Action Card */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-gradient-to-br from-purple-500 via-pink-500 to-red-500 rounded-3xl p-8 text-white shadow-2xl relative overflow-hidden"
          >
            {/* Background Pattern */}
            <div className="absolute inset-0 opacity-10">
              <div className="absolute top-0 right-0 w-32 h-32 bg-white rounded-full -mt-16 -mr-16"></div>
              <div className="absolute bottom-0 left-0 w-24 h-24 bg-white rounded-full -mb-12 -ml-12"></div>
            </div>

            <div className="relative z-10">
              <div className="flex items-start justify-between mb-6">
                <div className="flex-1">
                  <h2 className="text-2xl font-bold mb-3">Start New Assessment</h2>
                  <p className="text-purple-100 text-lg leading-relaxed">
                    Begin a new risk prediction analysis for patient treatment adherence monitoring.
                  </p>
                </div>
                <div className="w-16 h-16 bg-white/20 rounded-2xl flex items-center justify-center ml-6">
                  <Activity className="w-8 h-8 text-white" />
                </div>
              </div>
              
              <Link
                to="/predict"
                className="inline-flex items-center justify-between bg-white text-purple-600 px-6 py-4 rounded-xl font-bold hover:bg-purple-50 transition-all group shadow-lg border-2 border-white/30"
              >
                <span className="text-lg">Start New Prediction</span>
                <ArrowRight className="w-5 h-5 transform group-hover:translate-x-1 transition-transform" />
              </Link>
            </div>
          </motion.div>

          {/* Stats Grid */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="grid grid-cols-2 gap-6"
          >
            <StatCard
              icon={BarChart3}
              label="Total Predictions"
              value={stats.totalPredictions}
              trend="+12%"
              trendUp={true}
              color="blue"
            />
            <StatCard
              icon={AlertTriangle}
              label="High Risk Patients"
              value={stats.highRiskPatients}
              trend="+8%"
              trendUp={false}
              color="red"
            />
            <StatCard
              icon={Activity}
              label="Any Risk Cases"
              value={`${stats.anyRiskCases}%`}
              trend="+5%"
              trendUp={true}
              color="amber"
            />
            <StatCard
              icon={Users}
              label="Predictions Today"
              value={stats.predictionsToday}
              trend="+15%"
              trendUp={true}
              color="green"
            />
          </motion.div>
        </div>

        {/* Right Column - Risk Distribution & Recent Activity */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
          className="space-y-6"
        >
          {/* Risk Distribution */}
          <div className="bg-white rounded-2xl p-6 shadow-xl border border-gray-100">
            <div className="flex items-center mb-6">
              <div className="w-10 h-10 bg-gradient-to-br from-orange-400 to-red-500 rounded-xl flex items-center justify-center mr-3">
                <AlertTriangle className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800">Risk Distribution</h3>
            </div>

            <div className="space-y-4">
              {riskDistribution.map((risk, index) => (
                <motion.div
                  key={risk.level}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.4 + index * 0.1 }}
                  className="flex items-center justify-between p-3 bg-gradient-to-r from-gray-50 to-white rounded-xl border border-gray-200 hover:shadow-md transition-all"
                >
                  <div className="flex items-center space-x-3">
                    <div className={`w-3 h-3 rounded-full bg-gradient-to-r ${
                      risk.level.toLowerCase().includes('low') ? 'from-green-400 to-emerald-500' :
                      risk.level.toLowerCase().includes('medium') ? 'from-yellow-400 to-amber-500' :
                      risk.level.toLowerCase().includes('high') ? 'from-orange-400 to-red-500' :
                      'from-red-500 to-pink-600'
                    }`}></div>
                    <span className="font-medium text-gray-700">{risk.level}</span>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-gray-800">{risk.patients} patients</div>
                    <div className="text-sm text-gray-500">{risk.percentage}%</div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Recent Predictions */}
          <div className="bg-white rounded-2xl p-6 shadow-xl border border-gray-100">
            <div className="flex items-center mb-6">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-cyan-500 rounded-xl flex items-center justify-center mr-3">
                <Clock className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800">Recent Predictions</h3>
            </div>

            <div className="space-y-3">
              {recentPredictions.map((prediction, index) => (
                <motion.div
                  key={prediction.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 + index * 0.1 }}
                  className="flex items-center justify-between p-3 hover:bg-gradient-to-r from-blue-50 to-cyan-50 rounded-xl transition-all group cursor-pointer"
                >
                  <div className="flex items-center space-x-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      prediction.risk === 'High' ? 'bg-red-100 text-red-600' :
                      prediction.risk === 'Medium' ? 'bg-yellow-100 text-yellow-600' :
                      'bg-green-100 text-green-600'
                    }`}>
                      <User className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="font-semibold text-gray-800">{prediction.id}</div>
                      <div className="text-sm text-gray-500 flex items-center">
                        <Clock className="w-3 h-3 mr-1" />
                        {prediction.time}
                      </div>
                    </div>
                  </div>
                  <div className={`px-2 py-1 rounded-full text-xs font-bold ${
                    prediction.risk === 'High' ? 'bg-red-500 text-white' :
                    prediction.risk === 'Medium' ? 'bg-yellow-500 text-white' :
                    'bg-green-500 text-white'
                  }`}>
                    {prediction.risk}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>

      {/* Bottom Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Patient Statistics */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl p-6 text-white shadow-2xl"
        >
          <div className="flex items-center mb-6">
            <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center mr-3">
              <Users className="w-5 h-5 text-white" />
            </div>
            <h3 className="text-xl font-bold">Patient Statistics</h3>
          </div>

          <div className="space-y-4">
            {[
              { patients: 202, percentage: 48, label: 'Low Risk Engagement' },
              { patients: 249, percentage: 26, label: 'Medium Risk Monitoring' },
              { patients: 212, percentage: 19, label: 'High Risk Intervention' },
              { patients: 83, percentage: 7, label: 'Critical Risk Priority' }
            ].map((stat, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-white/10 rounded-xl backdrop-blur-sm">
                <div>
                  <div className="font-semibold">{stat.patients} patients</div>
                  <div className="text-indigo-100 text-sm">{stat.label}</div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold">{stat.percentage}%</div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Insights & Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="space-y-6"
        >
          {/* Insights Card */}
          <div className="bg-gradient-to-br from-green-400 to-emerald-500 rounded-2xl p-6 text-white shadow-2xl">
            <div className="flex items-center mb-4">
              <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center mr-3">
                <Heart className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-xl font-bold">Clinical Insights</h3>
            </div>
            <p className="text-green-50 leading-relaxed">
              <strong>70% of patients</strong> are in low to medium risk categories. 
              Focus retention efforts on the <strong>≥15% high-risk population</strong> for maximum impact.
            </p>
            <div className="mt-4 flex items-center space-x-2 text-green-100">
              <TrendingUp className="w-4 h-4" />
              <span className="text-sm font-medium">Recommendation: Prioritize high-risk patient follow-ups</span>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white rounded-2xl p-6 shadow-xl border border-gray-100">
            <h3 className="text-xl font-bold text-gray-800 mb-4">Quick Actions</h3>
            <div className="grid grid-cols-2 gap-3">
              <button className="bg-gradient-to-r from-blue-500 to-cyan-500 text-white py-3 rounded-xl font-semibold hover:from-blue-600 hover:to-cyan-600 transition-all flex items-center justify-center space-x-2">
                <Download className="w-4 h-4" />
                <span>Export Data</span>
              </button>
              <Link
                to="/metrics"
                className="bg-gradient-to-r from-purple-500 to-pink-500 text-white py-3 rounded-xl font-semibold hover:from-purple-600 hover:to-pink-600 transition-all flex items-center justify-center space-x-2"
              >
                <BarChart3 className="w-4 h-4" />
                <span>View Metrics</span>
              </Link>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Dashboard;
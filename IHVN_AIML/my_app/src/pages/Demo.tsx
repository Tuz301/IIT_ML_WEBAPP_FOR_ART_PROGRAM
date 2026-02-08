import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  Home,
  BarChart3,
  Stethoscope,
  Shield,
  Users,
  FileText,
  Activity,
  CheckCircle,
  ArrowRight,
  ExternalLink,
  Moon,
  Sun
} from 'lucide-react';

const Demo = () => {
  const [darkMode, setDarkMode] = useState(false);
  const [activeSection, setActiveSection] = useState<string>('overview');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  const sections = [
    {
      id: 'overview',
      title: 'Overview',
      icon: Home,
      description: 'Introduction to IIT ML Predictor application'
    },
    {
      id: 'dashboard',
      title: 'Dashboard',
      icon: BarChart3,
      description: 'View statistics, risk distribution, and recent predictions',
      route: '/'
    },
    {
      id: 'prediction',
      title: 'Risk Prediction',
      icon: Stethoscope,
      description: 'Generate ML-based treatment interruption risk predictions',
      route: '/predict'
    },
    {
      id: 'patients',
      title: 'Patient Management',
      icon: Users,
      description: 'Search, view, create, and manage patient records',
      route: '/patients'
    },
    {
      id: 'metrics',
      title: 'Model Metrics',
      icon: Activity,
      description: 'View ML model performance metrics and confusion matrix',
      route: '/metrics'
    },
    {
      id: 'field-ops',
      title: 'Field Operations',
      icon: ExternalLink,
      description: 'GPS tracking, voice notes, barcode scanner, photo capture',
      route: '/field-ops'
    },
    {
      id: 'reports',
      title: 'Reports & Analytics',
      icon: FileText,
      description: 'Generate reports, schedule automated reports, custom dashboards',
      route: '/reports'
    }
  ];

  const features = [
    {
      category: 'Authentication',
      items: [
        'User login with JWT token authentication',
        'Session timeout after 30 minutes of inactivity',
        'Protected routes with role-based access',
        'Token refresh mechanism',
        'Demo credentials: admin / admin123'
      ]
    },
    {
      category: 'Dashboard',
      items: [
        'Real-time statistics cards with animated counters',
        'Risk distribution visualization',
        'Recent predictions timeline',
        'Patient statistics breakdown',
        'Quick action buttons'
      ]
    },
    {
      category: 'Risk Prediction',
      items: [
        'Step-by-step prediction wizard',
        'Patient search with filtering',
        'Feature input validation',
        'ML model-based risk scoring',
        'Confidence percentage display',
        'Risk-specific recommendations'
      ]
    },
    {
      category: 'Patient Management',
      items: [
        'Patient list with pagination',
        'Search by name, ID, or phone',
        'Filter by gender, state, age range',
        'Create new patient records',
        'View patient details',
        'Edit patient information',
        'Delete patient records'
      ]
    },
    {
      category: 'Field Operations',
      items: [
        'GPS location tracking with accuracy',
        'Continuous location monitoring',
        'Open in Google Maps integration',
        'Voice-to-text notes using Web Speech API',
        'Barcode/QR code scanner',
        'Photo/document capture with webcam',
        'Emergency contact protocols'
      ]
    },
    {
      category: 'Reports & Analytics',
      items: [
        'PDF, Excel, CSV export formats',
        'Date range filtering',
        'Risk level filters',
        'Department filters',
        'Age range filters',
        'Scheduled report automation',
        'Custom dashboard builder'
      ]
    },
    {
      category: 'UI/UX Features',
      items: [
        'Dark/Light theme toggle',
        'Smooth animations with Framer Motion',
        'Responsive design for all devices',
        'Gradient backgrounds and cards',
        'Glass morphism effects',
        'Loading spinners and progress indicators',
        'Toast notifications',
        'Error boundary with retry mechanism'
      ]
    }
  ];

  const technologies = [
    { name: 'React', version: '18.3.1', description: 'UI library' },
    { name: 'TypeScript', version: '5.8.3', description: 'Type safety' },
    { name: 'Tailwind CSS', version: '3.4.17', description: 'Styling' },
    { name: 'Framer Motion', version: '11.18.2', description: 'Animations' },
    { name: 'Lucide React', version: '0.533.0', description: 'Icons' },
    { name: 'Recharts', version: '3.5.1', description: 'Charts' },
    { name: 'React Router', version: '6.30.1', description: 'Routing' },
    { name: 'Zod', version: '3.25.76', description: 'Validation' },
    { name: 'React Toastify', version: '11.0.5', description: 'Notifications' },
    { name: 'Zustand', version: '4.4.7', description: 'State management' }
  ];

  const renderOverview = () => (
    <div className="space-y-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl p-8 text-white shadow-2xl"
      >
        <h1 className="text-4xl font-bold mb-4">IIT ML Predictor Demo</h1>
        <p className="text-xl text-blue-100 mb-6">
          A comprehensive healthcare application for predicting patient treatment interruption risk using machine learning.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white/20 backdrop-blur-sm rounded-xl p-4">
            <div className="text-3xl font-bold">7+</div>
            <div className="text-sm text-blue-100">Core Pages</div>
          </div>
          <div className="bg-white/20 backdrop-blur-sm rounded-xl p-4">
            <div className="text-3xl font-bold">15+</div>
            <div className="text-sm text-blue-100">Components</div>
          </div>
          <div className="bg-white/20 backdrop-blur-sm rounded-xl p-4">
            <div className="text-3xl font-bold">10+</div>
            <div className="text-sm text-blue-100">Technologies</div>
          </div>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-white rounded-2xl shadow-xl p-6 border border-gray-100"
      >
        <h2 className="text-2xl font-bold text-gray-800 mb-4">Quick Start</h2>
        <div className="space-y-4">
          <div className="flex items-start space-x-4 p-4 bg-blue-50 rounded-xl">
            <div className="w-8 h-8 bg-blue-600 text-white rounded-lg flex items-center justify-center font-bold flex-shrink-0">1</div>
            <div>
              <h3 className="font-semibold text-gray-800">Login to Application</h3>
              <p className="text-gray-600 text-sm">Use demo credentials: <span className="font-mono bg-blue-100 px-2 py-1 rounded">admin / admin123</span></p>
            </div>
          </div>
          <div className="flex items-start space-x-4 p-4 bg-green-50 rounded-xl">
            <div className="w-8 h-8 bg-green-600 text-white rounded-lg flex items-center justify-center font-bold flex-shrink-0">2</div>
            <div>
              <h3 className="font-semibold text-gray-800">Explore the Dashboard</h3>
              <p className="text-gray-600 text-sm">View statistics, risk distribution, and recent predictions</p>
            </div>
          </div>
          <div className="flex items-start space-x-4 p-4 bg-purple-50 rounded-xl">
            <div className="w-8 h-8 bg-purple-600 text-white rounded-lg flex items-center justify-center font-bold flex-shrink-0">3</div>
            <div>
              <h3 className="font-semibold text-gray-800">Try Risk Prediction</h3>
              <p className="text-gray-600 text-sm">Select a patient and generate ML-based risk predictions</p>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );

  const renderFeatures = () => (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">Application Features</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {features.map((feature, index) => (
          <motion.div
            key={feature.category}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="bg-white rounded-2xl shadow-lg p-6 border border-gray-100"
          >
            <h3 className="text-lg font-bold text-gray-800 mb-4 pb-2 border-b">
              {feature.category}
            </h3>
            <ul className="space-y-2">
              {feature.items.map((item, i) => (
                <li key={i} className="flex items-start space-x-2 text-sm text-gray-700">
                  <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </motion.div>
        ))}
      </div>
    </div>
  );

  const renderTechnologies = () => (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">Technology Stack</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {technologies.map((tech, index) => (
          <motion.div
            key={tech.name}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.05 }}
            className="bg-white rounded-xl shadow-lg p-4 border border-gray-100 hover:shadow-xl transition-shadow"
          >
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-bold text-gray-800">{tech.name}</h3>
              <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">{tech.version}</span>
            </div>
            <p className="text-sm text-gray-600">{tech.description}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );

  const renderNavigation = () => (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">Application Navigation</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sections.filter(s => s.route).map((section, index) => (
          <motion.div
            key={section.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            whileHover={{ scale: 1.02 }}
            className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden"
          >
            <Link
              to={section.route!}
              className="block p-6 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-start space-x-4">
                <div className={`w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center flex-shrink-0`}>
                  <section.icon className="w-6 h-6 text-white" />
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-gray-800 mb-1">{section.title}</h3>
                  <p className="text-sm text-gray-600">{section.description}</p>
                </div>
                <ArrowRight className="w-5 h-5 text-gray-400" />
              </div>
            </Link>
          </motion.div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-slate-900 dark:to-gray-800">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-gray-200/60 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                <Shield className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  IIT Predictor Demo
                </h1>
                <p className="text-xs text-gray-500">Interactive Feature Showcase</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setDarkMode(!darkMode)}
                className="p-2 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
              >
                {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </button>
              <Link
                to="/login"
                className="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl font-semibold hover:from-blue-700 hover:to-purple-700 transition-all flex items-center space-x-2"
              >
                <span>Go to App</span>
                <ExternalLink className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Section Tabs */}
        <div className="flex flex-wrap gap-2 mb-8">
          {sections.map((section) => {
            const Icon = section.icon;
            return (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-xl font-medium transition-all ${
                  activeSection === section.id
                    ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg'
                    : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{section.title}</span>
              </button>
            );
          })}
        </div>

        {/* Section Content */}
        <motion.div
          key={activeSection}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white/50 backdrop-blur-sm rounded-2xl p-8"
        >
          {activeSection === 'overview' && renderOverview()}
          {activeSection === 'features' && renderFeatures()}
          {activeSection === 'technologies' && renderTechnologies()}
          {activeSection === 'navigation' && renderNavigation()}
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="bg-white/80 backdrop-blur-md border-t border-gray-200/60 mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
            <div className="text-sm text-gray-600">
              <strong>IIT ML Predictor</strong> - Treatment Interruption Risk Assessment System
            </div>
            <div className="text-sm text-gray-500">
              Built with React, TypeScript, and Tailwind CSS
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Demo;

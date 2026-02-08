// src/components/Navigation.tsx - UPDATED
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Home,
  BarChart3,
  Stethoscope,
  Shield,
  Users,
  FileText,
  LogOut,
  User,
  Activity
} from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import { useAuth } from '../contexts/AuthContext';

export const Navigation = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: Home },
    { path: '/predict', label: 'New Prediction', icon: Stethoscope },
    { path: '/metrics', label: 'Model Metrics', icon: BarChart3 },
    { path: '/patients', label: 'Patients', icon: Users },
    { path: '/field-ops', label: 'Field Ops', icon: Activity },
    { path: '/reports', label: 'Reports', icon: FileText },
  ];

  return (
    <nav className="bg-white/80 backdrop-blur-md border-b border-gray-200/60 sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg group-hover:shadow-xl transition-shadow">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                IIT Predictor
              </h1>
              <p className="text-xs text-gray-500">Treatment Risk Assessment</p>
            </div>
          </Link>

          {/* Navigation Links */}
          <div className="flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = item.path === '/patients'
                ? location.pathname.startsWith('/patients')
                : location.pathname === item.path;
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`relative px-4 py-2 rounded-xl font-medium transition-all duration-200 ${
                    isActive
                      ? 'text-blue-600 bg-blue-50'
                      : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                  }`}
                >
                  {isActive && (
                    <motion.div
                      layoutId="activeNav"
                      className="absolute inset-0 bg-blue-50 rounded-xl border border-blue-200"
                      transition={{ type: "spring", stiffness: 300, damping: 30 }}
                    />
                  )}
                  <div className="relative z-10 flex items-center space-x-2">
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </div>
                </Link>
              );
            })}
          </div>

          {/* User Menu */}
          <div className="flex items-center space-x-3">
            <Link
              to="/profile"
              className="flex items-center space-x-2 px-3 py-2 rounded-xl text-gray-600 hover:text-blue-600 hover:bg-gray-50 transition-colors"
            >
              <User className="w-4 h-4" />
              <span className="hidden sm:inline">{user?.username || 'Profile'}</span>
            </Link>

            <button
              onClick={() => {
                logout();
                navigate('/login');
              }}
              className="flex items-center space-x-2 px-3 py-2 rounded-xl text-gray-600 hover:text-red-600 hover:bg-gray-50 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">Logout</span>
            </button>

            <ThemeToggle />
          </div>
        </div>
      </div>
    </nav>
  );
};

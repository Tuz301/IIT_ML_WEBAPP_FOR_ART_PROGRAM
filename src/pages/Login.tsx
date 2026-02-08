import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  User,
  Lock,
  Eye,
  EyeOff,
  Loader,
  AlertCircle,
  Shield,
  Activity,
  HeartPulse,
  Dna,
  Microscope,
  Pill,
  Heart
} from 'lucide-react';
import { toast } from 'react-toastify';
import { useAuth } from '../contexts/AuthContext';

// Animated background particles
const FloatingParticle = ({ delay, x, y, duration, size }: { delay: number; x: string; y: string; duration: number; size: number }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0 }}
    animate={{ opacity: [0.1, 0.3, 0.1], scale: [0, 1, 0] }}
    transition={{
      duration,
      delay,
      repeat: Infinity,
      repeatType: "loop"
    }}
    style={{
      position: 'absolute',
      left: x,
      top: y,
      width: size,
      height: size
    }}
    className="rounded-full bg-gradient-to-br from-blue-400/20 to-purple-400/20 blur-xl"
  />
);

// Animated DNA helix
const DNAHelix = () => (
  <motion.div
    initial={{ opacity: 0, rotate: -180 }}
    animate={{ opacity: 0.15, rotate: 0 }}
    transition={{ duration: 2, ease: "easeOut" }}
    className="absolute top-20 left-10"
  >
    <Dna className="w-24 h-24 text-blue-500/30" />
  </motion.div>
);

// Animated heartbeat
const Heartbeat = () => (
  <motion.div
    className="absolute bottom-32 right-16"
    animate={{
      scale: [1, 1.1, 1],
      opacity: [0.2, 0.4, 0.2]
    }}
    transition={{
      duration: 1.5,
      repeat: Infinity,
      repeatType: "loop"
    }}
  >
    <HeartPulse className="w-20 h-20 text-red-500/30" />
  </motion.div>
);

// Animated microscope
const MicroscopeIcon = () => (
  <motion.div
    initial={{ opacity: 0, x: 50 }}
    animate={{ opacity: 0.2, x: 0 }}
    transition={{ duration: 2, delay: 0.5 }}
    className="absolute bottom-20 left-20"
  >
    <Microscope className="w-16 h-16 text-purple-500/30" />
  </motion.div>
);

// Animated pills
const FloatingPills = () => (
  <>
    <motion.div
      animate={{
        y: [0, -20, 0],
        rotate: [0, 360, 0]
      }}
      transition={{
        duration: 6,
        repeat: Infinity,
        repeatType: "loop"
      }}
      className="absolute top-1/4 right-1/4"
    >
      <Pill className="w-12 h-12 text-green-500/30" />
    </motion.div>
    <motion.div
      animate={{
        y: [0, 20, 0],
        rotate: [0, -360, 0]
      }}
      transition={{
        duration: 8,
        repeat: Infinity,
        repeatType: "loop",
        delay: 1
      }}
      className="absolute bottom-1/3 left-1/4"
    >
      <Pill className="w-10 h-10 text-blue-500/30" />
    </motion.div>
  </>
);

// Animated activity waves
const ActivityWaves = () => (
  <div className="absolute top-1/2 left-10">
    {[0, 1, 2].map((i) => (
      <motion.div
        key={i}
        className="absolute"
        initial={{ opacity: 0, scale: 0 }}
        animate={{
          opacity: [0, 0.3, 0],
          scale: [1, 1.5, 1]
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          repeatType: "loop",
          delay: i * 0.3
        }}
        style={{
          left: i * 20
        }}
      >
        <Activity className="w-6 h-6 text-cyan-500/40" />
      </motion.div>
    ))}
  </div>
);

export const Login = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isLoading } = useAuth();

  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const from = location.state?.from?.pathname || '/';

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.username.trim()) {
      newErrors.username = 'Username is required';
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsLoggingIn(true);

    try {
      const success = await login(formData.username, formData.password);

      if (success) {
        toast.success('Login successful!');
        // Add smooth transition delay
        setTimeout(() => {
          navigate(from, { replace: true });
        }, 300);
      } else {
        toast.error('Login failed');
        setIsLoggingIn(false);
      }
    } catch (error) {
      toast.error('An unexpected error occurred');
      setIsLoggingIn(false);
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Gradient Orbs */}
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.3, 0.5, 0.3]
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            repeatType: "loop"
          }}
          className="absolute top-1/4 -left-20 w-96 h-96 bg-blue-500/30 rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            scale: [1, 1.3, 1],
            opacity: [0.2, 0.4, 0.2]
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            repeatType: "loop",
            delay: 2
          }}
          className="absolute bottom-1/4 -right-20 w-96 h-96 bg-purple-500/30 rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            scale: [1, 1.1, 1],
            opacity: [0.2, 0.3, 0.2]
          }}
          transition={{
            duration: 6,
            repeat: Infinity,
            repeatType: "loop",
            delay: 4
          }}
          className="absolute top-1/2 left-1/2 w-80 h-80 bg-cyan-500/20 rounded-full blur-3xl"
        />

        {/* Floating Particles */}
        <FloatingParticle delay={0} x="10%" y="20%" duration={8} size={8} />
        <FloatingParticle delay={1} x="80%" y="30%" duration={10} size={12} />
        <FloatingParticle delay={2} x="30%" y="70%" duration={12} size={6} />
        <FloatingParticle delay={3} x="70%" y="80%" duration={9} size={10} />
        <FloatingParticle delay={4} x="50%" y="40%" duration={11} size={7} />
        <FloatingParticle delay={5} x="20%" y="50%" duration={7} size={9} />
        <FloatingParticle delay={6} x="90%" y="60%" duration={13} size={8} />
        <FloatingParticle delay={7} x="40%" y="90%" duration={10} size={11} />

        {/* Medical Icons */}
        <DNAHelix />
        <Heartbeat />
        <MicroscopeIcon />
        <FloatingPills />
        <ActivityWaves />

        {/* Grid Pattern */}
        <div 
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `
              linear-gradient(rgba(59, 130, 246, 0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(59, 130, 246, 0.1) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px'
          }}
        />
      </div>

      {/* Main Content */}
      <AnimatePresence mode="wait">
        {!isLoggingIn ? (
          <motion.div
            key="login"
            initial={{ opacity: 0, scale: 0.95, rotateX: -5 }}
            animate={{ opacity: 1, scale: 1, rotateX: 0 }}
            exit={{ 
              opacity: 0, 
              scale: 1.05, 
              rotateX: 5,
              filter: 'blur(10px)'
            }}
            transition={{ 
              duration: 0.5, 
              ease: [0.4, 0, 0.2, 1]
            }}
            className="min-h-screen flex items-center justify-center p-4 relative z-10"
          >
            <div className="w-full max-w-md">
              {/* Header */}
              <motion.div
                initial={{ opacity: 0, y: -30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, duration: 0.5 }}
                className="text-center mb-8"
              >
                <motion.div
                  initial={{ scale: 0, rotate: -180 }}
                  animate={{ scale: 1, rotate: 0 }}
                  transition={{ delay: 0.4, type: "spring", stiffness: 200 }}
                  className="w-20 h-20 bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-2xl shadow-blue-500/50"
                >
                  <Shield className="w-10 h-10 text-white" />
                </motion.div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent mb-3">
                  IIT ML Service
                </h1>
                <p className="text-gray-300 text-lg">
                  Advanced Treatment Risk Assessment Platform
                </p>
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.8 }}
                  className="flex items-center justify-center gap-2 mt-4"
                >
                  <div className="h-px w-12 bg-gradient-to-r from-transparent to-blue-400" />
                  <span className="text-xs text-blue-400 uppercase tracking-widest">Secure Access</span>
                  <div className="h-px w-12 bg-gradient-to-l from-blue-400 to-transparent" />
                </motion.div>
              </motion.div>

              {/* Login Form */}
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4, duration: 0.5 }}
                className="bg-white/10 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/20 p-8"
              >
                <form onSubmit={handleSubmit} className="space-y-6">
                  {/* Username Field */}
                  <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.5 }}
                  >
                    <label htmlFor="username" className="block text-sm font-medium text-gray-200 mb-2">
                      Username
                    </label>
                    <div className="relative">
                      <User className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
                      <input
                        id="username"
                        type="text"
                        value={formData.username}
                        onChange={(e) => handleInputChange('username', e.target.value)}
                        className={`w-full pl-10 pr-4 py-3 bg-white/5 border rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all text-white placeholder-gray-400 ${
                          errors.username ? 'border-red-400' : 'border-white/20'
                        }`}
                        placeholder="Enter your username"
                        disabled={isLoading}
                      />
                    </div>
                    {errors.username && (
                      <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex items-center mt-1 text-sm text-red-400"
                      >
                        <AlertCircle className="w-4 h-4 mr-1" />
                        {errors.username}
                      </motion.div>
                    )}
                  </motion.div>

                  {/* Password Field */}
                  <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.6 }}
                  >
                    <label htmlFor="password" className="block text-sm font-medium text-gray-200 mb-2">
                      Password
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
                      <input
                        id="password"
                        type={showPassword ? 'text' : 'password'}
                        value={formData.password}
                        onChange={(e) => handleInputChange('password', e.target.value)}
                        className={`w-full pl-10 pr-12 py-3 bg-white/5 border rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all text-white placeholder-gray-400 ${
                          errors.password ? 'border-red-400' : 'border-white/20'
                        }`}
                        placeholder="Enter your password"
                        disabled={isLoading}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-3 text-gray-400 hover:text-gray-200 transition-colors"
                        disabled={isLoading}
                      >
                        {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                      </button>
                    </div>
                    {errors.password && (
                      <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex items-center mt-1 text-sm text-red-400"
                      >
                        <AlertCircle className="w-4 h-4 mr-1" />
                        {errors.password}
                      </motion.div>
                    )}
                  </motion.div>

                  {/* Submit Button */}
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.7 }}
                  >
                    <button
                      type="submit"
                      disabled={isLoading}
                      className="w-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 text-white py-3 px-4 rounded-xl font-semibold hover:from-blue-600 hover:via-purple-600 hover:to-pink-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center shadow-lg shadow-blue-500/50 hover:shadow-xl hover:shadow-blue-500/70"
                    >
                      {isLoading ? (
                        <>
                          <Loader className="w-5 h-5 mr-2 animate-spin" />
                          Signing in...
                        </>
                      ) : (
                        <>
                          <Shield className="w-5 h-5 mr-2" />
                          Sign In
                        </>
                      )}
                    </button>
                  </motion.div>
                </form>

                {/* Demo Credentials */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.8 }}
                  className="mt-6 p-4 bg-blue-500/10 rounded-xl border border-blue-400/30"
                >
                  <h3 className="text-sm font-semibold text-blue-300 mb-2 flex items-center">
                    <Heart className="w-4 h-4 mr-2" />
                    Demo Credentials
                  </h3>
                  <div className="text-xs text-blue-200 space-y-1">
                    <div><strong>Username:</strong> admin</div>
                    <div><strong>Password:</strong> admin123</div>
                  </div>
                </motion.div>
              </motion.div>

              {/* Footer */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.9 }}
                className="text-center mt-6 text-sm text-gray-400"
              >
                <div className="flex items-center justify-center gap-2">
                  <Activity className="w-4 h-4 text-green-400" />
                  <span>IIT ML Prediction Service</span>
                  <Activity className="w-4 h-4 text-green-400" />
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  End-to-End Encryption • HIPAA Compliant
                </div>
              </motion.div>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="loading"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ 
              opacity: 0, 
              scale: 1.2,
              filter: 'blur(20px)'
            }}
            transition={{ 
              duration: 0.4
            }}
            className="min-h-screen flex items-center justify-center relative z-10"
          >
            <div className="text-center">
              <motion.div
                animate={{ 
                  scale: [1, 1.2, 1],
                  rotate: [0, 360, 0]
                }}
                transition={{ 
                  duration: 2,
                  repeat: Infinity,
                  repeatType: "loop"
                }}
                className="w-24 h-24 bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 rounded-full flex items-center justify-center mx-auto mb-6 shadow-2xl"
              >
                <Shield className="w-12 h-12 text-white" />
              </motion.div>
              <h2 className="text-2xl font-bold text-white mb-2">
                Authenticating...
              </h2>
              <p className="text-gray-300">
                Verifying your credentials
              </p>
              <motion.div
                className="mt-6"
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1.5, repeat: Infinity }}
              >
                <Loader className="w-8 h-8 text-blue-400 mx-auto" />
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Login;

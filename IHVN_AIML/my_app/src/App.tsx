import { Routes, Route, useLocation } from 'react-router-dom';
import { Suspense, lazy } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Navigation } from './components/Navigation';
import ProtectedRoute from './components/ProtectedRoute';

// Lazy load components for better performance
const Login = lazy(() => import('./pages/Login'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const ModelMetrics = lazy(() => import('./pages/ModelMetrics'));
const PredictionForm = lazy(() => import('./pages/PredictionForm'));
const PatientList = lazy(() => import('./pages/PatientList'));
const PatientDetail = lazy(() => import('./pages/PatientDetail'));
const PatientForm = lazy(() => import('./pages/PatientForm'));
const Reports = lazy(() => import('./pages/Reports'));
const Profile = lazy(() => import('./pages/Profile'));
const FieldOperations = lazy(() => import('./pages/FieldOperations'));
const Demo = lazy(() => import('./pages/Demo'));

// Loading component for Suspense fallback
const LoadingSpinner = () => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
  </div>
);

// Page transition wrapper component
const PageWrapper = ({ children }: { children: React.ReactNode }) => {
  const location = useLocation();
  
  return (
    <motion.div
      key={location.pathname}
      initial={{ opacity: 0, x: 20, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: -20, scale: 0.95 }}
      transition={{
        duration: 0.4,
        ease: [0.4, 0, 0.2, 1]
      }}
      className="w-full"
    >
      {children}
    </motion.div>
  );
};

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-slate-900 dark:to-gray-800 transition-colors duration-500">
      <Navigation />
      <main className="pt-20 pb-8 px-4 sm:px-6 lg:px-8">
        <Suspense fallback={<LoadingSpinner />}>
          <AnimatePresence mode="wait">
            <Routes>
              {/* Public routes */}
              <Route
                path="/demo"
                element={
                  <ProtectedRoute requireAuth={false}>
                    <PageWrapper>
                      <Demo />
                    </PageWrapper>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/login"
                element={
                  <ProtectedRoute requireAuth={false}>
                    <Login />
                  </ProtectedRoute>
                }
              />

              {/* Protected routes */}
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <PageWrapper>
                      <Dashboard />
                    </PageWrapper>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/metrics"
                element={
                  <ProtectedRoute>
                    <PageWrapper>
                      <ModelMetrics />
                    </PageWrapper>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/predict"
                element={
                  <ProtectedRoute>
                    <PageWrapper>
                      <PredictionForm />
                    </PageWrapper>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/patients"
                element={
                  <ProtectedRoute>
                    <PageWrapper>
                      <PatientList />
                    </PageWrapper>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/patients/new"
                element={
                  <ProtectedRoute>
                    <PageWrapper>
                      <PatientForm />
                    </PageWrapper>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/patients/:patientUuid"
                element={
                  <ProtectedRoute>
                    <PageWrapper>
                      <PatientDetail />
                    </PageWrapper>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/patients/:patientUuid/edit"
                element={
                  <ProtectedRoute>
                    <PageWrapper>
                      <PatientForm />
                    </PageWrapper>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/reports"
                element={
                  <ProtectedRoute>
                    <PageWrapper>
                      <Reports />
                    </PageWrapper>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/field-ops"
                element={
                  <ProtectedRoute>
                    <PageWrapper>
                      <FieldOperations />
                    </PageWrapper>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <PageWrapper>
                      <Profile />
                    </PageWrapper>
                  </ProtectedRoute>
                }
              />
            </Routes>
          </AnimatePresence>
        </Suspense>
      </main>
    </div>
  );
}

export default App;

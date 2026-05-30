import React from 'react';
import type { ReactNode } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import AdminDashboard from './components/admin/AdminDashboard';
import CustomerPage from './components/customer/CustomerPage';
import CustomerDashboard from './components/customer/CustomerDashboard';
import Login from './components/Login';
import Signup from './components/Signup';
import { fetchCurrentSession, getStoredToken } from './api/AuthSession';
import { getOnboardingEligibility } from './api/OnboardingApi';
import './App.css'

function useResolvedSession() {
  const [state, setState] = React.useState<{
    loading: boolean;
    role: string | null;
  }>({ loading: true, role: null });

  React.useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setState({ loading: false, role: null });
      return;
    }

    let cancelled = false;
    void (async () => {
      try {
        const session = await fetchCurrentSession(token);
        if (!cancelled) {
          setState({ loading: false, role: session.role });
        }
      } catch {
        if (!cancelled) {
          setState({ loading: false, role: null });
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}

// Redirects "/" to login or dashboard based on JWT and role
function HomeRedirect() {
  const { loading, role } = useResolvedSession();
  if (loading) return <div>Loading...</div>;
  if (role === "admin") return <Navigate to="/admin" replace />;
  if (role) return <CustomerHomeRedirect />;
  return <Navigate to="/login" replace />;
}

function CustomerHomeRedirect() {
  const [destination, setDestination] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const eligibility = await getOnboardingEligibility();
        if (!cancelled) {
          setDestination(eligibility.destination === "customer_dashboard" ? "/customer/dashboard" : "/customer");
        }
      } catch {
        if (!cancelled) {
          setDestination("/customer");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!destination) return <div>Loading...</div>;
  return <Navigate to={destination} replace />;
}

function ForbiddenMessage({ message }: { message: string }) {
  return <div className="container"><h2>{message}</h2></div>;
}

function RouteGate({
  children,
  allow,
  deniedMessage,
}: {
  children: ReactNode;
  allow: (role: string | null) => boolean;
  deniedMessage: string;
}) {
  const { loading, role } = useResolvedSession();
  if (loading) return <div>Loading...</div>;
  if (!role) return <Navigate to="/login" replace />;
  if (!allow(role)) return <ForbiddenMessage message={deniedMessage} />;
  return <>{children}</>;
}

// Protects admin route
function AdminRoute({ children }: { children: ReactNode }) {
  return (
    <RouteGate allow={(role) => role === "admin"} deniedMessage="This page is for admin only.">
      {children}
    </RouteGate>
  );
}

// Protects customer route
function CustomerRoute({ children }: { children: ReactNode }) {
  return (
    <RouteGate allow={(role) => !!role && role !== "admin"} deniedMessage="This page is for customers only.">
      {children}
    </RouteGate>
  );
}

function CustomerOnboardingRoute() {
  const [state, setState] = React.useState<{ loading: boolean; blocked: boolean }>({
    loading: true,
    blocked: false,
  });

  React.useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const eligibility = await getOnboardingEligibility();
        if (!cancelled) {
          setState({ loading: false, blocked: eligibility.destination === "customer_dashboard" });
        }
      } catch {
        if (!cancelled) {
          setState({ loading: false, blocked: false });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.loading) return <div>Loading...</div>;
  if (state.blocked) return <Navigate to="/customer/dashboard" replace />;
  return <CustomerPage />;
}

function App() {
  return (
    <Router>
      <main className='container'>
        <Routes>
          <Route path="/" element={<HomeRedirect />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route
            path="/admin"
            element={
              <AdminRoute>
                <AdminDashboard />
              </AdminRoute>
            }
          />
          <Route
            path="/customer"
            element={
              <CustomerRoute>
                <CustomerOnboardingRoute />
              </CustomerRoute>
            }
          />
          <Route
            path="/customer/dashboard"
            element={
              <CustomerRoute>
                <CustomerDashboard />
              </CustomerRoute>
            }
          />
        </Routes>
      </main>
    </Router>
  );
}

export default App

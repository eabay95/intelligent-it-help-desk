import { BrowserRouter, Navigate, Routes, Route } from "react-router-dom";
import AuthProvider from "./auth/AuthProvider";
import ProtectedRoute from "./auth/ProtectedRoute";
import Navbar from "./components/Navbar";
import AuthPage from "./pages/AuthPage";
import EmployeePortal from "./pages/EmployeePortal";
import TechnicianDashboard from "./pages/TechnicianDashboard";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Navbar />
        <Routes>
          <Route path="/login" element={<AuthPage key="login" mode="login" />} />
          <Route path="/register" element={<AuthPage key="register" mode="register" />} />
          <Route path="/forgot-password" element={<AuthPage key="forgot" mode="forgot" />} />
          <Route path="/reset-password" element={<AuthPage key="reset" mode="reset" />} />
          <Route path="/" element={<ProtectedRoute role="employee"><EmployeePortal /></ProtectedRoute>} />
          <Route path="/technician" element={<ProtectedRoute role="technician"><TechnicianDashboard /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

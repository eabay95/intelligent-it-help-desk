import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import EmployeePortal from "./pages/EmployeePortal";
import TechnicianDashboard from "./pages/TechnicianDashboard";

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />

      <Routes>
        <Route path="/" element={<EmployeePortal />} />
        <Route
          path="/technician"
          element={<TechnicianDashboard />}
        />
      </Routes>
    </BrowserRouter>
  );
}
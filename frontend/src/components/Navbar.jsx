import { NavLink } from "react-router-dom";

export default function Navbar() {
  return (
    <nav className="navbar">
      <h2>Intelligent IT Help Desk</h2>

      <div className="nav-links">
        <NavLink to="/">Employee Portal</NavLink>
        <NavLink to="/technician">Technician Dashboard</NavLink>
      </div>
    </nav>
  );
}
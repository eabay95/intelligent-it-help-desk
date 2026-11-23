import { createContext, useContext } from "react";

export const AuthContext = createContext(null);

export function useAuth() {
  return useContext(AuthContext);
}

export function homeFor(role) {
  return role === "technician" ? "/technician" : "/";
}

import { apiRequest } from "./client";

/** Matches `backend/routes/auth.py::_user_profile` exactly. */
export interface UserProfile {
  id: number;
  email: string;
  full_name: string;
  organization_id: number;
  organization_name: string | null;
  theme_preference: "light" | "dark";
  onboarding_completed_at: string | null;
  created_at: string;
}

export interface SignupPayload {
  email: string;
  password: string;
  confirm_password: string;
  full_name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface UpdateProfilePayload {
  theme_preference?: "light" | "dark";
  onboarding_completed?: boolean;
}

export const authApi = {
  signup: (payload: SignupPayload) => apiRequest<UserProfile>("/api/auth/signup", { method: "POST", json: payload }),
  login: (payload: LoginPayload) => apiRequest<UserProfile>("/api/auth/login", { method: "POST", json: payload }),
  logout: () => apiRequest<{ logged_out: boolean }>("/api/auth/logout", { method: "POST" }),
  session: () => apiRequest<UserProfile>("/api/auth/session"),
  forgotPassword: (email: string) =>
    apiRequest<{ message: string }>("/api/auth/forgot-password", { method: "POST", json: { email } }),
  resetPassword: (payload: { token: string; new_password: string; confirm_password: string }) =>
    apiRequest<{ message: string }>("/api/auth/reset-password", { method: "POST", json: payload }),
  updateProfile: (payload: UpdateProfilePayload) =>
    apiRequest<UserProfile>("/api/auth/profile", { method: "PATCH", json: payload }),
};

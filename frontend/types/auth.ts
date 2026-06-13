export type UserRole = "user" | "reviewer" | "admin";

export type AuthUser = {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

export type MeResponse = {
  user: AuthUser;
};
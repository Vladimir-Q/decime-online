export type UserRole = "admin" | "user";
export type AppLanguage = "ru" | "en";

export interface AuthConfig {
  auth_enabled: boolean;
  allow_registration: boolean;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserPublic {
  id: string;
  email: string;
  display_name: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  app_language?: AppLanguage | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  display_name?: string;
}

export interface UserCreateRequest {
  email: string;
  password: string;
  display_name?: string;
  role?: UserRole;
  is_active?: boolean;
}

export interface UserUpdateRequest {
  display_name?: string;
  role?: UserRole;
  is_active?: boolean;
  password?: string;
}

export interface UserPreferencesUpdateRequest {
  app_language: AppLanguage;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AdminUser {
  id: number;
  username: string;
  email: string;
  last_login_at: string | null;
}

export interface LoginResponse extends AdminUser {
  access_token: string;
  token_type?: string;
}


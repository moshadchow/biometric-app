import api from "./ApiService";

export interface AuthSessionUser {
  id: number;
  username: string;
  role: string;
}

export function getStoredToken(): string | null {
  return sessionStorage.getItem("jwt_token");
}

export async function fetchCurrentSession(token: string): Promise<AuthSessionUser> {
  const response = await api.get<AuthSessionUser>("/api/v1/users/my_session/", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
}

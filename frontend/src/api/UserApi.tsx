import api from "./ApiService";
import { fetchCurrentSession } from "./AuthSession";

interface AuthToken {
  access_token: string;
  token_type: string;
}

interface User {
  id: number;
  username: string;
  role: string;
}

const UserApi = {
  login: (username: string, password: string): Promise<{ data: AuthToken }> => {
    const formData = new FormData();
    formData.append("username", username);
    formData.append("password", password);
    return api.post("/api/v1/users/token", formData);
  },
  getSession: async (token: string): Promise<{ data: User }> => ({
    data: await fetchCurrentSession(token),
  }),
  signup: (username: string, password: string): Promise<{ data: User }> =>
    api.post("/api/v1/users/", { username, password }),
};

export default UserApi;

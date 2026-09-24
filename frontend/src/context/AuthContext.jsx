import {
    createContext,
    useContext,
    useEffect,
    useState
} from "react";

import {
    loginUser,
    registerUser,
    googleLoginUser,
    getCurrentUser
} from "../api/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(() => {
        const storedUser = localStorage.getItem("user");

        return storedUser ? JSON.parse(storedUser) : null;
    });

    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function restoreSession() {
            const token = localStorage.getItem("access_token");

            if (!token) {
                setLoading(false);
                return;
            }

            try {
                const currentUser = await getCurrentUser();

                setUser(currentUser);
                localStorage.setItem(
                    "user",
                    JSON.stringify(currentUser)
                );
            } catch {
                localStorage.removeItem("access_token");
                localStorage.removeItem("user");
                setUser(null);
            } finally {
                setLoading(false);
            }
        }

        restoreSession();
    }, []);

    async function login(email, password) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");

        const data = await loginUser(email, password);

        const token = data.access_token;

        localStorage.setItem("access_token", token);

        const currentUser = await getCurrentUser();

        localStorage.setItem(
            "user",
            JSON.stringify(currentUser)
        );

        setUser(currentUser);

        return currentUser;
    }

    async function loginWithGoogle(credential, password = null) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");

        const data = await googleLoginUser(credential, password);

        const token = data.access_token;

        localStorage.setItem("access_token", token);

        const currentUser = await getCurrentUser();

        localStorage.setItem(
            "user",
            JSON.stringify(currentUser)
        );

        setUser(currentUser);

        return currentUser;
    }

    async function register(data) {
        const registeredUser = await registerUser(data);

        return registeredUser;
    }

    async function refreshUser() {
        try {
            const currentUser = await getCurrentUser();
            setUser(currentUser);
            localStorage.setItem("user", JSON.stringify(currentUser));
            return currentUser;
        } catch (err) {
            console.warn("Could not refresh user session", err);
        }
    }

    function logout() {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");

        setUser(null);
    }

    return (
        <AuthContext.Provider
            value={{
                user,
                loading,
                login,
                loginWithGoogle,
                register,
                refreshUser,
                logout,
                isAuthenticated: Boolean(user)
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        return {
            user: null,
            loading: false,
            isAuthenticated: false,
            login: async () => {},
            loginWithGoogle: async () => {},
            register: async () => {},
            logout: () => {},
        };
    }
    return context;
}
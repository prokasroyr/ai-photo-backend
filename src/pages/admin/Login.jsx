import { signInWithPopup } from "firebase/auth";
import { auth, provider } from "../../services/firebase";

function Login() {
  const handleLogin = async () => {
    try {
      const result = await signInWithPopup(auth, provider);
      alert(`Welcome ${result.user.displayName}`);
    } catch (error) {
      alert(error.message);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        height: "100vh",
      }}
    >
      <h1>📸 AI Photo App</h1>
      <p>Professional Wedding Photo Delivery System</p>

      <button onClick={handleLogin}>
        Sign in with Google
      </button>
    </div>
  );
}

export default Login;
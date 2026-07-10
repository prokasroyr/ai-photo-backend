import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { getFirestore } from "firebase/firestore";
import { getStorage } from "firebase/storage";


const firebaseConfig = {
  apiKey: "AIzaSyBybeav0U8byuqHdUl2UQE7pWiNT9u43ns",
  authDomain: "ai-photo-app-f50a0.firebaseapp.com",
  projectId: "ai-photo-app-f50a0",
  storageBucket: "ai-photo-app-f50a0.firebasestorage.app",
  messagingSenderId: "171063053215",
  appId: "1:171063053215:web:74ee71c033e2d0db7a4baa",
};

const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);
export const provider = new GoogleAuthProvider();
export const db = getFirestore(app);
export const storage = getStorage(app);

export default app;
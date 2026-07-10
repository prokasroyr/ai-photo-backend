import { useEffect, useState } from "react";
import { collection, getDocs } from "firebase/firestore";
import { db } from "../../services/firebase";
import { useNavigate } from "react-router-dom";


function Dashboard() {
  const navigate = useNavigate();

    const [stats, setStats] = useState({
    events: 0,
   photos: 0,
    });
useEffect(() => {
  loadStats();
}, []);

const loadStats = async () => {
  try {
    const eventSnap = await getDocs(collection(db, "events"));
    const photoSnap = await getDocs(collection(db, "photos"));

    setStats({
      events: eventSnap.size,
      photos: photoSnap.size,
    });
  } catch (error) {
    console.error("Failed to load dashboard stats:", error);
  }
};
  return (
    <div className="space-y-8">

      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-800">
          📸 AI Photo Delivery Platform
        </h1>

        <p className="text-gray-500 mt-2">
          Welcome back, Photographer 👋
        </p>
      </div>

      {/* Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">

        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="text-gray-500">Events</h2>
          <p className="text-4xl font-bold mt-3">
            {stats.events}
          </p>
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="text-gray-500">Photos</h2>
          <p className="text-4xl font-bold mt-3">
          {stats.photos}
          </p>
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="text-gray-500">Clients</h2>
          <p className="text-4xl font-bold mt-3">0</p>
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="text-gray-500">Storage</h2>
          <p className="text-4xl font-bold mt-3">0 GB</p>
        </div>

      </div>

      {/* Quick Actions */}

      <div className="bg-white rounded-xl shadow p-6">

        <h2 className="text-xl font-bold mb-5">
          Quick Actions
        </h2>

        <div className="flex flex-wrap gap-4">

          <button
            onClick={() => navigate("/events/create")}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg"
          >
            ➕ Create Event
          </button>

          <button
            onClick={() => navigate("/events")}
            className="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg"
          >
            📁 My Events
          </button>

        </div>

      </div>

    </div>
  );
}

export default Dashboard;
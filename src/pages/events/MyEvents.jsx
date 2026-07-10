import { useEffect, useState } from "react";
import { collection, getDocs } from "firebase/firestore";
import { db } from "../../services/firebase";
import { useNavigate } from "react-router-dom";

function MyEvents() {
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);

  useEffect(() => {
    loadEvents();
  }, []);

  const loadEvents = async () => {
    const querySnapshot = await getDocs(collection(db, "events"));

    const list = [];

    querySnapshot.forEach((doc) => {
      list.push({
        id: doc.id,
        ...doc.data(),
      });
    });

    setEvents(list);
  };

  return (
    <div style={{ padding: "30px", fontFamily: "Arial" }}>
      <h1>📸 My Events</h1>

      {events.length === 0 ? (
        <p>No events found.</p>
      ) : (
        events.map((event) => (
          <div
            key={event.id}
            style={{
              border: "1px solid #ddd",
              borderRadius: "10px",
              padding: "15px",
              marginBottom: "15px",
            }}
          >
            <h3>{event.eventName}</h3>

            <p>📅 {event.eventDate}</p>

            <p>📍 {event.location}</p>

            <p>🆔 {event.eventCode}</p>

            <button onClick={() => navigate(`/events/${event.id}`)}>
            Open Event
            </button>
          </div>
        ))
      )}
    </div>
  );
}

export default MyEvents;
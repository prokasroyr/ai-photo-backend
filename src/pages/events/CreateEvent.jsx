import { useState } from "react";
import { db } from "../../services/firebase";
import { collection, addDoc } from "firebase/firestore";

function CreateEvent() {
  const [eventName, setEventName] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [location, setLocation] = useState("");
  const [eventType, setEventType] = useState("");

  const handleCreate = async () => {
  if (!eventName || !eventDate || !location || !eventType) {
    alert("সব তথ্য পূরণ করুন");
    return;
  }

  const eventCode = "WB-" + Math.floor(100000 + Math.random() * 900000);

  try {
    await addDoc(collection(db, "events"), {
      eventName,
      eventDate,
      location,
      eventType,
      eventCode,
      createdAt: new Date(),
    });

    alert("✅ Event Created Successfully");

    setEventName("");
    setEventDate("");
    setLocation("");
    setEventType("");

  } catch (error) {
    alert(error.message);
  }
};
  return (
    <div style={{ maxWidth: "500px", margin: "40px auto", fontFamily: "Arial" }}>
      <h1>📁 Create Event</h1>

      <input
        type="text"
        placeholder="Event Name"
        value={eventName}
        onChange={(e) => setEventName(e.target.value)}
        style={{ width: "100%", padding: "10px", marginBottom: "10px" }}
      />

      <input
        type="date"
        value={eventDate}
        onChange={(e) => setEventDate(e.target.value)}
        style={{ width: "100%", padding: "10px", marginBottom: "10px" }}
      />

      <input
        type="text"
        placeholder="Location"
        value={location}
        onChange={(e) => setLocation(e.target.value)}
        style={{ width: "100%", padding: "10px", marginBottom: "10px" }}
      />
      
      <select
        value={eventType}
        onChange={(e) => setEventType(e.target.value)}
        style={{ width: "100%", padding: "10px", marginBottom: "20px" }}
      >
        <option value="">Select Event Type</option>
        <option>Wedding</option>
        <option>Birthday</option>
        <option>Corporate</option>
        <option>Other</option>
      </select>

      <button
        onClick={handleCreate}
        style={{
          width: "100%",
          padding: "12px",
          fontSize: "16px",
          cursor: "pointer",
        }}
      >
        Create Event
      </button>
    </div>
  );
}

export default CreateEvent;
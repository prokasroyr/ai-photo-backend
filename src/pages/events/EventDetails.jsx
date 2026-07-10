import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { db } from "../../services/firebase";
import { doc, getDoc } from "firebase/firestore";
import PhotoUpload from "../../components/upload/PhotoUpload";
import Gallery from "../../components/gallery/Gallery";

function EventDetails() {
  const { id } = useParams();
  const [event, setEvent] = useState(null);

  useEffect(() => {
    loadEvent();
  }, []);

  const loadEvent = async () => {
    const docRef = doc(db, "events", id);
    const docSnap = await getDoc(docRef);

    if (docSnap.exists()) {
      setEvent(docSnap.data());
    }
  };

  if (!event) {
    return <h2 style={{ padding: "30px" }}>Loading...</h2>;
  }

  return (
    <div style={{ padding: "30px", fontFamily: "Arial" }}>
      <h1>{event.eventName}</h1>

      <p>📅 {event.eventDate}</p>

      <p>📍 {event.location}</p>

      <p>🆔 {event.eventCode}</p>

      <hr />

      <button>📤 Upload Photos</button>
      <PhotoUpload eventId={id} />

      <br /><br />

      <button>🖼 Gallery</button>

      <br /><br />

      <button>🤖 AI Face Processing</button>

      <br /><br />

      <button>👥 Clients</button>
      <hr />

    <Gallery eventId={id} />
    </div>
  );
}

export default EventDetails;
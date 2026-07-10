import { useEffect, useState } from "react";
import { db } from "../../services/firebase";
import {
  collection,
  query,
  where,
  onSnapshot,
  orderBy,
} from "firebase/firestore";

function Gallery({ eventId }) {
  const [photos, setPhotos] = useState([]);
  const [selectedPhotos, setSelectedPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const togglePhoto = (id) => {
  if (selectedPhotos.includes(id)) {
    setSelectedPhotos(selectedPhotos.filter((item) => item !== id));
  } else {
    setSelectedPhotos([...selectedPhotos, id]);
  }
    };
    const selectAll = () => {
  if (selectedPhotos.length === photos.length) {
    setSelectedPhotos([]);
  } else {
    setSelectedPhotos(photos.map((p) => p.id));
  }
    };


  useEffect(() => {

    const q = query(
    collection(db, "photos"),
    where("eventId", "==", eventId)
        );


        const unsubscribe = onSnapshot(q, (snapshot) => {

      const list = [];

      snapshot.forEach((doc) => {
        list.push({
          id: doc.id,
          ...doc.data(),
        });
      });

      setPhotos(list);
      setLoading(false);

    });


    return () => unsubscribe();

  }, [eventId]);


  if (loading) {
    return <p>Loading Photos...</p>;
  }


  return (
        

    <div style={{ marginTop: "30px" }}>
        <div style={{ marginBottom: "20px" }}>

<button onClick={selectAll}>
  {selectedPhotos.length === photos.length
    ? "Unselect All"
    : "Select All"}
</button>

<span style={{ marginLeft: "20px" }}>
Selected : {selectedPhotos.length}
</span>

<button
style={{
marginLeft:"20px",
background:"red",
color:"white"
}}
>
Delete Selected
</button>

</div>

      <h2>📷 Gallery ({photos.length})</h2>


      {photos.length === 0 && (
        <p>No Photos Uploaded</p>
      )}


      <div
        style={{
          display: "grid",
          gridTemplateColumns:
            "repeat(auto-fill,minmax(200px,1fr))",
          gap: "15px",
        }}
      >

        {photos.map((photo) => (
            

          <div
key={photo.id}
style={{
position:"relative"
}}
>

<input
type="checkbox"
checked={selectedPhotos.includes(photo.id)}
onChange={() => togglePhoto(photo.id)}
style={{
position:"absolute",
top:"10px",
left:"10px",
width:"20px",
height:"20px",
zIndex:5
}}
/>

<img
src={photo.imageUrl}
alt=""
style={{
width:"100%",
height:"200px",
objectFit:"cover",
borderRadius:"10px"
}}
/>

</div>
        ))}

      </div>

    </div>
  );
}

export default Gallery;
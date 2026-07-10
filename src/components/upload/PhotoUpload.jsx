import { useState } from "react";
import { CLOUD_NAME, UPLOAD_PRESET } from "../../services/cloudinary";
import { db } from "../../services/firebase";
import { collection, addDoc, serverTimestamp } from "firebase/firestore";

function PhotoUpload({ eventId }) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    setUploading(true);

const total = files.length;
let completed = 0;
   try {
  for (const file of files) {
    const formData = new FormData();

    formData.append("file", file);
    formData.append("upload_preset", UPLOAD_PRESET);

    const res = await fetch(
      `https://api.cloudinary.com/v1_1/${CLOUD_NAME}/image/upload`,
      {
        method: "POST",
        body: formData,
      }
    );

    const data = await res.json();

    if (!res.ok) {
      alert(data.error.message);
      continue;
    }

    await addDoc(collection(db, "photos"), {
      eventId: eventId,
      imageUrl: data.secure_url,
      publicId: data.public_id,
      createdAt: serverTimestamp(),
    });

    completed++;
setProgress(Math.round((completed / total) * 100));
  }
setProgress(100);
  alert("✅ All Photos Uploaded Successfully");
} catch (err) {
  alert("Upload Failed");
  console.error(err);
}

setUploading(false);
setProgress(0);
  };

  return (
    <div style={{ marginTop: "20px" }}>
      <input
         type="file"
         accept="image/*"
        multiple
         onChange={handleUpload}
        />

      {uploading && (
    <div style={{ marginTop: "15px" }}>
    <p>Uploading... {progress}%</p>

     <progress
      value={progress}
      max="100"
      style={{ width: "300px" }}
     ></progress>
        </div>
        )}
    </div>
   
  );
}

export default PhotoUpload;
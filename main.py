import os
import io
import json
import uuid
import zipfile
import gc  # 🧹 RAM খালি করার জন্য
from typing import List, Optional

import cv2
import numpy as np
import requests
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from fastapi import FastAPI, BackgroundTasks, HTTPException, Response, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import firebase_admin
from firebase_admin import credentials, firestore

import face_recognition

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from google.cloud.firestore_v1.base_query import FieldFilter

load_dotenv()

app = FastAPI(title="AI Photo Matcher API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- FIREBASE INIT ----------------
if not firebase_admin._apps:
    secret_file = "/etc/secrets/serviceAccountKey.json"
    local_paths = [
        "credentials/serviceAccountKey.json",
        "serviceAccountKey.json",
        os.path.join(os.path.dirname(__file__), "serviceAccountKey.json"),
        os.path.join(os.path.dirname(__file__), "credentials", "serviceAccountKey.json"),
    ]

    cred = None

    if os.path.exists(secret_file):
        try:
            with open(secret_file, "r") as f:
                cred_dict = json.load(f)
            if "private_key" in cred_dict:
                cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(cred_dict)
            print("✅ Firebase initialized from Render Secret File", flush=True)
        except Exception as e:
            print(f"⚠️ Render secret file error: {e}", flush=True)

    if not cred:
        for path in local_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        cred_dict = json.load(f)
                    if "private_key" in cred_dict:
                        cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
                    cred = credentials.Certificate(cred_dict)
                    print(f"✅ Firebase initialized from local path: {path}", flush=True)
                    break
                except Exception as e:
                    print(f"⚠️ Local credential error at {path}: {e}", flush=True)

    if not cred:
        firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")
        if firebase_json:
            try:
                cred_dict = json.loads(firebase_json)
                if "private_key" in cred_dict:
                    cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
                cred = credentials.Certificate(cred_dict)
                print("✅ Firebase initialized from Environment Variable", flush=True)
            except Exception as e:
                print(f"⚠️ Environment Variable error: {e}", flush=True)

    if cred:
        firebase_admin.initialize_app(cred)
    else:
        raise RuntimeError("❌ Firebase credentials not found!")

db = firestore.client()

# ---------------- CLOUDINARY INIT ----------------
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# ---------------- SCHEMAS ----------------
class ProcessEventRequest(BaseModel):
    eventId: str

class StartSearchRequest(BaseModel):
    eventId: str
    selfieUrl: str

class DownloadSingleRequest(BaseModel):
    imageUrl: str
    filename: Optional[str] = "photo.jpg"
    watermarkText: Optional[str] = None

class DeletePhotoRequest(BaseModel):
    photoId: str

class DownloadZipRequest(BaseModel):
    imageUrls: List[str] = []
    zipName: Optional[str] = "photos.zip"
    watermarkText: Optional[str] = None

# ---------------- HELPER: IMAGE RESIZER ----------------
def resize_image_if_large(img_np: np.ndarray, max_dim: int = 400) -> np.ndarray:
    """ফ্রি RAM (512MB) বাঁচাতে ছবি ৪০০ পিক্সেলে নামিয়ে আনবে"""
    h, w = img_np.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(img_np, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return img_np

def add_watermark(image_np: np.ndarray, text: str) -> np.ndarray:
    if not text:
        return image_np
    h, w, _ = image_np.shape
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(1.0, w / 1600.0)
    thickness = max(2, int(font_scale * 2))
    (text_w, text_h), _ = cv2.getTextSize(text, font, font_scale, thickness)
    margin = int(w * 0.05)
    text_x = w - text_w - margin
    text_y = h - margin

    overlay = image_np.copy()
    cv2.rectangle(overlay, (text_x - 10, text_y - text_h - 10), (text_x + text_w + 10, text_y + 10), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.4, image_np, 0.6, 0, image_np)
    cv2.putText(image_np, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
    return image_np

# ---------------- TASK 1: EVENT PROCESSOR ----------------
def process_event_photos_task(event_id: str):
    print(f"\n🚀 [AI ENGINE] Processing Started for Event ID: {event_id}", flush=True)
    event_ref = db.collection("events").document(event_id)
    
    try:
        photos_query = db.collection("photos").where(filter=FieldFilter("eventId", "==", event_id)).get()
        total_photos = len(photos_query)
        print(f"📊 Total Photos Found in Database: {total_photos}", flush=True)

        if total_photos == 0:
            event_ref.set({
                "processingStatus": {
                    "status": "completed",
                    "total": 0,
                    "processed": 0,
                    "failed": 0,
                    "percentage": 100
                }
            }, merge=True)
            return

        processed_count = 0
        failed_count = 0

        event_ref.set({
            "processingStatus": {
                "status": "processing",
                "total": total_photos,
                "processed": 0,
                "failed": 0,
                "percentage": 0
            }
        }, merge=True)

        for index, photo_doc in enumerate(photos_query):
            photo_data = photo_doc.to_dict()
            photo_id = photo_doc.id

            raw_url = (
                photo_data.get("cloudinaryUrl") or 
                photo_data.get("secure_url") or 
                photo_data.get("imageUrl") or 
                photo_data.get("photoUrl") or 
                photo_data.get("url")
            )

            print(f"📸 [{index + 1}/{total_photos}] Processing Photo ID: {photo_id}", flush=True)

            if not raw_url:
                print(f"❌ Skipped: No image URL found in document {photo_id}", flush=True)
                failed_count += 1
            else:
                try:
                    resp = requests.get(raw_url, timeout=(5, 10), verify=False)
                    if resp.status_code != 200:
                        raise Exception(f"HTTP Status {resp.status_code}")

                    image_array = np.frombuffer(resp.content, dtype=np.uint8)
                    img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

                    if img is None or img.size == 0:
                        raise Exception("Corrupt or empty image")

                    # ক্র্যাশ রুখতে ৪০০ পিক্সেল রিসাইজ লজিক
                    img = resize_image_if_large(img, max_dim=400)

                    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    rgb_img = np.ascontiguousarray(rgb_img, dtype=np.uint8)

                    face_locations = face_recognition.face_locations(rgb_img, model="hog")
                    face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

                    if len(face_encodings) > 0:
                        encodings_list = [json.dumps(enc.tolist()) for enc in face_encodings]
                        db.collection("photos").document(photo_id).set({
                            "faceEncodings": encodings_list,
                            "hasFace": True,
                            "faceCount": len(face_encodings),
                            "aiProcessed": True
                        }, merge=True)
                        print(f"   ✅ Detected {len(face_encodings)} face(s)", flush=True)
                    else:
                        db.collection("photos").document(photo_id).set({
                            "hasFace": False,
                            "faceCount": 0,
                            "aiProcessed": True
                        }, merge=True)
                        print("   ⚠️ No faces detected", flush=True)

                    processed_count += 1

                    # 🧹 মেমোরি খালি করার জন্য কোড
                    del img, rgb_img, face_locations, face_encodings
                    gc.collect()

                except Exception as photo_err:
                    print(f"   ❌ Error processing photo {photo_id}: {photo_err}", flush=True)
                    failed_count += 1
                    gc.collect()

            percentage = int(((index + 1) / total_photos) * 100)
            is_done = (index + 1) == total_photos

            event_ref.set({
                "processingStatus": {
                    "status": "completed" if is_done else "processing",
                    "total": total_photos,
                    "processed": processed_count,
                    "failed": failed_count,
                    "percentage": percentage
                }
            }, merge=True)

        print(f"🎉 Processing Complete for Event: {event_id}\n", flush=True)

    except Exception as e:
        print(f"❌ Fatal Error in Background Task: {e}", flush=True)
        event_ref.set({
            "processingStatus": {
                "status": "failed",
                "error": str(e)
            }
        }, merge=True)

# ---------------- TASK 2: FACE SEARCH ----------------
def perform_face_search(event_id: str, selfie_url: str, job_id: str):
    job_ref = db.collection("aiJobs").document(job_id)
    try:
        print(f"\n🔎 AI Search Started | Job: {job_id}", flush=True)

        resp = requests.get(selfie_url, timeout=10, verify=False)
        if resp.status_code != 200:
            raise Exception("Failed to fetch selfie image")

        img_array = np.frombuffer(resp.content, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            raise Exception("Invalid selfie image format")

        img = resize_image_if_large(img, max_dim=400)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        rgb_img = np.ascontiguousarray(rgb_img, dtype=np.uint8)

        selfie_encs = face_recognition.face_encodings(rgb_img)
        
        # মেমোরি খালি করুন
        del img, rgb_img
        gc.collect()

        if not selfie_encs:
            job_ref.update({"status": "failed", "progress": 0, "error": "No face found in selfie"})
            return

        target_enc = selfie_encs[0]
        photos_query = db.collection("photos").where(filter=FieldFilter("eventId", "==", event_id)).get()
        total_photos = len(photos_query)

        if total_photos == 0:
            job_ref.update({"status": "completed", "progress": 100, "matchedPhotos": 0})
            return

        matched_photos = []
        for index, photo_doc in enumerate(photos_query):
            photo_data = photo_doc.to_dict()
            photo_id = photo_doc.id

            stored_encs = photo_data.get("faceEncodings", [])
            matched = False

            for stored_enc in stored_encs:
                try:
                    enc_arr = np.array(json.loads(stored_enc) if isinstance(stored_enc, str) else stored_enc)
                    if face_recognition.compare_faces([enc_arr], target_enc, tolerance=0.50)[0]:
                        matched = True
                        break
                except Exception:
                    pass

            if matched:
                img_url = photo_data.get("cloudinaryUrl") or photo_data.get("imageUrl") or photo_data.get("url")
                if img_url:
                    matched_photos.append({"photoId": photo_id, "imageUrl": img_url})
                    db.collection("photoMatches").add({
                        "jobId": job_id,
                        "eventId": event_id,
                        "photoId": photo_id,
                        "imageUrl": img_url
                    })

            progress = int(((index + 1) / total_photos) * 100)
            job_ref.update({
                "progress": progress,
                "processedPhotos": index + 1,
                "matchedPhotos": len(matched_photos),
                "status": "processing"
            })

        job_ref.update({
            "status": "completed",
            "progress": 100,
            "matchedPhotos": len(matched_photos)
        })
        print(f"🎉 Search Finished. Matches Found: {len(matched_photos)}", flush=True)

    except Exception as e:
        print(f"❌ Search Task Error: {e}", flush=True)
        job_ref.update({"status": "failed", "error": str(e)})

# ---------------- ENDPOINTS ----------------
@app.get("/")
def home():
    return {"status": "online", "message": "AI Engine Server Ready"}

# 📸 NEW: UPLOAD SELFIE ENDPOINT
@app.post("/upload-selfie")
async def upload_selfie(file: UploadFile = File(...)):
    """গেস্ট সেলফি আপলোড করে ক্লাউডিনারির URL রিটার্ন করবে"""
    try:
        upload_result = cloudinary.uploader.upload(
            file.file,
            folder="selfies"
        )
        selfie_url = upload_result.get("secure_url") or upload_result.get("url")
        return {
            "success": True,
            "url": selfie_url,
            "path": selfie_url,
            "selfieUrl": selfie_url
        }
    except Exception as e:
        print(f"❌ Selfie upload error: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-event")
async def process_event(req: ProcessEventRequest, background_tasks: BackgroundTasks):
    if not req.eventId:
        raise HTTPException(status_code=400, detail="eventId is required")
    background_tasks.add_task(process_event_photos_task, req.eventId)
    return {"success": True, "message": "AI task scheduled", "eventId": req.eventId}

@app.post("/start-search")
async def start_search(req: StartSearchRequest, background_tasks: BackgroundTasks):
    if not req.eventId or not req.selfieUrl:
        raise HTTPException(status_code=400, detail="eventId and selfieUrl are required")

    job_id = str(uuid.uuid4())
    db.collection("aiJobs").document(job_id).set({
        "jobId": job_id,
        "eventId": req.eventId,
        "status": "processing",
        "progress": 0,
        "createdAt": firestore.SERVER_TIMESTAMP
    })

    background_tasks.add_task(perform_face_search, req.eventId, req.selfieUrl, job_id)
    return {"success": True, "jobId": job_id}

@app.get("/search-status/{search_id}")
async def get_search_status(search_id: str):
    job_doc = db.collection("aiJobs").document(search_id).get()
    if not job_doc.exists:
        return {"status": "not_found", "progress": 0}
    
    data = job_doc.to_dict()
    if data.get("status") == "completed":
        matches = db.collection("photoMatches").where(filter=FieldFilter("jobId", "==", search_id)).get()
        data["matches"] = [{"photoId": m.id, **m.to_dict()} for m in matches]
    return data

@app.post("/download-single")
async def download_single(req: DownloadSingleRequest):
    resp = requests.get(req.imageUrl, timeout=15)
    img_np = cv2.imdecode(np.frombuffer(resp.content, np.uint8), cv2.IMREAD_COLOR)
    if req.watermarkText:
        img_np = add_watermark(img_np, req.watermarkText)
    _, encoded_img = cv2.imencode(".jpg", img_np)
    return Response(content=encoded_img.tobytes(), media_type="image/jpeg", headers={"Content-Disposition": f"attachment; filename={req.filename}"})

@app.post("/download-zip")
async def download_zip(req: DownloadZipRequest):
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for idx, url in enumerate(req.imageUrls):
            try:
                resp = requests.get(url, timeout=10)
                img_np = cv2.imdecode(np.frombuffer(resp.content, np.uint8), cv2.IMREAD_COLOR)
                if req.watermarkText:
                    img_np = add_watermark(img_np, req.watermarkText)
                _, encoded_img = cv2.imencode(".jpg", img_np)
                zf.writestr(f"photo_{idx + 1}.jpg", encoded_img.tobytes())
            except Exception:
                pass
    zip_io.seek(0)
    return Response(content=zip_io.getvalue(), media_type="application/zip", headers={"Content-Disposition": f"attachment; filename={req.zipName}"})

@app.delete("/delete-photo")
async def delete_photo(req: DeletePhotoRequest):
    photo_ref = db.collection("photos").document(req.photoId)
    photo_doc = photo_ref.get()
    if not photo_doc.exists:
        raise HTTPException(status_code=404, detail="Photo not found")

    public_id = photo_doc.to_dict().get("publicId")
    if public_id:
        cloudinary.uploader.destroy(public_id, resource_type="image", invalidate=True)
    photo_ref.delete()
    return {"success": True, "message": "Deleted"}
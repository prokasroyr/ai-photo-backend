import os
import io
import json
import uuid
import zipfile
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

# AI Face Recognition
import face_recognition

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from google.cloud.firestore_v1.base_query import FieldFilter

# ---------------- 1. FASTAPI & CORS SETUP ----------------
app = FastAPI(title="AI Photo Matcher API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Uploads directory setup for selfie storage
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- 2. FIREBASE INITIALIZATION ----------------
# ---------------- 2. FIREBASE INITIALIZATION ----------------

if not firebase_admin._apps:

    firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")

if not firebase_admin._apps:
    # Render-এর Secret File অথবা লোকাল পিসির ফাইল থেকে সরাসরি রিড করবে
    if os.path.exists("/etc/secrets/serviceAccountKey.json"):
        cred = credentials.Certificate("/etc/secrets/serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized from Render Secret File")
    elif os.path.exists("serviceAccountKey.json"):
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized from local serviceAccountKey.json")
    else:
        raise RuntimeError("❌ Firebase service account file not found!")
db = firestore.client()

# ---------------- CLOUDINARY CONFIG ----------------
load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# ---------------- 3. PYDANTIC SCHEMAS ----------------
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

# ---------------- 4. HELPER FUNCTIONS ----------------
def add_watermark(image_np: np.ndarray, text: str) -> np.ndarray:
    """ছবিতে প্রফেশনালভাবে নিচের ডান কোণে ওয়াটারমার্ক বসানোর ফাংশন"""
    if not text:
        return image_np
    
    h, w, _ = image_np.shape

    # ছবির রেজোল্যুশন অনুযায়ী ফন্ট স্কেল ও থিকনেস ঠিক করা
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(3, w / 1600)
    thickness = max(6, int(font_scale * 2))

    # টেক্সটের ওয়াইড ও হাইট হিসাব করা
    (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)

    # নিচের ডান কোণে পজিশন ঠিক করা (৩% মার্জিন রেখে)
    margin = int(w * 0.05)
    text_x = w - text_w - margin
    text_y = h - margin

    # ব্যাকগ্রাউন্ডের হালকা কালো শেড (Box)
    pad = 10
    overlay = image_np.copy()
    cv2.rectangle(
        overlay, 
        (text_x - pad, text_y - text_h - pad), 
        (text_x + text_w + pad, text_y + pad), 
        (0, 0, 0), 
        -1
    )
    
    # ব্যাকগ্রাউন্ডটি হালকা ট্রান্সপারেন্ট করা (৪০% কালো, ৬০% আসল ছবি)
    cv2.addWeighted(overlay, 0.4, image_np, 0.6, 0, image_np)

    # সাদা রঙের টেক্সট বসানো
    cv2.putText(
        image_np, 
        text, 
        (text_x, text_y), 
        font, 
        font_scale, 
        (255, 255, 255), 
        thickness, 
        cv2.LINE_AA
    )

    return image_np

# ---------------- 5. BACKGROUND TASKS ----------------
def process_event_photos_task(event_id: str):
    """ইভেন্টের সব ফটো প্রসেস করার ব্যাকগ্রাউন্ড টাস্ক"""
    try:
        event_ref = db.collection("events").document(event_id)
        photos_query = db.collection("photos").where("eventId", "==", event_id).get()
        total_photos = len(photos_query)
        
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
            print(f"⚠️ No photos found for event: {event_id}")
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

            print(f"\n📸 Processing Photo [{index + 1}/{total_photos}] - ID: {photo_id}")
            print(f"🔗 URL: {raw_url}")

            if not raw_url:
                print("❌ Error: No valid image URL found in document!")
                failed_count += 1
                continue

            try:
                resp = requests.get(raw_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}, verify=False)
                if resp.status_code != 200:
                    raise Exception(f"Failed to fetch image. HTTP Status: {resp.status_code}")

                image_array = np.frombuffer(resp.content, dtype=np.uint8)
                img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                
                if img is None:
                    raise Exception("OpenCV Image decoding failed (Corrupt or unsupported format)")

                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                rgb_img = np.ascontiguousarray(rgb_img)

                face_locations = face_recognition.face_locations(rgb_img)
                face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

                if len(face_encodings) > 0:
                    encodings_list = [json.dumps(enc.tolist()) for enc in face_encodings]
                    
                    db.collection("photos").document(photo_id).set({
                        "faceEncodings": encodings_list,
                        "hasFace": True,
                        "faceCount": len(face_encodings),
                        "aiProcessed": True
                    }, merge=True)
                    print(f"✅ Found {len(face_encodings)} face(s)")
                else:
                    db.collection("photos").document(photo_id).set({
                        "hasFace": False,
                        "faceCount": 0,
                        "aiProcessed": True
                    }, merge=True)
                    print("⚠️ No face found in this image")
                
                processed_count += 1

            except Exception as photo_err:
                print(f"❌ Error processing photo ID [{photo_id}]: {photo_err}")
                failed_count += 1

            percentage = int(((index + 1) / total_photos) * 100)
            is_completed = (index + 1) == total_photos

            event_ref.set({
                "processingStatus": {
                    "status": "completed" if is_completed else "processing",
                    "total": total_photos,
                    "processed": processed_count,
                    "failed": failed_count,
                    "percentage": percentage
                }
            }, merge=True)

        print(f"\n🎉 AI Processing finished for event: {event_id} | Total: {total_photos}, Processed: {processed_count}, Failed: {failed_count}\n")

    except Exception as e:
        print(f"❌ Fatal error in event processing task: {e}")
        db.collection("events").document(event_id).set({
            "processingStatus": {
                "status": "failed",
                "error": str(e)
            }
        }, merge=True)

def perform_face_search(event_id: str, selfie_url: str, job_id: str):
    """সেলফি দিয়ে ইভেন্টের সব ফটো থেকে ব্যাকগ্রাউন্ডে চেহারা ম্যাচ করার টাস্ক"""
    job_ref = db.collection("aiJobs").document(job_id)

    try:
        print(f"\n🔎 Starting AI Face Search")
        print(f"🆔 Job ID: {job_id}")
        print(f"🎟️ Event ID: {event_id}")

        if selfie_url.startswith("http://") or selfie_url.startswith("https://"):
            resp = requests.get(
                selfie_url,
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0"},
                verify=False
            )
            if resp.status_code != 200:
                raise Exception(f"Failed to download selfie. HTTP {resp.status_code}")

            img_array = np.frombuffer(resp.content, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        else:
            img = cv2.imread(selfie_url)

        if img is None:
            raise Exception("Could not read selfie image")

        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        rgb_img = np.ascontiguousarray(rgb_img)

        selfie_encodings = face_recognition.face_encodings(rgb_img)

        if not selfie_encodings:
            job_ref.update({
                "status": "failed",
                "progress": 0,
                "error": "No face found in selfie"
            })
            print("❌ No face found in selfie")
            return

        target_encoding = selfie_encodings[0]
        print("✅ Selfie face encoding created")

        photos_query = db.collection("photos").where(
            filter=FieldFilter("eventId", "==", event_id)
        ).get()

        total_photos = len(photos_query)
        print(f"📸 Total event photos: {total_photos}")

        if total_photos == 0:
            job_ref.update({
                "status": "completed",
                "progress": 100,
                "processedPhotos": 0,
                "matchedPhotos": 0,
                "totalPhotos": 0
            })
            print(f"⚠️ No photos found for event: {event_id}")
            return

        job_ref.update({
            "status": "processing",
            "progress": 0,
            "totalPhotos": total_photos,
            "processedPhotos": 0,
            "matchedPhotos": 0
        })

        matched_photos = []
        processed_count = 0

        for index, photo_doc in enumerate(photos_query):
            photo_data = photo_doc.to_dict()
            photo_id = photo_doc.id

            stored_encodings = photo_data.get("faceEncodings", [])
            matched = False

            for stored_enc in stored_encodings:
                try:
                    if isinstance(stored_enc, str):
                        enc_array = np.array(json.loads(stored_enc))
                    else:
                        enc_array = np.array(stored_enc)

                    match = face_recognition.compare_faces(
                        [enc_array],
                        target_encoding,
                        tolerance=0.50
                    )[0]

                    if match:
                        matched = True
                        break
                except Exception as encoding_error:
                    print(f"⚠️ Encoding error for photo {photo_id}: {encoding_error}")

            if matched:
                image_url = (
                    photo_data.get("cloudinaryUrl")
                    or photo_data.get("imageUrl")
                    or photo_data.get("photoUrl")
                    or photo_data.get("url")
                )

                if image_url:
                    matched_photos.append({
                        "photoId": photo_id,
                        "imageUrl": image_url,
                        "score": 0.95
                    })

                    db.collection("photoMatches").add({
                        "jobId": job_id,
                        "eventId": event_id,
                        "photoId": photo_id,
                        "imageUrl": image_url
                    })

                    print(f"🎯 MATCH FOUND: {photo_id}")

            processed_count = index + 1
            progress_percentage = int((processed_count / total_photos) * 100)

            job_ref.update({
                "progress": progress_percentage,
                "processedPhotos": processed_count,
                "matchedPhotos": len(matched_photos),
                "status": "processing"
            })

            print(f"📊 Progress: {progress_percentage}% ({processed_count}/{total_photos})")

        job_ref.update({
            "status": "completed",
            "progress": 100,
            "processedPhotos": total_photos,
            "matchedPhotos": len(matched_photos),
            "totalPhotos": total_photos
        })

        print("\n🎉 AI FACE SEARCH COMPLETED")
        print(f"📸 Total: {total_photos}")
        print(f"🎯 Matches: {len(matched_photos)}")
        print(f"🆔 Job: {job_id}\n")

    except Exception as e:
        print(f"❌ Search Error: {e}")
        job_ref.update({
            "status": "failed",
            "error": str(e)
        })

# ---------------- 6. API ENDPOINTS ----------------

@app.get("/")
def home():
    return {"message": "AI Photo Matching Server is Running!"}

@app.post("/process-event")
async def process_event(req: ProcessEventRequest, background_tasks: BackgroundTasks):
    if not req.eventId:
        raise HTTPException(status_code=400, detail="eventId is required")

    background_tasks.add_task(process_event_photos_task, req.eventId)

    return {
        "success": True,
        "message": "AI Processing started in background",
        "eventId": req.eventId
    }

@app.post("/upload-selfie")
async def upload_selfie(file: UploadFile = File(...)):
    """সেলফি আপলোড করার এন্ডপয়েন্ট"""
    try:
        file_extension = file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
            
        return {"success": True, "path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/start-search")
async def start_search(
    req: StartSearchRequest,
    background_tasks: BackgroundTasks
):
    """ব্যাকগ্রাউন্ডে AI face search শুরু করার endpoint"""
    if not req.eventId:
        raise HTTPException(status_code=400, detail="eventId is required")

    if not req.selfieUrl:
        raise HTTPException(status_code=400, detail="selfieUrl is required")

    job_id = str(uuid.uuid4())

    print("\n===================================")
    print("🤖 NEW AI SEARCH JOB")
    print("===================================")
    print(f"🆔 Job ID: {job_id}")
    print(f"🎟️ Event ID: {req.eventId}")

    photos_query = db.collection("photos").where(
        filter=FieldFilter("eventId", "==", req.eventId)
    ).get()

    total_photos = len(photos_query)
    print(f"📸 Total Photos: {total_photos}")

    db.collection("aiJobs").document(job_id).set({
        "jobId": job_id,
        "eventId": req.eventId,
        "selfieUrl": req.selfieUrl,
        "status": "processing",
        "progress": 0,
        "totalPhotos": total_photos,
        "processedPhotos": 0,
        "matchedPhotos": 0,
        "error": "",
        "createdAt": firestore.SERVER_TIMESTAMP
    })

    print("✅ aiJobs document created")

    background_tasks.add_task(
        perform_face_search,
        req.eventId,
        req.selfieUrl,
        job_id
    )

    return {
        "success": True,
        "jobId": job_id,
        "eventId": req.eventId,
        "message": "AI search started"
    }

@app.get("/search-status/{search_id}")
async def get_search_status(search_id: str):
    """ফায়ারস্টোরের aiJobs থেকে সার্চ স্ট্যাটাস চেক করার এন্ডপয়েন্ট"""
    try:
        job_doc = db.collection("aiJobs").document(search_id).get()
        if not job_doc.exists:
            return {"status": "not_found", "progress": 0}

        job_data = job_doc.to_dict()
        status = job_data.get("status", "processing")
        progress = job_data.get("progress", 0)

        response_data = {
            "status": status,
            "progress": progress
        }

        if status == "completed":
            matches_query = db.collection("photoMatches").where(
                filter=FieldFilter("jobId", "==", search_id)
            ).get()
            
            matches = [{"photoId": m.id, **m.to_dict()} for m in matches_query]
            response_data["matches"] = matches

        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/download-single")
async def download_single(req: DownloadSingleRequest):
    try:
        resp = requests.get(req.imageUrl, timeout=15)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Image download failed")

        img_np = cv2.imdecode(np.frombuffer(resp.content, np.uint8), cv2.IMREAD_COLOR)
        
        if req.watermarkText:
            img_np = add_watermark(img_np, req.watermarkText)

        _, encoded_img = cv2.imencode(".jpg", img_np)
        
        return Response(
            content=encoded_img.tobytes(),
            media_type="image/jpeg",
            headers={"Content-Disposition": f"attachment; filename={req.filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/download-zip")
async def download_zip(req: DownloadZipRequest):
    try:
        zip_io = io.BytesIO()
        
        with zipfile.ZipFile(zip_io, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for idx, url in enumerate(req.imageUrls):
                try:
                    resp = requests.get(url, timeout=10)
                    if resp.status_code == 200:
                        img_np = cv2.imdecode(np.frombuffer(resp.content, np.uint8), cv2.IMREAD_COLOR)
                        
                        if req.watermarkText:
                            img_np = add_watermark(img_np, req.watermarkText)

                        _, encoded_img = cv2.imencode(".jpg", img_np)
                        zf.writestr(f"photo_{idx + 1}.jpg", encoded_img.tobytes())
                except Exception as img_err:
                    print(f"Skipping image {url}: {img_err}")

        zip_io.seek(0)
        
        return Response(
            content=zip_io.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={req.zipName}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete-photo")
async def delete_photo(req: DeletePhotoRequest):
    try:
        photo_ref = db.collection("photos").document(req.photoId)
        photo_doc = photo_ref.get()

        if not photo_doc.exists:
            raise HTTPException(
                status_code=404,
                detail="Photo not found in Firestore"
            )

        photo_data = photo_doc.to_dict()
        public_id = photo_data.get("publicId")

        if not public_id:
            raise HTTPException(
                status_code=400,
                detail="Cloudinary publicId not found"
            )

        print("\n===================================")
        print("🗑️ DELETE PHOTO")
        print("===================================")
        print(f"📸 Photo ID: {req.photoId}")
        print(f"☁️ Cloudinary Public ID: {public_id}")

        result = cloudinary.uploader.destroy(
            public_id,
            resource_type="image",
            type="upload",
            invalidate=True
        )

        print(f"☁️ Cloudinary Delete Result: {result}")

        if result.get("result") in ["ok", "not found"]:
            photo_ref.delete()
            print("🔥 Firestore document deleted")
            print("✅ Photo completely deleted")

            return {
                "success": True,
                "message": "Photo deleted successfully",
                "photoId": req.photoId,
                "publicId": public_id,
                "cloudinary": result.get("result")
            }

        raise HTTPException(
            status_code=500,
            detail=f"Cloudinary delete failed: {result}"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Delete error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
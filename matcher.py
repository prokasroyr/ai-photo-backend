import json
import numpy as np
import face_recognition

def search_matching_photos(selfie_file_path, photos_list, tolerance=0.50):
    """
    সেলফির সাথে ডাটাবেসে থাকা ছবির faceEncodings তুলনা করে ম্যাচ করার ফাংশন
    """
    matched_photos = []

    try:
        # ১. সেলফি থেকে ফেস এনকোডিং বের করা
        selfie_image = face_recognition.load_image_file(selfie_file_path)
        selfie_encodings = face_recognition.face_encodings(selfie_image)

        if len(selfie_encodings) == 0:
            print("❌ No face detected in the uploaded selfie!")
            return []

        target_encoding = selfie_encodings[0]
        print(f"📸 Selfie face encoding generated successfully.")

        # ২. ডাটাবেসের সব ছবির সাথে ফেস ডিস্ট্যান্স চেক করা
        for photo in photos_list:
            photo_encodings = photo.get("faceEncodings", [])
            photo_url = photo.get("imageUrl") or photo.get("cloudinaryUrl") or photo.get("url")

            if not photo_encodings or not photo_url:
                continue

            for enc_item in photo_encodings:
                try:
                    # String (JSON) থাকলে array তে রূপান্তর
                    if isinstance(enc_item, str):
                        db_encoding = np.array(json.loads(enc_item))
                    else:
                        db_encoding = np.array(enc_item)

                    # Euclidean Distance বের করা (Distance যত কম, ম্যাচ তত নিশ্চিত)
                    distance = face_recognition.face_distance([db_encoding], target_encoding)[0]
                    
                    print(f"🔍 Photo ID [{photo.get('id')}]: Distance = {distance:.4f}")

                    # tolerance = 0.50 এর কম হলে ম্যাচ ধরবে (প্রয়োজনে 0.55 করতে পারেন)
                    if distance <= tolerance:
                        # Distance কে Match Percentage (Score) এ রূপান্তর
                        score = round(float(1 - distance), 2)
                        
                        matched_photos.append({
                            "id": photo.get("id"),
                            "imageUrl": photo_url,
                            "score": max(score, 0.50)
                        })
                        break # একটি ছবিতে ফেস ম্যাচ করলে পরের এনকোডিংয়ে যাওয়ার দরকার নেই
                except Exception as err:
                    print(f"⚠️ Error parsing encoding: {err}")
                    continue

    except Exception as e:
        print(f"❌ Error in face matching process: {e}")
        return []

    # সর্বোচ্চ স্কোরের ওপর ভিত্তি করে সর্টিং
    matched_photos.sort(key=lambda x: x["score"], reverse=True)
    print(f"🎉 Total Matched Photos Found: {len(matched_photos)}")
    
    return matched_photos
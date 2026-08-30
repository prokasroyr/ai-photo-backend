import os
from deepface import DeepFace


def generate_embedding(image_path: str):
    """Generates 512-dim face embedding for a given image.

    Returns None if no face is detected.
    """
    if not os.path.exists(image_path):
        print(f"⚠️ File does not exist: {image_path}")
        return None

    try:
        # enforce_detection=True দিলে মুখ না পেলে DeepFace Exception দেয়
        result = DeepFace.represent(
            img_path=image_path,
            model_name="Facenet512",
            detector_backend="opencv",
            enforce_detection=True,
        )

        if result and len(result) > 0:
            return result[0]["embedding"]

        return None

    except ValueError:
        # মুখ খুঁজে না পেলে ValueError হ্যান্ডেল করা হচ্ছে
        print(f"❌ No face detected in image: {image_path}")
        return None
    except Exception as e:
        print(f"⚠️ Unexpected error in DeepFace: {e}")
        return None
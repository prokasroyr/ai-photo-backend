from deepface import DeepFace


def get_embedding(image_path):

    embedding = DeepFace.represent(
        img_path=image_path,
        model_name="Facenet512",
        detector_backend="opencv",
        enforce_detection=False
    )

    return embedding
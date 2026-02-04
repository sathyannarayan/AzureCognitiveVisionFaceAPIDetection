import os
from dotenv import load_dotenv
from azure.cognitiveservices.vision.face import FaceClient
from azure.cognitiveservices.vision.face.models import FaceAttributeType, APIErrorException
from msrest.authentication import CognitiveServicesCredentials
from PIL import Image, ImageDraw, ImageFont

# Load environment
load_dotenv()

cog_endpoint = (os.getenv("AI_SERVICE_ENDPOINT") or "").rstrip("/")
cog_key = (os.getenv("AI_SERVICE_KEY") or "").strip()

if not cog_endpoint or not cog_key:
    raise ValueError("AI_SERVICE_ENDPOINT or AI_SERVICE_KEY not set in .env")

# Display config used (mask key for security)
key_display = f"{cog_key[:4]}...{cog_key[-4:]}" if len(cog_key) > 8 else "****"
print("Using .env config:")
print(f"  AI_SERVICE_ENDPOINT = {cog_endpoint}")
print(f"  AI_SERVICE_KEY = {key_display}")
print()

# Authenticate Face client
credentials = CognitiveServicesCredentials(cog_key)
face_client = FaceClient(cog_endpoint, credentials)

def _raise_401_help():
    raise SystemExit(
        "Azure Face API returned 401 (access denied).\n\n"
        "Fix:\n"
        "1. In Azure Portal go to your Face resource (create one: AI Services → Face).\n"
        "2. Open 'Keys and Endpoint' and copy Key 1 and Endpoint.\n"
        "3. In this folder, edit .env and set:\n"
        "   AI_SERVICE_ENDPOINT=<your endpoint, e.g. https://your-name.cognitiveservices.azure.com>\n"
        "   AI_SERVICE_KEY=<Key 1 from portal>\n"
        "4. Use a Face resource only (Computer Vision keys will not work here)."
    )

def detect_faces(image_file):
    # Minimal attributes to avoid API errors
    features = [
        FaceAttributeType.glasses,
        FaceAttributeType.blur,
        FaceAttributeType.occlusion
    ]

    with open(image_file, "rb") as image_data:
        try:
            detected_faces = face_client.face.detect_with_stream(
                image=image_data,
                return_face_attributes=features,
                return_face_id=False
            )
        except APIErrorException as e:
            if "401" in str(e) or "invalid subscription key" in str(e).lower():
                _raise_401_help()
            raise

    if not detected_faces:
        print(f"No faces detected in {image_file}.")
        return []

    print(f"{len(detected_faces)} face(s) detected in {image_file}.\n")

    # Annotate image
    image = Image.open(image_file)
    draw = ImageDraw.Draw(image)

    # Use a bigger font for face tags
    try:
        font = ImageFont.truetype("arial.ttf", size=20)
    except:
        font = ImageFont.load_default()

    for idx, face in enumerate(detected_faces, start=1):
        r = face.face_rectangle
        box = [(r.left, r.top), (r.left + r.width, r.top + r.height)]
        draw.rectangle(box, outline="lime", width=3)

        # Add face number above the rectangle
        tag = f"Face {idx}"
        draw.text((r.left, r.top - 25), tag, fill="lime", font=font)

        # Print readable attributes in terminal
        attrs = face.face_attributes
        glasses = attrs.glasses.name if attrs.glasses else "NoGlasses"
        blur = attrs.blur.blur_level.name if attrs.blur else "None"
        occlusion = ", ".join([k for k,v in attrs.occlusion.__dict__.items() if v]) or "None"

        print(f"{tag}:")
        print(f" - Glasses: {glasses}")
        print(f" - Blur Level: {blur}")
        print(f" - Occlusion: {occlusion}\n")

    # Save annotated image
    base = os.path.basename(image_file)
    outputfile = f"detected_{base}"
    image.save(outputfile)
    print(f"Annotated image saved as {outputfile}\n")

    return detected_faces

if __name__ == "__main__":
    test_images = [
        "images/face1.jpg",
        "images/face2.jpg",
        "images/faces.jpg"
    ]

    summary = {}
    for img in test_images:
        print(f"--- Processing {img} ---")
        faces = detect_faces(img)
        summary[img] = len(faces)

    print("\n=== Detection Summary ===")
    for img, count in summary.items():
        print(f"{img}: {count} face(s) detected")

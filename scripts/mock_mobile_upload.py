import requests
import json
import base64
import os
from time import sleep

# Replace with the path to a test logbook image
TEST_IMAGE_PATH = r"C:\Nipuna\TEST\runs\detect\tea_standard_20260308_1721\val_batch0_pred.jpg"
UPLOAD_URL = "http://localhost:8000/api/upload"

def mock_teavision_upload():
    print(f"Mocking TeaVision logbook upload to {UPLOAD_URL}...")
    
    if not os.path.exists(TEST_IMAGE_PATH):
        print(f"Error: Could not find test image at {TEST_IMAGE_PATH}")
        return

    # Metadata that the TeaVision App sends
    metadata = {
        "capture_type": "logbook",
        "device": {"model": "Test Script Emulator", "os_version": "14"},
        "quality": {"is_blurry": False, "is_dark": False, "glare_detected": False}
    }

    try:
        with open(TEST_IMAGE_PATH, "rb") as f:
            files = {"image": ("test_logbook.jpg", f, "image/jpeg")}
            data = {"metadata": json.dumps(metadata)}
            
            response = requests.post(UPLOAD_URL, files=files, data=data)
            
            print(f"Response Status: {response.status_code}")
            print(f"Response Body: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200:
                print("\n✅ Upload successful! The frontend should automatically pick this up in 3 seconds.")
            else:
                print("❌ Upload failed.")
    except Exception as e:
        print(f"❌ Error during request: {e}")

if __name__ == "__main__":
    print("Wait 5 seconds to get Web App Ready...")
    sleep(1)
    mock_teavision_upload()

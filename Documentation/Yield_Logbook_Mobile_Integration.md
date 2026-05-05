# Yield Logbook & Tea Leaf Mobile Integration

This document outlines the architecture and user flow for the **Mobile-to-Desktop Integration** built into the TeaVision web platform. This feature allows users to seamlessly bridge their mobile device's camera with the desktop dashboard for high-quality image extraction.

## 🌟 Overview
The mobile integration solves the problem of getting photos of **Tea Yield Logbooks** and **Tea Leaves** from a user's phone onto their desktop for AI processing, without requiring them to email or text the photos to themselves.

By spinning up a local LAN server bridge, the desktop dashboard can instantly receive images captured on a mobile phone's browser.

## ⚙️ How It Works (Architecture)

1. **The QR Connect Initialization**
   - When a user clicks **"📱 QR Connect"** on the React frontend, the app determines the desktop's local IP address.
   - It generates a QR code representing a special endpoint URL (`http://<IP_ADDRESS>:8000/mobile`).

2. **Mobile Capture System (`/mobile/upload`)**
   - The user scans the QR code using their iPhone or Android camera.
   - Their phone opens a lightweight web page served by the FastAPI `main.py` backend.
   - This page taps directly into the phone's native camera using standard HTML5 `<input type="file" capture="environment">`.
   - When a photo is taken, it is instantly POSTed to the backend's `/mobile/upload` route, which caches the image in the server's memory.

3. **Desktop Retrieval (`/mobile/latest`)**
   - Back on the Desktop dashboard, the user clicks the **"From Phone"** button.
   - The React frontend fires an asynchronous GET request to `/mobile/latest`.
   - The backend responds with a Base64 encoded payload of the image the phone just captured.
   - The frontend decodes this Base64 string back into a `File` object and injects it directly into the Dropzone UI, treating it exactly as if the user had browsed their hard drive for the file.

## 🚀 Features Integrated

### 1. Yield Logbook Digitization (`LogbookOCRPage.jsx`)
- Replaces the need to scan thick, physical logbooks with a flatbed scanner.
- The user can simply snap a picture of their physical logbook page on their phone, and it beams straight into the OCR parsing pipeline to be converted into an Excel spreadsheet.

### 2. Tea Leaf Quality Detection (`DetectionPage.jsx`)
- Replaces the need for uploading pre-saved images.
- Users can take clear, macro shots of tea buds directly in the field using their high-quality smartphone cameras, then seamlessly process them through the YOLOv8 model on their desktop to check for disease, bud quality, and leaf measurements.

## 🛠️ Tech Stack
- **Frontend**: React.js, HTML5 Camera API (`capture="environment"`).
- **Backend / Bridge**: Python FastAPI, standard fast memory-caching.
- **Network Protocol**: HTTP over Local Area Network (LAN).

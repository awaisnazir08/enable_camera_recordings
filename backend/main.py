import os
import cv2
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread, Event
from contextlib import asynccontextmanager
import time
from pydantic import BaseModel
from camera_manager import CameraManager

class RecordingRequest(BaseModel):
    filename: str
    record_local: bool

# Camera indices
camera_indices = [0]
cameras = {}
stop_events = {}

# Function to open cameras with multiple attempts
def open_cameras():
    global cameras
    for index in camera_indices:
        print(f"Attempting to open camera {index}...")
        for attempt in range(3):  # Up to 3 attempts to open the camera
            cap = cv2.VideoCapture(index)
            time.sleep(0.5)  # Delay to allow the camera to initialize
            if cap.isOpened():
                print(f"Camera {index} opened successfully.")
                cameras[index] = cap
                break
            else:
                print(f"Error: Unable to open camera {index}. Attempt {attempt + 1}/3.")
                time.sleep(1)  # Delay before the next attempt
        else:
            print(f"Unable to open camera {index} after multiple attempts.")
            raise Exception(f"Unable to open camera {index}.")

# Function to close cameras
def close_cameras():
    print("Closing cameras...")
    for index, cam in cameras.items():
        if cam.isOpened():
            cam.release()

# Function generating frames continuously for a video stream
def generate_frames(camera_index):
    print(f"Streaming camera {camera_index}...")
    while True:
        if camera_index not in cameras or not cameras[camera_index].isOpened():
            print(f"Error: Camera {camera_index} not opened.")
            break
        success, frame = cameras[camera_index].read()
        if not success:
            print(f"Error: Failed to read the stream from camera {camera_index}.")
            break
        # Encode the image in JPEG format
        _, buffer = cv2.imencode('.jpeg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@asynccontextmanager
async def lifespan(app: FastAPI):
# Startup code (replaces @app.on_event("startup"))
    try:
        open_cameras()
    except Exception as e:
        print(f"Startup error: {e}")
    
    yield  # This point separates startup from shutdown
    # Shutdown code (replaces @app.on_event("shutdown"))
    close_cameras()

# Create the FastAPI application
app = FastAPI(lifespan=lifespan)
camera_manager = CameraManager(camera_indices)
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# # Route to open cameras on application startup
# @app.on_event("startup")
# def startup_event():
#     try:
#         open_cameras()
#     except Exception as e:
#         print(f"Startup error: {e}")

# # Route to close cameras on application shutdown
# @app.on_event("shutdown")
# def shutdown_event():
#     close_cameras()

# Route for video streams
@app.get("/video_feed/{camera_index}")
async def video_feed(camera_index: int):
    if camera_index not in camera_indices:
        raise HTTPException(status_code=404, detail="Camera not found.")
    return StreamingResponse(generate_frames(camera_index), media_type="multipart/x-mixed-replace; boundary=frame")

# Entry point for the frontend
@app.get("/frontend/index.html")
async def get_index():
    print("Loading index.html...")
    try:
        return StreamingResponse(open("../frontend/index.html", "rb"), media_type="text/html")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="index.html file not found.")

# Static file routes
@app.get("/frontend/{file_name}")
async def get_static_file(file_name: str):
    file_path = os.path.join("..", "frontend", file_name)  # Adjusting the path to go one level up
    media_type = "text/css" if file_name.endswith('.css') else "application/javascript"
    try:
        return StreamingResponse(open(file_path, "rb"), media_type=media_type)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File {file_name} not found.")

# # Route to start recording
# @app.post("/start_recording")
# async def start_recording(filename: str, record_local: bool):
#     # Assuming camera_manager is a global instance of CameraManager
#     print(filename)
#     print(record_local)
#     camera_manager.start_recording(filename, record_local)
#     return {"status": "Recording started"}


# Route to start recording
@app.post("/start_recording")
async def start_recording(request: RecordingRequest):
    filename = request.filename
    record_local = request.record_local
    # print(filename)
    # print(record_local)
    # Assuming camera_manager is a global instance of CameraManager
    camera_manager.start_recording(filename, record_local)
    return {"status": "Recording started"}

# Route to stop recording
@app.post("/stop_recording")
async def stop_recording():
    camera_manager.stop_recording()
    # camera_manager.close_all()
    return {"status": "Recording stopped"}

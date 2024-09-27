import cv2
import os
from datetime import datetime
import threading

class CameraManager:
    def __init__(self, camera_indices):
        self.cameras = [cv2.VideoCapture(i) for i in camera_indices]
        self.recording = False
        self.out_writers = []
        self.frames = [None] * len(camera_indices)  # To store the latest frame for each camera
        self.frame_lock = threading.Lock()  # A lock to ensure thread-safe access to frames
        self.running = True  # Used to control the frame-grabbing threads

        # Start a thread for each camera to continuously grab frames
        self.frame_threads = []
        for i in range(len(self.cameras)):
            thread = threading.Thread(target=self._grab_frames, args=(i,))
            thread.start()
            self.frame_threads.append(thread)

    def _grab_frames(self, index):
        """Continuously grab frames from the camera and store them."""
        camera = self.cameras[index]
        while self.running:
            success, frame = camera.read()
            if success:
                with self.frame_lock:
                    self.frames[index] = frame

    def get_camera_stream(self, index):
        """Return frames for streaming."""
        while True:
            with self.frame_lock:
                frame = self.frames[index]

            if frame is None:
                continue

            _, jpeg = cv2.imencode('.jpeg', frame)
            frame = jpeg.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

    def start_recording(self, filename, local):
        """Start recording frames to a file."""
        if self.recording:
            print("Already recording.")
            return

        self.recording = True
        self.out_writers = []

        # Create a folder with the current date (yymmdd)
        date_folder = datetime.now().strftime('%Y%m%d')
        recordings_dir = f"recordings/{date_folder}"
        if not os.path.exists(recordings_dir):
            os.makedirs(recordings_dir)

        for i, cam in enumerate(self.cameras):
            if cam.isOpened():
                # Generate the video filename with a timestamp
                timestamp = datetime.now().strftime('%H%M%S')
                video_filename = f"{filename}_cam{i}_{timestamp}.avi"
                full_path = os.path.join(recordings_dir, video_filename)

                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                fps = 30
                frame_width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
                frame_height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

                # Create the VideoWriter object
                out = cv2.VideoWriter(full_path, fourcc, fps, (frame_width, frame_height))
                if not out.isOpened():
                    print(f"Error: Unable to open VideoWriter for {full_path}")
                    continue

                self.out_writers.append(out)
                print(f"Recording started for {full_path}")

        # Start a thread for recording
        threading.Thread(target=self._record_video).start()

    def _record_video(self):
        """Record frames to the file."""
        while self.recording:
            with self.frame_lock:
                for i, frame in enumerate(self.frames):
                    if frame is not None and i < len(self.out_writers):
                        self.out_writers[i].write(frame)

    def stop_recording(self):
        """Stop recording."""
        if not self.recording:
            print("Not currently recording.")
            return

        self.recording = False
        print("Stopping recording.")

        for out in self.out_writers:
            out.release()
            print("VideoWriter released.")
        self.out_writers = []

    def close_all(self):
        """Release all cameras."""
        self.running = False  # Stop frame grabbing threads
        for cam in self.cameras:
            cam.release()

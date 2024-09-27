import cv2
import os
from datetime import datetime
import threading

class CameraManager:
    def __init__(self, camera_indices):
        self.cameras = [cv2.VideoCapture(i) for i in camera_indices]
        self.recording = False
        self.out_writers = []

    def get_camera_stream(self, index):
        camera = self.cameras[index]
        while True:
            success, frame = camera.read()
            if not success:
                break
            _, jpeg = cv2.imencode('.jpg', frame)
            frame = jpeg.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

    def start_recording(self, filename, local):
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
            
        # Start recording in a separate thread
        threading.Thread(target=self._record_video, args=(filename, recordings_dir)).start()

    def _record_video(self, filename, recordings_dir):
        # Recording with 'XVID' codec for better compatibility
        for i, cam in enumerate(self.cameras):
            if cam.isOpened():
                # Generate the video filename with a timestamp
                timestamp = datetime.now().strftime('%H%M%S')
                video_filename = f"{filename}_cam{i}_{timestamp}.avi"
                full_path = os.path.join(recordings_dir, video_filename)

                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                fps = 30  # Default to 30 fps
                frame_width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
                frame_height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

                # Create the VideoWriter object
                out = cv2.VideoWriter(full_path, fourcc, fps, (frame_width, frame_height))
                if not out.isOpened():
                    print(f"Error: Unable to open VideoWriter for {full_path}")
                    continue
                
                self.out_writers.append(out)
                print(f"Recording started for {full_path}")

                # Start writing the frames
                while self.recording:
                    success, frame = cam.read()
                    if not success:
                        break
                    out.write(frame)

    def stop_recording(self):
        if not self.recording:
            print("Not currently recording.")
            return

        self.recording = False
        print("Stopping recording.")

        # Release all VideoWriters
        for out in self.out_writers:
            out.release()
            print("VideoWriter released.")
        self.out_writers = []

    def close_all(self):
        for cam in self.cameras:
            cam.release()

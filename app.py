import cv2
import time
import datetime
import threading
import os
from pymongo import MongoClient
import gridfs
from ultralytics import YOLO
from flask import Flask, render_template, Response, request
from flask_socketio import SocketIO
import pyttsx3
import subprocess
import requests

app = Flask(__name__)
socketio = SocketIO(app)

# 두 개의 YOLO 모델 로드
model_violence = YOLO("Polygon_Violence.pt")
model_punch_kick = YOLO("punch_kick.pt")
cap = cv2.VideoCapture(0)

# 실제 FPS 계산
fps = cap.get(cv2.CAP_PROP_FPS)
if fps == 0:
    fps = 20.0  # 기본값으로 설정

fourcc = cv2.VideoWriter_fourcc(*'XVID')
recording = False
start_time = 0
recorded_frames = []
video_file = 'recorded_fight.avi'

# MongoDB 초기화
client = MongoClient('mongodb://localhost:27017/')
db = client['video_db']
fs = gridfs.GridFS(db)

# pyttsx3 엔진 초기화
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

# 음성 알림 상태를 제어할 플래그 추가
alert_triggered = False


def play_alert_sound():
    """Play the alert sound."""
    global alert_triggered

    if not alert_triggered:
        alert_triggered = True
        print("cctv:173 Alert triggered! Playing voice alert.")

        def speak():
            try:
                engine = pyttsx3.init(driverName='sapi5')  # Windows 환경일 경우
                
                engine.say("위험 상황 발생. 위험 상황이 발생하였습니다!")
                engine.runAndWait()
                print("cctv:205 Voice alert triggered successfully.")
            except Exception as e:
                print(f"cctv: Error occurred during voice alert: {e}")
            finally:
                global alert_triggered
                alert_triggered = False  # 플래그 해제

        # 비동기 실행
        threading.Thread(target=speak).start()


def insert_video_data(file_path, confidence, punch_count, kick_count, severity):
    try:
        with open(file_path, 'rb') as f:
            contents = f.read()
            timestamped_filename = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{os.path.basename(file_path)}"
            fs.put(contents, filename=timestamped_filename, confidence=confidence, punch_count=punch_count, kick_count=kick_count, severity=severity)
            print(f"Video inserted into GridFS: {timestamped_filename} with Severity: {severity}")
    except Exception as e:
        print(f"Failed to insert video into GridFS: {e}")

def convert_to_mp4(input_file, output_file, recorded_fps):
    # 지정한 FPS로 mp4로 변환
    command = ['ffmpeg', '-i', input_file, '-c:v', 'libx264', '-preset', 'slow', '-crf', '22', '-r', str(recorded_fps), output_file]
    subprocess.run(command, check=True)

def overlay_timestamp(frame, timestamp):
    """Overlay the given timestamp on the frame."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    color = (255, 255, 255)  # White color
    thickness = 1
    position = (10, 30)  # Position to display the timestamp
    cv2.putText(frame, timestamp, position, font, font_scale, color, thickness, cv2.LINE_AA)

def record_video(frames, video_temp_file, fight_prob, punch_count, kick_count):
    if not frames:
        print("No frames to record.")
        return

    frame_height, frame_width = frames[0].shape[:2]
    recorded_fps = len(frames) / 10.0

    # Initialize video writer with calculated FPS
    out = cv2.VideoWriter(video_temp_file, fourcc, recorded_fps, (frame_width, frame_height))
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for frame in frames:
        # Overlay timestamp on each frame
        overlay_timestamp(frame, timestamp)
        out.write(frame)
    
    out.release()

    # Convert and save as mp4 using the calculated FPS
    output_file = video_temp_file.replace('.avi', '.mp4')
    convert_to_mp4(video_temp_file, output_file, recorded_fps)

    # Calculate total count and assess injury severity
    total_count = punch_count + kick_count
    if total_count >= 35:
        severity = "치명상"
    elif total_count >= 25:
        severity = "중상"
    elif total_count >= 15:
        severity = "경상"
    else:
        severity = "None"

    # Insert the video and injury data into the database
    insert_video_data(output_file, fight_prob, punch_count, kick_count, severity)
    print(f"Video recorded and processed: {output_file}, Severity: {severity}")

def generate_frames():
    global recording, start_time, recorded_frames
    detection_count = 0
    last_reset_time = time.time()
    punch_count = 0
    kick_count = 0

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to capture frame")
            break
        else:
            if recording:
                results = model_punch_kick.predict(source=frame)
            else:
                results = model_violence.predict(source=frame)

            plots = frame  # BBox를 숨기고 원본 프레임을 사용
            fight_prob = 0

            if not recording:
                if hasattr(results[0], 'boxes') and results[0].boxes is not None:
                    for box in results[0].boxes:
                        class_index = box.cls
                        confidence = box.conf
                        if class_index == 1 and confidence >= 0.65:
                            fight_prob = confidence
                            detection_count += 1
                            print(f"Detection {detection_count} with confidence: {confidence}")
                            break

                socketio.emit('progress', {'detection_count': detection_count})

                current_time = time.time()
                if current_time - last_reset_time >= 180:
                    last_reset_time = current_time
                    detection_count = 0
                    socketio.emit('reset_progress')

                if detection_count >= 12:
                    threading.Thread(target=play_alert_sound).start()  # Trigger sound alert
                    recording = True
                    detection_count = 0  # Reset detection count immediately after alert
                    socketio.emit('reset_progress')
                    start_time = current_time
                    recorded_frames = []
                    punch_count = 0
                    kick_count = 0
                    print("Recording started")

            if recording:
                recorded_frames.append(frame)
                current_time = time.time()

                if hasattr(results[0], 'boxes') and results[0].boxes is not None:
                    for box in results[0].boxes:
                        class_index = box.cls
                        confidence = box.conf
                        if confidence >= 0.25:
                            if class_index == 0:  # punch
                                punch_count += 1
                                print(f"Punch detected, count: {punch_count}")
                            elif class_index == 1:  # kick
                                kick_count += 2
                                print(f"Kick detected, count: {kick_count}")

                if current_time - start_time >= 10:
                    recording = False
                    print("Recording stopped")
                    video_temp_file = f"temp_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{video_file}"

                    threading.Thread(target=record_video, args=(recorded_frames[:], video_temp_file, fight_prob, punch_count, kick_count)).start()

                    # Reset detection count after recording ends to allow new alerts
                    detection_count = 0

            ret, buffer = cv2.imencode('.jpg', plots)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
def send_kakao_message():
    """Send an alert message to KakaoTalk."""
    url = 'https://kapi.kakao.com/v2/api/talk/memo/default/send'
    headers = {
        'Authorization': 'Bearer TVCHIcJfTON3u_fBf4URVqTLqciXFTZSAAAAAQo8JFkAAAGTZkbuX-Q1KlcE_6bt',  
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
    'template_object': '{"object_type":"text","text":"위험 상황 발생!","link":{"web_url":"http://192.168.10.122:5000","mobile_web_url":"http://192.168.10.122:5000"}}'
} #주소는 현재 와이파이 주소

    try:
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            print("카카오톡 메시지가 성공적으로 전송되었습니다.")
        else:
            print(f"카카오톡 메시지 전송 실패: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"카카오톡 메시지 전송 중 오류 발생: {e}")


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cctv')
def cctv():
    return render_template('cctv.html')  # CCTV 페이지로 이동

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/videos')
def videos():
    video_files = [
        {
            'filename': file.filename,
            'punch_count': file.punch_count,
            'kick_count': file.kick_count,
            'severity': file.severity
        }
        for file in fs.find()
    ]
    return render_template('videos.html', video_files=video_files)

@app.route('/video/<filename>')
def video(filename):
    grid_out = fs.find_one({'filename': filename})
    if grid_out:
        return Response(grid_out.read(), mimetype='video/mp4')
    else:
        return "Video not found", 404

@app.route('/trigger_alert', methods=['POST'])
def trigger_alert():
    threading.Thread(target=play_alert_sound).start()  # 음성 알림 실행
    threading.Thread(target=send_kakao_message).start()  # 카카오톡 메시지 전송
    return "Alert triggered", 200


if __name__ == '__main__':
    try:
        socketio.run(app, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("Interrupted by user")
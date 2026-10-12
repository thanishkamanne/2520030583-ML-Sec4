from pathlib import Path
from collections import Counter
from datetime import datetime
import uuid
import json
import os

import cv2
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
RESULT_DIR = BASE_DIR / "results"
UPLOAD_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB
ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}

# Model is loaded lazily so the website can display setup errors clearly.
model = None
model_load_error = None
VEHICLE_CLASSES = {2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}


def get_model():
    global model, model_load_error
    if model is not None:
        return model
    if model_load_error:
        raise RuntimeError(model_load_error)
    try:
        from ultralytics import YOLO
        # On first run, Ultralytics downloads the small pretrained weights if absent.
        model = YOLO("yolov8n.pt")
        return model
    except Exception as exc:
        model_load_error = (
            "Could not load the YOLO model. Check your internet connection on first run "
            "and install the packages from requirements.txt. Details: " + str(exc)
        )
        raise RuntimeError(model_load_error)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def classify_density(avg_visible, peak_visible):
    """Demo thresholds only; calibrate for a particular camera before real deployment."""
    score = max(avg_visible, peak_visible * 0.65)
    if score < 4:
        return "Light", "Traffic appears relatively clear in the analyzed frames.", "low"
    if score < 10:
        return "Moderate", "Several vehicles are visible. Continue monitoring for queue growth.", "medium"
    return "Heavy", "Many vehicles are visible. Review the annotated video for queueing or slow movement.", "high"


def analyze_video(video_path, output_path):
    detector = get_model()
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError("The uploaded file could not be opened as a video.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if width <= 0 or height <= 0:
        cap.release()
        raise ValueError("The video does not contain readable frames.")

    # Keep output at original size, but sample at most about 8 frames per second for speed.
    sample_every = max(1, int(round(fps / 8)))
    writer_fps = max(1.0, fps / sample_every)
    writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), writer_fps, (width, height))
    if not writer.isOpened():
        cap.release()
        raise ValueError("Could not create the annotated output video. Try another video format.")

    seen_ids = set()
    class_counts = Counter()
    samples = []
    processed_frames = 0
    peak_visible = 0
    frame_index = 0
    first_time = datetime.now().timestamp()

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_index % sample_every != 0:
                frame_index += 1
                continue

            result = detector.track(frame, persist=True, classes=list(VEHICLE_CLASSES.keys()),
                                    conf=0.25, verbose=False, tracker="bytetrack.yaml")[0]
            annotated = result.plot()
            visible_now = 0
            if result.boxes is not None and len(result.boxes) > 0:
                for i, box in enumerate(result.boxes):
                    cls_id = int(box.cls[0].item())
                    name = VEHICLE_CLASSES.get(cls_id, "Vehicle")
                    visible_now += 1
                    track_id = None
                    if result.boxes.id is not None:
                        track_id = int(result.boxes.id[i].item())
                    if track_id is not None:
                        key = f"{cls_id}:{track_id}"
                        if key not in seen_ids:
                            seen_ids.add(key)
                            class_counts[name] += 1
                    else:
                        # Fallback when tracking IDs are unavailable; this is a detection count, not unique count.
                        class_counts[name] += 1

            processed_frames += 1
            peak_visible = max(peak_visible, visible_now)
            elapsed_video = frame_index / fps
            samples.append({"seconds": round(elapsed_video, 1), "visible": visible_now})
            cv2.putText(annotated, f"RoadPulse AI | visible: {visible_now}", (18, 36),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
            writer.write(annotated)
            frame_index += 1
    finally:
        cap.release()
        writer.release()

    if processed_frames == 0:
        raise ValueError("No readable frames were found in this video.")

    avg_visible = sum(s["visible"] for s in samples) / len(samples)
    density, explanation, severity = classify_density(avg_visible, peak_visible)
    # Trend alert is a simple signal, not a validated forecast.
    window = max(1, len(samples) // 3)
    early_avg = sum(s["visible"] for s in samples[:window]) / min(window, len(samples))
    late_avg = sum(s["visible"] for s in samples[-window:]) / min(window, len(samples))
    trend_delta = late_avg - early_avg
    if len(samples) >= 6 and trend_delta >= 2:
        alert = "Vehicle presence increased during the clip; check for congestion build-up."
        alert_type = "warning"
    elif len(samples) >= 6 and trend_delta <= -2:
        alert = "Vehicle presence decreased toward the end of the clip."
        alert_type = "good"
    else:
        alert = "No strong increase in visible vehicle count was detected in this clip."
        alert_type = "neutral"

    duration = total_frames / fps if total_frames > 0 else frame_index / fps
    return {
        "total_unique_vehicles": int(sum(class_counts.values())),
        "vehicle_counts": {k: int(class_counts.get(k, 0)) for k in ["Car", "Motorcycle", "Bus", "Truck"]},
        "density": density,
        "severity": severity,
        "explanation": explanation,
        "alert": alert,
        "alert_type": alert_type,
        "average_visible": round(avg_visible, 2),
        "peak_visible": int(peak_visible),
        "duration_seconds": round(duration, 1),
        "processed_frames": int(processed_frames),
        "timeline": samples[::max(1, len(samples)//30)],
        "method_note": "Traffic levels use provisional visible-vehicle thresholds, not calibrated road capacity. Vehicle counts can be affected by occlusion, camera angle, lighting, and tracking errors.",
        "video_url": f"/results/{output_path.name}"
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "model_loaded": model is not None})


@app.route("/analyze", methods=["POST"])
def analyze():
    if "video" not in request.files:
        return jsonify({"error": "Please choose a road video first."}), 400
    file = request.files["video"]
    if not file or not file.filename:
        return jsonify({"error": "Please choose a road video first."}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type. Use MP4, AVI, MOV, MKV, or WEBM."}), 400

    safe_name = secure_filename(file.filename)
    token = uuid.uuid4().hex[:10]
    input_path = UPLOAD_DIR / f"{token}_{safe_name}"
    output_path = RESULT_DIR / f"analyzed_{token}.mp4"
    file.save(input_path)
    try:
        data = analyze_video(input_path, output_path)
        data["filename"] = safe_name
        return jsonify(data)
    except ValueError as exc:
        output_path.unlink(missing_ok=True)
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        return jsonify({"error": str(exc)}), 500
    finally:
        input_path.unlink(missing_ok=True)


@app.route("/results/<path:filename>")
def result_file(filename):
    return send_from_directory(RESULT_DIR, filename, as_attachment=False)


if __name__ == "__main__":
    print("RoadPulse AI is starting at http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)

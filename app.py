from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os

app = Flask(__name__, static_folder=".")
CORS(app)

MAGNIFIC_BASE = "https://api.magnific.com"


@app.route("/")
def index():
    return send_from_directory(".", "kling_motion_control.html")


# Validasi URL sebelum kirim ke Magnific
@app.route("/v1/validate-urls", methods=["POST"])
def validate_urls():
    body = request.get_json()
    image_url = body.get("image_url", "")
    video_url = body.get("video_url", "")
    results = {}

    for key, url in [("image_url", image_url), ("video_url", video_url)]:
        if not url:
            results[key] = {"ok": False, "reason": "URL kosong"}
            continue
        try:
            r = requests.head(url, allow_redirects=True, timeout=10)
            ct = r.headers.get("Content-Type", "")
            size = int(r.headers.get("Content-Length", 0))
            final_url = r.url

            if r.status_code >= 400:
                results[key] = {"ok": False, "reason": f"HTTP {r.status_code} — URL tidak bisa diakses"}
            elif key == "image_url" and not any(x in ct for x in ["image/", "octet-stream"]):
                results[key] = {"ok": False, "reason": f"Bukan file gambar (Content-Type: {ct})"}
            elif key == "video_url" and not any(x in ct for x in ["video/", "octet-stream"]):
                results[key] = {"ok": False, "reason": f"Bukan file video (Content-Type: {ct})"}
            elif key == "image_url" and size > 10 * 1024 * 1024:
                results[key] = {"ok": False, "reason": f"File terlalu besar ({size//1024//1024}MB, maks 10MB)"}
            else:
                results[key] = {"ok": True, "content_type": ct, "size": size, "final_url": final_url}
        except requests.exceptions.Timeout:
            results[key] = {"ok": False, "reason": "Timeout — URL terlalu lambat diakses"}
        except requests.exceptions.ConnectionError:
            results[key] = {"ok": False, "reason": "Tidak bisa terhubung ke URL"}
        except Exception as e:
            results[key] = {"ok": False, "reason": str(e)}

    print(f"\n[VALIDATE] {results}\n")
    return jsonify(results)



@app.route("/v1/ai/video/kling-v3-motion-control-std", methods=["POST"])
def create_task():
    api_key = request.headers.get("x-magnific-api-key", "")
    body = request.get_json()
    print(f"\n[POST] Request body:")
    print(f"  image_url : {body.get('image_url')}")
    print(f"  video_url : {body.get('video_url')}")
    print(f"  orientation: {body.get('character_orientation')}")
    print(f"  cfg_scale  : {body.get('cfg_scale')}")
    try:
        resp = requests.post(
            f"{MAGNIFIC_BASE}/v1/ai/video/kling-v3-motion-control-std",
            json=body,
            headers={
                "Content-Type": "application/json",
                "x-magnific-api-key": api_key,
            },
            timeout=30,
        )
        data = resp.json()
        print(f"[POST] Response {resp.status_code}: {data}\n")
        return jsonify(data), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"message": f"Proxy error: {str(e)}"}), 502


# GET — cek status task
@app.route("/v1/ai/video/kling-v3-motion-control-std/<task_id>", methods=["GET"])
def get_task(task_id):
    api_key = request.headers.get("x-magnific-api-key", "")
    try:
        resp = requests.get(
            f"{MAGNIFIC_BASE}/v1/ai/video/kling-v3-motion-control-std/{task_id}",
            headers={"x-magnific-api-key": api_key},
            timeout=15,
        )
        data = resp.json()
        print(f"\n[STATUS {resp.status_code}] task={task_id}")
        print(f"  → {data}\n")
        return jsonify(data), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"message": f"Proxy error: {str(e)}"}), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  ✅  Server berjalan di http://localhost:{port}")
    print(f"  🌐  Buka browser ke http://localhost:{port}\n")
    app.run(debug=True, port=port)

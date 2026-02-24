import logging
import random
import string
import time
import threading

from flask import Flask, request, jsonify, render_template

from flask_cors import CORS
app = Flask(__name__)

CORS(app)
storage = {}  # { code: { "text": "...", "expires": 1234567890 } }

def generate_code():
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(4))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)

# Metrics
metrics = {
    "total_cleanups": 0,
    "total_expired_removed": 0,
    "last_cleanup_time": None
}

def run_cleanup_once():
    now = time.time()
    expired_keys = [code for code, entry in storage.items() if entry["expires"] < now]

    for code in expired_keys:
        del storage[code]

    # Update metrics
    metrics["total_cleanups"] += 1
    metrics["total_expired_removed"] += len(expired_keys)
    metrics["last_cleanup_time"] = time.time()

    # Logging
    logging.info(f"Cleanup run: removed {len(expired_keys)} expired codes. "
                 f"Active codes: {len(storage)}")

    return len(expired_keys)

def cleanup_expired_codes():
    while True:
        now = time.time()
        expired_keys = [code for code, entry in storage.items() if entry["expires"] < now]

        for code in expired_keys:
            del storage[code]

        # Update metrics
        metrics["total_cleanups"] += 1
        metrics["total_expired_removed"] += len(expired_keys)
        metrics["last_cleanup_time"] = time.time()

        # Logging
        logging.info(f"Cleanup run: removed {len(expired_keys)} expired codes. "
                     f"Active codes: {len(storage)}")

        # sleep 5 minutes
        time.sleep(5 * 60)

@app.route("/cleanup", methods=["GET", "POST"])
def cleanup_endpoint():
    removed = run_cleanup_once()
    return jsonify({"removed": removed, "active_codes": len(storage)})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "active_codes": len(storage)})

@app.route("/store", methods=['POST'])
def store():
    text = request.json.get("text", "")
    if len(text) > 5000:
        return jsonify({"error": "Content Too Large, use less than 5000 characters."}), 413

    code = generate_code()

    # check for code duplication - generate until we get a free code
    while code in storage:
        code = generate_code()

    expires = time.time() + 2 * 60 * 60  # 2 hours

    storage[code] = {"text": text, "expires": expires}
    return jsonify({"code": code})


@app.route("/retrieve", methods=['GET'])
def retrieve():
    code = request.args.get("code", "").lower()

    if code not in storage:
        return jsonify({"error": "Invalid code"}), 404

    entry = storage[code]

    if time.time() > entry["expires"]:
        del storage[code]
        return jsonify({"error": "Code expired"}), 410

    return jsonify({"text": entry["text"]})


@app.route("/share.html", methods=['GET'])
def sharePage():
    return render_template('share.html')

@app.route("/quiz.html", methods=['GET'])
def sharePage():
    return render_template('quiz.html')

@app.route("/", methods=['GET'])
def indexPage():
    return render_template('share.html')


if __name__ == "__main__":
    cleanup_thread = threading.Thread(target=cleanup_expired_codes, daemon=True)
    cleanup_thread.start()

    app.run(host="0.0.0.0", port=5000)

import random
import string
import time

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

storage = {}  # { code: { "text": "...", "expires": 1234567890 } }


def generate_code():
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(4))


@app.route("/store", methods=['POST'])
def store():
    text = request.json.get("text", "")
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
def indexPage():
    return render_template('share.html')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

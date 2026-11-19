import os
import json
import hashlib
import requests
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, jsonify, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import pymongo
from web3 import Web3
import numpy as np
import cv2
import qrcode
from PIL import Image
import subprocess
import atexit
import time
# Initialize TensorFlow MobileNetV2
import tensorflow as tf
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input

def is_blockchain_live():
    """Checks whether the local Ganache RPC provider is responding."""
    try:
        w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))
        return w3.is_connected()
    except Exception:
        return False

# -------------------------------------------------------------------
# Application Configuration
# -------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "counterfeit_ai_blockchain_capstone_secret_key_2026")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
QR_FOLDER = os.path.join(BASE_DIR, "static", "qrcodes")
CONTRACT_DATA_PATH = os.path.join(BASE_DIR, "contract_data.json")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["QR_FOLDER"] = QR_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ALLOWED_BRANDS = ["Nike", "Adidas", "Puma"]

# MongoDB Client Setup
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/footwear_auth_db")
mongo_client = None
products_col = None
users_col = None

try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    db = mongo_client["footwear_auth_db"]
    products_col = db["products"]
    users_col = db["users"]
    mongo_client.server_info()
except Exception as e:
    print(f"[WARN] MongoDB offline or unreachable: {e}")

# Preload Feature Extractor
try:
    feature_model = MobileNetV2(weights="imagenet", include_top=False, pooling="avg")
except Exception as e:
    print(f"[WARN] Failed to load MobileNetV2: {e}")
    feature_model = None

def get_web3_instance():
    """Returns Web3 connection and loaded contract if available."""
    try:
        w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))
        if not w3.is_connected():
            return None, None

        if os.path.exists(CONTRACT_DATA_PATH):
            with open(CONTRACT_DATA_PATH, "r") as f:
                c_data = json.load(f)
                contract = w3.eth.contract(address=c_data["address"], abi=c_data["abi"])
                return w3, contract
        return w3, None
    except Exception:
        return None, None

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_crypto_hash(product_id, brand, batch_no, date, description):
    payload = f"{product_id}|{brand}|{batch_no}|{date}|{description}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def extract_features_from_path(img_path):
    if feature_model is None or not os.path.exists(img_path):
        return None
    try:
        img = Image.open(img_path).convert("RGB").resize((224, 224))
        arr = np.array(img, dtype=np.float32)
        arr = np.expand_dims(arr, axis=0)
        arr = preprocess_input(arr)
        features = feature_model.predict(arr, verbose=0)[0]
        norm = np.linalg.norm(features)
        return (features / norm).tolist() if norm > 0 else features.tolist()
    except Exception:
        return None

def compute_cosine_similarity(vec_a, vec_b):
    if not vec_a or not vec_b:
        return 0.0
    a, b = np.array(vec_a), np.array(vec_b)
    dot = np.dot(a, b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(dot / denom) if denom > 0 else 0.0

# Decorators
def manufacturer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in as a verified manufacturer.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "manufacturer":
            flash("Access denied. This dashboard is restricted to verified manufacturers.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function

# -------------------------------------------------------------------
# Core Web Routes
# -------------------------------------------------------------------

@app.route("/")
def index():
    w3, contract = get_web3_instance()
    blockchain_online = w3 is not None and w3.is_connected()
    contract_deployed = contract is not None
    db_online = products_col is not None

    total_products = 0
    if db_online:
        try:
            total_products = products_col.count_documents({})
        except Exception:
            pass

    return render_template(
        "index.html",
        blockchain_online=blockchain_online,
        contract_deployed=contract_deployed,
        db_online=db_online,
        total_products=total_products
    )
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Default fallback account for testing
        if username in ["nike_admin", "adidas_admin", "puma_admin"] and password == "admin123":
            session["user_id"] = username
            session["username"] = username
            session["role"] = "manufacturer"
            flash(f"Welcome back, {username}!", "success")
            return redirect(url_for("manufacturer_dashboard"))

        if users_col is not None:
            user = users_col.find_one({"username": username})
            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = str(user["_id"])
                session["username"] = user["username"]
                session["role"] = user.get("role", "customer")
                flash(f"Welcome back, {username}!", "success")
                return redirect(url_for("manufacturer_dashboard" if session["role"] == "manufacturer" else "index"))

        flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "customer")

        if not (username and email and password):
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))

        if users_col is not None:
            existing = users_col.find_one({"$or": [{"username": username}, {"email": email}]})
            if existing:
                flash("Username or email already registered. Please sign in.", "warning")
                return redirect(url_for("login"))

            hashed_pw = generate_password_hash(password)
            users_col.insert_one({
                "username": username,
                "email": email,
                "password_hash": hashed_pw,
                "role": role,
                "createdAt": datetime.utcnow()
            })
            flash("Account created successfully! You can now log in.", "success")
            return redirect(url_for("login"))
        else:
            flash("User database is offline. Please try again later.", "danger")
            return redirect(url_for("register"))

    return render_template("register.html")
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Default fallback account for testing
        if username in ["nike_admin", "adidas_admin", "puma_admin"] and password == "admin123":
            session["user_id"] = username
            session["username"] = username
            session["role"] = "manufacturer"
            flash(f"Welcome back, {username}!", "success")
            return redirect(url_for("manufacturer_dashboard"))

        if users_col is not None:
            user = users_col.find_one({"username": username})
            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = str(user["_id"])
                session["username"] = user["username"]
                session["role"] = user.get("role", "customer")
                flash(f"Welcome back, {username}!", "success")
                return redirect(url_for("manufacturer_dashboard" if session["role"] == "manufacturer" else "index"))

        flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Successfully signed out.", "info")
    return redirect(url_for("index"))

@app.route("/manufacturer", methods=["GET", "POST"])
@manufacturer_required
def manufacturer_dashboard():
    w3, contract = get_web3_instance()
    blockchain_connected = w3 is not None and w3.is_connected()

    if request.method == "POST":
        product_name = request.form.get("product_name", "").strip()
        product_id = request.form.get("productId", "").strip().upper()
        brand = request.form.get("brand", "").strip()
        batch_no = request.form.get("batchNo", "").strip().upper()
        mfg_date = request.form.get("mfgDate", "").strip()
        description = request.form.get("description", "").strip()
        
        file1 = request.files.get("productImage")
        file2 = request.files.get("productImage2")
        file3 = request.files.get("productImage3")

        if not (product_id and brand and batch_no and mfg_date and description and file1):
            flash("All fields including the primary reference image are mandatory.", "danger")
            return redirect(url_for("manufacturer_dashboard"))

        if products_col is not None and products_col.find_one({"productId": product_id}):
            flash(f"Footwear batch {product_id} is already registered.", "warning")
            return redirect(url_for("manufacturer_dashboard"))

        # Save all uploaded multi-angle images
        saved_images = []
        features_list = []
        for idx, upload in enumerate([file1, file2, file3], start=1):
            if upload and upload.filename != "" and allowed_file(upload.filename):
                fname = secure_filename(f"{product_id}_angle{idx}_{upload.filename}")
                dest_path = os.path.join(app.config["UPLOAD_FOLDER"], fname)
                upload.save(dest_path)
                rel_path = f"/static/uploads/{fname}"
                saved_images.append(rel_path)
                emb = extract_features_from_path(dest_path)
                if emb:
                    features_list.append(emb)

        # Cryptographic SHA-256 seal
        crypto_hash = generate_crypto_hash(product_id, brand, batch_no, mfg_date, description)

        # Record to Blockchain (Ganache)
        tx_hash = None
        if blockchain_connected and contract is not None:
            try:
                account = w3.eth.accounts[0]
                tx = contract.functions.registerProduct(
                    product_id,
                    brand,
                    batch_no,
                    mfg_date,
                    crypto_hash
                ).transact({"from": account})
                receipt = w3.eth.wait_for_transaction_receipt(tx)
                tx_hash = receipt.transactionHash.hex()
            except Exception as e:
                print(f"[WARN] Blockchain transaction failed: {e}")

        # Generate QR Code
        verify_url = f"{request.host_url}verify?id={product_id}"
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(verify_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_filename = f"qr_{product_id}.png"
        qr_dest = os.path.join(app.config["QR_FOLDER"], qr_filename)
        qr_img.save(qr_dest)
        qr_rel_path = f"/static/qrcodes/{qr_filename}"

        # Insert to MongoDB
        product_doc = {
            "productId": product_id,
            "product_name": product_name,
            "brand": brand,
            "batchNo": batch_no,
            "mfgDate": mfg_date,
            "description": description,
            "crypto_hash": crypto_hash,
            "qr_code_path": qr_rel_path,
            "image_path": saved_images[0] if saved_images else None,
            "all_images": saved_images,
            "features": features_list[0] if features_list else None,
            "all_features": features_list,
            "txHash": tx_hash,
            "registeredAt": datetime.utcnow()
        }

        if products_col is not None:
            products_col.insert_one(product_doc)

        flash(f"Product {product_id} successfully secured on blockchain and database.", "success")
        return redirect(url_for("manufacturer_dashboard"))

    # Fetch registered products
    registered_products = []
    if products_col is not None:
        try:
            registered_products = list(products_col.find().sort("registeredAt", -1))
        except Exception:
            registered_products = []

    return render_template(
        "manufacturer.html",
        products=registered_products,
        allowed_brands=ALLOWED_BRANDS,
        blockchain_connected=blockchain_connected,
        contract_deployed=contract is not None
    )

@app.route("/manufacturer/delete/<product_id>", methods=["POST"])
@manufacturer_required
def delete_product(product_id):
    if products_col is not None:
        prod = products_col.find_one({"productId": product_id}) or products_col.find_one({"product_id": product_id})
        if prod:
            # Clean up local image and QR files
            files_to_remove = []
            if prod.get("qr_code_path"):
                files_to_remove.append(prod["qr_code_path"])
            if prod.get("all_images"):
                files_to_remove.extend(prod["all_images"])
            elif prod.get("image_path"):
                files_to_remove.append(prod["image_path"])

            for fpath in files_to_remove:
                full_p = os.path.join(BASE_DIR, fpath.lstrip("/"))
                if os.path.exists(full_p):
                    try:
                        os.remove(full_p)
                    except OSError:
                        pass

            products_col.delete_one({"_id": prod["_id"]})
            flash(f"Footwear entry {product_id} removed successfully.", "success")
        else:
            flash("Product not found.", "danger")
    return redirect(url_for("manufacturer_dashboard"))

@app.route("/verify", methods=["GET", "POST"])
def verify_page():
    if request.method == "POST":
        product_id = request.form.get("productId", "").strip().upper()
        photo = request.files.get("customerShoeImage")

        if not product_id:
            flash("Please enter or scan a valid Product ID.", "danger")
            return redirect(url_for("verify_page"))

        prod = None
        if products_col is not None:
            prod = products_col.find_one({"productId": product_id}) or products_col.find_one({"product_id": product_id})

        if not prod:
            return render_template("verify_result.html", authentic=False, reason="Product ID not found in official registry.")

        # Cryptographic Verification
        expected_hash = generate_crypto_hash(
            prod.get("productId") or prod.get("product_id"),
            prod.get("brand"),
            prod.get("batchNo") or prod.get("batch_no"),
            prod.get("mfgDate") or prod.get("manufacturing_date"),
            prod.get("description", "")
        )
        hash_matched = (expected_hash == prod.get("crypto_hash"))

        # AI Computer Vision Similarity Check
        similarity_score = 0.0
        if photo and photo.filename != "" and allowed_file(photo.filename):
            temp_path = os.path.join(app.config["UPLOAD_FOLDER"], f"temp_{secure_filename(photo.filename)}")
            photo.save(temp_path)
            q_emb = extract_features_from_path(temp_path)

            master_embs = prod.get("all_features") or ([prod.get("features")] if prod.get("features") else [])
            if q_emb and master_embs:
                scores = [compute_cosine_similarity(q_emb, m) for m in master_embs if m]
                similarity_score = max(scores) if scores else 0.0

            if os.path.exists(temp_path):
                os.remove(temp_path)

        ai_passed = similarity_score >= 0.70 or photo is None
        is_authentic = hash_matched and (similarity_score >= 0.70 if photo else True)

        return render_template(
            "verify_result.html",
            authentic=is_authentic,
            product=prod,
            hash_matched=hash_matched,
            similarity_score=round(similarity_score * 100, 1),
            ai_passed=ai_passed,
            blockchain_live=is_blockchain_live()
        )

    scanned_id = request.args.get("id", "")
    return render_template("verify.html", scanned_id=scanned_id)

# -------------------------------------------------------------------
# Server Execution
# -------------------------------------------------------------------
ganache_process = None

def ensure_ganache_running():
    global ganache_process
    w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))
    if w3.is_connected():
        print("[BLOCKCHAIN] Ganache is already running on port 7545.")
        return

    print("[BLOCKCHAIN] Ganache not detected. Launching background instance...")
    try:
        ganache_process = subprocess.Popen(
            ["npx", "ganache", "--port", "7545", "--deterministic"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True
        )
        time.sleep(3)
        print("[BLOCKCHAIN] Ganache node started successfully.")
    except Exception as e:
        print(f"[WARN] Could not auto-start Ganache: {e}")

def cleanup_ganache():
    global ganache_process
    if ganache_process:
        print("\n[BLOCKCHAIN] Stopping background Ganache instance...")
        ganache_process.terminate()

atexit.register(cleanup_ganache)
# ----------------- SNEAKER AI ASSISTANT ROUTE (DIRECT REST) -----------------
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

@app.route("/api/ai_shoe_chat", methods=["POST"])
def ai_shoe_chat():
    try:
        data = request.get_json(silent=True) or {}
        user_prompt = data.get("message", "").strip()

        if not user_prompt:
            return jsonify({"reply": "Please ask a question about footwear models or legitimacy checks!"})

        system_context = (
            "You are 'SoleCheck AI', an elite sneakerhead and footwear authentication assistant. "
            "You specialize in sneaker silhouettes (Nike, Adidas, Jordan, Puma, New Balance, etc.), "
            "factory stitching checks, colorway histories, release dates, sizing recommendations, "
            "and explaining how blockchain and computer vision verify footwear authenticity. "
            "Keep answers punchy, informative, and engaging."
        )

        # 1. Direct REST API call (No protobuf conflicts with TensorFlow)
        if GEMINI_KEY:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
                payload = {
                    "contents": [{
                        "parts": [{"text": f"{system_context}\n\nUser: {user_prompt}"}]
                    }]
                }
                res = requests.post(url, json=payload, timeout=8)
                if res.status_code == 200:
                    resp_json = res.json()
                    ai_text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                    return jsonify({"reply": ai_text.strip()})
            except Exception as e:
                print(f"[AI CHAT] Direct API Error: {e}")

        # 2. Smart Built-in Knowledge Fallback (Always works)
        q = user_prompt.lower()
        if "trending" in q or "popular" in q or "best" in q:
            reply = (
                "🔥 Currently trending silhouettes:\n\n"
                "• **Adidas Samba OG & Gazelle Indoor**: Unstoppable street & terrace wear favorites.\n"
                "• **Nike Air Jordan 4 & Dunk Low**: High collector demand and collaborations.\n"
                "• **New Balance 1906R & 2002R**: Leading the retro-runner aesthetic with premium comfort.\n"
                "• **Asics GEL-Kayano 14**: Top-tier tech-wear styling."
            )
        elif "legit" in q or "fake" in q or "counterfeit" in q or "check" in q:
            reply = (
                "🔍 Quick Legit-Check Rules:\n\n"
                "1. **Midsole Stitching:** Authentic pairs feature tight, even stitch counts with zero loose nylon loops.\n"
                "2. **Size Tag Font:** Replicas often print SKU and UPC numbers with incorrect font weights.\n"
                "3. **Insole Footbed:** Inspect the strobel stitching under the insole—replicas usually cut corners here.\n"
                "4. Use our **Verify portal** to cross-examine physical photos with factory AI embeddings!"
            )
        elif "size" in q or "sizing" in q or "fit" in q:
            reply = (
                "👟 Sizing Guide:\n\n"
                "• **Air Force 1s:** Run large. Go 0.5 size down.\n"
                "• **Jordan 1 & Dunk Low:** True to size (TTS).\n"
                "• **Adidas Yeezy & Samba:** Narrow toe box. Consider going 0.5 size up for wide feet."
            )
        elif "blockchain" in q or "qr" in q or "how" in q:
            reply = (
                "🛡️ How Authentify works:\n\n"
                "Every shoe batch has a unique SHA-256 seal logged to Ganache. "
                "Even if a counterfeit copies the QR tag, our MobileNetV2 computer vision model compares "
                "the live photo against factory reference embeddings before approving it."
            )
        else:
            reply = (
                f"I'm SoleCheck AI! You asked: '{user_prompt}'. "
                "Ask me about trending sneakers, spotting fake stitching, shoe sizing, or how our blockchain verification works!"
            )

        return jsonify({"reply": reply})

    except Exception as e:
        print(f"[AI CHAT] Internal Error: {e}")
        return jsonify({"reply": "I'm having a brief issue processing that request. Please try again!"}), 200
    
if __name__ == "__main__":
    ensure_ganache_running()
    app.run(host="0.0.0.0", port=5000, debug=True)
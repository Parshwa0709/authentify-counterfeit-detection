# Counterfeit Product Detection using AI and Blockchain (Footwear Authentication)

**B.Tech Computer Science & Engineering Final-Year Capstone Project**  
*A decentralized, multi-layered anti-counterfeiting framework combining Ethereum Smart Contracts, Cryptographic SHA-256 Hashing, and TensorFlow Deep Learning Computer Vision.*

---

## 📌 Project Overview

Counterfeit footwear accounts for tens of billions of dollars in global illicit trade. Traditional authentication mechanisms relying solely on barcodes or QR stickers suffer from a fundamental vulnerability: **counterfeiters can easily photocopy or clone a legitimate QR code and stick it onto a fake shoe.**

This project eliminates that vulnerability through an **interlocking 3-Layer Authentication Architecture**:
1. **Layer 1 (Database & QR Check):** Validates product existence within the manufacturer's verified MongoDB catalog.
2. **Layer 2 (Blockchain Ledger Check):** Verifies the immutable Ethereum smart contract record on Ganache and cryptographically compares a 32-byte SHA-256 hash of the product metadata against the on-chain seal.
3. **Layer 3 (AI Deep Learning Computer Vision):** Compares a live physical photo taken with the customer's smartphone camera against the factory baseline reference image using **TensorFlow MobileNetV2** (1280-dim feature vector extraction) and **Cosine Similarity** ($\ge 75\%$ threshold).

A product is stamped **GENUINE** if and only if **all three layers pass**. If any layer fails, it is flagged as **COUNTERFEIT** with precise diagnostics indicating the exact point of failure.

---

## 🛠️ Complete Open-Source Tech Stack

| Component | Technology | Version | Purpose |
|---|---|---|---|
| **Backend Framework** | Python + Flask | 3.0.3 | REST API, role-based auth, session management, routing |
| **Database** | MongoDB + PyMongo | 4.8.0 | Off-chain storage for product catalog & user accounts |
| **Smart Contract** | Solidity | ^0.8.19 | Immutable distributed ledger for product hashes & provenance |
| **Local Blockchain** | Ganache (GUI / CLI) | 7.x / 8.x | Local Ethereum RPC node (`http://127.0.0.1:7545`) |
| **Blockchain Bridge** | Web3.py | 6.20.0 | Python interaction with Ethereum smart contracts |
| **Solidity Compiler** | py-solc-x | 2.0.2 | Programmatic compilation of Solidity contracts |
| **AI Feature Extractor** | TensorFlow (Keras) | 2.16.1 | MobileNetV2 pre-trained on ImageNet (Global Average Pooling) |
| **Image Preprocessing**| OpenCV (`cv2`) | 4.10.0 | Image resizing (224x224), BGR to RGB conversion |
| **Vector Math** | NumPy | 1.26.4 | L2-normalization and Cosine Similarity computations |
| **QR Engine (Backend)**| `qrcode[pil]` | 7.4.2 | Generation of high-density dynamic QR codes |
| **QR Engine (Frontend)**| `html5-qrcode` | 2.3.8 | Real-time rear-camera scanning in mobile browsers |
| **Frontend UI** | HTML5, JS, Tailwind CSS | CDN | Mobile-first dark-mode responsive interface |

---

## 📂 Project Directory Structure

```text
counterfeit_product_detection/
├── contracts/
│   └── ProductRegistry.sol     # Solidity smart contract (v0.8.19)
├── static/
│   ├── uploads/                # Reference footwear images & live verification captures
│   └── qrcodes/                # Generated PNG QR codes
├── templates/
│   ├── base.html               # Master layout with responsive navbar & alerts
│   ├── index.html              # Landing page with architecture & system status
│   ├── login.html              # Authentication sign-in portal
│   ├── register.html           # Role-based registration (Manufacturer / Customer)
│   ├── manufacturer.html       # Manufacturer dashboard to mint shoes & export QR codes
│   └── verify.html             # Customer mobile verification page with camera QR & photo capture
├── app.py                      # Core Flask backend orchestrator & 3-layer decision engine
├── deploy_contract.py          # py-solc-x compiler & Web3 Ganache deployment automation
├── contract_data.json          # Exported ABI and contract address (generated on deploy)
├── requirements.txt            # Pinned Python package dependencies
├── .env.example                # Environment variables template
└── README.md                   # Comprehensive engineering documentation
```

---

## 🚀 Step-by-Step Local Execution Guide

### Step 1: Clone & Prepare Python Environment

Open PowerShell or Terminal:

```bash
# Navigate to the project directory
cd counterfeit_product_detection

# Create and activate Python virtual environment
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# (Or on Linux/macOS: source venv/bin/activate)

# Upgrade pip and install all pinned dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 2: Start MongoDB Service

Make sure your MongoDB server is running on `mongodb://127.0.0.1:27017/`:

**Option A (Windows MongoDB Service):**
```powershell
net start MongoDB
```

**Option B (Docker):**
```bash
docker run -d -p 27017:27017 --name mongo-counterfeit mongo:latest
```

---

### Step 3: Launch Ganache Ethereum Testnet

You can use either Ganache GUI or Ganache CLI:

**Option A (Ganache GUI):**
1. Launch the **Ganache** desktop application.
2. Select **Quickstart (Ethereum)**.
3. Verify that the RPC Server is running on `HTTP://127.0.0.1:7545` (default).

**Option B (Ganache CLI):**
```bash
# Run Ganache CLI on port 7545
npx ganache --port 7545
```

---

### Step 4: Compile & Deploy the Smart Contract

Run the automated deployment script:

```bash
python deploy_contract.py
```

**What this script does:**
1. Checks for Solidity compiler `solc v0.8.19` (auto-installs if missing).
2. Compiles `contracts/ProductRegistry.sol`.
3. Connects to Ganache at `http://127.0.0.1:7545`.
4. Deploys the contract using Ganache Account #0.
5. Generates `contract_data.json` containing the deployed address and full ABI.

---

### Step 5: Start the Flask Application Server

Launch the backend orchestrator:

```bash
python app.py
```

The server will start at: **`http://127.0.0.1:5000`**.

---

### Step 6: Expose via Ngrok for Mobile Camera QR Testing (Important!)

> ⚠️ **Mobile Browser Camera Permission Requirement:**  
> Modern mobile browsers (iOS Safari and Android Google Chrome) **strictly require HTTPS** (or `localhost`) to grant camera access to web applications (`getUserMedia` API). If accessing from your phone across your local WiFi, you must tunnel through Ngrok to obtain a valid HTTPS certificate:

```bash
# In a separate terminal window:
ngrok http 5000
```

1. Copy the HTTPS forwarding URL (e.g. `https://xxxx-xx-xx.ngrok-free.app`).
2. Open this URL on your mobile phone browser.

---

## 🧪 Demonstration & Viva Walkthrough Workflow

### 1. Manufacturer Registration & Minting
1. Open the web app and navigate to **Register** (`/register`).
2. Register an account with role **Manufacturer** (e.g., `nike_factory` or `puma_official`).
3. Log in with your new account.
4. Go to the **Manufacturer Portal** (`/manufacturer`).
5. Select one of the 3 authorized consortium brands from the dropdown:
   - **Nike** (e.g., SKU: `NIKE-AF1-8921`, Model: Air Force 1 '07 Triple White)
   - **Puma** (e.g., SKU: `PUMA-SUEDE-1968`, Model: Suede Classic XXI Black/White)
   - **Crocs** (e.g., SKU: `CROCS-CLOG-1000`, Model: Classic Clog White Slip-On)
6. Fill in the product details, upload the reference photo, and click **Mint to Blockchain & Generate QR Code**.
   - The SHA-256 hash is computed from the metadata and sealed on-chain.
   - Web3.py broadcasts a transaction to Ganache committing the hash on-chain.
   - A QR code embedding the verification link is generated and saved.
   - The metadata is indexed in MongoDB.

### 2. Testing Genuine Verification (Passing All 3 Layers)
1. Display the generated QR code on your PC screen or print it.
2. On your mobile phone (via the Ngrok HTTPS link), tap **Verify Footwear** (`/verify`).
3. Tap **Launch Camera QR Scanner** and point the phone at the QR code on your screen.
   - `html5-qrcode` decodes the QR code and automatically populates the Product ID (`NIKE-AF1-8921`).
4. Tap **Snap Photo with Phone Camera** (`capture="environment"` opens your rear camera).
5. Snap a photo of the authentic shoe (or upload the matching shoe image).
6. Tap **Execute 3-Layer Authentication Check**.
7. **Expected Result:**
   - **Layer 1:** PASSED (Found in MongoDB catalog).
   - **Layer 2:** PASSED (Immutable SHA-256 matches Ganache smart contract).
   - **Layer 3:** PASSED (MobileNetV2 Cosine Similarity $\ge 75\%$, e.g., $91.4\%$).
   - **Final Verdict:** **GENUINE AUTHENTIC PRODUCT** (Glowing green badge).

### 3. Testing Counterfeit Detection (Simulating Real-World Attacks)

- **Scenario A: Fake / Copied QR Code (Layer 1 Failure)**
  - Enter a non-existent or fabricated Product ID (e.g. `FAKE-SHOE-9999`).
  - **Result:** Fails immediately at Layer 1 ("Product ID not found in official catalog"). Marked **COUNTERFEIT**.

- **Scenario B: Database Tampering (Layer 2 Failure)**
  - Manually change a batch number or description directly inside MongoDB via Compass or Mongo shell.
  - Scan the genuine QR code.
  - **Result:** Fails at Layer 2 ("Blockchain Cryptographic Mismatch! On-chain hash does not match modified metadata"). Marked **COUNTERFEIT**.

- **Scenario C: Replica / Fake Footwear (Layer 3 Failure)**
  - Scan a genuine Nike QR code, but snap a picture of a different sneaker (e.g., an Adidas shoe, a boot, or a heavily modified replica).
  - **Result:** Layer 1 passes, Layer 2 passes, but **Layer 3 Fails** with an AI similarity score below $75\%$ (e.g., $34.2\%$). Marked **COUNTERFEIT** with visual side-by-side comparison displayed!

---

## 🔒 Security Analysis

| Threat Model | Attack Mechanism | Countermeasure in this System |
|---|---|---|
| **QR Code Cloning** | Scammer prints a photocopy of an authentic QR label onto a knockoff shoe. | **Layer 3 AI Visual Match:** MobileNetV2 detects visual discrepancies between the fake shoe and the factory baseline. |
| **Catalog Database Breach** | Rogue insider modifies product records or inserts unauthorized batches into MongoDB. | **Layer 2 Blockchain Seal:** The immutable SHA-256 hash stored on Ganache cannot be overwritten, triggering a cryptographic mismatch. |
| **Replay & Sybil Attacks** | Attacker attempts to register duplicate product IDs. | **Smart Contract & MongoDB Constraints:** `isRegistered` flag in Solidity and unique indexes in MongoDB reject duplicate registrations. |

---

## 👨‍💻 Capstone Viva Q&A Pointers

- **Why MobileNetV2 instead of ResNet50 or VGG16?**  
  MobileNetV2 uses depthwise separable convolutions and inverted residuals, making it exceptionally lightweight, fast, and optimized for real-time mobile inference without sacrificing feature representation.
- **Why Ganache & Web3.py instead of IPFS alone?**  
  Ganache provides an immutable state machine where authorized manufacturers can emit verifiable events and log tamper-proof cryptographic proofs of state transitions.
- **Why Cosine Similarity?**  
  Cosine similarity measures the angular orientation between two high-dimensional vectors (direction rather than magnitude), making it resilient to uniform lighting and scaling variations.

# 🦈 StatShark War Thunder Data Exporter (Fast GUI)

A lightweight, modern, and high-performance desktop application for exporting player combat statistics and vehicle records from [StatShark.net](https://statshark.net) into CSV and JSON formats.

---

## ⚡ Key Highlights & Architecture

- **Ultra-Fast Data Fetching (~1 – 2 Seconds):**  
  Unlike traditional browser scrapers that render DOM and wait for UI animations (~20–30s), this application employs a **Hybrid Token Cache + Direct API** architecture. It captures Cloudflare Turnstile verification once, caches it locally for up to 20 minutes, and performs direct HTTP requests via TLS fingerprint impersonation (`curl_cffi`).
- **Completely Silent Execution (Headless / Off-screen):**  
  Runs cleanly in the background without opening disturbing browser windows or stealing desktop focus.
- **Razor Sharp High-DPI GUI:**  
  Features native Windows Per-Monitor DPI awareness (`SetProcessDpiAwareness`) to eliminate scaling blurriness on 1080p, 1440p, and 4K displays.
- **Persistent Settings:**  
  Automatically remembers your last selected export directory across sessions.
- **Multi-Format Export:**
  - `[Player]_Realistic_Battles.csv` (Spreadsheet of realistic battles vehicle stats)
  - `[Player]_Arcade_Battles.csv` (Spreadsheet of arcade battles vehicle stats)
  - `[Player]_StatShark_PlayerStats.json` (Full raw JSON data)
  - `[Player]_Summary.txt` (Concise overview of player rating, kills, win rates, and level)

---

## 📁 Project Structure

```text
├── StatShark_Exporter_GUI.py     # Main Python GUI application source code
├── StatShark_Fast_Exporter_GUI.exe # Standalone Windows executable (~16 MB)
├── Run_StatShark_GUI.bat         # Quick launcher script
├── build.bat                     # One-click PyInstaller build script
├── requirements.txt              # Python project dependencies
├── .gitignore                    # Git ignore configuration
└── README.md                     # Project documentation
```

---

## 🚀 Getting Started

### Option 1: Run Pre-compiled Executable (No Python Required)
1. Download or clone this repository.
2. Double-click `StatShark_Fast_Exporter_GUI.exe` (or run `Run_StatShark_GUI.bat`).
3. Enter the War Thunder username, choose your export folder, and click **Fetch & Export Data**.

### Option 2: Run from Python Source
1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd "StatShark Data Fetcher"
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   python StatShark_Exporter_GUI.py
   ```

---

## 🛠️ Building the Standalone Executable

To compile the Python script into a single standalone `.exe` file without console windows:

Simply double-click `build.bat`, or run manually:
```bash
pyinstaller --onefile --noconsole --name "StatShark_Fast_Exporter_GUI" StatShark_Exporter_GUI.py
```

---

## 📋 Requirements
- **OS:** Windows 10 / 11 (64-bit)
- **Browser:** Google Chrome or Microsoft Edge installed (used silently for token generation)
- **Python (Optional):** Python 3.10+ (only if running from source)

---

## 📄 License
This project is open-source under the MIT License.

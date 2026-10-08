"""
StatShark War Thunder Data Exporter (Ultra Fast GUI Edition)
High-DPI Razor Sharp UI with Persistent Settings and Direct API Caching.
"""

import sys
import os
import json
import csv
import time
import asyncio
import threading
import subprocess
import urllib.request
from pathlib import Path
import socket
import websockets
from curl_cffi import requests

# Enable High-DPI Awareness for Windows to eliminate blurriness
if os.name == 'nt':
    try:
        import ctypes
        # Try Per-Monitor V2 (2), fallback to System DPI (1)
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Configuration and Cache Paths
CONFIG_FILE = os.path.join(os.environ.get("LOCALAPPDATA", str(Path.home())), "statshark_gui_config.json")
CACHE_FILE = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "statshark_token_cache.json")
TOKEN_TTL = 1200 # 20 minutes (StatShark server TTL is 25 minutes)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

def load_cached_token():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            if time.time() - d.get("timestamp", 0) < TOKEN_TTL:
                return d.get("token")
        except Exception:
            pass
    return None

def save_token(token):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"token": token, "timestamp": time.time()}, f)
    except Exception:
        pass

def find_browser():
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def get_free_port():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]
    except Exception:
        return 9338

def clean_country(c_str):
    if not c_str:
        return ""
    if c_str.startswith("country_"):
        return c_str[len("country_"):].upper()
    return c_str

def format_kd(kills, deaths):
    try:
        deaths = int(deaths)
        kills = int(kills)
        if deaths == 0:
            return f"{kills:.2f}"
        return f"{(kills / deaths):.2f}"
    except Exception:
        return "0.00"

async def acquire_fresh_token(browser_path, log_cb):
    port = get_free_port()
    user_data = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "statshark_cache_profile")
    os.makedirs(user_data, exist_ok=True)

    log_cb("[1/3] Refreshing StatShark security token in background...")
    cmd = [
        browser_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data}",
        "--window-position=-32000,-32000",
        "--window-size=800,600",
        "--disable-notifications",
        "--mute-audio",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank"
    ]
    
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

    proc = subprocess.Popen(cmd, startupinfo=startupinfo)
    try:
        ws_url = None
        for _ in range(30):
            try:
                resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=0.3)
                tabs = json.loads(resp.read().decode('utf-8'))
                page_tab = next((t for t in tabs if t.get("type") == "page"), tabs[0])
                ws_url = page_tab["webSocketDebuggerUrl"]
                break
            except Exception:
                await asyncio.sleep(0.1)

        if not ws_url:
            raise Exception("Failed to connect to browser debugging port.")

        async with websockets.connect(ws_url) as ws:
            msg_id = 1
            async def send(method, params=None):
                nonlocal msg_id
                cid = msg_id
                msg_id += 1
                await ws.send(json.dumps({"id": cid, "method": method, "params": params or {}}))
                while True:
                    raw = await ws.recv()
                    data = json.loads(raw)
                    if data.get("id") == cid:
                        return data.get("result", {})

            await send("Page.enable")
            await send("Network.enable")
            await send("Page.navigate", {"url": "https://statshark.net"})

            token = None
            t0 = time.time()
            while not token and time.time() - t0 < 15:
                raw = await asyncio.wait_for(ws.recv(), timeout=8)
                data = json.loads(raw)
                if data.get("method") == "Network.requestWillBeSent":
                    h = data.get("params", {}).get("request", {}).get("headers", {})
                    for k, v in h.items():
                        if k.lower() == "x-turnstile-token":
                            token = v
                            break

            if not token:
                raise Exception("Timed out waiting for Cloudflare Turnstile verification token.")

            save_token(token)
            log_cb("      Security token captured & cached (valid for 20 minutes)!")
            return token
    finally:
        try:
            proc.kill()
        except Exception:
            pass

def fetch_data_direct(browser_path, username, uid_input=None, log_cb=None):
    if log_cb is None:
        log_cb = lambda msg: None

    token = load_cached_token()
    if token:
        log_cb("[1/3] Using cached session token (ultra-fast)...")
    else:
        log_cb("[1/3] Session token missing or expired. Acquiring fresh token...")
        token = asyncio.run(acquire_fresh_token(browser_path, log_cb))

    def make_api_calls(active_token):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://statshark.net/",
            "Origin": "https://statshark.net",
            "X-Turnstile-Token": active_token
        }
        session = requests.Session(impersonate="chrome124")

        target_uid = uid_input.strip() if uid_input and uid_input.strip() else None

        if not target_uid:
            log_cb(f"[2/3] Searching UID for player '{username}' via API...")
            search_url = f"https://statshark.net/api/stat/GetIdByName?Name={username}&IgnoreCase=true&MaxCount=5&Details=false"
            res = session.get(search_url, headers=headers)
            if res.status_code in (401, 406):
                return False, "TOKEN_EXPIRED"
            if res.status_code != 200:
                raise Exception(f"Player search failed with HTTP status {res.status_code}")
            
            data_map = res.json()
            if not data_map:
                raise Exception(f"Player '{username}' was not found on StatShark.")
            target_uid = list(data_map.keys())[0]
            matched_name = data_map[target_uid]
            log_cb(f"      Matched UID: {target_uid} ({matched_name})")
        else:
            log_cb(f"[2/3] Using direct UID: {target_uid}")

        log_cb("[3/3] Downloading player statistics via API...")
        stat_url = f"https://statshark.net/api/stat/makestatrequestbyid/{target_uid}"
        stat_res = session.post(stat_url, headers=headers, json={})
        if stat_res.status_code in (401, 406):
            return False, "TOKEN_EXPIRED"
        if stat_res.status_code != 200:
            raise Exception(f"Failed to fetch stats with HTTP status {stat_res.status_code}")

        result_data = stat_res.json()
        if not result_data or "Basics" not in result_data:
            raise Exception("Received empty or invalid player statistics payload.")

        return True, (target_uid, result_data)

    success, payload = make_api_calls(token)
    if not success and payload == "TOKEN_EXPIRED":
        log_cb("[INFO] Token expired during request. Auto-refreshing...")
        token = asyncio.run(acquire_fresh_token(browser_path, log_cb))
        success, payload = make_api_calls(token)
        if not success:
            raise Exception("API request rejected even after refreshing token.")

    return payload

def export_files(out_dir, raw_data, uid, options, log_cb):
    basics = raw_data.get("Basics", {})
    profile = raw_data.get("Profile", {})
    vehicles = raw_data.get("Vehicles", [])
    
    clean_name = basics.get("nickname", f"User_{uid}")
    safe_name = "".join(c for c in clean_name if c.isalnum() or c in (' ', '_', '-')).strip()
    if not safe_name:
        safe_name = f"User_{uid}"

    exported_files = []

    # 1. Raw JSON
    if options.get("export_json", True):
        json_path = os.path.join(out_dir, f"{safe_name}_StatShark_PlayerStats.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)
        exported_files.append(json_path)
        log_cb(f" -> Raw JSON          : {os.path.basename(json_path)}")

    csv_headers = [
        "Rank", "Country", "Vehicle Name", "Victories", "Battles",
        "Winrate (%)", "Respawns", "Deaths", "Air Kills", "Ground Kills",
        "Naval Kills", "Score", "Time Played (s)", "Type", "Branch",
        "Vehicle ID", "K/D Ratio"
    ]

    def write_csv(filepath, v_list):
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(csv_headers)
            for row in v_list:
                if not isinstance(row, list) or len(row) < 16:
                    continue
                deaths = row[7] if len(row) > 7 else 0
                g_kills = row[9] if len(row) > 9 else 0
                a_kills = row[8] if len(row) > 8 else 0
                n_kills = row[10] if len(row) > 10 else 0
                total_kills = g_kills + a_kills + n_kills
                kd_val = format_kd(total_kills, deaths)

                formatted_row = [
                    row[0],
                    clean_country(row[1]),
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                    row[6],
                    row[7],
                    row[8],
                    row[9],
                    row[10],
                    row[11],
                    row[12],
                    row[13],
                    row[14],
                    row[15],
                    kd_val
                ]
                writer.writerow(formatted_row)

    # 2. Realistic Battles CSV
    if options.get("export_rb", True) and len(vehicles) > 1:
        rb_path = os.path.join(out_dir, f"{safe_name}_Realistic_Battles.csv")
        write_csv(rb_path, vehicles[1])
        exported_files.append(rb_path)
        log_cb(f" -> Realistic (RB) CSV: {os.path.basename(rb_path)}")

    # 3. Arcade Battles CSV
    if options.get("export_ab", True) and len(vehicles) > 0:
        ab_path = os.path.join(out_dir, f"{safe_name}_Arcade_Battles.csv")
        write_csv(ab_path, vehicles[0])
        exported_files.append(ab_path)
        log_cb(f" -> Arcade (AB) CSV   : {os.path.basename(ab_path)}")

    # 4. Summary TXT
    if options.get("export_summary", True):
        sum_path = os.path.join(out_dir, f"{safe_name}_Summary.txt")
        rb_pvp = profile.get("rb", {}).get("pvp_played", {})
        ab_pvp = profile.get("arcade", {}).get("pvp_played", {})
        
        rb_games = rb_pvp.get("games", 0)
        rb_wins = rb_pvp.get("wins", 0)
        rb_wr = (rb_wins / rb_games * 100) if rb_games > 0 else 0.0

        ab_games = ab_pvp.get("games", 0)
        ab_wins = ab_pvp.get("wins", 0)
        ab_wr = (ab_wins / ab_games * 100) if ab_games > 0 else 0.0

        rb_vehicles = len(vehicles[1]) if len(vehicles) > 1 else 0
        ab_vehicles = len(vehicles[0]) if len(vehicles) > 0 else 0

        summary_content = (
            f"=== STATSHARK WAR THUNDER PLAYER PROFILE ===\n"
            f"Username     : {basics.get('nickname', clean_name)}\n"
            f"User ID (UID): {basics.get('uid', uid)}\n"
            f"Squadron     : {basics.get('SquadronName', '-')}\n"
            f"Level        : {basics.get('level', '-')}\n"
            f"Title        : {basics.get('title', '-')}\n"
            f"Ban Status   : {basics.get('banStatus', '-')}\n"
            f"Last Updated : {basics.get('lastupdate', '-')}\n\n"
            f"=== REALISTIC BATTLES (RB) ===\n"
            f"Total Battles: {rb_games:,}\n"
            f"Victories    : {rb_wins:,} ({rb_wr:.2f}%)\n"
            f"Ground Kills : {rb_pvp.get('groundKillsP', 0):,}\n"
            f"Air Kills    : {rb_pvp.get('airKillsP', 0):,}\n"
            f"Vehicles Used: {rb_vehicles}\n\n"
            f"=== ARCADE BATTLES (AB) ===\n"
            f"Total Battles: {ab_games:,}\n"
            f"Victories    : {ab_wins:,} ({ab_wr:.2f}%)\n"
            f"Ground Kills : {ab_pvp.get('groundKillsP', 0):,}\n"
            f"Air Kills    : {ab_pvp.get('airKillsP', 0):,}\n"
            f"Vehicles Used: {ab_vehicles}\n"
        )
        with open(sum_path, "w", encoding="utf-8") as f:
            f.write(summary_content)
        exported_files.append(sum_path)
        log_cb(f" -> Summary Text      : {os.path.basename(sum_path)}")

    return exported_files

class StatSharkApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("StatShark War Thunder Data Exporter")
        self.geometry("680x700")
        self.minsize(620, 640)

        self.configure(bg="#1e1e2e")
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        self.bg_color = "#1e1e2e"
        self.card_bg = "#252538"
        self.text_color = "#cdd6f4"
        self.accent_color = "#89b4fa"
        self.success_color = "#a6e3a1"
        self.error_color = "#f38ba8"

        self.cfg = load_config()
        self.last_export_dir = self.cfg.get("last_save_dir", str(Path.home() / "Desktop"))

        self._setup_ui()

    def _setup_ui(self):
        # Header
        header = tk.Frame(self, bg=self.bg_color, pady=12)
        header.pack(fill="x")

        lbl_title = tk.Label(
            header, 
            text="⚡ StatShark WT Fast Data Exporter", 
            font=("Segoe UI", 16, "bold"), 
            fg=self.accent_color, 
            bg=self.bg_color
        )
        lbl_title.pack()

        lbl_sub = tk.Label(
            header, 
            text="Fast player profile & vehicle stats exporter via StatShark API (~1-2 seconds)", 
            font=("Segoe UI", 9), 
            fg="#a6adc8", 
            bg=self.bg_color
        )
        lbl_sub.pack()

        # Input Card
        card = tk.LabelFrame(
            self, 
            text=" Search Parameters & Output Settings ", 
            font=("Segoe UI", 10, "bold"),
            fg=self.accent_color, 
            bg=self.card_bg, 
            bd=1, 
            relief="solid",
            padx=16, 
            pady=14
        )
        card.pack(fill="x", padx=18, pady=6)

        # 1. Username (starts completely blank without placeholder)
        tk.Label(card, text="War Thunder Username:", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.card_bg).grid(row=0, column=0, sticky="w", pady=5)
        self.ent_username = tk.Entry(card, font=("Segoe UI", 10), bg="#313244", fg="#ffffff", insertbackground="#ffffff", relief="flat")
        self.ent_username.grid(row=0, column=1, columnspan=2, sticky="ew", pady=5, ipady=4)

        # 2. Player ID (UID)
        tk.Label(card, text="User ID / UID (Optional):", font=("Segoe UI", 9), fg=self.text_color, bg=self.card_bg).grid(row=1, column=0, sticky="w", pady=5)
        self.ent_uid = tk.Entry(card, font=("Segoe UI", 10), bg="#313244", fg="#ffffff", insertbackground="#ffffff", relief="flat")
        self.ent_uid.grid(row=1, column=1, columnspan=2, sticky="ew", pady=5, ipady=4)

        # 3. Save Directory (remembers last saved location)
        tk.Label(card, text="Save Location:", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.card_bg).grid(row=2, column=0, sticky="w", pady=5)
        self.ent_dir = tk.Entry(card, font=("Segoe UI", 10), bg="#313244", fg="#ffffff", insertbackground="#ffffff", relief="flat")
        self.ent_dir.grid(row=2, column=1, sticky="ew", pady=5, ipady=4)
        
        # Load remembered directory
        saved_dir = self.last_export_dir if os.path.exists(self.last_export_dir) else str(Path.home() / "Desktop")
        self.ent_dir.insert(0, saved_dir)

        btn_browse = tk.Button(
            card, 
            text="📁 Browse...", 
            font=("Segoe UI", 9), 
            bg="#45475a", 
            fg="#ffffff", 
            activebackground="#585b70",
            relief="flat",
            cursor="hand2",
            command=self._browse_dir
        )
        btn_browse.grid(row=2, column=2, padx=(8, 0), pady=5)

        card.columnconfigure(1, weight=1)

        # Export Options Card
        opt_frame = tk.Frame(self, bg=self.bg_color, pady=4)
        opt_frame.pack(fill="x", padx=18)

        self.var_rb = tk.BooleanVar(value=True)
        self.var_ab = tk.BooleanVar(value=True)
        self.var_json = tk.BooleanVar(value=True)
        self.var_summary = tk.BooleanVar(value=True)

        cb_style = {"bg": self.bg_color, "fg": self.text_color, "selectcolor": "#313244", "activebackground": self.bg_color, "font": ("Segoe UI", 9)}
        tk.Checkbutton(opt_frame, text="Realistic Battles (RB) CSV", variable=self.var_rb, **cb_style).pack(side="left", padx=4)
        tk.Checkbutton(opt_frame, text="Arcade Battles (AB) CSV", variable=self.var_ab, **cb_style).pack(side="left", padx=4)
        tk.Checkbutton(opt_frame, text="Raw JSON", variable=self.var_json, **cb_style).pack(side="left", padx=4)
        tk.Checkbutton(opt_frame, text="Summary TXT", variable=self.var_summary, **cb_style).pack(side="left", padx=4)

        # Action Button
        action_frame = tk.Frame(self, bg=self.bg_color, pady=8)
        action_frame.pack(fill="x", padx=18)

        self.btn_start = tk.Button(
            action_frame, 
            text="🚀 Fetch & Export Data", 
            font=("Segoe UI", 11, "bold"),
            bg="#a6e3a1", 
            fg="#11111b", 
            activebackground="#94e2d5",
            relief="flat",
            cursor="hand2",
            pady=7,
            command=self._start_fetch
        )
        self.btn_start.pack(fill="x")

        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=18, pady=(0, 6))

        # Log & Status Box
        log_card = tk.LabelFrame(
            self, 
            text=" Activity Log & Status ", 
            font=("Segoe UI", 9, "bold"),
            fg=self.accent_color, 
            bg=self.card_bg, 
            bd=1, 
            relief="solid",
            padx=8, 
            pady=8
        )
        log_card.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        self.txt_log = tk.Text(
            log_card, 
            font=("Consolas", 9), 
            bg="#181825", 
            fg="#cdd6f4", 
            relief="flat",
            wrap="word",
            padx=8,
            pady=8
        )
        self.txt_log.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(log_card, command=self.txt_log.yview)
        scrollbar.pack(side="right", fill="y")
        self.txt_log.config(yscrollcommand=scrollbar.set)

        # Bottom Bar
        bottom_frame = tk.Frame(self, bg=self.bg_color, pady=4)
        bottom_frame.pack(fill="x", padx=18, pady=(0, 10))

        self.btn_open_folder = tk.Button(
            bottom_frame,
            text="📂 Open Output Folder",
            font=("Segoe UI", 9),
            bg="#313244",
            fg="#cdd6f4",
            state="disabled",
            relief="flat",
            cursor="hand2",
            command=self._open_output_folder
        )
        self.btn_open_folder.pack(side="right")

        self.log("[READY] Ready. Token Cache system active.")

    def log(self, msg):
        def _append():
            self.txt_log.insert("end", msg + "\n")
            self.txt_log.see("end")
        self.after(0, _append)

    def _browse_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.ent_dir.get(), title="Select Output Folder")
        if chosen:
            self.ent_dir.delete(0, "end")
            self.ent_dir.insert(0, chosen)
            self.last_export_dir = chosen
            self.cfg["last_save_dir"] = chosen
            save_config(self.cfg)

    def _open_output_folder(self):
        if self.last_export_dir and os.path.exists(self.last_export_dir):
            if os.name == 'nt':
                os.startfile(self.last_export_dir)
            else:
                subprocess.run(["xdg-open", self.last_export_dir])

    def _set_busy(self, is_busy):
        if is_busy:
            self.btn_start.config(state="disabled", text="⏳ Processing Data...", bg="#45475a", fg="#a6adc8")
            self.progress.start(10)
        else:
            self.btn_start.config(state="normal", text="🚀 Fetch & Export Data", bg="#a6e3a1", fg="#11111b")
            self.progress.stop()

    def _start_fetch(self):
        username = self.ent_username.get().strip()
        uid = self.ent_uid.get().strip()
        out_dir = self.ent_dir.get().strip()

        if not username and not uid:
            messagebox.showwarning("Input Required", "Please enter a War Thunder Username or User ID (UID)!")
            return

        if not out_dir:
            messagebox.showwarning("Input Required", "Please select an output folder location!")
            return

        if not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create output folder:\n{e}")
                return

        # Save last used directory to persistent config
        self.last_export_dir = out_dir
        self.cfg["last_save_dir"] = out_dir
        save_config(self.cfg)

        browser = find_browser()
        if not browser:
            messagebox.showerror(
                "Browser Not Found", 
                "Neither Google Chrome nor Microsoft Edge was found on this computer.\n"
                "A browser is required for Cloudflare verification."
            )
            return

        options = {
            "export_rb": self.var_rb.get(),
            "export_ab": self.var_ab.get(),
            "export_json": self.var_json.get(),
            "export_summary": self.var_summary.get()
        }

        self._set_busy(True)
        self.btn_open_folder.config(state="disabled")
        self.log(f"\n--- Starting Data Fetch for: '{username or uid}' ---")

        threading.Thread(
            target=self._worker, 
            args=(browser, username, uid, out_dir, options), 
            daemon=True
        ).start()

    def _worker(self, browser, username, uid, out_dir, options):
        try:
            t_start = time.time()
            target_uid, data = fetch_data_direct(browser, username, uid_input=uid, log_cb=self.log)

            self.log("[SAVE] Writing export files to destination folder...")
            export_files(out_dir, data, target_uid, options, self.log)
            elapsed = time.time() - t_start

            self.after(0, lambda: self.btn_open_folder.config(state="normal", bg="#89b4fa", fg="#11111b"))
            self.log(f"[SUCCESS] All files exported successfully in {elapsed:.2f} seconds! ⚡")
            self.log(f"          Folder: {out_dir}")

            self.after(0, lambda: messagebox.showinfo(
                "Export Successful!", 
                f"Data successfully fetched and saved to:\n{out_dir}\n\nElapsed time: {elapsed:.2f} seconds!"
            ))
        except Exception as e:
            self.log(f"[ERROR] An error occurred: {e}")
            self.after(0, lambda: messagebox.showerror("Export Failed", f"An error occurred while processing data:\n{e}"))
        finally:
            self.after(0, lambda: self._set_busy(False))

if __name__ == "__main__":
    app = StatSharkApp()
    app.mainloop()

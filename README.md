# StatShark War Thunder Data Exporter

https://github.com/user-attachments/assets/9c82d707-cc25-4404-b2a9-556a74e362f4

## Download
Download the latest standalone executable from the [Releases](https://github.com/SwithinHalee/statshark-exporter/releases/latest) page (no Python installation required).

---

## What is this?
StatShark War Thunder Data Exporter is a desktop tool designed to quickly fetch and export War Thunder player profiles and vehicle statistics directly from StatShark.net.

It provides an intuitive graphical interface and a standalone executable (StatShark_Fast_Exporter_GUI.exe), allowing anyone to pull player records without needing manual web scraping or technical setup.

---

## What is it used for?
This tool is used to download comprehensive combat statistics and vehicle history for any War Thunder player, saving the information locally into structured files for spreadsheets, record-keeping, squadron management, or statistical analysis.

For each exported player, the app generates:
- **Realistic Battles CSV (`[Player]_Realistic_Battles.csv`):**  
  A spreadsheet containing every vehicle used in Realistic Battles (Rank, Country, Vehicle Name, Battles, Victories, Win Rate, Respawns, Deaths, Air Kills, Ground Kills, Naval Kills, Score, Time Played, and K/D Ratio).
- **Arcade Battles CSV (`[Player]_Arcade_Battles.csv`):**  
  A vehicle-by-vehicle breakdown for Arcade Battles.
- **Summary Text (`[Player]_Summary.txt`):**  
  A quick-read overview of player info (Level, Title, Squadron, Ban Status) and overall combat performance (total battles, victories, win rate %, and kills).
- **Raw JSON (`[Player]_StatShark_PlayerStats.json`):**  
  The full raw data payload from the StatShark API for developers and advanced data analysis.

---

## How it works
1. **Silent Background Authentication:**  
   StatShark is protected by Cloudflare security verification. The tool automatically resolves verification tokens in the background without displaying browser windows or disrupting your desktop.
2. **Direct API Fetching:**  
   Instead of slowly rendering the entire web page and simulating clicks, the tool queries StatShark's backend API directly to resolve player User IDs (UID) and download stats in approximately 1–2 seconds.
3. **Parsing and Local Storage:**  
   The returned data is automatically formatted into CSV spreadsheets, plain text summaries, and JSON files, then saved to your selected destination folder. The tool remembers your chosen save location for subsequent exports.

---

## How to use
1. Download and run `StatShark_Fast_Exporter_GUI.exe` from [Releases](https://github.com/SwithinHalee/statshark-exporter/releases/latest) (or double-click `Run_StatShark_GUI.bat`).
2. Enter the target War Thunder Username (User ID is optional).
3. Choose your Save Location (defaults to Desktop, or click Browse...).
4. Check the export formats you need (RB CSV, AB CSV, Raw JSON, Summary TXT).
5. Click Fetch & Export Data.
6. When completed, click Open Output Folder to immediately view your exported files.

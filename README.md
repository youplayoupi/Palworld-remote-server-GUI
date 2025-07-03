# Palworld Server Manager

A comprehensive GUI application for managing your Palworld server hosted on a VPS or dedicated linux server from a Windows workstation. This tool provides PalWorldSettings.ini configuration file management, Palworld REST API functionality & server control (start, stop, update).

---

## Features
- Download and edit server configuration files from your VPS
- Upload modified configurations back to the server
- Real-time server information and player management via REST API
- Server control: start, stop, restart, update, backup, and restore
- Auto-refresh and live player list monitoring
- SteamCMD update functionality
---

## Prerequisites

1. **PuTTY Tools** (Windows):
   - Download from: https://www.putty.org/
   - Or install via package manager: `winget install PuTTY.PuTTY`
   - The app will auto-detect common installation paths
   - If not found, you can manually configure paths in the app

2. **Python 3.7+**
3. **VPS Access**: Configured PuTTY session for your Ubuntu VPS
4. **Palworld Server**: Running with REST API enabled

---

## Installation

1. Clone or download this repository
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---
## Configuration

### 1. Basic Configuration
- Copy `config_template.py` to `config.py` and fill in your details.
- All sensitive information stays in `config.py` (never committed to git).

### 2. PuTTY Setup (Windows)
- Install PuTTY and set up a session for your VPS (see below for details).
- Use SSH key authentication for best security.

### 3. Palworld Server
- Enable REST API in your Palworld server configuration.
- Ensure the API is accessible on the configured port (default: 8212).

### 4. File Paths
- Update the following variables in `config.py` if your paths differ:
  - `REMOTE_CONFIG_PATH`: Path to PalWorldSettings.ini on your VPS
  - `LOCAL_CONFIG_PATH`: Local path for temporary config files (default: `downloads/PalWorldSettings.ini`)

---

## PuTTY Session Setup (Windows)

1. **Install PuTTY** (if not already installed):
   - Download from https://www.putty.org/
   - Default installation path: `C:\Program Files\PuTTY\`

2. **SSH Key Authentication Setup (Recommended):**
   - Convert your private key to `.ppk` format using PuTTYgen.
   - Create a PuTTY session with your VPS hostname/IP, port 22, and your `.ppk` key.
   - Save the session (e.g., "PalworldVPS").

3. **Password Authentication Setup (Alternative):**
   - Create session as above but skip the private key step.
   - PuTTY will prompt for password when needed.

4. **Test PuTTY Session:**
   - In PuTTY GUI, select your session and click "Open" to verify connection.

5. **App Configuration:**
   - Run the app: `python -m gui.main_app`
   - If PuTTY tools aren't auto-detected, a configuration dialog will appear.
   - Use the browse buttons to locate `plink.exe` and `pscp.exe` if needed.
   - Test the connection using the "Test Connection" button.

---

## Usage

1. **Run the application:**
   ```bash
   python -m gui.main_app
   ```

2. **Tabs Overview:**
   - **README:** Project info and instructions.
   - **Server Configuration:** Configure PuTTY, SteamCMD, and test connections.
   - **Palworld Settings:** Download, edit, and upload your PalWorldSettings.ini.
   - **API Control:** Configure API, test connection, view server info, manage players.
   - **Server Control:** Start/stop/restart/update server, view logs, backup/download saves.

3. **Common Actions:**
   - Download and edit server config.
   - Save and upload config to server.
   - Start, stop, or restart the server.
   - Update server via SteamCMD.
   - Backup and download the server's Saved folder (backups stored in `downloads/`).
   - Manage players (kick, ban, teleport).
   - Send announcements.

---

## Project Structure

```
project_root/
│
├── gui/
│   └── main_app.py           # Main GUI application
│
├── managers/
│   ├── api_manager.py
│   ├── config_manager.py
│   ├── palworld_config_manager.py
│   ├── server_manager.py
│   └── ssh_manager.py
│
├── downloads/                # Downloaded configs and backups (gitignored)
├── config_template.py        # Safe template for user config
├── config.py                 # Your actual config (not in repo)
├── requirements.txt          # Python dependencies
├── README.md
└── .gitignore
```

---

## Security Notes

- Store sensitive information (passwords, API keys) securely in `config.py` (never in the repo)
- Use SSH key authentication for VPS access
- The `downloads/` folder and `config.py` are gitignored by default

---

## Contributing

Feel free to submit issues and enhancement requests!

---

## Troubleshooting

### Connection Issues
- Verify PuTTY session configuration
- Check network connectivity to VPS
- Ensure SSH access is working

### API Issues
- Verify Palworld REST API is enabled
- Check API port configuration
- Ensure firewall allows API access

### Configuration Issues
- Verify file paths on VPS
- Check file permissions
- Ensure Palworld server is running

---

## License

This project is open source and available under the MIT License. 
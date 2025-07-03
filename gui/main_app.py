try:
    import ttkbootstrap as tb
    from ttkbootstrap.constants import *
except ImportError:
    raise ImportError("ttkbootstrap is not installed. Please run 'pip install ttkbootstrap' in your terminal.")
from tkinter import messagebox, scrolledtext, Listbox
import subprocess
import threading
import json
import os
from datetime import datetime
from typing import Optional
import posixpath

# Import our new modules
from managers.ssh_manager import SSHManager
from managers.api_manager import PalworldAPIManager
from managers.config_manager import ConfigManager
from managers.palworld_config_manager import PalworldConfigManager
from managers.server_manager import PalworldServerManager

class PalworldConfigApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Palworld Server Manager")
        
        # Initialize managers
        self.config_manager: ConfigManager = ConfigManager()
        self.palworld_config_manager: PalworldConfigManager = PalworldConfigManager()
        self.ssh_manager: Optional[SSHManager] = None
        self.api_manager: Optional[PalworldAPIManager] = None
        self.server_manager: Optional[PalworldServerManager] = None
        
        # Initialize SSH and API managers
        self.initialize_managers()
        
        # GUI state
        self.settings = {}
        self.inputs = {}
        self.auto_refresh_job = None

        # Create main layout: sidebar (left) and content (right)
        self.main_frame = tb.Frame(root)
        self.main_frame.pack(fill="both", expand=True)

        # Sidebar for navigation (add border for visibility)
        self.sidebar = tb.Frame(self.main_frame, borderwidth=2, relief="groove")
        self.sidebar.pack(side="left", fill="y")

        # Content area
        self.content_area = tb.Frame(self.main_frame)
        self.content_area.pack(side="left", fill="both", expand=True)

        # Create frames for each tab and call setup functions once
        self.readme_frame = tb.Frame(self.content_area)
        self.setup_readme_tab()
        self.readme_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.readme_frame.lower()

        self.config_frame = tb.Frame(self.content_area)
        self.setup_config_tab()
        self.config_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.config_frame.lower()

        self.palworld_settings_frame = tb.Frame(self.content_area)
        self.setup_palworld_settings_tab()
        self.palworld_settings_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.palworld_settings_frame.lower()

        self.api_frame = tb.Frame(self.content_area)
        self.setup_api_tab()
        self.api_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.api_frame.lower()

        self.server_frame = tb.Frame(self.content_area)
        self.setup_server_tab()
        self.server_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.server_frame.lower()

        # List of (icon, button text, frame)
        self.tabs = [
            ("📖", "README", self.readme_frame),
            ("🛠️", "Server Configuration", self.config_frame),
            ("📝", "Palworld Settings", self.palworld_settings_frame),
            ("🔌", "API Control", self.api_frame),
            ("🖥️", "Server Control", self.server_frame),
        ]

        self.tab_buttons = []
        for idx, (icon, text, frame) in enumerate(self.tabs):
            btn = tb.Button(self.sidebar, text=f"{icon} {text}", width=22, bootstyle="secondary", command=lambda i=idx: self.show_tab(i))
            btn.pack(fill="x", pady=2, padx=4)
            self.tab_buttons.append(btn)
        # Show the first tab by default
        self.show_tab(0)

        # Status and output console must be created before any setup_*_tab calls
        self.status = tb.StringVar()
        tb.Label(root, textvariable=self.status, foreground="blue").pack()

        self.output_console = scrolledtext.ScrolledText(root, height=10, width=80)
        self.output_console.pack(fill="both", expand=True, pady=5)
        self.output_console.insert(tb.END, "Console output will appear here...\n")
        self.output_console.config(state="disabled")

    def initialize_managers(self):
        """Initialize SSH and API managers"""
        # Initialize SSH manager
        plink_path = self.config_manager.get_plink_path()
        pscp_path = self.config_manager.get_pscp_path()
        session_name = self.config_manager.get_config("PUTTY_SESSION")
        
        if plink_path and pscp_path:
            self.ssh_manager = SSHManager(plink_path, pscp_path, session_name)
            
            # Configure direct connection if enabled
            if self.config_manager.get_config("USE_DIRECT_CONNECTION"):
                host = self.config_manager.get_config("SSH_HOST")
                port = self.config_manager.get_config("SSH_PORT")
                username = self.config_manager.get_config("SSH_USERNAME")
                if host and username:
                    self.ssh_manager.set_direct_connection(host, port, username)
        
        # Initialize API manager
        api_base = self.config_manager.get_config("PALWORLD_API_BASE")
        api_username = self.config_manager.get_config("PALWORLD_API_USERNAME")
        api_password = self.config_manager.get_config("PALWORLD_API_PASSWORD")
        
        if api_base and api_username and api_password:
            self.api_manager = PalworldAPIManager(api_base, api_username, api_password)
            
        # Initialize Server manager
        server_path = self.config_manager.get_config("SERVER_PATH") or "~/Steam/steamapps/common/PalServer"
        screen_session = self.config_manager.get_config("SCREEN_SESSION") or "palworld_server"
        steamcmd_path = self.config_manager.get_config("STEAMCMD_PATH") or "steamcmd"
        self.server_manager = PalworldServerManager(server_path, screen_session, self.ssh_manager, steamcmd_path)

    def check_putty_tools(self):
        """Check if PuTTY tools are available and show configuration dialog if needed"""
        plink_path = self.config_manager.get_plink_path()
        pscp_path = self.config_manager.get_pscp_path()
        
        if not plink_path or not pscp_path:
            self.show_putty_config_dialog()
        else:
            self.log(f"✅ PuTTY tools found: {plink_path}, {pscp_path}")

    def show_putty_config_dialog(self):
        """Show dialog to configure PuTTY paths"""
        dialog = tb.Toplevel(self.root)
        dialog.title("PuTTY Configuration")
        dialog.geometry("600x450")
        dialog.transient(self.root)
        dialog.grab_set()

        tb.Label(dialog, text="PuTTY tools not found. Please configure the paths:", font=("Arial", 10, "bold")).pack(pady=10)

        # Plink path
        tb.Label(dialog, text="Plink Path:").pack(anchor="w", padx=20)
        plink_var = tb.StringVar(value=self.config_manager.get_plink_path() or "")
        plink_entry = tb.Entry(dialog, textvariable=plink_var, width=50)
        plink_entry.pack(padx=20, pady=5, fill="x")

        # PSCP path
        tb.Label(dialog, text="PSCP Path:").pack(anchor="w", padx=20)
        pscp_var = tb.StringVar(value=self.config_manager.get_pscp_path() or "")
        pscp_entry = tb.Entry(dialog, textvariable=pscp_var, width=50)
        pscp_entry.pack(padx=20, pady=5, fill="x")

        # Session name
        tb.Label(dialog, text="PuTTY Session Name:").pack(anchor="w", padx=20)
        session_var = tb.StringVar(value=self.config_manager.get_config("PUTTY_SESSION"))
        session_entry = tb.Entry(dialog, textvariable=session_var, width=30)
        session_entry.pack(padx=20, pady=5, fill="x")

        # Direct connection options
        tb.Label(dialog, text="Direct Connection (if session doesn't work):", font=("Arial", 9, "bold")).pack(anchor="w", padx=20, pady=(10,5))
        
        # Host
        tb.Label(dialog, text="Host/IP:").pack(anchor="w", padx=20)
        host_var = tb.StringVar()
        host_entry = tb.Entry(dialog, textvariable=host_var, width=30)
        host_entry.pack(padx=20, pady=5, fill="x")
        
        # Port
        tb.Label(dialog, text="Port:").pack(anchor="w", padx=20)
        port_var = tb.StringVar(value="22")
        port_entry = tb.Entry(dialog, textvariable=port_var, width=10)
        port_entry.pack(padx=20, pady=5, fill="x")
        
        # Username
        tb.Label(dialog, text="Username:").pack(anchor="w", padx=20)
        username_var = tb.StringVar()
        username_entry = tb.Entry(dialog, textvariable=username_var, width=30)
        username_entry.pack(padx=20, pady=5, fill="x")

        # Test connection button
        def test_connection():
            # Update config manager
            self.config_manager.update_config("PLINK_PATH", plink_var.get())
            self.config_manager.update_config("PSCP_PATH", pscp_var.get())
            self.config_manager.update_config("PUTTY_SESSION", session_var.get())
            
            # Reinitialize SSH manager
            self.ssh_manager = SSHManager(plink_var.get(), pscp_var.get(), session_var.get())
            
            # Test both session and direct connection
            success, message = self.ssh_manager.test_connection()
            if success:
                messagebox.showinfo("Success", "PuTTY connection test successful!")
                dialog.destroy()
            else:
                # Try direct connection if session fails
                if host_var.get() and username_var.get():
                    self.ssh_manager.set_direct_connection(host_var.get(), port_var.get(), username_var.get())
                    success, message = self.ssh_manager.test_connection()
                    if success:
                        messagebox.showinfo("Success", "Direct connection test successful!")
                        dialog.destroy()
                    else:
                        messagebox.showerror("Error", "Both session and direct connection failed. Please check your configuration.")
                else:
                    messagebox.showerror("Error", "PuTTY connection test failed. Please check your configuration.")

        tb.Button(dialog, text="🔍 Test Connection", bootstyle="info", command=test_connection).pack(pady=10)

        # Browse buttons
        def browse_plink():
            from tkinter import filedialog
            filename = filedialog.askopenfilename(
                title="Select Plink executable",
                filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
            )
            if filename:
                plink_var.set(filename)

        def browse_pscp():
            from tkinter import filedialog
            filename = filedialog.askopenfilename(
                title="Select PSCP executable",
                filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
            )
            if filename:
                pscp_var.set(filename)

        browse_frame = tb.Frame(dialog)
        browse_frame.pack(pady=5)
        tb.Button(browse_frame, text="🔎 Browse Plink", bootstyle="info", command=browse_plink).pack(side="left", padx=5)
        tb.Button(browse_frame, text="🔎 Browse PSCP", bootstyle="info", command=browse_pscp).pack(side="left", padx=5)

        # Help text
        help_text = """
Common PuTTY installation locations:
• C:\\Program Files\\PuTTY\\
• C:\\Program Files (x86)\\PuTTY\\
• ~\\AppData\\Local\\Programs\\PuTTY\\

IMPORTANT - SSH Key Authentication:
1. Create a PuTTY session named '{session}' in PuTTY GUI
2. Configure SSH connection details (hostname, port 22)
3. Go to Connection → SSH → Auth → Credentials
4. Browse to your private key file (.ppk format)
5. Save the session
6. Test the session in PuTTY GUI first

If using password authentication:
1. Create session as above but skip step 4
2. PuTTY will prompt for password when needed

Alternative - Direct Connection:
If session doesn't work, use direct connection with host/IP, port, and username.
        """.format(session=self.config_manager.get_config("PUTTY_SESSION"))
        
        help_label = tb.Label(dialog, text=help_text, justify="left", font=("Arial", 8))
        help_label.pack(pady=10, padx=20, anchor="w")

    def setup_readme_tab(self):
        """Display the README file contents in the first tab"""
        import os
        readme_text = scrolledtext.ScrolledText(self.readme_frame, height=30, width=100)
        readme_text.pack(fill="both", expand=True, padx=10, pady=10)
        readme_path = "README.md"
        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
            readme_text.insert(tb.END, content)
        else:
            readme_text.insert(tb.END, "README.md file not found in the project directory.")
        readme_text.config(state="disabled")

    def setup_config_tab(self):
        # Settings button
        settings_frame = tb.Frame(self.config_frame)
        settings_frame.pack(fill="x", padx=10, pady=5)
        tb.Button(settings_frame, text="⚙️ PuTTY Settings", bootstyle="info", command=self.show_putty_config_dialog, width=20).pack(side="left")
        tb.Button(settings_frame, text="🔍 Test Connection", bootstyle="info", command=self.test_putty_connection, width=20).pack(side="left", padx=5)
        tb.Button(settings_frame, text="📁 Test SFTP", bootstyle="info", command=self.test_scp_connection, width=20).pack(side="left", padx=5)
        tb.Button(settings_frame, text="🔍 Find Config", bootstyle="info", command=self.find_config_file, width=20).pack(side="left", padx=5)
        tb.Button(settings_frame, text="📋 List Steam Files", bootstyle="info", command=self.list_steam_config_files, width=20).pack(side="left", padx=5)
        # SteamCMD Path configuration
        steamcmd_frame = tb.Frame(self.config_frame)
        steamcmd_frame.pack(fill="x", padx=10, pady=5)
        tb.Label(steamcmd_frame, text="SteamCMD Path (full path, e.g. /home/ubuntu/steamcmd/steamcmd.sh, or just 'steamcmd' if in PATH):").pack(side="left")
        self.steamcmd_path_var = tb.StringVar(value=self.config_manager.get_config("STEAMCMD_PATH") or "steamcmd")
        steamcmd_entry = tb.Entry(steamcmd_frame, textvariable=self.steamcmd_path_var, width=50)
        steamcmd_entry.pack(side="left", padx=5)
        def save_steamcmd_path():
            self.config_manager.update_config("STEAMCMD_PATH", self.steamcmd_path_var.get())
            self.config_manager.save_config_to_file()
            self.log(f"✅ SteamCMD path updated: {self.steamcmd_path_var.get()}")
        tb.Button(steamcmd_frame, text="💾 Save", bootstyle="success", command=save_steamcmd_path, width=10).pack(side="left", padx=5)
        # Test SteamCMD button
        def test_steamcmd():
            self.log("🔍 Testing SteamCMD path...")
            steamcmd_path = self.steamcmd_path_var.get()
            if not self.ssh_manager:
                self.log("❌ SSH manager not initialized. Please configure PuTTY paths.")
                return
            test_cmd = f"{steamcmd_path} +quit"
            stdout, stderr = self.ssh_manager.execute_command(test_cmd, timeout=60)
            if stdout:
                self.log(f"[SteamCMD stdout]:\n{stdout}")
            if stderr:
                self.log(f"[SteamCMD stderr]:\n{stderr}")
            if (stderr and ("command not found" in stderr or "not recognized" in stderr)) or (not stdout and not stderr):
                self.log("❌ SteamCMD test failed: Path is incorrect or SteamCMD is not executable.")
            else:
                self.log("✅ SteamCMD test completed. If you see a version or exit message above, the path is correct.")
        tb.Button(steamcmd_frame, text="🔍 Test SteamCMD", bootstyle="info", command=test_steamcmd, width=15).pack(side="left", padx=5)

    def setup_palworld_settings_tab(self):
        # Download, save, and settings form (remove upload button)
        tb.Button(self.palworld_settings_frame, text="⬇ Download Config", bootstyle="info", command=self.download_config, width=40).pack(pady=2)
        # Info label shown if config is not loaded
        self.palworld_info_label = tb.Label(self.palworld_settings_frame, text="Please download the configuration file to edit settings.", foreground="blue")
        self.palworld_info_label.pack(pady=10)
        self.frame = tb.Frame(self.palworld_settings_frame)
        self.frame.pack(padx=10, pady=10)
        tb.Button(self.palworld_settings_frame, text="💾 Save and Upload Config", bootstyle="success", command=self.save_and_upload).pack(pady=5)
        # Only show settings form if config is loaded
        if self.settings and "PalWorldSettings" in self.settings:
            self.palworld_info_label.pack_forget()
            self.show_settings_form()
        else:
            # Hide the settings form frame if not loaded
            for widget in self.frame.winfo_children():
                widget.destroy()

    def setup_api_tab(self):
        # API Settings button
        api_settings_frame = tb.Frame(self.api_frame)
        api_settings_frame.pack(fill="x", padx=10, pady=5)
        tb.Button(api_settings_frame, text="🔑 API Settings", bootstyle="info", command=self.show_api_config_dialog, width=20).pack(side="left")
        tb.Button(api_settings_frame, text="🔍 Test API", bootstyle="info", command=self.test_api_connection, width=20).pack(side="left", padx=5)

        # Server Info Section
        info_frame = tb.LabelFrame(self.api_frame, text="Server Information", padding=10)
        info_frame.pack(fill="x", padx=10, pady=5)

        self.server_info_text = scrolledtext.ScrolledText(info_frame, height=8, width=60)
        self.server_info_text.pack(fill="x")
        tb.Button(info_frame, text="🔄 Refresh Server Info", bootstyle="info", command=self.refresh_server_info).pack(pady=5)

        # Player Management Section
        player_frame = tb.LabelFrame(self.api_frame, text="Player Management", padding=10)
        player_frame.pack(fill="x", padx=10, pady=5)

        # Player list
        self.player_listbox = Listbox(player_frame, height=6)
        self.player_listbox.pack(fill="x", pady=5)
        
        player_buttons_frame = tb.Frame(player_frame)
        player_buttons_frame.pack(fill="x")
        
        tb.Button(player_buttons_frame, text="🔄 Refresh Players", bootstyle="info", command=self.refresh_players).pack(side="left", padx=2)
        tb.Button(player_buttons_frame, text="🚫 Kick Player", bootstyle="danger", command=self.kick_selected_player).pack(side="left", padx=2)
        tb.Button(player_buttons_frame, text="🔨 Ban Player", bootstyle="danger", command=self.ban_selected_player).pack(side="left", padx=2)

    def setup_server_tab(self):
        """Setup the server control tab"""
        # Server Status Section
        status_frame = tb.LabelFrame(self.server_frame, text="Server Status", padding=10)
        status_frame.pack(fill="x", padx=10, pady=5)
        
        self.server_status_label = tb.Label(status_frame, text="Checking server status...", foreground="blue")
        self.server_status_label.pack(pady=5)
        
        status_buttons_frame = tb.Frame(status_frame)
        status_buttons_frame.pack(fill="x")
        
        tb.Button(status_buttons_frame, text="🔄 Refresh Status", bootstyle="info", command=self.refresh_server_status, width=15).pack(side="left", padx=2)
        tb.Button(status_buttons_frame, text="📋 Get Logs", bootstyle="info", command=self.get_server_logs, width=15).pack(side="left", padx=2)
        
        # Server Control Section
        control_frame = tb.LabelFrame(self.server_frame, text="Server Control", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        control_buttons_frame = tb.Frame(control_frame)
        control_buttons_frame.pack(fill="x")
        
        tb.Button(control_buttons_frame, text="🚀 Start Server", bootstyle="primary", command=self.start_server, width=15).pack(side="left", padx=2)
        tb.Button(control_buttons_frame, text="🔄 Stop Server", bootstyle="danger", command=self.stop_server, width=15).pack(side="left", padx=2)
        tb.Button(control_buttons_frame, text="🔄 Restart Server", bootstyle="info", command=self.restart_server, width=15).pack(side="left", padx=2)
        tb.Button(control_buttons_frame, text="⬆ Update Server", bootstyle="primary", command=self.update_server, width=15).pack(side="left", padx=2)
        
        # Move auto-refresh var and checkbox here
        self.auto_refresh_var = tb.BooleanVar()
        tb.Checkbutton(control_frame, text="Auto-refresh every 30 seconds", variable=self.auto_refresh_var, 
                      command=self.toggle_auto_refresh).pack(pady=5)
        
        # Server Settings Section
        settings_frame = tb.LabelFrame(self.server_frame, text="Server Settings", padding=10)
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        # Port setting
        port_frame = tb.Frame(settings_frame)
        port_frame.pack(fill="x", pady=2)
        tb.Label(port_frame, text="Port:").pack(side="left")
        self.port_var = tb.StringVar(value="8211")
        tb.Entry(port_frame, textvariable=self.port_var, width=10).pack(side="left", padx=5)
        
        # Server Commands Section
        commands_frame = tb.LabelFrame(self.server_frame, text="Server Commands", padding=10)
        commands_frame.pack(fill="x", padx=10, pady=5)
        
        # Remove command input and common commands, only add backup button
        tb.Button(commands_frame, text="💾 Backup & Download Saved", bootstyle="success", command=self.backup_and_download_saved, width=30).pack(pady=10)
        
        # Server Logs Section
        logs_frame = tb.LabelFrame(self.server_frame, text="Server Logs", padding=10)
        logs_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.server_logs_text = scrolledtext.ScrolledText(logs_frame, height=10, width=80)
        self.server_logs_text.pack(fill="both", expand=True)
        
        # Add after the Update Server button in setup_server_tab
        def show_update_log():
            if not self.server_manager:
                self.log("❌ Server manager not initialized. Please configure server settings.")
                return
            def fetch_log():
                server_manager = self.server_manager
                if server_manager is None:
                    return
                log_text, error = server_manager.get_update_log(50)
                running = server_manager.is_update_running()
                status = "Update running..." if running else "Update complete."
                popup = tb.Toplevel(self.root)
                popup.title("SteamCMD Update Log")
                popup.geometry("700x500")
                status_label = tb.Label(popup, text=status, foreground="green" if running else "blue")
                status_label.pack(pady=5)
                log_box = scrolledtext.ScrolledText(popup, height=25, width=90)
                log_box.pack(padx=10, pady=10, fill="both", expand=True)
                log_box.insert(tb.END, log_text if log_text is not None else (error if error is not None else ""))
                log_box.config(state="disabled")
                auto_refresh_var = tb.BooleanVar(value=True)
                def refresh_log(auto=False):
                    log_box.config(state="normal")
                    new_log, new_error = server_manager.get_update_log(50)
                    log_box.delete(1.0, tb.END)
                    log_box.insert(tb.END, new_log if new_log is not None else (new_error if new_error is not None else ""))
                    log_box.config(state="disabled")
                    running_now = server_manager.is_update_running()
                    popup.title(f"SteamCMD Update Log - {'Running' if running_now else 'Complete'}")
                    status_label.config(text="Update running..." if running_now else "Update complete.", foreground="green" if running_now else "blue")
                    if auto_refresh_var.get() and running_now and auto:
                        popup.after(5000, lambda: refresh_log(auto=True))
                def on_auto_refresh_toggle():
                    if auto_refresh_var.get():
                        refresh_log(auto=True)
                tb.Button(popup, text="Refresh", command=refresh_log).pack(pady=5)
                tb.Checkbutton(popup, text="Auto-refresh every 5s", variable=auto_refresh_var, command=on_auto_refresh_toggle).pack()
                if running:
                    popup.after(5000, lambda: refresh_log(auto=True))
            threading.Thread(target=fetch_log).start()
        tb.Button(control_buttons_frame, text="📄 View Update Log", bootstyle="info", command=show_update_log, width=18).pack(side="left", padx=2)
        
        # Initial status check
        self.refresh_server_status()

    def show_api_config_dialog(self):
        """Show dialog to configure API settings"""
        dialog = tb.Toplevel(self.root)
        dialog.title("Palworld API Configuration")
        dialog.geometry("500x350")
        dialog.transient(self.root)
        dialog.grab_set()

        tb.Label(dialog, text="Palworld REST API Configuration:", font=("Arial", 10, "bold")).pack(pady=10)

        # API Base URL
        tb.Label(dialog, text="API Base URL:").pack(anchor="w", padx=20)
        api_url_var = tb.StringVar(value=self.config_manager.get_config("PALWORLD_API_BASE"))
        api_url_entry = tb.Entry(dialog, textvariable=api_url_var, width=50)
        api_url_entry.pack(padx=20, pady=5, fill="x")

        # API Username
        tb.Label(dialog, text="Username:").pack(anchor="w", padx=20)
        api_username_var = tb.StringVar(value=self.config_manager.get_config("PALWORLD_API_USERNAME"))
        api_username_entry = tb.Entry(dialog, textvariable=api_username_var, width=50)
        api_username_entry.pack(padx=20, pady=5, fill="x")

        # API Password
        tb.Label(dialog, text="Password:").pack(anchor="w", padx=20)
        api_password_var = tb.StringVar(value=self.config_manager.get_config("PALWORLD_API_PASSWORD"))
        api_password_entry = tb.Entry(dialog, textvariable=api_password_var, width=50, show="*")
        api_password_entry.pack(padx=20, pady=5, fill="x")

        # Show/Hide password checkbox
        show_password_var = tb.BooleanVar()
        def toggle_password():
            if show_password_var.get():
                api_password_entry.config(show="")
            else:
                api_password_entry.config(show="*")
        
        tb.Checkbutton(dialog, text="Show password", variable=show_password_var, command=toggle_password).pack(padx=20, pady=5)

        # Save button
        def save_api_config():
            # Update config manager
            self.config_manager.update_config("PALWORLD_API_BASE", api_url_var.get())
            self.config_manager.update_config("PALWORLD_API_USERNAME", api_username_var.get())
            self.config_manager.update_config("PALWORLD_API_PASSWORD", api_password_var.get())
            
            # Save to config.py so it persists after restart
            self.config_manager.save_config_to_file()
            
            # Reinitialize API manager
            self.api_manager = PalworldAPIManager(
                api_url_var.get(),
                api_username_var.get(),
                api_password_var.get()
            )
            
            self.log("✅ API configuration updated and saved")
            dialog.destroy()

        tb.Button(dialog, text="💾 Save Configuration", bootstyle="success", command=save_api_config).pack(pady=10)

        # Help text
        help_text = """
API Configuration Help:
• API Base URL: Your Palworld server's IP and port (e.g., http://192.168.1.100:8212)
• Username: The username for API authentication (usually "admin")
• Password: The password configured in your Palworld server settings
• Make sure your server has REST API enabled
• Uses Basic Authentication (Authorization header) as per official API docs
• Credentials are base64 encoded and sent in the Authorization header
        """
        
        help_label = tb.Label(dialog, text=help_text, justify="left", font=("Arial", 8))
        help_label.pack(pady=10, padx=20, anchor="w")

    def log(self, text):
        """Log message to console (thread-safe)"""
        def append_log():
            self.output_console.config(state="normal")
            self.output_console.insert(tb.END, text + "\n")
            self.output_console.see(tb.END)
            self.output_console.config(state="disabled")
        self.root.after(0, append_log)

    def test_putty_connection(self):
        """Test PuTTY connection to the server"""
        if not self.ssh_manager:
            self.log("❌ SSH manager not initialized. Please configure PuTTY paths.")
            return
            
        success, message = self.ssh_manager.test_connection()
        if success:
            self.log("✅ PuTTY connection test successful")
        else:
            self.log(f"❌ PuTTY connection failed: {message}")

    def test_api_connection(self):
        """Test API connection to the server"""
        if not self.api_manager:
            self.log("❌ API manager not initialized. Please configure API settings.")
            return
            
        def test_connection():
            self.log("🔍 Testing Palworld API connection...")
            # Type assertion to help linter
            api_manager = self.api_manager
            assert api_manager is not None
            success, message = api_manager.test_connection()
            if success:
                self.log("✅ API connection test successful")
                # Test with authentication
                info = api_manager.get_server_info()
                if info:
                    self.log(f"✅ Server info: {json.dumps(info, indent=2)}")
                    # Also display in the server info box
                    self.server_info_text.config(state="normal")
                    self.server_info_text.delete(1.0, tb.END)
                    self.server_info_text.insert(tb.END, json.dumps(info, indent=2))
                    self.server_info_text.config(state="disabled")
                else:
                    self.log("❌ Authentication failed")
            else:
                self.log(f"❌ API connection test failed: {message}")

        threading.Thread(target=test_connection).start()

    def download_config(self):
        """Download configuration file from server"""
        if not self.ssh_manager:
            self.log("❌ SSH manager not initialized. Please configure PuTTY paths.")
            return
        try:
            self.log("⬇ Starting config download...")
            remote_path = self.config_manager.get_config("REMOTE_CONFIG_PATH")
            local_path = self.config_manager.get_config("LOCAL_CONFIG_PATH")
            ssh_manager = self.ssh_manager
            assert ssh_manager is not None
            # Always resolve the full remote path
            full_remote_path, _ = ssh_manager.get_full_path(remote_path)
            if not full_remote_path or not full_remote_path.strip():
                self.log(f"⚠️ Could not resolve full path for config: {remote_path}")
                # Try to resolve the directory and copy the default config
                config_dir = os.path.dirname(remote_path)
                default_path = "~/Steam/steamapps/common/PalServer/DefaultPalWorldSettings.ini"
                full_default_path, _ = ssh_manager.get_full_path(default_path)
                full_config_dir, _ = ssh_manager.get_full_path(config_dir)
                if not full_default_path or not full_config_dir:
                    self.log(f"❌ Could not resolve full path for default config or config directory.")
                    self.status.set(f"❌ Could not resolve full path for default config or config directory.")
                    return
                full_target_path = posixpath.join(full_config_dir.strip(), os.path.basename(remote_path))
                copy_cmd = f"cp '{full_default_path.strip()}' '{full_target_path}'"
                stdout, stderr = ssh_manager.execute_command(copy_cmd)
                if stderr:
                    self.log(f"❌ Failed to copy default config: {stderr}")
                    self.status.set(f"❌ Failed to copy default config: {stderr}")
                    return
                self.log(f"✅ Default config copied to {full_target_path}")
                # Try to resolve the full path again
                full_remote_path, _ = ssh_manager.get_full_path(remote_path)
                if not full_remote_path or not full_remote_path.strip():
                    self.log(f"❌ Still could not resolve full path for config after copying default.")
                    self.status.set(f"❌ Still could not resolve full path for config after copying default.")
                    return
                full_remote_path = full_remote_path.strip()
            else:
                full_remote_path = full_remote_path.strip()
            # Check if config file exists on server (use full path)
            file_exists, _ = ssh_manager.test_file_exists(full_remote_path)
            if not file_exists:
                self.log(f"❌ Config file not found at {full_remote_path} even after attempting to copy default.")
                self.status.set(f"❌ Config file not found at {full_remote_path} even after attempting to copy default.")
                return
            success, message = ssh_manager.download_file(full_remote_path, local_path)
            if success:
                self.load_config()
                self.palworld_info_label.pack_forget()
                self.show_settings_form()
                self.status.set("✅ Config downloaded and loaded.")
                self.log("✅ Config file downloaded successfully.")
            else:
                self.log(f"❌ Download failed: {message}")
                self.status.set(f"❌ Download failed: {message}")
                self.palworld_info_label.pack(pady=10)
                for widget in self.frame.winfo_children():
                    widget.destroy()
        except Exception as e:
            self.log(f"❌ Unexpected error: {str(e)}")
            self.status.set(f"❌ Error: {str(e)}")
            self.palworld_info_label.pack(pady=10)
            for widget in self.frame.winfo_children():
                widget.destroy()

    def upload_config(self):
        """Upload configuration file to server"""
        if not self.ssh_manager:
            self.log("❌ SSH manager not initialized. Please configure PuTTY paths.")
            return
            
        try:
            self.log("⬆ Starting config upload...")
            local_path = self.config_manager.get_config("LOCAL_CONFIG_PATH")
            remote_path = self.config_manager.get_config("REMOTE_CONFIG_PATH")
            
            # Type assertion to help linter
            ssh_manager = self.ssh_manager
            assert ssh_manager is not None
            success, message = ssh_manager.upload_file(local_path, remote_path)
            
            if success:
                self.status.set("✅ Config uploaded.")
                self.log("✅ Config file uploaded successfully.")
            else:
                self.log(f"❌ Upload failed: {message}")
                self.status.set(f"❌ Upload failed: {message}")
                
        except Exception as e:
            self.log(f"❌ Unexpected error: {str(e)}")
            self.status.set(f"❌ Error: {str(e)}")

    def load_config(self):
        """Load Palworld configuration file"""
        local_path = self.config_manager.get_config("LOCAL_CONFIG_PATH")
        self.settings = self.palworld_config_manager.load_palworld_config(local_path)
        
        # Debug: Print loaded settings
        self.log(f"📋 Loaded settings: {self.settings}")
        if "PalWorldSettings" in self.settings:
            self.log(f"📋 PalWorldSettings keys: {list(self.settings['PalWorldSettings'].keys())}")
        else:
            self.log("❌ No PalWorldSettings section found in config file")

    def show_settings_form(self):
        """Show the settings form with organized sections"""
        for widget in self.frame.winfo_children():
            widget.destroy()

        # Create a scrollable frame
        canvas = tb.Canvas(self.frame)
        scrollbar = tb.Scrollbar(self.frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tb.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack the canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mouse wheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        row = 0
        config_fields = self.palworld_config_manager.get_config_fields()
        
        # Debug: Print what we're looking for vs what we have
        self.log(f"🔍 Looking for fields in: {list(config_fields['PalWorldSettings'].keys())}")
        if "PalWorldSettings" in self.settings:
            self.log(f"📄 Found in file: {list(self.settings['PalWorldSettings'].keys())}")
        
        # Define section groupings
        sections = {
            "Server Settings": ["ServerName", "ServerDescription", "AdminPassword", "ServerPassword", 
                              "ServerPlayerMaxNum", "PublicIP", "PublicPort"],
            "Game Balance": ["Difficulty", "DayTimeSpeedRate", "NightTimeSpeedRate", "ExpRate", 
                           "DeathPenalty", "GuildPlayerMaxNum"],
            "Pal Settings": ["PalCaptureRate", "PalSpawnNumRate", "PalDamageRateAttack", "PalDamageRateDefense",
                           "PalStaminaDecreaceRate", "PalStomachDecreaceRate", "PalAutoHPRegeneRate",
                           "PalAutoHpRegeneRateInSleep", "PalEggDefaultHatchingTime"],
            "Player Settings": ["PlayerDamageRateAttack", "PlayerDamageRateDefense", "PlayerStaminaDecreaceRate",
                              "PlayerStomachDecreaceRate", "PlayerAutoHPRegeneRate", "PlayerAutoHpRegeneRateInSleep"],
            "Base Camp": ["BaseCampMaxNumInGuild", "BaseCampWorkerMaxNum"],
            "Building": ["BuildObjectDamageRate", "BuildObjectDeteriorationDamageRate", "MaxBuildingLimitNum"],
            "Collection": ["CollectionDropRate", "CollectionObjectHpRate", "CollectionObjectRespawnSpeedRate"],
            "Enemy & Items": ["EnemyDropItemRate", "ItemWeightRate", "EquipmentDurabilityDamageRate"],
            "Gameplay Features": ["bEnableFastTravel", "bEnableInvaderEnemy", "bHardcore", "bPalLost", 
                                "bShowPlayerList", "bCharacterRecreateInHardcore", "bInvisibleOtherGuildBaseCampAreaFX",
                                "bIsRandomizerPalLevelRandom", "bIsUseBackupSaveData", "bBuildAreaLimit",
                                "bAllowGlobalPalboxExport", "bAllowGlobalPalboxImport"],
            "Randomizer": ["RandomizerSeed", "RandomizerType"],
            "Crossplay": ["CrossplayPlatforms", "AllowConnectPlatform"],
            "Chat & Supply": ["ChatPostLimitPerMinute", "SupplyDropSpan"],
            "Sync Settings": ["ServerReplicatePawnCullDistance", "ItemContainerForceMarkDirtyInterval"],
            "API & Logging": ["RESTAPIEnabled", "RESTAPIPort", "RCONEnabled", "RCONPort", "LogFormatType"]
        }
        
        for section_name, field_names in sections.items():
            # Create section header with toggle functionality
            section_frame = tb.LabelFrame(scrollable_frame, text=section_name, padding=5)
            section_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=2)
            row += 1
            
            section_row = 0
            for field_name in field_names:
                if field_name in config_fields["PalWorldSettings"]:
                    value_type = config_fields["PalWorldSettings"][field_name]
                    default_value = self.settings.get("PalWorldSettings", {}).get(field_name, "")
                    
                    # Debug: Print field value
                    self.log(f"📝 Field {field_name}: '{default_value}'")
                    
                    # Create label and input widget
                    tb.Label(section_frame, text=field_name, width=25, anchor="w").grid(row=section_row, column=0, sticky="w", padx=5)
                    
                    if isinstance(value_type, list):  # dropdown
                        var = tb.StringVar(value=default_value)
                        widget = tb.Combobox(section_frame, textvariable=var, values=value_type, state="readonly", width=30)
                    elif value_type == bool:
                        var = tb.BooleanVar(value=default_value.lower() == "true")
                        widget = tb.Checkbutton(section_frame, variable=var)
                    else:
                        var = tb.StringVar(value=default_value)
                        widget = tb.Entry(section_frame, textvariable=var, width=30)

                    widget.grid(row=section_row, column=1, sticky="w", padx=5, pady=2)
                    self.inputs[("PalWorldSettings", field_name)] = var
                    section_row += 1

        # Configure grid weights
        scrollable_frame.grid_columnconfigure(0, weight=1)

    def save_and_upload(self):
        """Save configuration and upload to server"""
        # Save to local file
        local_path = self.config_manager.get_config("LOCAL_CONFIG_PATH")
        settings = {}
        
        for (section, key), var in self.inputs.items():
            if section not in settings:
                settings[section] = {}
            settings[section][key] = str(var.get())
            
        self.palworld_config_manager.save_palworld_config(local_path, settings)
        
        # Upload to server
        self.upload_config()

    def run_steamcmd_update(self):
        """Run SteamCMD update"""
        if not self.ssh_manager:
            self.log("❌ SSH manager not initialized. Please configure PuTTY paths.")
            return
            
        def run_update():
            self.log("🚀 Running SteamCMD update...")
            steamcmd_cmd = 'bash -c "steamcmd +login anonymous +app_update 2394010 validate +quit"'
            
            # Type assertion to help linter
            ssh_manager = self.ssh_manager
            assert ssh_manager is not None
            stdout, stderr = ssh_manager.execute_command(steamcmd_cmd)
            
            if stdout:
                for line in stdout.split('\n'):
                    if line.strip():
                        self.log(line.strip())
                self.log("✅ SteamCMD update complete.")
            else:
                self.log(f"❌ SteamCMD error: {stderr}")

        threading.Thread(target=run_update).start()

    def refresh_server_info(self):
        """Get server information"""
        if not self.api_manager:
            self.log("❌ API manager not initialized. Please configure API settings.")
            return
            
        def fetch_info():
            self.log("🔄 Fetching server information...")
            # Type assertion to help linter
            api_manager = self.api_manager
            assert api_manager is not None
            info = api_manager.get_server_info()
            if info:
                self.server_info_text.config(state="normal")
                self.server_info_text.delete(1.0, tb.END)
                self.server_info_text.insert(tb.END, json.dumps(info, indent=2))
                self.server_info_text.config(state="disabled")
                self.log("✅ Server info updated")
            else:
                self.log("❌ Failed to fetch server info")

        threading.Thread(target=fetch_info).start()

    def refresh_players(self):
        """Get player list"""
        if not self.api_manager:
            self.log("❌ API manager not initialized. Please configure API settings.")
            return
            
        def fetch_players():
            self.log("🔄 Fetching player list...")
            # Type assertion to help linter
            api_manager = self.api_manager
            assert api_manager is not None
            players = api_manager.get_players()
            if players:
                self.player_listbox.delete(0, tb.END)
                
                for player in players:
                    if isinstance(player, dict):
                        name = player.get('name', 'Unknown')
                        playeruid = player.get('playeruid', 'N/A')
                        self.player_listbox.insert(tb.END, f"{name} ({playeruid})")
                    elif isinstance(player, str):
                        self.player_listbox.insert(tb.END, f"{player} (N/A)")
                    else:
                        self.player_listbox.insert(tb.END, f"{str(player)} (N/A)")
                
                self.log(f"✅ Found {len(players)} players")
            else:
                self.log("❌ Failed to fetch players")

        threading.Thread(target=fetch_players).start()

    def kick_selected_player(self):
        """Kick selected player"""
        if not self.api_manager:
            self.log("❌ API manager not initialized. Please configure API settings.")
            return
            
        selection = self.player_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a player to kick")
            return
        
        player_entry = self.player_listbox.get(selection[0])
        if " (" in player_entry:
            player_name = player_entry.split(" (")[0]
        else:
            player_name = player_entry
            
        if messagebox.askyesno("Confirm Kick", f"Are you sure you want to kick {player_name}?"):
            # Type assertion to help linter
            api_manager = self.api_manager
            assert api_manager is not None
            success = api_manager.kick_player(player_name)
            if success:
                self.log(f"✅ Kicked player: {player_name}")
                self.refresh_players()
            else:
                self.log(f"❌ Failed to kick player: {player_name}")

    def ban_selected_player(self):
        """Ban selected player"""
        if not self.api_manager:
            self.log("❌ API manager not initialized. Please configure API settings.")
            return
            
        selection = self.player_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a player to ban")
            return
        
        player_entry = self.player_listbox.get(selection[0])
        if " (" in player_entry:
            player_name = player_entry.split(" (")[0]
        else:
            player_name = player_entry
            
        if messagebox.askyesno("Confirm Ban", f"Are you sure you want to ban {player_name}?"):
            # Type assertion to help linter
            api_manager = self.api_manager
            assert api_manager is not None
            success = api_manager.ban_player(player_name)
            if success:
                self.log(f"✅ Banned player: {player_name}")
                self.refresh_players()
            else:
                self.log(f"❌ Failed to ban player: {player_name}")

    def teleport_player(self):
        """Teleport player to coordinates"""
        if not self.api_manager:
            self.log("❌ API manager not initialized. Please configure API settings.")
            return
            
        selection = self.player_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a player to teleport")
            return
        
        player_entry = self.player_listbox.get(selection[0])
        if " (" in player_entry:
            player_name = player_entry.split(" (")[0]
        else:
            player_name = player_entry
        
        # Create teleport dialog
        dialog = tb.Toplevel(self.root)
        dialog.title("Teleport Player")
        dialog.geometry("300x150")
        
        tb.Label(dialog, text="X Coordinate:").pack()
        x_var = tb.StringVar()
        tb.Entry(dialog, textvariable=x_var).pack()
        
        tb.Label(dialog, text="Y Coordinate:").pack()
        y_var = tb.StringVar()
        tb.Entry(dialog, textvariable=y_var).pack()
        
        tb.Label(dialog, text="Z Coordinate:").pack()
        z_var = tb.StringVar()
        tb.Entry(dialog, textvariable=z_var).pack()
        
        def do_teleport():
            try:
                # Type assertion to help linter
                api_manager = self.api_manager
                assert api_manager is not None
                success = api_manager.teleport_player(
                    player_name,
                    float(x_var.get()),
                    float(y_var.get()),
                    float(z_var.get())
                )
                if success:
                    self.log(f"✅ Teleported {player_name} to ({x_var.get()}, {y_var.get()}, {z_var.get()})")
                else:
                    self.log(f"❌ Failed to teleport {player_name}")
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter valid coordinates")

        tb.Button(dialog, text="🗺️ Teleport", bootstyle="primary", command=do_teleport).pack(pady=10)

    def show_announce_dialog(self):
        """Show announcement dialog"""
        if not self.api_manager:
            self.log("❌ API manager not initialized. Please configure API settings.")
            return
            
        dialog = tb.Toplevel(self.root)
        dialog.title("Send Announcement")
        dialog.geometry("400x200")
        
        tb.Label(dialog, text="Message:").pack()
        message_var = tb.StringVar()
        tb.Entry(dialog, textvariable=message_var, width=50).pack(pady=5)
        
        def send_announcement():
            if message_var.get().strip():
                # Type assertion to help linter
                api_manager = self.api_manager
                assert api_manager is not None
                success = api_manager.send_announcement(message_var.get())
                if success:
                    self.log(f"✅ Announcement sent: {message_var.get()}")
                else:
                    self.log("❌ Failed to send announcement")
                dialog.destroy()
            else:
                messagebox.showwarning("Warning", "Please enter a message")

        tb.Button(dialog, text="📢 Send", bootstyle="primary", command=send_announcement).pack(pady=10)

    def shutdown_server(self):
        """Shutdown the server"""
        if not self.api_manager:
            self.log("❌ API manager not initialized. Please configure API settings.")
            return
            
        if messagebox.askyesno("Confirm Shutdown", "Are you sure you want to shutdown the server?"):
            # Type assertion to help linter
            api_manager = self.api_manager
            assert api_manager is not None
            success = api_manager.shutdown_server()
            if success:
                self.log("✅ Server shutdown initiated")
            else:
                self.log("❌ Failed to shutdown server")

    def toggle_auto_refresh(self):
        """Toggle auto-refresh functionality"""
        if self.auto_refresh_var.get():
            self.schedule_auto_refresh()
        else:
            if hasattr(self, 'auto_refresh_job'):
                self.root.after_cancel(self.auto_refresh_job)

    def schedule_auto_refresh(self):
        """Schedule next auto-refresh"""
        if self.auto_refresh_var.get():
            self.refresh_server_info()
            self.refresh_players()
            self.auto_refresh_job = self.root.after(30000, self.schedule_auto_refresh)  # 30 seconds

    def test_scp_connection(self):
        """Test SFTP connection to the server by downloading a small temp file using PSCP"""
        if not self.ssh_manager:
            self.log("❌ SSH manager not initialized. Please configure PuTTY paths.")
            return
        
        try:
            self.log("🔍 Testing SFTP connection by downloading a temp file...")
            temp_remote = "/tmp/palworld_sftp_test.txt"
            temp_local = "palworld_sftp_test.txt"
            # Create a temp file on the server
            stdout, stderr = self.ssh_manager.execute_command(f"echo 'SFTP test' > {temp_remote}")
            # Try to download the temp file
            success, message = self.ssh_manager.download_file(temp_remote, temp_local)
            if success:
                self.log("✅ SFTP connection test successful (file downloaded)")
                self.status.set("✅ SFTP connection test successful")
                # Clean up local temp file
                try:
                    os.remove(temp_local)
                except Exception:
                    pass
            else:
                self.log(f"❌ SFTP connection failed: {message}")
                self.status.set(f"❌ SFTP connection failed: {message}")
        except Exception as e:
            self.log(f"❌ SFTP connection error: {str(e)}")
            self.status.set(f"❌ SFTP connection error: {str(e)}")

    def find_config_file(self):
        """Find the PalWorldSettings.ini file on the server, and propose to create it if not found"""
        if not self.ssh_manager:
            self.log("❌ SSH manager not initialized. Please configure PuTTY paths.")
            return
        try:
            self.log("🔍 Finding config file...")
            found_path, message = self.ssh_manager.find_config_file()
            if found_path:
                self.log(f"🎯 Recommended config path: {found_path}")
                self.log("💡 You can update this path in config.py")
                if messagebox.askyesno("Config Found", f"Found config file at:\n{found_path}\n\nUpdate the path in config.py?"):
                    self.update_config_path(found_path)
            else:
                self.log("❌ Config file not found in any common locations")
                if messagebox.askyesno("Config Not Found", "Config file not found. Do you want to create it?"):
                    remote_path = self.config_manager.get_config("REMOTE_CONFIG_PATH")
                    default_path = "~/Steam/steamapps/common/PalServer/DefaultPalWorldSettings.ini"
                    ssh_manager = self.ssh_manager
                    # Get the full absolute path of ~/Steam/steamapps/common/PalServer/Pal
                    pal_dir = "~/Steam/steamapps/common/PalServer/Pal"
                    full_pal_dir, _ = ssh_manager.get_full_path(pal_dir)
                    full_default_path, _ = ssh_manager.get_full_path(default_path)
                    if not full_pal_dir or not full_default_path:
                        self.log(f"❌ Could not resolve full path for {pal_dir} or default config.")
                        while messagebox.askretrycancel("Error", f"Could not resolve full path for {pal_dir} or default config. Retry?"):
                            full_pal_dir, _ = ssh_manager.get_full_path(pal_dir)
                            full_default_path, _ = ssh_manager.get_full_path(default_path)
                            if full_pal_dir and full_default_path:
                                break
                        else:
                            return
                        full_pal_dir = full_pal_dir.strip()
                        full_default_path = full_default_path.strip()
                    else:
                        full_pal_dir = full_pal_dir.strip()
                        full_default_path = full_default_path.strip()
                    # Create the folders using the absolute path
                    while True:
                        create_dirs_cmd = f"mkdir -p '{full_pal_dir}/Saved/Config/LinuxServer'"
                        stdout, stderr = ssh_manager.execute_command(create_dirs_cmd)
                        self.log(f"[DEBUG] mkdir stdout: {stdout}")
                        self.log(f"[DEBUG] mkdir stderr: {stderr}")
                        if stderr:
                            self.log(f"❌ Failed to create directories: {stderr}")
                            if not messagebox.askretrycancel("Error", f"Failed to create directories: {stderr}\nRetry?"):
                                return
                        else:
                            break
                    # Copy the default config to the new location using the absolute path
                    full_target_path = f"{full_pal_dir}/Saved/Config/LinuxServer/PalWorldSettings.ini"
                    while True:
                        copy_cmd = f"cp '{full_default_path}' '{full_target_path}'"
                        stdout, stderr = ssh_manager.execute_command(copy_cmd)
                        if stderr:
                            self.log(f"❌ Failed to copy default config: {stderr}")
                            if not messagebox.askretrycancel("Error", f"Failed to copy default config: {stderr}\nRetry?"):
                                return
                        else:
                            break
                    self.log(f"✅ Default config copied to {full_target_path}")
                    # Check if the file now exists
                    file_exists, _ = ssh_manager.test_file_exists(full_target_path)
                    if not file_exists:
                        self.log(f"❌ Default config was not properly copied to {full_target_path}")
                        if not messagebox.askretrycancel("Copy Failed", f"Default config was not properly copied to {full_target_path}\nRetry?"):
                            return
                        # If retry, go back to copy step
                        while True:
                            copy_cmd = f"cp '{full_default_path}' '{full_target_path}'"
                            stdout, stderr = ssh_manager.execute_command(copy_cmd)
                            if stderr:
                                self.log(f"❌ Failed to copy default config: {stderr}")
                                if not messagebox.askretrycancel("Error", f"Failed to copy default config: {stderr}\nRetry?"):
                                    return
                            else:
                                break
                        file_exists, _ = ssh_manager.test_file_exists(full_target_path)
                        if not file_exists:
                            self.log(f"❌ Default config was not properly copied to {full_target_path} (after retry)")
                            return
                    if messagebox.askyesno("Default Config Created", f"Default config created at:\n{full_target_path}\n\nUpdate the path in config.py?"):
                        self.update_config_path(full_target_path)
                else:
                    self.log("💡 Try these manual steps:")
                    self.log("   1. Connect to your VPS via SSH")
                    self.log("   2. Run: find / -name 'PalWorldSettings.ini' 2>/dev/null")
                    self.log("   3. Update the path in config.py")
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
            self.status.set(f"❌ Error: {str(e)}")

    def update_config_path(self, new_path):
        """Update the config path in config.py"""
        try:
            self.config_manager.update_config("REMOTE_CONFIG_PATH", new_path)
            self.config_manager.save_config_to_file()
            
            self.log(f"✅ Updated config path to: {new_path}")
            self.log("🔄 Please restart the application for changes to take effect")
            
        except Exception as e:
            self.log(f"❌ Failed to update config: {str(e)}")

    def list_steam_config_files(self):
        """List Steam config files"""
        if not self.ssh_manager:
            self.log("❌ SSH manager not initialized. Please configure PuTTY paths.")
            return
            
        try:
            self.log("🔍 Listing Steam config files...")
            
            # Type assertion to help linter
            ssh_manager = self.ssh_manager
            assert ssh_manager is not None
            stdout, stderr = ssh_manager.list_steam_config_files()
            
            if stdout:
                self.log("📁 Steam config files:")
                for line in stdout.strip().split('\n'):
                    if line.strip():
                        self.log(f"   {line}")
            else:
                self.log("❌ No Steam config files found")
                
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
            self.status.set(f"❌ Error: {str(e)}")

    def refresh_server_status(self):
        """Refresh server status"""
        if not self.server_manager:
            self.log("❌ Server manager not initialized. Please configure server settings.")
            return
            
        def update_status():
            # Type assertion to help linter
            server_manager = self.server_manager
            assert server_manager is not None
            running, message = server_manager.get_server_status()
            def update_label():
                if running:
                    self.server_status_label.config(text=f"✅ {message}", foreground="green")
                else:
                    self.server_status_label.config(text=f"❌ {message}", foreground="red")
            self.server_status_label.after(0, update_label)
        
        threading.Thread(target=update_status).start()

    def get_server_logs(self):
        """Get server logs"""
        if not self.server_manager:
            self.log("❌ Server manager not initialized. Please configure server settings.")
            return
            
        def fetch_logs():
            # Type assertion to help linter
            server_manager = self.server_manager
            assert server_manager is not None
            logs, error = server_manager.get_server_logs()
            def update_logs():
                if logs:
                    self.server_logs_text.config(state="normal")
                    self.server_logs_text.delete(1.0, tb.END)
                    self.server_logs_text.insert(tb.END, logs)
                    self.server_logs_text.config(state="disabled")
                    self.log("✅ Server logs updated")
                else:
                    self.log(f"❌ Failed to get logs: {error}")
            self.server_logs_text.after(0, update_logs)
        
        threading.Thread(target=fetch_logs).start()

    def start_server(self):
        """Start the server"""
        if not self.server_manager:
            self.log("❌ Server manager not initialized. Please configure server settings.")
            return
            
        if messagebox.askyesno("Confirm Start", "Are you sure you want to start the server?"):
            def start():
                # Type assertion to help linter
                server_manager = self.server_manager
                assert server_manager is not None
                success, message = server_manager.start_server(self.port_var.get())
                if success:
                    self.log("✅ Server started successfully")
                    self.refresh_server_status()
                else:
                    self.log(f"❌ Failed to start server: {message}")
            
            threading.Thread(target=start).start()

    def stop_server(self):
        """Stop the server"""
        if not self.server_manager:
            self.log("❌ Server manager not initialized. Please configure server settings.")
            return
            
        if messagebox.askyesno("Confirm Stop", "Are you sure you want to stop the server?"):
            def stop():
                # Type assertion to help linter
                server_manager = self.server_manager
                assert server_manager is not None
                success, message = server_manager.stop_server()
                if success:
                    self.log("✅ Server stopped successfully")
                    self.refresh_server_status()
                else:
                    self.log(f"❌ Failed to stop server: {message}")
            
            threading.Thread(target=stop).start()

    def restart_server(self):
        """Restart the server"""
        if not self.server_manager:
            self.log("❌ Server manager not initialized. Please configure server settings.")
            return
            
        if messagebox.askyesno("Confirm Restart", "Are you sure you want to restart the server?"):
            def restart():
                # Type assertion to help linter
                server_manager = self.server_manager
                assert server_manager is not None
                success, message = server_manager.restart_server(self.port_var.get())
                if success:
                    self.log("✅ Server restarted successfully")
                    self.refresh_server_status()
                else:
                    self.log(f"❌ Failed to restart server: {message}")
            
            threading.Thread(target=restart).start()

    def update_server(self):
        """Update the server"""
        if not self.server_manager:
            self.log("❌ Server manager not initialized. Please configure server settings.")
            return
            
        if messagebox.askyesno("Confirm Update", "Are you sure you want to update the server?"):
            def update():
                # Type assertion to help linter
                server_manager = self.server_manager
                assert server_manager is not None
                success, message = server_manager.update_server()
                if success:
                    self.log("✅ Server updated successfully")
                else:
                    self.log(f"❌ Failed to update server: {message}")
            
            threading.Thread(target=update).start()

    def backup_and_download_saved(self):
        """Backup and download the Palworld Saved folder from the VPS"""
        if not self.server_manager:
            self.log("❌ Server manager not initialized. Please configure server settings.")
            return
        
        def do_backup():
            self.log("💾 Creating backup and downloading Saved folder from VPS...")
            server_manager = self.server_manager
            assert server_manager is not None
            success, message, local_file = server_manager.save_and_download_backup()
            def update_backup_status():
                if success:
                    self.log(f"✅ {message}")
                    self.status.set(f"✅ Backup downloaded: {local_file}")
                    messagebox.showinfo("Backup Complete", f"Backup downloaded to: {local_file}")
                else:
                    self.log(f"❌ {message}")
                    self.status.set(f"❌ Backup failed: {message}")
                    messagebox.showerror("Backup Failed", message)
            self.server_status_label.after(0, update_backup_status)
        
        threading.Thread(target=do_backup).start()

    def show_tab(self, idx):
        # Hide all frames
        for i, (icon, text, frame) in enumerate(self.tabs):
            frame.lower()
        # Show selected frame
        icon, text, frame = self.tabs[idx]
        frame.lift()
        # Highlight the active tab button
        for i, btn in enumerate(self.tab_buttons):
            btn.config(bootstyle="primary" if i == idx else "secondary")

if __name__ == "__main__":
    root = tb.Window(themename="superhero")
    root.geometry("1920x1080")
    root.minsize(800, 600)
    app = PalworldConfigApp(root)
    root.mainloop() 
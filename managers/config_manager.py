import os
from typing import Optional, Any

class ConfigManager:
    def __init__(self):
        # Default configuration
        self.config = {
            "PUTTY_SESSION": "Your Putty Session Name",
            "REMOTE_CONFIG_PATH": "~/Steam/steamapps/common/PalServer/Pal/Saved/Config/LinuxServer/PalWorldSettings.ini",
            "LOCAL_CONFIG_PATH": "downloads/PalWorldSettings.ini",
            "PALWORLD_API_BASE": "http://yourIP:yourport",
            "PALWORLD_API_USERNAME": "admin",
            "PALWORLD_API_PASSWORD": "yourpwd",
            "PLINK_PATH": None,
            "PSCP_PATH": None,
            "SSH_HOST": None,
            "SSH_PORT": "22",
            "SSH_USERNAME": None,
            "USE_DIRECT_CONNECTION": False,
            "SERVER_PATH": "~/Steam/steamapps/common/PalServer",
            "SCREEN_SESSION": "palworld_server",
            "STEAMCMD_PATH": "your steamcmd path on the server"
        }
        
        # Common PuTTY installation paths on Windows
        self.putty_paths = [
            "plink",  # If in PATH
            "C:\\Program Files\\PuTTY\\plink.exe",
            "C:\\Program Files (x86)\\PuTTY\\plink.exe",
            os.path.expanduser("~\\AppData\\Local\\Programs\\PuTTY\\plink.exe"),
            os.path.expanduser("~\\Downloads\\putty\\plink.exe"),
        ]

        self.pscp_paths = [
            "pscp",  # If in PATH
            "C:\\Program Files\\PuTTY\\pscp.exe",
            "C:\\Program Files (x86)\\PuTTY\\pscp.exe",
            os.path.expanduser("~\\AppData\\Local\\Programs\\PuTTY\\pscp.exe"),
            os.path.expanduser("~\\Downloads\\putty\\pscp.exe"),
        ]
        
        # Load configuration
        self.load_config()
        
    def load_config(self):
        """Load configuration from config.py if it exists"""
        try:
            import config
            
            # Update config with values from config.py
            for key in self.config.keys():
                if hasattr(config, key):
                    self.config[key] = getattr(config, key)
                    
        except ImportError:
            # config.py doesn't exist, use defaults
            pass
            
    def find_executable(self, paths: list, name: str) -> Optional[str]:
        """Find executable in the given paths"""
        for path in paths:
            if os.path.isfile(path):
                return path
            # Try with .exe extension if not already present
            if not path.endswith('.exe'):
                exe_path = path + '.exe'
                if os.path.isfile(exe_path):
                    return exe_path
        return None
        
    def get_plink_path(self) -> Optional[str]:
        """Get plink path, auto-detect if not configured"""
        if self.config["PLINK_PATH"] and os.path.isfile(self.config["PLINK_PATH"]):
            return self.config["PLINK_PATH"]
        return self.find_executable(self.putty_paths, "plink")
        
    def get_pscp_path(self) -> Optional[str]:
        """Get pscp path, auto-detect if not configured"""
        if self.config["PSCP_PATH"] and os.path.isfile(self.config["PSCP_PATH"]):
            return self.config["PSCP_PATH"]
        return self.find_executable(self.pscp_paths, "pscp")
        
    def update_config(self, key: str, value: Any):
        """Update a configuration value"""
        self.config[key] = value
        
    def get_config(self, key: str) -> Any:
        """Get a configuration value"""
        return self.config.get(key)
        
    def save_config_to_file(self, filename: str = "config.py"):
        """Save current configuration to config.py"""
        config_content = "# Palworld Server Manager Configuration\n\n"
        
        for key, value in self.config.items():
            if isinstance(value, str):
                config_content += f'{key} = "{value}"\n'
            else:
                config_content += f'{key} = {value}\n'
                
        with open(filename, "w") as f:
            f.write(config_content) 
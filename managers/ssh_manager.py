import subprocess
import os
import threading
from typing import Optional, Tuple, List

class SSHManager:
    def __init__(self, plink_path: str, pscp_path: str, session_name: str = "PalworldVPS"):
        self.plink_path = plink_path
        self.pscp_path = pscp_path
        self.session_name = session_name
        self.use_direct_connection = False
        self.ssh_host = None
        self.ssh_port = "22"
        self.ssh_username = None
        
    def set_direct_connection(self, host: str, port: str, username: str):
        """Configure direct SSH connection instead of PuTTY session"""
        self.use_direct_connection = True
        self.ssh_host = host
        self.ssh_port = port
        self.ssh_username = username
        
    def set_session_connection(self):
        """Use PuTTY session connection"""
        self.use_direct_connection = False
        
    def _get_base_cmd(self) -> List[str]:
        """Get the base command for SSH operations"""
        if self.use_direct_connection and self.ssh_host and self.ssh_username:
            return [self.plink_path, "-batch", "-ssh", f"{self.ssh_username}@{self.ssh_host}", "-P", self.ssh_port]
        else:
            return [self.plink_path, "-batch", self.session_name]
            
    def test_connection(self) -> Tuple[bool, str]:
        """Test SSH connection to the server"""
        if not self.plink_path:
            return False, "plink.exe not found"
            
        try:
            base_cmd = self._get_base_cmd()
            test_cmd = base_cmd + ["echo 'Connection test successful'"]
            
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                return True, "Connection successful"
            else:
                error_msg = result.stderr.strip()
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            return False, "Connection timed out"
        except Exception as e:
            return False, str(e)
            
    def execute_command(self, command: str, timeout: int = 30) -> Tuple[Optional[str], Optional[str]]:
        """Execute a command via SSH"""
        if not self.plink_path:
            return None, "plink.exe not found"
            
        try:
            base_cmd = self._get_base_cmd()
            cmd = base_cmd + [command]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            
            if result.returncode == 0:
                return result.stdout, result.stderr
            else:
                return None, result.stderr
                
        except subprocess.TimeoutExpired:
            return None, "Command timed out"
        except Exception as e:
            return None, str(e)
            
    def execute_sftp_commands(self, sftp_commands: List[str], timeout: int = 30) -> Tuple[Optional[str], Optional[str]]:
        """Execute SFTP commands through a single connection"""
        if not self.plink_path:
            return None, "plink.exe not found"
            
        try:
            # Create SFTP command script
            sftp_script = "\n".join(sftp_commands)
            
            # Choose connection method
            if self.use_direct_connection and self.ssh_host and self.ssh_username:
                cmd = [self.plink_path, "-batch", "-ssh", f"{self.ssh_username}@{self.ssh_host}", "-P", self.ssh_port, "sftp"]
            else:
                cmd = [self.plink_path, "-batch", self.session_name, "sftp"]
            
            result = subprocess.run(
                cmd,
                input=sftp_script,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return result.stdout, result.stderr
            else:
                return None, result.stderr
            
        except subprocess.TimeoutExpired:
            return None, "SFTP command timed out"
        except Exception as e:
            return None, str(e)
            
    def get_full_path(self, path: str) -> Tuple[Optional[str], Optional[str]]:
        """Get the full absolute path by expanding ~ and resolving relative paths"""
        # Use 'readlink -f' to get the absolute path, expanding ~
        return self.execute_command(f"readlink -f {path}")
        
    def download_file(self, remote_path: str, local_path: str) -> Tuple[bool, str]:
        """Download a file from the server using PSCP"""
        if not self.pscp_path:
            return False, "pscp.exe not found"
            
        try:
            # Get the full absolute path first
            full_path_stdout, full_path_stderr = self.get_full_path(remote_path)
            if full_path_stdout:
                full_remote_path = full_path_stdout.strip()
            else:
                # Fallback to original path if expansion fails
                full_remote_path = remote_path
                
            # Choose connection method for PSCP
            if self.use_direct_connection and self.ssh_host and self.ssh_username:
                cmd = [self.pscp_path, "-batch", "-ssh", "-P", self.ssh_port, f"{self.ssh_username}@{self.ssh_host}:{full_remote_path}", local_path]
            else:
                cmd = [self.pscp_path, "-batch", f"{self.session_name}:{full_remote_path}", local_path]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(local_path):
                return True, "Download successful"
            else:
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            return False, "Download timed out"
        except Exception as e:
            return False, str(e)
            
    def upload_file(self, local_path: str, remote_path: str) -> Tuple[bool, str]:
        """Upload a file to the server using PSCP"""
        if not os.path.exists(local_path):
            return False, "Local file not found"
            
        if not self.pscp_path:
            return False, "pscp.exe not found"
            
        try:
            # Get the full absolute path first
            full_path_stdout, full_path_stderr = self.get_full_path(remote_path)
            if full_path_stdout:
                full_remote_path = full_path_stdout.strip()
            else:
                # Fallback to original path if expansion fails
                full_remote_path = remote_path
                
            # Choose connection method for PSCP
            if self.use_direct_connection and self.ssh_host and self.ssh_username:
                cmd = [self.pscp_path, "-batch", "-ssh", "-P", self.ssh_port, local_path, f"{self.ssh_username}@{self.ssh_host}:{full_remote_path}"]
            else:
                cmd = [self.pscp_path, "-batch", local_path, f"{self.session_name}:{full_remote_path}"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return True, "Upload successful"
            else:
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            return False, "Upload timed out"
        except Exception as e:
            return False, str(e)
            
    def get_current_directory(self) -> Tuple[Optional[str], Optional[str]]:
        """Get the current directory on the server"""
        return self.execute_command("pwd")
        
    def list_directory(self, path: str = ".") -> Tuple[Optional[str], Optional[str]]:
        """List directory contents"""
        return self.execute_command(f"ls -la '{path}'")
        
    def test_directory_exists(self, path: str) -> Tuple[bool, str]:
        """Test if a directory exists on the server"""
        stdout, stderr = self.execute_command(f"test -d '{path}' && echo 'EXISTS' || echo 'NOT_FOUND'")
        
        if stdout and "EXISTS" in stdout:
            return True, "Directory exists"
        else:
            return False, "Directory not found"
            
    def test_file_exists(self, path: str) -> Tuple[bool, str]:
        """Test if a file exists on the server"""
        stdout, stderr = self.execute_command(f"test -f '{path}' && echo 'EXISTS' || echo 'NOT_FOUND'")
        
        if stdout and "EXISTS" in stdout:
            return True, "File exists"
        else:
            return False, "File not found"
            
    def find_config_file(self) -> Tuple[Optional[str], str]:
        """Find the PalWorldSettings.ini file on the server"""
        # Try to change to the Steam directory and check for the config file
        steam_path = "~/Steam/steamapps/common/PalServer/Pal/Saved/Config/LinuxServer/"
        
        # First try to list the directory contents to see if it exists and what's there
        stdout, stderr = self.execute_command(f"cd {steam_path} && ls -la")
        
        if stdout:
            # Check if PalWorldSettings.ini appears anywhere in the output
            lines = stdout.strip().split('\n')
            for line in lines:
                if 'PalWorldSettings.ini' in line:
                    return steam_path + "PalWorldSettings.ini", "Config file found"
            return None, "PalWorldSettings.ini not found in Steam directory"
        elif stderr and "No such file or directory" in stderr:
            return None, f"Steam directory not found at {steam_path}"
        else:
            return None, "Could not access Steam directory"
            
    def list_steam_config_files(self) -> Tuple[Optional[str], Optional[str]]:
        """List all files in the Steam config directory"""
        steam_path = "~/Steam/steamapps/common/PalServer/Pal/Saved/Config/LinuxServer/"
        
        return self.execute_command(f"cd {steam_path} && ls -la") 
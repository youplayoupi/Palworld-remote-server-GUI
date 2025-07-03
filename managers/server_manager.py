import subprocess
import time
from typing import Optional, Tuple, List

class PalworldServerManager:
    """Manages PalWorld server operations using SSHManager for remote execution"""
    
    def __init__(self, server_path: str, screen_session_name: str, ssh_manager, steamcmd_path: str = "steamcmd"):
        self.server_path = server_path
        self.screen_session_name = screen_session_name
        self.ssh_manager = ssh_manager
        self.steamcmd_path = steamcmd_path
        
    def is_server_running(self) -> bool:
        """Check if the PalWorld server is running in a screen session (remote)"""
        stdout, stderr = self.ssh_manager.execute_command(f"screen -list | grep {self.screen_session_name}")
        return stdout is not None and self.screen_session_name in stdout
    
    def get_server_status(self) -> Tuple[bool, str]:
        """Get detailed server status (remote)"""
        if not self.is_server_running():
            return False, "Server is not running"
        
        # Get screen session info
        stdout, stderr = self.ssh_manager.execute_command(f"screen -list | grep {self.screen_session_name}")
        if stdout:
            return True, f"Server is running in screen session: {stdout.strip()}"
        else:
            return False, "Server status unknown"
    
    def start_server(self, port: str = "8211") -> Tuple[bool, str]:
        """Start the PalWorld server in a screen session (remote), redirecting output to a log file"""
        if self.is_server_running():
            return False, "Server is already running"
        
        try:
            # Create a new screen session and start the server, redirecting output to server.log
            start_command = (
                f"screen -dmS {self.screen_session_name} bash -c "
                f"'cd {self.server_path} && ./PalServer.sh -port={port} -players=5 "
                f"-useperfthreads -NoAsyncLoadingThread -UseMultithreadForDS -NumberOfWorkerThreadsServer=3 "
                f"> server.log 2>&1'"
            )
            
            stdout, stderr = self.ssh_manager.execute_command(start_command, timeout=60)
            
            if stderr:
                return False, f"Failed to start server: {stderr}"
            
            # Wait a moment for the server to start
            time.sleep(5)
            
            # Verify the server started
            if self.is_server_running():
                return True, "Server started successfully (logging to server.log)"
            else:
                return False, "Server failed to start (screen session not found, check server.log)"
                
        except Exception as e:
            return False, f"Error starting server: {str(e)}"
    
    def stop_server(self) -> Tuple[bool, str]:
        """Stop the PalWorld server and terminate the screen session (remote)"""
        if not self.is_server_running():
            return False, "Server is not running"
        
        try:
            # Send quit command to the server
            quit_command = f"screen -S {self.screen_session_name} -X stuff $'quit\\n'"
            stdout, stderr = self.ssh_manager.execute_command(quit_command)
            
            # Wait for the server to shut down gracefully
            time.sleep(10)
            
            # Force kill the screen session if it's still running
            if self.is_server_running():
                kill_command = f"screen -S {self.screen_session_name} -X quit"
                stdout, stderr = self.ssh_manager.execute_command(kill_command)
                
                # Wait a bit more
                time.sleep(5)
                
                if self.is_server_running():
                    return False, "Failed to stop server (screen session still running)"
            
            return True, "Server stopped successfully"
            
        except Exception as e:
            return False, f"Error stopping server: {str(e)}"
    
    def restart_server(self, port: str = "8211") -> Tuple[bool, str]:
        """Restart the PalWorld server (remote)"""
        # Stop the server first
        success, message = self.stop_server()
        if not success and "not running" not in message:
            return False, f"Failed to stop server: {message}"
        
        # Wait a moment
        time.sleep(5)
        
        # Start the server
        return self.start_server(port)
    
    def update_server(self) -> Tuple[bool, str]:
        """Update the PalWorld server using SteamCMD (remote, in screen session)"""
        try:
            # Stop the server if it's running
            if self.is_server_running():
                self.log("Stopping server for update...")
                success, message = self.stop_server()
                if not success:
                    return False, f"Failed to stop server for update: {message}"
                time.sleep(10)

            # Use the configured SteamCMD path
            steamcmd_path = getattr(self, 'steamcmd_path', 'steamcmd')
            # Start SteamCMD in a detached screen session, output to log
            update_command = (
                f"screen -dmS steamcmd_update bash -c \"{steamcmd_path} +login anonymous +app_update 2394010 validate +quit | tee ~/steamcmd_update.log\""
            )
            stdout, stderr = self.ssh_manager.execute_command(update_command, timeout=30)
            if stderr:
                return False, f"Failed to start update: {stderr}"
            return True, "Update started in background. Monitor progress via log."
        except Exception as e:
            return False, f"Error updating server: {str(e)}"

    def is_update_running(self) -> bool:
        """Check if the steamcmd_update screen session is running"""
        stdout, stderr = self.ssh_manager.execute_command("screen -list | grep steamcmd_update")
        return stdout is not None and "steamcmd_update" in stdout

    def get_update_log(self, lines: int = 50) -> Tuple[Optional[str], Optional[str]]:
        """Fetch the last N lines of the update log"""
        cat_command = f"tail -n {lines} ~/steamcmd_update.log"
        stdout, stderr = self.ssh_manager.execute_command(cat_command)
        if stdout:
            return stdout, None
        else:
            return None, stderr or "No log output found."
    
    def get_server_logs(self, lines: int = 50) -> Tuple[Optional[str], Optional[str]]:
        """Get recent server logs from the screen session (remote)"""
        if not self.is_server_running():
            return None, "Server is not running"
        
        # Get logs from the screen session (remote hardcopy to /tmp, then cat)
        log_command = f"screen -S {self.screen_session_name} -X hardcopy /tmp/palworld_logs.txt"
        stdout, stderr = self.ssh_manager.execute_command(log_command)
        
        if stderr:
            return None, f"Failed to get logs: {stderr}"
        
        # Read the log file remotely
        try:
            cat_command = "tail -n {} /tmp/palworld_logs.txt".format(lines)
            log_stdout, log_stderr = self.ssh_manager.execute_command(cat_command)
            if log_stdout:
                return log_stdout, None
            else:
                return None, f"Failed to read log file: {log_stderr}"
        except Exception as e:
            return None, f"Failed to read log file: {str(e)}"
    
    def send_command(self, command: str) -> Tuple[bool, str]:
        """Send a command to the running server (remote)"""
        if not self.is_server_running():
            return False, "Server is not running"
        
        try:
            # Send command to the screen session
            screen_command = f"screen -S {self.screen_session_name} -X stuff $'{command}\\n'"
            stdout, stderr = self.ssh_manager.execute_command(screen_command)
            
            if stderr:
                return False, f"Failed to send command: {stderr}"
            
            return True, f"Command '{command}' sent successfully"
            
        except Exception as e:
            return False, f"Error sending command: {str(e)}"
    
    def get_server_info(self) -> dict:
        """Get comprehensive server information (remote)"""
        info = {
            "running": self.is_server_running(),
            "screen_session": self.screen_session_name,
            "server_path": self.server_path
        }
        
        if info["running"]:
            status, message = self.get_server_status()
            info["status_message"] = message
            
            # Try to get basic process info
            stdout, stderr = self.ssh_manager.execute_command(f"ps aux | grep PalServer | grep -v grep")
            if stdout:
                info["process_info"] = stdout.strip()
        
        return info
    
    def log(self, message: str):
        """Log a message (can be overridden for custom logging)"""
        print(f"[PalworldServerManager] {message}")
    
    def save_and_download_backup(self, local_backup_path: Optional[str] = None) -> tuple:
        """
        Create a tar.gz backup of the Palworld Saved folder on the VPS, download it, and clean up.
        Returns (success: bool, message: str, local_file_path: str or None)
        """
        import datetime
        # Define remote and local paths
        date_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        remote_saved_dir = f"{self.server_path}/Pal/Saved"
        remote_archive = f"/tmp/palworld_saved_backup_{date_str}.tar.gz"
        if local_backup_path is None:
            local_backup_path = f"downloads/PalServer_Saved_backup_{date_str}.tar.gz"

        # Resolve ~ to full path for server_path
        full_server_path, _ = self.ssh_manager.get_full_path(self.server_path)
        if not full_server_path:
            return False, f"Failed to resolve full path for {self.server_path}", None
        full_server_path = full_server_path.strip()

        # 1. Create the archive on the VPS
        tar_cmd = f"tar czf '{remote_archive}' -C '{full_server_path}/Pal' Saved"
        stdout, stderr = self.ssh_manager.execute_command(tar_cmd, timeout=120)
        if stderr:
            return False, f"Failed to create archive: {stderr}", None

        # 2. Download the archive
        success, message = self.ssh_manager.download_file(remote_archive, local_backup_path)
        if not success:
            # Try to clean up remote archive even if download failed
            self.ssh_manager.execute_command(f"rm -f '{remote_archive}'")
            return False, f"Download failed: {message}", None

        # 3. Clean up remote archive
        self.ssh_manager.execute_command(f"rm -f '{remote_archive}'")

        return True, f"Backup saved and downloaded to {local_backup_path}", local_backup_path 
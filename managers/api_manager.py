import requests
import json
import base64
from typing import Optional, Dict, Any, List, Tuple, Union

class PalworldAPIManager:
    def __init__(self, api_base: str, username: str, password: str):
        self.api_base = api_base
        self.username = username
        self.password = password
        
        # API endpoints
        self.endpoints = {
            "info": "/v1/api/info",
            "players": "/v1/api/players",
            "kick": "/v1/api/kick",
            "ban": "/v1/api/ban",
            "teleport": "/v1/api/teleport",
            "shutdown": "/v1/api/shutdown",
            "save": "/v1/api/save",
            "announce": "/v1/api/announce"
        }
        
    def _create_auth_header(self) -> str:
        """Create Basic Authentication header"""
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded_credentials}"
        
    def _make_request(self, endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Make API request to Palworld server"""
        try:
            url = f"{self.api_base}{endpoint}"
            
            headers = {
                "Accept": "application/json",
                "Authorization": self._create_auth_header()
            }
            
            # Add Content-Type for POST requests
            if method == "POST" and data:
                headers["Content-Type"] = "application/json"
            
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=10)
            else:
                return None
            
            # Debug: Print response details
            print(f"API Request: {method} {url}")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Text: {response.text[:500]}...")  # First 500 chars
            
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError as e:
                    print(f"JSON Decode Error: {e}")
                    print(f"Raw Response: {response.text}")
                    return None
            elif response.status_code == 401:
                print("Authentication failed")
                return None
            else:
                print(f"HTTP Error: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Request Exception: {e}")
            return None
            
    def test_connection(self) -> Tuple[bool, str]:
        """Test API connection to the server"""
        # First test basic connectivity
        try:
            response = requests.get(f"{self.api_base}/v1/api/info", timeout=5)
            if response.status_code == 401:
                return True, "Server is reachable but requires authentication"
            elif response.status_code == 200:
                return True, "Server responded without authentication (check if API is enabled)"
            else:
                return False, f"Server responded with status: {response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, f"Cannot reach server: {str(e)}"
            
    def get_server_info(self) -> Optional[Dict[str, Any]]:
        """Get server information"""
        result = self._make_request(self.endpoints["info"])
        if isinstance(result, dict):
            return result
        return None
        
    def get_players(self) -> Optional[List[Dict[str, Any]]]:
        """Get player list"""
        print("Getting players list...")
        result = self._make_request(self.endpoints["players"])
        print(f"Players result type: {type(result)}")
        print(f"Players result: {result}")
        
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "players" in result:
            # Some APIs wrap the players list in a dict
            return result["players"]
        elif isinstance(result, dict) and "data" in result:
            # Some APIs wrap the players list in a data field
            return result["data"]
        else:
            print(f"Unexpected players response format: {result}")
            return None
        
    def kick_player(self, player_uid: str) -> bool:
        """Kick a player"""
        data = {"playeruid": player_uid}
        result = self._make_request(self.endpoints["kick"], method="POST", data=data)
        return result is not None
        
    def ban_player(self, player_uid: str) -> bool:
        """Ban a player"""
        data = {"playeruid": player_uid}
        result = self._make_request(self.endpoints["ban"], method="POST", data=data)
        return result is not None
        
    def teleport_player(self, player_uid: str, x: float, y: float, z: float) -> bool:
        """Teleport a player to coordinates"""
        data = {
            "playeruid": player_uid,
            "x": x,
            "y": y,
            "z": z
        }
        result = self._make_request(self.endpoints["teleport"], method="POST", data=data)
        return result is not None
        
    def save_world(self) -> bool:
        """Save the world"""
        result = self._make_request(self.endpoints["save"], method="POST")
        return result is not None
        
    def send_announcement(self, message: str) -> bool:
        """Send an announcement"""
        data = {"message": message}
        result = self._make_request(self.endpoints["announce"], method="POST", data=data)
        return result is not None
        
    def shutdown_server(self) -> bool:
        """Shutdown the server"""
        result = self._make_request(self.endpoints["shutdown"], method="POST")
        return result is not None
        
    def update_credentials(self, username: str, password: str):
        """Update API credentials"""
        self.username = username
        self.password = password
        
    def update_api_base(self, api_base: str):
        """Update API base URL"""
        self.api_base = api_base 
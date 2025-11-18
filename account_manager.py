import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, Optional
import time


class AccountManager:
    """Handles account registration, login, and game room playing"""
    
    def __init__(self, proxy_url=None):
        self.session = requests.Session()
        self.base_url = "https://gladecontest.ca/"
        self.login_form_id = "gform_3"
        self.register_form_id = "gform_1"
        self.proxy_url = proxy_url
        
        # Set proxy if provided
        if self.proxy_url:
            self.set_proxy(self.proxy_url)
    
    def set_proxy(self, proxy_url):
        """Set proxy for the session (auto-rotating proxy URL)"""
        try:
            if proxy_url and proxy_url.strip():
                # Support both http and https
                self.session.proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
                print(f"🔄 Proxy enabled: {proxy_url}")
        except Exception as e:
            print(f"⚠️ Error setting proxy: {e}")
    
    def register_account(self, account: Dict) -> bool:
        """Register a new account"""
        try:
            print(f"📝 Registering account: {account['email']}")
            
            # Load registration page
            r = self.session.get(self.base_url)
            soup = BeautifulSoup(r.text, "html.parser")
            
            form = soup.find("form", {"id": self.register_form_id})
            if not form:
                raise Exception("Could not find registration form (gform_1).")
            
            # Extract hidden fields
            hidden = {}
            for inp in form.find_all("input", {"type": "hidden"}):
                if inp.get("name"):
                    hidden[inp["name"]] = inp.get("value", "")
            
            # Build payload
            payload = hidden.copy()
            payload.update({
                "input_1": account['first_name'],
                "input_3": account['last_name'],
                "input_11": account['password'],
                "input_11_2": account['password'],
                "input_4": account['email'],
                "input_13": account['phone_number'],
                
                # Required checkboxes
                "input_6.1": "1",
                "input_6.2": form.find("input", {"name": "input_6.2"}).get("value", "") if form.find("input", {"name": "input_6.2"}) else "",
                "input_6.3": "1",
                
                "input_12.1": "1",
                "input_12.2": form.find("input", {"name": "input_12.2"}).get("value", "") if form.find("input", {"name": "input_12.2"}) else "",
                "input_12.3": "1",
                
                "input_7": "",
                "input_14": "",
            })
            
            # Convert to multipart format
            files = {k: (None, v) for k, v in payload.items()}
            
            # Submit form
            resp = self.session.post(self.base_url, files=files)
            
            if resp.status_code == 200:
                print(f"✅ Account registered: {account['email']}")
                return True
            else:
                print(f"❌ Registration failed for {account['email']}: Status {resp.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error registering {account['email']}: {str(e)}")
            return False
    
    def login(self, email: str, password: str) -> bool:
        """Login to an account"""
        try:
            print(f"🔐 Logging in: {email}")
            
            home = self.session.get(self.base_url)
            soup = BeautifulSoup(home.text, "html.parser")
            
            form = soup.find("form", {"id": self.login_form_id})
            if not form:
                raise Exception("Login form gform_3 not found")
            
            hidden = {
                i.get("name"): i.get("value", "")
                for i in form.find_all("input", {"type": "hidden"})
                if i.get("name")
            }
            
            payload = hidden.copy()
            payload.update({
                "input_1": email,
                "input_3": password
            })
            
            multipart = {k: (None, v) for k, v in payload.items()}
            
            resp = self.session.post(self.base_url, files=multipart)
            
            if "Login to play" in resp.text:
                print(f"❌ Login failed for {email}")
                return False
            
            print(f"✅ Logged in: {email}")
            return True
            
        except Exception as e:
            print(f"❌ Error logging in {email}: {str(e)}")
            return False
    
    def extract_game_nonce(self, html: str) -> Optional[str]:
        """Extract gameAjax.nonce from room page"""
        m = re.search(
            r"gameAjax\s*=\s*\{\s*ajaxurl:\s*'[^']*',\s*nonce:\s*'([a-zA-Z0-9]+)'",
            html
        )
        return m.group(1) if m else None
    
    def play_room(self, room_number: int, room_key: str) -> bool:
        """Play a game room"""
        try:
            print(f"🎮 Playing Room {room_number}...")
            
            room_url = f"{self.base_url}game-room/room-{room_number}/"
            room_resp = self.session.get(room_url)
            html = room_resp.text
            
            nonce = self.extract_game_nonce(html)
            if not nonce:
                print(f"❌ Could not find nonce for Room {room_number}")
                return False
            
            print(f"🟢 Room {room_number} nonce: {nonce}")
            
            # Submit score
            score_payload = {
                "action": "update_user_score",
                "_ajax_nonce": nonce,
                "rtm_api_room_key": room_key,
                "user_score": "10"
            }
            
            score_resp = self.session.post(
                f"{self.base_url}wp-admin/admin-ajax.php",
                data=score_payload
            )
            
            print(f"📨 Room {room_number} submit status: {score_resp.status_code}")
            print(f"🧾 Response: {score_resp.text}")
            
            if score_resp.status_code == 200:
                print(f"✅ Room {room_number} played successfully")
                return True
            else:
                print(f"❌ Room {room_number} play failed")
                return False
                
        except Exception as e:
            print(f"❌ Error playing Room {room_number}: {str(e)}")
            return False
    
    def get_room_key(self, room_number: int) -> str:
        """Get room key based on room number"""
        room_keys = {
            1: "Misc1",
            2: "Misc2",
            3: "Misc3"
        }
        return room_keys.get(room_number, "Misc1")
    
    def process_account_for_room(self, account: Dict, room_number: int, 
                                 register_first: bool = False) -> bool:
        """
        Process an account for a specific room
        If register_first is True, register the account first (only for room 1)
        """
        try:
            # Register account if needed (only for room 1)
            if register_first and room_number == 1:
                if not self.register_account(account):
                    return False
                # Wait a bit after registration
                time.sleep(2)
            
            # Login
            if not self.login(account['email'], account['password']):
                return False
            
            # Wait a bit after login
            time.sleep(1)
            
            # Play room
            room_key = self.get_room_key(room_number)
            if not self.play_room(room_number, room_key):
                return False
            
            print(f"✅ Successfully processed {account['email']} for Room {room_number}\n")
            return True
            
        except Exception as e:
            print(f"❌ Error processing account {account['email']}: {str(e)}\n")
            return False

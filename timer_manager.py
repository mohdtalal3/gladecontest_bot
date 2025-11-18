from datetime import datetime, timedelta
from typing import Dict, Optional


class TimerManager:
    """Manages 24-hour cooldown timers between rooms"""
    
    COOLDOWN_HOURS = 24
    
    @staticmethod
    def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
        """Parse ISO format timestamp string to datetime"""
        if not timestamp_str:
            return None
        try:
            return datetime.fromisoformat(timestamp_str)
        except:
            return None
    
    @staticmethod
    def is_ready_for_next_room(account: Dict, next_room_number: int) -> bool:
        """
        Check if account is ready to play the next room
        Room 1: Always ready if not played
        Room 2: Ready if room 1 completed and 24 hours passed
        Room 3: Ready if room 2 completed and 24 hours passed
        """
        if next_room_number == 1:
            # Room 1 can always be played if not completed
            return account.get('room1_status', 'false') == 'false'
        
        elif next_room_number == 2:
            # Must have completed room 1
            room1_status = account.get('room1_status', 'false')
            if room1_status != 'true':
                print(f"Debug: Account {account.get('email')} - Room 1 status: {room1_status} (not 'true')")
                return False
            
            # Already played room 2
            room2_status = account.get('room2_status', 'false')
            if room2_status == 'true':
                print(f"Debug: Account {account.get('email')} - Room 2 already completed")
                return False
            
            # Check 24-hour cooldown from room 1
            room1_timestamp_str = account.get('room1_timestamp', '')
            room1_timestamp = TimerManager.parse_timestamp(room1_timestamp_str)
            if not room1_timestamp:
                print(f"Debug: Account {account.get('email')} - No valid room1_timestamp")
                return False
            
            time_elapsed = datetime.now() - room1_timestamp
            cooldown_required = timedelta(hours=TimerManager.COOLDOWN_HOURS)
            
            print(f"Debug: Account {account.get('email')}")
            print(f"  - Room1 timestamp: {room1_timestamp_str}")
            print(f"  - Current time: {datetime.now().isoformat()}")
            print(f"  - Time elapsed: {time_elapsed}")
            print(f"  - Cooldown required: {cooldown_required}")
            print(f"  - Ready: {time_elapsed >= cooldown_required}")
            
            return time_elapsed >= cooldown_required
        
        elif next_room_number == 3:
            # Must have completed room 2
            if account.get('room2_status', 'false') != 'true':
                return False
            
            # Already played room 3
            if account.get('room3_status', 'false') == 'true':
                return False
            
            # Check 24-hour cooldown from room 2
            room2_timestamp = TimerManager.parse_timestamp(
                account.get('room2_timestamp', '')
            )
            if not room2_timestamp:
                return False
            
            time_elapsed = datetime.now() - room2_timestamp
            return time_elapsed >= timedelta(hours=TimerManager.COOLDOWN_HOURS)
        
        return False
    
    @staticmethod
    def get_time_until_ready(account: Dict, next_room_number: int) -> Optional[timedelta]:
        """
        Get time remaining until account is ready for next room
        Returns None if already ready or unable to calculate
        """
        if next_room_number == 1:
            return timedelta(0)  # Room 1 is always ready
        
        elif next_room_number == 2:
            if account.get('room1_status', 'false') != 'true':
                return None  # Room 1 not completed
            
            room1_timestamp = TimerManager.parse_timestamp(
                account.get('room1_timestamp', '')
            )
            if not room1_timestamp:
                return None
            
            time_elapsed = datetime.now() - room1_timestamp
            cooldown_time = timedelta(hours=TimerManager.COOLDOWN_HOURS)
            
            if time_elapsed >= cooldown_time:
                return timedelta(0)  # Ready now
            
            return cooldown_time - time_elapsed
        
        elif next_room_number == 3:
            if account.get('room2_status', 'false') != 'true':
                return None  # Room 2 not completed
            
            room2_timestamp = TimerManager.parse_timestamp(
                account.get('room2_timestamp', '')
            )
            if not room2_timestamp:
                return None
            
            time_elapsed = datetime.now() - room2_timestamp
            cooldown_time = timedelta(hours=TimerManager.COOLDOWN_HOURS)
            
            if time_elapsed >= cooldown_time:
                return timedelta(0)  # Ready now
            
            return cooldown_time - time_elapsed
        
        return None
    
    @staticmethod
    def format_time_remaining(td: Optional[timedelta]) -> str:
        """Format timedelta to readable string"""
        if td is None:
            return "Not available"
        
        if td.total_seconds() <= 0:
            return "Ready now"
        
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m remaining"
        else:
            return f"{minutes}m remaining"
    
    @staticmethod
    def filter_ready_accounts(accounts: list, room_number: int) -> list:
        """Filter accounts that are ready to play the specified room"""
        ready_accounts = []
        for account in accounts:
            if TimerManager.is_ready_for_next_room(account, room_number):
                ready_accounts.append(account)
        return ready_accounts

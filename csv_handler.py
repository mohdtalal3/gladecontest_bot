import csv
from datetime import datetime
from typing import List, Dict


class CSVHandler:
    """Handles reading and writing CSV files with account and room status data"""
    
    FIELDNAMES = [
        'email',
        'password',
        'first_name',
        'last_name',
        'phone_number',
        'room1_status',
        'room1_timestamp',
        'room2_status',
        'room2_timestamp',
        'room3_status',
        'room3_timestamp'
    ]
    
    @staticmethod
    def read_csv(filepath: str) -> List[Dict]:
        """Read CSV file and return list of account dictionaries"""
        accounts = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Normalize status values to lowercase for consistency
                    room1_status = row.get('room1_status', 'false').lower()
                    room2_status = row.get('room2_status', 'false').lower()
                    room3_status = row.get('room3_status', 'false').lower()
                    
                    # Initialize status fields if not present
                    account = {
                        'email': row.get('email', ''),
                        'password': row.get('password', ''),
                        'first_name': row.get('first_name', ''),
                        'last_name': row.get('last_name', ''),
                        'phone_number': row.get('phone_number', ''),
                        'room1_status': room1_status,
                        'room1_timestamp': row.get('room1_timestamp', ''),
                        'room2_status': room2_status,
                        'room2_timestamp': row.get('room2_timestamp', ''),
                        'room3_status': room3_status,
                        'room3_timestamp': row.get('room3_timestamp', '')
                    }
                    accounts.append(account)
        except Exception as e:
            raise Exception(f"Error reading CSV: {str(e)}")
        
        return accounts
    
    @staticmethod
    def write_csv(filepath: str, accounts: List[Dict]):
        """Write accounts list to CSV file"""
        try:
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=CSVHandler.FIELDNAMES)
                writer.writeheader()
                writer.writerows(accounts)
        except Exception as e:
            raise Exception(f"Error writing CSV: {str(e)}")
    
    @staticmethod
    def update_room_status(account: Dict, room_number: int, status: bool = True):
        """Update room status and timestamp for an account"""
        room_key = f'room{room_number}_status'
        timestamp_key = f'room{room_number}_timestamp'
        
        account[room_key] = 'true' if status else 'false'
        if status:
            account[timestamp_key] = datetime.now().isoformat()
        
        return account
    
    @staticmethod
    def get_output_filename(room_number: int) -> str:
        """Get output filename based on room number"""
        if room_number == 1:
            return 'ready_for_room2.csv'
        elif room_number == 2:
            return 'ready_for_room3.csv'
        elif room_number == 3:
            return 'completed_process.csv'
        return 'output.csv'

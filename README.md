# Glade Contest Bot - Room Manager

A comprehensive automation tool for managing Glade Contest accounts across multiple game rooms with a user-friendly GUI.

## Features

- ✅ **Automated Account Registration** - Register new accounts automatically (Room 1 only)
- 🎮 **Multi-Room Support** - Play Rooms 1, 2, and 3
- ⚡ **Multi-Threading Support** - Process multiple accounts concurrently (1-50 threads)
- 🔄 **Auto-Rotating Proxy Support** - Use rotating proxies for requests
- ⏰ **24-Hour Timer Management** - Automatic cooldown tracking between rooms
- 💾 **Incremental CSV Saves** - Progress saved after each account
- 📊 **Real-time Progress Tracking** - Live status updates and progress bar
- 🎯 **Smart Account Filtering** - Only processes accounts ready for selected room
- 📁 **Automatic File Output** - Generates organized CSV files for each stage

## Installation

1. **Install Python 3.8+** (if not already installed)

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install requests beautifulsoup4 PyQt6
```

## Usage

### 1. Prepare Your CSV File

Create a CSV file with the following columns:
- `email` - Account email address
- `password` - Account password
- `first_name` - First name
- `last_name` - Last name
- `phone_number` - Phone number (format: +1XXXXXXXXXX)

**Example (sample_accounts.csv):**
```csv
email,password,first_name,last_name,phone_number
user1@hotmail.com,Password123!,John,Doe,+14161234567
user2@hotmail.com,Password123!,Jane,Smith,+14162345678
```

### 2. Run the Application

```bash
python gui_app.py
```

### 3. Process Accounts

1. **Click "Select CSV File"** and choose your accounts file
2. **(Optional) Configure Proxy**:
   - Enter your auto-rotating proxy URL in the format: `http://username:password@proxy.com:port`
   - Click "Test Proxy" to verify it's working
   - Leave empty to use direct connection
3. **(Optional) Configure Threading**:
   - Set the number of concurrent threads (1-50)
   - Recommended: 5-20 threads for optimal performance
   - More threads = faster processing (but more resource usage)
4. **Select a room** to process:
   - **Room 1**: Registers new accounts and plays Room 1
   - **Room 2**: Plays Room 2 (requires Room 1 completed + 24 hours)
   - **Room 3**: Plays Room 3 (requires Room 2 completed + 24 hours)
5. **Click "Start Processing"**
6. Monitor progress in the log window

### 4. Output Files

The bot automatically generates CSV files after each stage:

- **After Room 1**: `ready_for_room2.csv` - Accounts ready for Room 2 in 24 hours
- **After Room 2**: `ready_for_room3.csv` - Accounts ready for Room 3 in 24 hours
- **After Room 3**: `completed_process.csv` - All rooms completed

Each output file includes:
- Original account data
- Room status fields (`room1_status`, `room2_status`, `room3_status`)
- Timestamps for each room completion
- Progress saved incrementally (every account processed)

## Workflow

### Complete 3-Room Process

**Day 1:**
1. Upload `accounts.csv`
2. Select Room 1 and start processing
3. Bot registers accounts and plays Room 1
4. Output: `ready_for_room2.csv` (with Room 1 completed timestamps)

**Day 2 (24+ hours later):**
1. Upload `ready_for_room2.csv` or reload file
2. Select Room 2 and start processing
3. Bot plays Room 2 (no registration needed)
4. Output: `ready_for_room3.csv` (with Room 2 completed timestamps)

**Day 3 (24+ hours later):**
1. Upload `ready_for_room3.csv` or reload file
2. Select Room 3 and start processing
3. Bot plays Room 3
4. Output: `completed_process.csv` (all rooms completed)

## Features Explained

### Multi-Threading Support
- Process multiple accounts concurrently for faster execution
- Configurable thread count (1-50 threads)
- Each thread handles account registration, login, and room playing independently
- Thread-safe operations with proper synchronization
- Recommended settings:
  - **Small batches (< 10 accounts)**: 1-5 threads
  - **Medium batches (10-50 accounts)**: 5-10 threads
  - **Large batches (50+ accounts)**: 10-20 threads
- Real-time thread status in logs (shows which thread is processing which account)

### Proxy Support
- Configure auto-rotating proxy URLs for enhanced privacy
- Supports HTTP/HTTPS proxies with authentication
- Format: `http://username:password@proxy.com:port`
- Test proxy functionality before processing
- Each thread uses the configured proxy
- Leave empty for direct connection

### 24-Hour Timer System
- Tracks when each account completes each room
- Automatically filters out accounts not yet ready
- Shows time remaining until accounts are eligible
- Prevents premature room attempts

### Incremental Saving
- Progress saved after each account is processed
- Safe to stop and resume at any time
- No data loss if interrupted
- Each account update immediately written to output file

### Smart Account Management
- **Room 1**: Requires registration → Creates new accounts
- **Room 2 & 3**: Uses existing accounts → No registration needed
- Automatic session management
- Handles login and game nonce extraction

### GUI Features
- Real-time status updates
- Progress bar showing completion
- Account readiness counter
- Timer display for next available accounts
- Stop/resume capability
- File reload functionality
- Proxy configuration with test functionality
- Multi-threading configuration

## File Structure

```
├── gui_app.py              # Main GUI application
├── account_manager.py      # Registration, login, and game playing logic
├── csv_handler.py          # CSV reading/writing utilities
├── timer_manager.py        # 24-hour cooldown management
├── requirements.txt        # Python dependencies
├── sample_accounts.csv     # Example input file
└── README.md              # This file
```

## CSV File Format

### Input Format (Initial)
```csv
email,password,first_name,last_name,phone_number
user@email.com,Password123,John,Doe,+14161234567
```

### Output Format (After Processing)
```csv
email,password,first_name,last_name,phone_number,room1_status,room1_timestamp,room2_status,room2_timestamp,room3_status,room3_timestamp
user@email.com,Password123,John,Doe,+14161234567,true,2025-11-18T10:30:45.123456,false,,false,
```

## Troubleshooting

### Proxy Issues
- **Proxy test fails**: Verify the proxy URL format and credentials
- **Slow requests**: Normal with some proxy services, be patient
- **Connection errors**: Try without proxy first to verify account credentials
- **Rotating proxy**: The system automatically uses your proxy URL for all requests

### "No accounts are ready for Room X"
- Check that previous room is completed (`roomX_status = true`)
- Verify 24 hours have passed since previous room
- Use "Reload File" to refresh account status

### Registration Failures
- Verify email format is valid
- Check password meets requirements
- Ensure phone number format: +1XXXXXXXXXX
- Check internet connection

### Login Failures
- Verify credentials are correct
- Account may already be registered
- Try manual login to verify account exists

## Notes

- **Registration only needed for Room 1** - Subsequent rooms use existing accounts
- **24-hour cooldown is mandatory** - System enforces wait time between rooms
- **Incremental saves protect progress** - Safe to stop/resume anytime
- **One room at a time** - Select only one room checkbox at a time
- **Output files auto-named** - Based on which room was processed

## Support

For issues or questions:
1. Check the log output in the GUI for error messages
2. Verify CSV file format matches requirements
3. Ensure all dependencies are installed
4. Check internet connectivity

## Advanced Usage

### Using Proxies

The bot supports auto-rotating proxies to help distribute requests and avoid rate limits:

**Proxy URL Formats:**
```
# Basic HTTP proxy
http://proxy.example.com:8080

# Proxy with authentication
http://username:password@proxy.example.com:8080

# HTTPS proxy
https://username:password@proxy.example.com:8080
```

**Popular Proxy Services:**
- Rotating residential proxies (recommended for account registration)
- Datacenter proxies
- Mobile proxies

**How to Use:**
1. Enter your proxy URL in the "Proxy Configuration" section
2. Click "Test Proxy" to verify it works
3. The bot will automatically use this proxy for all requests
4. Leave empty to use direct connection (no proxy)

**Benefits:**
- Distribute requests across multiple IPs
- Avoid rate limiting
- Better success rates for bulk operations
- Support for rotating proxy services

### Processing Multiple Batches
You can run multiple CSV files through the system:
```bash
# Process batch 1
python gui_app.py  # Load batch1.csv, process Room 1

# Process batch 2
python gui_app.py  # Load batch2.csv, process Room 1
```

### Resuming After Interruption
If processing is interrupted:
1. The last output file contains all successfully processed accounts
2. Simply reload that file and continue
3. Incremental saves ensure no data loss

### Testing with Small Batches
Test with 1-2 accounts first to verify everything works before processing large batches.

## License

This tool is for educational purposes only. Use responsibly and in accordance with the website's terms of service.

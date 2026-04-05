import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

DB_FILE = Path(__file__).parent / "notes_registry.db"

def init_db():
    """Database aur table banata hai agar nahi bani ho."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scanned_files (
            file_hash TEXT PRIMARY KEY,
            original_name TEXT,
            subject TEXT,
            final_path TEXT,
            scan_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_file_hash(filepath: Path) -> str:
    """File ka DNA (SHA-256 Hash) nikalta hai. Yeh 100% accurate deduplication hai."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        # File ko chhote chunks mein padhte hain taaki RAM full na ho (e.g. 500MB file ke liye)
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def check_duplicate(filepath: Path) -> dict | None:
    """Check karta hai ki kya yeh file pehle scan ho chuki hai."""
    file_hash = get_file_hash(filepath)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT original_name, subject, final_path, scan_date FROM scanned_files WHERE file_hash = ?", (file_hash,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "original_name": result[0],
            "subject": result[1],
            "final_path": result[2],
            "scan_date": result[3]
        }
    return None

def register_file(filepath: Path, original_name: str, subject: str, final_path: str):
    """Nayi file ka record database mein save karta hai."""
    file_hash = get_file_hash(filepath)
    scan_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO scanned_files 
        (file_hash, original_name, subject, final_path, scan_date) 
        VALUES (?, ?, ?, ?, ?)
    ''', (file_hash, original_name, subject, final_path, scan_date))
    conn.commit()
    conn.close()

# Start hote hi database initialise kar do
init_db()
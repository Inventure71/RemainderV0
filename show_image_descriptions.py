#!/usr/bin/env python3
"""
Script to display all image descriptions stored in the database.
"""

import os
import sqlite3
import sys

# Determine the application directory
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    app_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'RemainderApp')
else:
    app_dir = os.getcwd()

# Database path
db_path = os.path.join(app_dir, "Databases", "messages.db")

def get_image_descriptions():
    """Get all image descriptions from the database."""
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return []
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query all images with descriptions
        cursor.execute("""
            SELECT mi.id, mi.message_id, mi.file_path, mi.description, m.content
            FROM message_images mi
            JOIN messages m ON mi.message_id = m.id
            WHERE mi.description IS NOT NULL AND mi.description != ''
            ORDER BY mi.id DESC
        """)
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    except Exception as e:
        print(f"Error accessing database: {e}")
        return []

def display_descriptions(descriptions):
    """Display image descriptions in a readable format."""
    if not descriptions:
        print("No image descriptions found. Process some images first.")
        return
    
    print(f"\nFound {len(descriptions)} image descriptions:\n")
    print("=" * 80)
    
    for i, img in enumerate(descriptions):
        file_name = os.path.basename(img['file_path'])
        
        # Truncate content if it's too long
        content = img['content']
        if len(content) > 100:
            content = content[:100] + "..."
        
        print(f"\nIMAGE {i+1}: {file_name}")
        print(f"ID: {img['id']} | Message ID: {img['message_id']}")
        print(f"File path: {img['file_path']}")
        print(f"Message content: {content}")
        print("\nDESCRIPTION:")
        print("-" * 40)
        print(img['description'])
        print("=" * 80)

if __name__ == "__main__":
    descriptions = get_image_descriptions()
    display_descriptions(descriptions)
    
    if descriptions:
        print(f"\nTotal: {len(descriptions)} image descriptions found.")
    
    input("\nPress Enter to exit...") 
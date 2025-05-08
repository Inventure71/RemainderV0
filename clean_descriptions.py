#!/usr/bin/env python3
"""
Script to clean up existing image descriptions that contain raw JSON.
"""

import os
import json
import sqlite3
import sys

# Determine the application directory
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    app_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'RemainderApp')
else:
    app_dir = os.getcwd()

# Database path
db_path = os.path.join(app_dir, "Databases", "messages.db")

def clean_image_descriptions():
    """Clean up existing image descriptions that contain raw JSON."""
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all images with descriptions
        cursor.execute("""
            SELECT id, description FROM message_images 
            WHERE description IS NOT NULL AND description != ''
        """)
        
        updates = 0
        for row in cursor.fetchall():
            img_id, description = row
            
            if "Auto-generated description: ```json" in description:
                try:
                    print(f"Cleaning description for image ID {img_id}...")
                    
                    # Extract the JSON content
                    json_str = description.split("```json")[1].split("```")[0].strip()
                    json_data = json.loads(json_str)
                    
                    # Format the cleaned description
                    clean_description = ""
                    for img_data in json_data.get('images', []):
                        if clean_description:
                            clean_description += "\n\n"
                            
                        # Add the description
                        desc = img_data.get('description', '')
                        if desc:
                            clean_description += f"{desc}"
                        
                        # Add text content if present
                        text = img_data.get('text_content')
                        if text and text.lower() != 'null':
                            clean_description += f"\n\nText content:\n{text}"
                    
                    # Display before/after for verification
                    print("\nBEFORE:")
                    print("-" * 40)
                    print(description[:200] + "..." if len(description) > 200 else description)
                    print("\nAFTER:")
                    print("-" * 40)
                    print(clean_description)
                    print()
                    
                    # Update the database
                    if clean_description:
                        cursor.execute(
                            "UPDATE message_images SET description = ? WHERE id = ?",
                            (clean_description, img_id)
                        )
                        updates += 1
                        
                except Exception as e:
                    print(f"Error cleaning description for image ID {img_id}: {e}")
                    continue
        
        conn.commit()
        print(f"Successfully cleaned {updates} image descriptions.")
        return True
            
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        print(traceback.format_exc())
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def clear_image_descriptions():
    """Clear all image descriptions to allow reprocessing."""
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Clear all descriptions
        cursor.execute("UPDATE message_images SET description = NULL")
        affected = cursor.rowcount
        conn.commit()
        
        print(f"Cleared {affected} image descriptions.")
        return True
            
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        print(traceback.format_exc())
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    # If an argument is provided and it's "clear", clear all descriptions
    if len(sys.argv) > 1 and sys.argv[1].lower() == "clear":
        clear_image_descriptions()
    else:
        # Otherwise clean the descriptions
        clean_image_descriptions()
    
    input("\nPress Enter to exit...") 
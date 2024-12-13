import asyncio
import curses
import pandas as pd
import re
import subprocess
import threading
import time
from threading import Timer

# Add these variables at the global scope
speech_timer = None
last_spoken_term = ""
debounce_timer = None

# Global variables
scroll_position = 0  # Initialize scroll_position globally
results = pd.DataFrame()  # Initialize results as an empty DataFrame
warning = ""  # Initialize warning as an empty string

MAX_SEARCH_TERM_LENGTH = 100  # Set a maximum length for the search term

# Function to read data from Google Sheets CSV
async def load_data(sheet_url):
    """Asynchronously read data from Google Sheets CSV"""
    try:
        data = await asyncio.to_thread(pd.read_csv, sheet_url)
        return data
    except Exception as e:
        return None
    
# Function to filter data based on search term
def search_data(data, search_term):
    # Check if data is empty
    if data is None or data.empty:
        return pd.DataFrame(), "Warning: No data loaded from CSV file!"
    
    if search_term == "":
        return pd.DataFrame(), ""
        
    # Escape special regex characters in the search term
    search_term = re.escape(search_term)
    
    # Perform case-insensitive search across all columns using vectorized operations
    mask = data.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
    filtered = data[mask]
    
    return filtered, ""

def wrap_text(text, width):
    """Break text into lines on word boundaries"""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= width:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    return lines

async def debounced_speak(text):
    """Speak text after a delay, canceling any pending speech"""
    global speech_timer, last_spoken_term
    
    if speech_timer is not None:
        speech_timer.cancel()
    
    if text.strip() and text != last_spoken_term:
        def speak():
            global last_spoken_term
            asyncio.run(speak_text(text))
            last_spoken_term = text
            
        speech_timer = Timer(0.5, speak)
        speech_timer.start()

async def speak_text(text):
    """Speak the given text using flite asynchronously"""
    if text.strip():  # Only speak if there's actual text
        try:
            #await asyncio.to_thread(subprocess.run, ['flite', '-t', text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            await asyncio.to_thread(subprocess.run, ['flite', '-t', ""], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass  # Silently fail if flite isn't available

async def handle_key_input(stdscr, key, search_term, cursor_pos, results):
    global scroll_position, warning, debounce_timer, MAX_SEARCH_TERM_LENGTH  # Include MAX_SEARCH_TERM_LENGTH

    # Handle special keys
    if key in (curses.KEY_BREAK, 27):  # ESC key or Break key
        # Ignore these keys and do nothing
        return search_term, cursor_pos, True  # Continue the loop

    # Handle other special keys (Backspace, Arrow keys, etc.)
    if key == curses.KEY_BACKSPACE or key == 127:  # Backspace
        if cursor_pos > 0:
            search_term = search_term[:cursor_pos-1] + search_term[cursor_pos:]
            cursor_pos -= 1
            reset_debounce_timer(results, search_term, stdscr)
    elif key == curses.KEY_LEFT:  # Left arrow
        cursor_pos = max(0, cursor_pos - 1)
    elif key == curses.KEY_RIGHT:  # Right arrow
        cursor_pos = min(len(search_term), cursor_pos + 1)
    elif key == curses.KEY_UP:  # Up arrow
        if scroll_position > 0:
            scroll_position -= 1
    elif key == curses.KEY_DOWN:  # Down arrow
        if len(results) > scroll_position + (curses.LINES - 7):
            scroll_position += 1
    elif 0 <= key < 256:  # Check if key is a valid character code
        # Insert character at cursor position
        if len(search_term) < MAX_SEARCH_TERM_LENGTH:  # Check length before adding
            search_term = search_term[:cursor_pos] + chr(key) + search_term[cursor_pos:]
            cursor_pos += 1
            scroll_position = 0

        # Check if the search term matches "skibity"
        if search_term.lower() == "skibity":
            # Show the image using fbi in quiet mode in a separate process
            subprocess.Popen(['sudo','fbi', '-q', '-T', '1', '-a', './skibity.jpg'])
            time.sleep(1)  # Show the image for 1 second
            
            # Clear the screen and return to the console app
            stdscr.clear()  # Clear the screen
            stdscr.refresh()  # Refresh the screen to return to the console app

    else:
        # Ignore other keys
        return search_term, cursor_pos, True

    # Ensure cursor position does not exceed the length of the search term
    cursor_pos = min(cursor_pos, len(search_term))

    # Reset the debounce timer on any key press
    reset_debounce_timer(results, search_term, stdscr)  # Pass results, search_term, and stdscr to reset_debounce_timer
    return search_term, cursor_pos, True

def perform_search(data, search_term, stdscr):
    global results, warning
#    print(f"Performing search for: {search_term}")  # Debug statement
    results, warning = search_data(data, search_term)  # Call search_data after debounce
    # Call the display function to show results
    display_results(stdscr, results, scroll_position, warning)

def reset_debounce_timer(data, search_term, stdscr):  # Pass data, search_term, and stdscr
    global debounce_timer
    if debounce_timer is not None:
        debounce_timer.cancel()  # Cancel the previous timer

    # Set a new timer for 0.4 seconds
    debounce_timer = Timer(0.4, lambda: perform_search(data, search_term, stdscr))  # Pass data, search_term, and stdscr
    debounce_timer.start()

def display_results(stdscr, results, scroll_position, warning):
    stdscr.addstr(4, 1, "Results:", curses.color_pair(1))
    stdscr.addstr(5, 0, " " * 80)  # Clear previous results

    # Display warning if exists
    if warning:
        stdscr.addstr(3, 0, warning, curses.color_pair(1) | curses.A_BOLD)

    # Display results headers
    stdscr.addstr(4, 1, "Location", curses.color_pair(1))
    stdscr.addstr(4, 12, "Item", curses.color_pair(1))
    stdscr.addstr(4, 42, "Notes", curses.color_pair(1))
    stdscr.addstr(5, 2, "-" * (curses.COLS - 4), curses.color_pair(1))

    # Display results with wrapping for both Item and Notes columns
    current_row = 6
    visible_rows = curses.LINES - 6
    start_idx = scroll_position
    end_idx = min(len(results), scroll_position + visible_rows)

    for _, row in results.iloc[start_idx:end_idx].iterrows():
        location = str(row.iloc[0])[:10]  # Use .iloc to access by position
        item = str(row.iloc[1])
        notes = str(row.iloc[5]) if pd.notna(row.iloc[5]) else ""  # Use .iloc to access by position

        # Display Location
        stdscr.addstr(current_row, 1, location, curses.color_pair(1))

        # Handle Item column
        wrapped_item = wrap_text(item, 28)  # Adjust width as necessary
        for i, line in enumerate(wrapped_item):
            if i == 0:  # First line goes next to Location
                stdscr.addstr(current_row, 12, line[:28], curses.color_pair(1))
            else:  # Subsequent lines are indented
                current_row += 1
                stdscr.addstr(current_row, 12, line[:28], curses.color_pair(1))

        # Handle Notes column
        if notes.strip():
            wrapped_notes = wrap_text(notes, 40)  # Adjust width as necessary
            for i, note_line in enumerate(wrapped_notes):
                if i == 0:  # First line goes on same row as first item line
                    stdscr.addstr(current_row - (len(wrapped_item) - 1), 42, note_line[:40], curses.color_pair(1))
                else:  # Subsequent lines go below
                    current_row += 1
                    stdscr.addstr(current_row, 42, note_line[:40], curses.color_pair(1))
        current_row += 1

        # Prevent overflow beyond screen bottom
        if current_row >= curses.LINES - 2:  # Leave room for scroll indicator
            break

    # Update scroll position handling
    if len(results) > visible_rows:
        scroll_msg = f"More results, scroll with arrow keys ({scroll_position + 1}-{end_idx} of {len(results)})"
        stdscr.addstr(curses.LINES - 1, 2, scroll_msg, curses.color_pair(1) | curses.A_BOLD)

    stdscr.refresh()  # Refresh the screen to show updated results

# Curses-based UI
async def main(stdscr):
    global scroll_position, results, warning, MAX_SEARCH_TERM_LENGTH  # Declare globals to modify them

    # Initialize color pairs
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    stdscr.bkgd(' ', curses.color_pair(1))  # Set default background

        # Get terminal dimensions
    height = curses.LINES
    width = curses.COLS

    # Set MAX_SEARCH_TERM_LENGTH based on terminal width
    MAX_SEARCH_TERM_LENGTH = width - 25  # Leave some space for padding
    
    # Enable cursor blinking
    curses.curs_set(2)  # 2 = blinking cursor, 1 = visible steady cursor, 0 = invisible
    
    # URL for the published Google Sheet (CSV format)
    sheet_url = "https://docs.google.com/spreadsheets/d/1PzYgCDP4Xb5Dv-2rx-G6PfGiw7bu-m-pfrca8q9V9oA/export?format=csv"

    # Load the data asynchronously
    data = await load_data(sheet_url)

    # Initialize curses
    curses.curs_set(1)  # Show the cursor for text input
    stdscr.clear()
    stdscr.refresh()

    # Initialize variables
    search_term = ""
    cursor_pos = 0
    results, warning = search_data(data, "")  # Initialize both results and warning
    
    try:
        while True:
            stdscr.clear()
            
            print("display loop")

            # Get terminal dimensions
            height = curses.LINES
            width = curses.COLS
            
            # Define column positions and widths based on screen size
            loc_start = 1
            loc_width = 10
            item_start = loc_start + loc_width + 1
            item_width = 28
            notes_start = item_start + item_width + 2
            notes_width = max(10, width - notes_start - 2)  # Ensure at least 10 chars, but shrink if needed
            
            # Display title and search field
            stdscr.addstr(1, 1, "Search the Fablab Inventory", curses.color_pair(1))
            stdscr.addstr(2, 1, "Enter text to search: ", curses.color_pair(1))
            
            # Draw the search term with cursor
            search_start = 23  # Position after "Enter text to search: "
            for i, char in enumerate(search_term):
                if i == cursor_pos:
                    stdscr.addstr(2, search_start + i, char, curses.A_REVERSE)
                else:
                    stdscr.addstr(2, search_start + i, char)
            
            # If cursor is at the end, show a highlighted space
            if cursor_pos == len(search_term):
                stdscr.addstr(2, search_start + len(search_term), " ", curses.A_REVERSE)
            
            # Move cursor to correct position
            stdscr.move(2, search_start + cursor_pos)

            # Get user input
            key = stdscr.getch()
            search_term, cursor_pos, continue_loop = await handle_key_input(stdscr, key, search_term, cursor_pos, data)
            if not continue_loop:
                break  # Exit the loop if ESC key is pressed

            # Debounced speech
            await debounced_speak(search_term)  # Call the debounced function asynchronously

            # Perform search after debounce
            if debounce_timer is None:
                perform_search(data, search_term, stdscr)  # Pass stdscr to display results

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        stdscr.addstr(curses.LINES - 1, 0, "Exiting... Press any key.")
        stdscr.refresh()
        stdscr.getch()  # Wait for a key press before exiting

    stdscr.addstr(curses.LINES - 1, 0, "Exiting... Press any key.")
    stdscr.refresh()
    stdscr.getch()

# Run the curses app
if __name__ == "__main__":
    try:
        curses.wrapper(lambda stdscr: asyncio.run(main(stdscr)))
    finally:
        # Clean up any pending speech timer
        if speech_timer is not None:
            speech_timer.cancel()

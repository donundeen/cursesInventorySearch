import curses
import pandas as pd
import re

# Function to read data from Google Sheets CSV
def load_data(sheet_url):
    try:
        data = pd.read_csv(sheet_url)
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
    
    # Perform case-insensitive search across all columns
    filtered = data[data.apply(
        lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)]
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

# Curses-based UI
def main(stdscr):
    # Initialize color pairs
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    stdscr.bkgd(' ', curses.color_pair(1))  # Set default background
    
    # Enable cursor blinking
    curses.curs_set(2)  # 2 = blinking cursor, 1 = visible steady cursor, 0 = invisible
    
    # URL for the published Google Sheet (CSV format)
    sheet_url = "https://docs.google.com/spreadsheets/d/1PzYgCDP4Xb5Dv-2rx-G6PfGiw7bu-m-pfrca8q9V9oA/export?format=csv"

    # Load the data
    data = load_data(sheet_url)

    # Initialize curses
    curses.curs_set(1)  # Show the cursor for text input
    stdscr.clear()
    stdscr.refresh()

    # Initialize variables
    search_term = ""
    cursor_pos = 0
    scroll_position = 0
    results, warning = search_data(data, "")  # Initialize both results and warning
    
    while True:
        stdscr.clear()
        
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

        # Clear results area
        stdscr.addstr(3, 0, " " * 80)
        stdscr.addstr(4, 0, "Results:")
        stdscr.addstr(5, 0, " " * 80)

        # Clear all lines below the search input
        for i in range(3, curses.LINES):
            stdscr.move(i, 0)
            stdscr.clrtoeol()
        
        # Display warning if exists
        if warning:
            stdscr.addstr(3, 0, warning, curses.color_pair(1) | curses.A_BOLD)
        
        # Display results
        stdscr.addstr(4, loc_start, "Location", curses.color_pair(1))
        stdscr.addstr(4, item_start, "Item", curses.color_pair(1))
        stdscr.addstr(4, notes_start, "Notes", curses.color_pair(1))
        stdscr.addstr(5, 2, "-" * (width - 4), curses.color_pair(1))
        
        # Display results with wrapping for both Item and Notes columns
        current_row = 6
        visible_rows = curses.LINES - 6
        start_idx = scroll_position
        end_idx = min(len(results), scroll_position + visible_rows)
        
        for _, row in results.iloc[start_idx:end_idx].iterrows():
            location = str(row.values[0])[:loc_width]
            item = str(row.values[1])
            notes = str(row.values[5]) if pd.notna(row.values[5]) else ""
            
            # Display Location
            stdscr.addstr(current_row, loc_start, location, curses.color_pair(1))
            
            # Handle Item column
            wrapped_item = wrap_text(item, item_width)
            for i, line in enumerate(wrapped_item):
                if i == 0:  # First line goes next to Location
                    stdscr.addstr(current_row, item_start, line[:item_width], curses.color_pair(1))
                else:  # Subsequent lines are indented
                    current_row += 1
                    stdscr.addstr(current_row, item_start, line[:item_width], curses.color_pair(1))
            
            # Handle Notes column
            if notes.strip():
                wrapped_notes = wrap_text(notes, notes_width)
                for i, note_line in enumerate(wrapped_notes):
                    if i == 0:  # First line goes on same row as first item line
                        stdscr.addstr(current_row - (len(wrapped_item) - 1), notes_start, note_line[:notes_width], curses.color_pair(1))
                    else:  # Subsequent lines go below
                        current_row += 1
                        try: 
                            stdscr.addstr(current_row, notes_start, note_line[:notes_width], curses.color_pair(1))
                        except:
                            current_row -= 1        
            current_row += 1
            
            # Prevent overflow beyond screen bottom
            if current_row >= curses.LINES - 2:  # Leave room for scroll indicator
                break
        
        # Update scroll position handling
        if len(results) > visible_rows:
            scroll_msg = f"More results, scroll with arrow keys ({scroll_position + 1}-{end_idx} of {len(results)})"
            try:
                stdscr.addstr(curses.LINES-1, 2, scroll_msg, curses.color_pair(1) | curses.A_BOLD)
            except:
                pass
        stdscr.refresh()

        # Get user input
        key = stdscr.getch()
        
        # Handle special keys
        if key == curses.KEY_BACKSPACE or key == 127:  # Backspace
            if cursor_pos > 0:
                search_term = search_term[:cursor_pos-1] + search_term[cursor_pos:]
                cursor_pos -= 1
                results, warning = search_data(data, search_term)  # Search after backspace
        elif key == curses.KEY_LEFT:  # Left arrow
            cursor_pos = max(0, cursor_pos - 1)
        elif key == curses.KEY_RIGHT:  # Right arrow
            cursor_pos = min(len(search_term), cursor_pos + 1)
        elif key == 27:  # ESC key to exit
            break  # Now this break is inside a loop
        elif key == curses.KEY_UP:  # Up arrow
            if scroll_position > 0:
                scroll_position -= 1
        elif key == curses.KEY_DOWN:  # Down arrow
            if len(results) > scroll_position + (curses.LINES - 7):
                scroll_position += 1
        else:
            # Insert character at cursor position
            search_term = search_term[:cursor_pos] + chr(key) + search_term[cursor_pos:]
            cursor_pos += 1
            results, warning = search_data(data, search_term)  # Search after adding character

    stdscr.addstr(curses.LINES - 1, 0, "Exiting... Press any key.")
    stdscr.refresh()
    stdscr.getch()

# Run the curses app
if __name__ == "__main__":
    curses.wrapper(main)

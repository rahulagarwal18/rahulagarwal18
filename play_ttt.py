import os
import re
import sys
import random

def print_err(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)

def load_readme():
    with open("README.md", "r", encoding="utf-8") as f:
        return f.read()

def save_readme(content):
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

def extract_board(readme):
    # Find the board section
    match = re.search(r'<!-- TTT_BOARD_START -->(.*?)<!-- TTT_BOARD_END -->', readme, re.DOTALL)
    if not match:
        print_err("Could not find TTT_BOARD in README.md")
    
    board_text = match.group(1)
    
    # Extract the cells
    # We look for ⬜, ❌, ⭕
    cells = []
    for char in board_text:
        if char in ['⬜', '❌', '⭕']:
            cells.append(char)
            
    if len(cells) != 9:
        # If board is corrupted, reset it
        cells = ['⬜'] * 9
        
    return cells

def check_win(board, player):
    win_lines = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8], # rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8], # cols
        [0, 4, 8], [2, 4, 6]             # diagonals
    ]
    for line in win_lines:
        if board[line[0]] == player and board[line[1]] == player and board[line[2]] == player:
            return True
    return False

def generate_board_md(board, status_msg=""):
    md = "\n"
    if status_msg:
        md += f"**{status_msg}**\n\n"
        
    md += "| | | |\n"
    md += "|---|---|---|\n"
    
    for row in range(3):
        row_str = "|"
        for col in range(3):
            idx = row * 3 + col
            val = board[idx]
            if val == '⬜' and not status_msg.startswith("Game Over"):
                # Make it clickable
                link = f"https://github.com/rahulagarwal18/rahulagarwal18/issues/new?title=ttt%7C{idx}&body=Just+click+Submit+new+issue+to+play+your+move!"
                row_str += f" [{val}]({link}) |"
            else:
                row_str += f" {val} |"
        md += row_str + "\n"
        
    if status_msg.startswith("Game Over"):
        md += "\n[🔄 Play Again](https://github.com/rahulagarwal18/rahulagarwal18/issues/new?title=ttt%7Creset&body=Just+click+Submit+new+issue+to+reset+the+board!)\n"
        
    md += "\n"
    return md

def main():
    issue_title = os.environ.get("ISSUE_TITLE", "")
    if not issue_title.startswith("ttt|"):
        print("Not a tic-tac-toe move.")
        sys.exit(0)
        
    action = issue_title.split("|")[1].strip()
    
    readme = load_readme()
    board = extract_board(readme)
    
    if action == "reset":
        board = ['⬜'] * 9
        status = "New game started! You are ❌. Your turn!"
    else:
        try:
            move_idx = int(action)
        except ValueError:
            print_err("Invalid move index.")
            
        if move_idx < 0 or move_idx > 8 or board[move_idx] != '⬜':
            print_err("Invalid move. Cell occupied or out of bounds.")
            
        # Player move
        board[move_idx] = '❌'
        
        if check_win(board, '❌'):
            status = "Game Over! You win! 🎉"
        elif '⬜' not in board:
            status = "Game Over! It's a draw! 🤝"
        else:
            # AI move (O)
            empty_cells = [i for i, x in enumerate(board) if x == '⬜']
            ai_move = random.choice(empty_cells)
            board[ai_move] = '⭕'
            
            if check_win(board, '⭕'):
                status = "Game Over! I win! 🤖"
            elif '⬜' not in board:
                status = "Game Over! It's a draw! 🤝"
            else:
                status = "I made my move. Your turn!"
                
    new_board_md = generate_board_md(board, status)
    
    # Replace in README
    new_readme = re.sub(r'<!-- TTT_BOARD_START -->.*?<!-- TTT_BOARD_END -->', 
                        f'<!-- TTT_BOARD_START -->{new_board_md}<!-- TTT_BOARD_END -->', 
                        readme, flags=re.DOTALL)
                        
    save_readme(new_readme)
    print("Board updated successfully.")

if __name__ == "__main__":
    main()

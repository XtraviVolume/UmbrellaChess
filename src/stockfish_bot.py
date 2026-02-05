import multiprocess
import pyautogui
import time
import sys
import os
import chess
import re
from grabbers.chesscom_grabber import ChesscomGrabber
from utilities import char_to_num
from maia_handler import MaiaHandler
from mouse_utils import human_drag_to, human_move_to
import keyboard

class StockfishBot(multiprocess.Process):
    def __init__(self, chrome_url, chrome_session_id, pipe, overlay_queue, 
                 enable_manual, enable_autosolve, 
                 enable_automatch, mouse_latency, 
                 maia_model="rapid",
                 bot_elo=1500, opponent_elo=1500, accuracy=100, force_solid=True,
                 speed_bullet=0.3, speed_blitz=0.5, speed_rapid=1.0): 
        multiprocess.Process.__init__(self)

        self.chrome_url = chrome_url
        self.chrome_session_id = chrome_session_id
        self.pipe = pipe
        self.overlay_queue = overlay_queue
        
        self.enable_manual = enable_manual
        self.enable_autosolve = enable_autosolve
        self.enable_automatch = enable_automatch
        self.mouse_latency = mouse_latency
        
        self.model_type = maia_model
        
        self.bot_elo = bot_elo
        self.opponent_elo = opponent_elo
        self.accuracy = accuracy
        self.force_solid = force_solid
        
        self.speed_bullet = speed_bullet
        self.speed_blitz = speed_blitz
        self.speed_rapid = speed_rapid

        self.grabber = None
        self.is_white = None
        self.maia = None
        self.board = None

    def _to_screen_pos(self, move_str):
        # Convert algebraic move (e.g. "a1") to screen X,Y coordinates
        offset_x, offset_y = self.grabber.get_top_left_corner()
        board_loc = self.grabber.get_board().location
        board_x = offset_x + board_loc["x"]
        board_y = offset_y + board_loc["y"]
        
        sq_size = self.grabber.get_board().size['width'] / 8

        # Flip coordinates if playing black
        if self.is_white:
            x = board_x + sq_size * (char_to_num(move_str[0]) - 1) + sq_size / 2
            y = board_y + sq_size * (8 - int(move_str[1])) + sq_size / 2
        else:
            x = board_x + sq_size * (8 - char_to_num(move_str[0])) + sq_size / 2
            y = board_y + sq_size * (int(move_str[1]) - 1) + sq_size / 2

        return x, y

    def _get_move_coords(self, uci_move):
        start_x, start_y = self._to_screen_pos(uci_move[0:2])
        end_x, end_y = self._to_screen_pos(uci_move[2:4])
        return (start_x, start_y), (end_x, end_y)

    def execute_move(self, uci_move):
        start_pos, end_pos = self._get_move_coords(uci_move)

        # Determine move speed
        multiplier = self.speed_rapid
        if "bullet" in self.model_type.lower():
            if "ultra" in self.model_type.lower():
                multiplier = 0.1
            else:
                multiplier = self.speed_bullet
        elif "blitz" in self.model_type.lower():
            multiplier = self.speed_blitz
            
        # Perform drag action
        human_move_to(int(start_pos[0]), int(start_pos[1]), speed_multiplier=multiplier)
        human_drag_to(int(end_pos[0]), int(end_pos[1]), speed_multiplier=multiplier)

        # Handle Promotion
        if len(uci_move) == 5:
            time.sleep(0.1 + self.mouse_latency)
            promo_char = uci_move[4]
            # Calculate promotion square position based on piece type relative to landing square
            # Simplified: just click the landing square (usually Queen) or calculate offset if needed
            # For now, default to reusing end_pos which works for Queen on most sites
            human_move_to(int(end_pos[0]), int(end_pos[1]), speed_multiplier=multiplier)
            pyautogui.click(button='left')

    def wait_delete_signal(self):
        while self.pipe.recv() != "DELETE":
            pass

    def next_puzzle(self):
        self.grabber.click_puzzle_next()
        self.pipe.send("RESTART")
        self.wait_delete_signal()

    def next_match(self):
        time.sleep(2)
        self.grabber.click_game_next()
        self.pipe.send("RESTART")
        self.wait_delete_signal()

    def run(self):
        try:
            self.grabber = ChesscomGrabber(self.chrome_url, self.chrome_session_id)
            self.grabber.reset_moves_list()
        except Exception as e:
            self.pipe.send("ERR_BROWSER")
            return

        try:
            self.maia = MaiaHandler(model_type=self.model_type)
            if self.maia.model is None:
                raise Exception("Model load failed")
        except Exception:
            self.pipe.send("ERR_EXE")
            return

        # Board Detection
        for _ in range(5):
            self.grabber.update_board_elem()
            if self.grabber.get_board():
                break
            time.sleep(1)
            
        if not self.grabber.get_board():
            self.pipe.send("ERR_NOBOARD")
            return

        # Color Detection
        while self.is_white is None:
            self.is_white = self.grabber.is_white()
            if self.grabber.is_game_over():
                self.pipe.send("ERR_GAMEOVER")
                return
            if self.pipe.poll():
                if self.pipe.recv() == "STOP":
                    return
            time.sleep(1)

        # Initial Moves
        initial_moves = None
        for _ in range(5):
            initial_moves = self.grabber.get_move_list()
            if initial_moves is not None:
                break
            time.sleep(1)
            
        if initial_moves is None:
            self.pipe.send("ERR_MOVES")
            return

        self.board = chess.Board()
        for m in initial_moves:
            self.board.push_san(m)
        
        self.send_gui_update()
        self.pipe.send("START")

        if initial_moves:
            self.pipe.send("M_MOVE" + ",".join(initial_moves))

        # Main Loop
        while True:
            # My Turn?
            if (self.is_white and self.board.turn == chess.WHITE) or \
               (not self.is_white and self.board.turn == chess.BLACK):
                
                best_move = self.get_best_move()
                if not best_move:
                    time.sleep(0.5)
                    continue

                # Manual Mode Check
                if self.enable_manual:
                    s_pos, e_pos = self._get_move_coords(best_move)
                    self.overlay_queue.put([((int(s_pos[0]), int(s_pos[1])), (int(e_pos[0]), int(e_pos[1])))])
                    
                    waited_move = False
                    while True:
                        if keyboard.is_pressed("3"):
                            break # Execute bot move
                        
                        # Check if user moved manually
                        current_moves = self.grabber.get_move_list()
                        if len(current_moves) != len(initial_moves):
                            waited_move = True
                            initial_moves = current_moves
                            self.board.push_uci(self.board.parse_san(current_moves[-1]).uci())
                            break
                    
                    if waited_move:
                        self.overlay_queue.put([])
                        self.send_gui_update()
                        self.pipe.send("S_MOVE" + initial_moves[-1])
                        continue

                # Execute Move
                move_san = self.board.san(chess.Move.from_uci(best_move))
                self.board.push_uci(best_move)
                initial_moves.append(move_san)
                
                self.execute_move(best_move)
                self.overlay_queue.put([])

                self.send_gui_update()
                self.pipe.send("S_MOVE" + move_san)

                if self.board.is_checkmate():
                   self.handle_game_over()
                   return

                time.sleep(0.1)

            # Opponent's Turn
            prev_len = len(initial_moves)
            while True:
                if self.grabber.is_game_over():
                    self.handle_game_over()
                    return
                
                new_moves = self.grabber.get_move_list()
                if not new_moves: return # connection lost?

                if len(new_moves) == 0 and prev_len > 0:
                     # New Game Detected
                     self.pipe.send("RESTART")
                     self.wait_delete_signal()
                     return

                if len(new_moves) > prev_len:
                    initial_moves = new_moves
                    break
            
            # Update board state
            opp_move = initial_moves[-1]
            self.board.push_san(opp_move)
            self.send_gui_update()
            self.pipe.send("S_MOVE" + opp_move)

            if self.board.is_checkmate():
                self.handle_game_over()
                return

    def get_best_move(self):
        move_num = self.board.fullmove_number
        force_best = self.force_solid and move_num <= 8
        
        # Simple repetition avoidance
        for _ in range(3):
            move = self.maia.get_best_move(
                self.board,
                elo_self=self.bot_elo,
                elo_oppo=self.opponent_elo,
                accuracy_percent=self.accuracy,
                force_best_move=force_best,
                move_number=move_num
            )
            if not move: return None
            
            self.board.push(chess.Move.from_uci(move))
            rep = self.board.is_repetition(2)
            self.board.pop()
            
            if not rep or move_num > 30:
                return move
                
        return move # Fallback

    def handle_game_over(self):
        if self.enable_autosolve and self.grabber.is_game_puzzles():
            self.next_puzzle()
        elif self.enable_automatch:
            self.next_match()

    def send_gui_update(self):
        # Calculate material
        vals = {chess.PAWN:1, chess.KNIGHT:3, chess.BISHOP:3, chess.ROOK:5, chess.QUEEN:9}
        w_mat = sum(len(self.board.pieces(p, chess.WHITE))*v for p,v in vals.items())
        b_mat = sum(len(self.board.pieces(p, chess.BLACK))*v for p,v in vals.items())
        adv = w_mat - b_mat
        mat_str = f"+{adv}" if adv > 0 else str(adv)
        
        # Send to GUI
        self.pipe.send(f"EVAL|Maia|-|-|{mat_str}|-|")
        
        # Send to Overlay
        if self.grabber and self.grabber.get_board():
            off_x, off_y = self.grabber.get_top_left_corner()
            b_elem = self.grabber.get_board()
            self.overlay_queue.put({
                "eval": 0.0,
                "eval_type": "cp",
                "is_white": self.is_white,
                "board_position": {
                    'x': off_x + b_elem.location['x'],
                    'y': off_y + b_elem.location['y'],
                    'width': b_elem.size['width'],
                    'height': b_elem.size['height']
                }
            })

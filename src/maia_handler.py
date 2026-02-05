import torch
import chess
import random
try:
    import maia2.model
    import maia2.inference
except ImportError:
    print("Maia2 library not found. Please install it.")

try:
    import chess.polyglot
except ImportError:
    pass

class MiniOpeningBook:
    """
    Expanded hardcoded opening book to ensure solid play in the first few moves.
    Includes common lines for Ruy Lopez, Sicilian, French, Caro-Kann, Italian, QGD, Indian Defenses.
    """
    def __init__(self):
        # Keys are "Piece Placement" part of FEN.
        self.book = {
            # --- START ---
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR": ["e2e4", "d2d4", "g1f3", "c2c4"],

            # --- VS 1. e4 ---
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR": ["c7c5", "e7e5", "e7e6", "c7c6", "d7d6"], # Sicilian, e5, French, Caro, Pirc

            # --- VS 1. d4 ---
            "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR": ["g8f6", "d7d5", "e7e6", "f7f5"], # Indian, d5, Horowitz, Dutch

            # --- VS 1. Nf3 ---
            "rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R": ["d7d5", "g8f6", "c7c5", "g7g6"],

            # --- VS 1. c4 ---
            "rnbqkbnr/pppppppp/8/8/2P5/8/PP1PPPPP/RNBQKBNR": ["e7e5", "c7c5", "g8f6", "g7g6"],

            # === WHITE OPENINGS (Ply 3) ===
            # 1. e4 e5
            "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR": ["g1f3", "b1c3", "f1c4"], # King's Knight, Vienna, Bishop's
            # 1. e4 c5
            "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR": ["g1f3", "b1c3", "c2c3"], # Open Sicilian, Closed, Alapin
             # 1. e4 e6 (French)
            "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR": ["d2d4", "g1f3"],
            # 1. d4 d5
            "rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR": ["c2c4", "g1f3", "c1f4"], # Queen's Gambit, Knight, London

            # === BLACK DEFENSES (Ply 4) ===
            # 1. e4 e5 2. Nf3
            "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R": ["b8c6", "g8f6", "d7d6"], # Nc6, Petrov, Philidor
            # 1. e4 2. Nc3 (Vienna)
            "rnbqkbnr/pppp1ppp/8/4p3/4P3/2N5/PPPP1PPP/R1BQKBNR": ["g8f6", "b8c6", "f8c5"],
            # 1. e4 e5 2. Bc4 (Bishop's)
            "rnbqkbnr/pppp1ppp/8/4p3/2B1P3/8/PPPP1PPP/RNBQKBNR": ["g8f6", "b8c6", "f8c5"],
            # 1. d4 d5 2. c4 (QG)
            "rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR": ["e7e6", "c7c6", "d5c4"], # Declined, Slav, Accepted
            # 1. d4 d5 2. Nf3
            "rnbqkbnr/ppp1pppp/8/3p4/3P4/5N2/PPP1PPPP/RNBQKB1R": ["g8f6", "e7e6", "c7c6"],

            # === DEEPER LINES (Ply 5+) ===
            # Ruy Lopez: 1. e4 e5 2. Nf3 Nc6 3. Bb5
            "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R": ["f1b5", "f1c4", "d2d4", "b1c3"],
            # Italian: 1. e4 e5 2. Nf3 Nc6 3. Bc4
            "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R": ["f8c5", "g8f6", "h7h6"],
            # Sicilian Open: 1. e4 c5 2. Nf3 d6 3. d4
            "rnbqkbnr/pp2pppp/3p4/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R": ["d2d4", "c2c3", "f1b5"],
            # QGD: 1. d4 d5 2. c4 e6 3. Nc3
            "rnbqkbnr/ppp2ppp/4p3/3p4/2PP4/8/PP2PPPP/RNBQKBNR": ["b1c3", "g1f3"],
        }

    def get_move(self, board):
        # Simplified key: Piece placement is the first part of FEN
        piece_placement = board.fen().split(" ")[0]
        
        # print(f"[DEBUG BOOK] Checking Key: {piece_placement}")
        
        if piece_placement in self.book:
            moves = self.book[piece_placement]
            chosen = random.choice(moves)
            # print(f"[DEBUG BOOK] HIT! Moves: {moves} -> Chosen: {chosen}")
            return chosen
        return None

class MaiaHandler:
    def __init__(self, model_type="rapid", device=None):
        self.model_type = model_type
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        self.model = None
        self.prepared = None
        self.internal_book = MiniOpeningBook()
        self.polyglot_book = None
        
        # Try to load external book.bin
        self.load_polyglot_book()
        
        self.load_model()
        
        # Prepare static data needed for inference
        try:
            self.prepared = maia2.inference.prepare()
        except Exception as e:
            print(f"Error preparing Maia inference data: {e}")

    def load_polyglot_book(self):
        import os
        # Search common names
        candidates = ["book.bin", "openings.bin", "perfect2023.bin", "gm2001.bin"]
        paths = [
            os.path.join(os.getcwd(), c) for c in candidates
        ] + [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), c) for c in candidates
        ] + [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", c) for c in candidates
        ]

        for p in paths:
            if os.path.isfile(p):
                try:
                    self.polyglot_book = chess.polyglot.open_reader(p)
                    print(f"[BOOK] Loaded Polyglot book: {p}")
                    return
                except Exception as e:
                    print(f"[BOOK] Found {p} but failed to load: {e}")
        
        print("[BOOK] No external .bin book found. Using internal simplified book.")

    def load_model(self):
        print(f"Loading Maia 2 model: {self.model_type} on {self.device}...")
        try:
            self.model = maia2.model.from_pretrained(type=self.model_type, device=self.device)
            print(f"Maia 2 Model '{self.model_type}' loaded successfully.")
        except Exception as e:
            print(f"Error loading Maia 2 model '{self.model_type}': {e}")
            if self.model_type != "rapid":
                print("Attempting fallback to 'rapid'...")
                try:
                    self.model = maia2.model.from_pretrained(type="rapid", device=self.device)
                    print("Fallback 'rapid' model loaded successfully.")
                except Exception as e2:
                    print(f"Critical Error: Could not load fallback model: {e2}")
                    self.model = None
            else:
                 self.model = None

    def get_best_move(self, board, elo_self=1500, elo_oppo=1500, accuracy_percent=100, force_best_move=False, exclude_moves=None, move_number=0):
        """
        Get the predicted move from Maia 2 or Opening Book.
        """
        # print(f"[DEBUG] get_best_move: move={move_number}, force_solid={force_best_move}")
        
        if exclude_moves is None:
            exclude_moves = []
            
        # --- 1. EXTERNAL POLYGLOT BOOK ---
        if self.polyglot_book and move_number <= 30: # Use book deeper if available
            try:
                # Get weighted choice
                entry = self.polyglot_book.weighted_choice(board)
                move = entry.move.uci()
                if move not in exclude_moves:
                    print(f"[BOOK] Polyglot Hit: {move}")
                    return move
            except IndexError:
                pass # No move in book
            except Exception as e:
                print(f"[BOOK] Polyglot Error: {e}")

        # --- 2. INTERNAL HARDCODED BOOK ---
        # If "Force Solid Openings" is ON and it's early game.
        if force_best_move and move_number <= 12:
            book_move_str = self.internal_book.get_move(board)
            if book_move_str:
                if book_move_str not in exclude_moves:
                    print(f"[BOOK] Internal Hit: {book_move_str}")
                    return book_move_str

        # --- 3. MAIA MODEL ---
        if self.model is None:
            return None
        
        try:
            game_fen = board.fen()
            
            # Boost Elo potentially for better moves if not in book but still early
            final_elo_self = elo_self
            if force_best_move and move_number <= 15:
                final_elo_self = 2800
                # print(f"[DEBUG] Opening phase (not in book), boosting Elo to 2800")
            
            # Run Inference
            move_probs, win_prob = maia2.inference.inference_each(
                self.model, 
                self.prepared, 
                game_fen, 
                final_elo_self, 
                elo_oppo
            )
            
            if move_probs:
                moves = list(move_probs.keys())
                probs = list(move_probs.values())
                
                # Filter out excluded moves
                if exclude_moves:
                    filtered_moves = []
                    filtered_probs = []
                    for m, p in zip(moves, probs):
                         if m not in exclude_moves:
                             filtered_moves.append(m)
                             filtered_probs.append(p)
                    
                    if filtered_moves:
                        moves = filtered_moves
                        probs = filtered_probs
                
                num_moves = len(moves)
                if num_moves == 0:
                    return None

                # Selection Logic based on Accuracy
                selected_move = None
                
                if accuracy_percent >= 90:
                    selected_move = moves[0]
                elif accuracy_percent >= 50:
                    top_k = min(6, num_moves) 
                    selected_move = random.choices(moves[:top_k], weights=probs[:top_k], k=1)[0]
                else:
                    # Low Accuracy Logic
                    if accuracy_percent < 25:
                        min_rank, max_rank = 10, 30
                    elif accuracy_percent < 40:
                         min_rank, max_rank = 5, 15
                    else: 
                         min_rank, max_rank = 2, 6
                         
                    min_rank = min(min_rank, num_moves - 1)
                    max_rank = min(max_rank, num_moves - 1)
                    if min_rank > max_rank: min_rank = max_rank
                    
                    bad_move_prob = 1.0 - (accuracy_percent / 100.0)
                    
                    if random.random() < bad_move_prob:
                         selected_move = random.choice(moves[min_rank : max_rank + 1])
                    else:
                         selected_move = random.choice(moves[:3])
                
                return selected_move
            
            return None
            
        except Exception as e:
            print(f"Error in Maia move generation: {e}")
            return None

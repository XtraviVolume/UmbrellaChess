from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By

from grabbers.grabber import Grabber


class ChesscomGrabber(Grabber):
    def __init__(self, chrome_url, chrome_session_id):
        super().__init__(chrome_url, chrome_session_id)
        # The moves_list is now initialized in the base class

    def update_board_elem(self):
        try:
            self._board_elem = self.chrome.find_element(By.XPATH, "//*[@id='board-play-computer']")
        except NoSuchElementException:
            try:
                self._board_elem = self.chrome.find_element(By.XPATH, "//*[@id='board-single']")
            except NoSuchElementException:
                self._board_elem = None

    def is_white(self):
        board = self.get_board()
        if not board:
            return None

        # Strategy 1: SVG Coordinates (standard)
        # Look for text inside the board's SVG
        try:
            # Try to find all text elements that might be coordinates
            # Often they are <text> or <text class="coordinate-light"> etc.
            text_elements = board.find_elements(By.TAG_NAME, "text")
            
            # Filter for elements that are likely coordinates (single digit/char)
            coords = []
            for elem in text_elements:
                txt = elem.text.strip()
                if txt in ["1", "8", "a", "h"]:
                     coords.append(elem)
            
            if coords:
                # Find the element with the largest Y (bottom) and smallest X (left)
                # But X/Y attributes are strings in SVG, need to parse
                bottom_left = None
                max_y = -1.0
                min_x = float('inf')
                
                for elem in coords:
                    try:
                        # Some SVGs use 'x' and 'y' attributes
                        x_attr = elem.get_attribute("x")
                        y_attr = elem.get_attribute("y")
                        
                        if x_attr and y_attr:
                            x = float(x_attr)
                            y = float(y_attr)
                            
                            # We want biggest Y (bottom) and smallest X (left)
                            # Logic: If 1 is at bottom-left, it's White. If 8 is at bottom-left, it's Black.
                            # Priority: Bottom-most, then Left-most.
                            
                            if y > max_y:
                                max_y = y
                                min_x = x
                                bottom_left = elem
                            elif y == max_y and x < min_x:
                                min_x = x
                                bottom_left = elem
                    except ValueError:
                        continue

                if bottom_left:
                    val = bottom_left.text.strip()
                    print(f"[DEBUG] Found bottom-left coordinate: '{val}'")
                    # White: 1 or a at bottom-left
                    # Black: 8 or h at bottom-left
                    return val in ["1", "a"]
        except Exception as e:
            print(f"[DEBUG] SVG Coordinate check failed: {e}")
            pass

        # Strategy 2: HTML Coordinates (class .coordinates or .coords)
        try:
            coords = board.find_elements(By.CSS_SELECTOR, ".coordinates, .coords")
            # print(f"[DEBUG] Found {len(coords)} HTML coordinate containers")
            for coord in coords:
                # Often modern chess.com puts '1' '8' etc in divs
                # Check inner text
                txt = coord.get_attribute("innerText") or coord.text
                if "1" in txt and "8" in txt:
                    # If we have a container with all numbers
                    # Hard to distinguish position without bounding box
                    pass
                
            # If we find a specific coordinate element for rank 1
            # usually <text> is the safest bet for the board SVG
            pass
        except Exception:
            pass

        # Strategy 3: HTML DOM Position for '1'
        # Modern chess.com sometimes uses div.coordinate-light or div.coordinate-dark
        # with inline styles for top/left.
        try:
             # Look for any element containing "1"
             ones = board.find_elements(By.XPATH, ".//*[text()='1']")
             eights = board.find_elements(By.XPATH, ".//*[text()='8']")
             
            #  print(f"[DEBUG] DOM Ones: {len(ones)}, Eights: {len(eights)}")
             
             if ones and not eights:
                 return True # Simplistic assumption
             if eights and not ones:
                 return False
             
             if ones and eights:
                 # compare vertical position of the first '1' and first '8'
                 # Element being "lower" on screen means higher Y value (usually)
                 # but rect.y is distance from top. So bigger Y = lower.
                 
                 r1 = ones[0].rect
                 r8 = eights[0].rect
                 
                #  print(f"[DEBUG] R1.y: {r1['y']}, R8.y: {r8['y']}")

                 # If '1' is below '8' (bigger Y), then White is at bottom -> Player is White
                 return r1['y'] > r8['y']

        except Exception as e:
            print(f"[DEBUG] Rect compare failed: {e}")
            pass

        return None

    def is_game_over(self):
        try:
            # Check 1: Modal
            if self.chrome.find_elements(By.CLASS_NAME, "board-modal-container"):
                return True
            
            # Check 2: Sidebar Game Over Buttons
            # The presence of "New Game" or "Rematch" buttons in the sidebar indicates game over
            sidebar_btns = self.chrome.find_elements(By.CSS_SELECTOR, 
                ".game-over-buttons-component button, .live-game-buttons-component button, .daily-game-footer-component button")
            
            for btn in sidebar_btns:
                if btn.is_displayed():
                    text = btn.text.lower()
                    keywords = ["new", "play", "rematch", "новая", "играть", "реванш"]
                    if any(k in text for k in keywords):
                        return True

            return False
        except NoSuchElementException:
            return False
        except Exception:
            return False

    def reset_moves_list(self):
        """Reset the moves list when a new game starts"""
        self.moves_list = {}

    def get_move_list(self):
        # Find the moves list
        try:
            move_list_elem = self.chrome.find_element(By.CLASS_NAME, "play-controller-scrollable")
        except NoSuchElementException:
            try:
                move_list_elem = self.chrome.find_element(By.CLASS_NAME, "mode-swap-move-list-wrapper-component")
            except NoSuchElementException:
                    return None

        # Check if we're in a new game by looking at the number of moves
        # If there are no visible moves but we have moves in our list, we're in a new game
        visible_moves = move_list_elem.find_elements(By.CSS_SELECTOR, "div.node[data-node]")
        if len(visible_moves) == 0 and self.moves_list:
            # Reset moves list for new game
            self.reset_moves_list()

        # Select all children with class containing "white node" or "black node"
        # Moves that are not pawn moves have a different structure
        # containing children
        if not self.moves_list:
            # If the moves list is empty, find all moves
            moves = move_list_elem.find_elements(By.CSS_SELECTOR, "div.node[data-node]")
        else:
            # If the moves list is not empty, find only the new moves
            moves = move_list_elem.find_elements(By.CSS_SELECTOR, "div.node[data-node]:not([data-processed])")

        for move in moves:
            move_class = move.get_attribute("class")

            # Check if it is indeed a move
            if "white-move" in move_class or "black-move" in move_class:
                # Check if it has a figure - search deeper in the structure
                try:
                    # Look for any element with data-figurine attribute anywhere within this move
                    figurine_elem = move.find_element(By.CSS_SELECTOR, "[data-figurine]")
                    figure = figurine_elem.get_attribute("data-figurine")
                except NoSuchElementException:
                    figure = None

                # Check if it was en-passant or figure-move
                if figure is None:
                    # If the moves_list is empty or the last move was not the current move
                    self.moves_list[move.get_attribute("data-node")] = move.text
                elif "=" in move.text:
                    m = move.text + figure
                    # If the move is a check, add the + in the end
                    if "+" in m:
                        m = m.replace("+", "")
                        m += "+"

                    # If the moves_list is empty or the last move was not the current move
                    self.moves_list[move.get_attribute("data-node")] = m
                else:
                    # If the moves_list is empty or the last move was not the current move
                    self.moves_list[move.get_attribute("data-node")] = figure + move.text

                # Mark the move as processed
                self.chrome.execute_script("arguments[0].setAttribute('data-processed', 'true')", move)

        return list(self.moves_list.values())

    def is_game_puzzles(self):
        return False

    def click_puzzle_next(self):
        pass

    def click_game_next(self):
        from selenium.common.exceptions import StaleElementReferenceException
        import time
        print("[DEBUG] Attempting to click Next/New Game...")

        def safe_click(element, name="element"):
            try:
                # 1. Standard Click
                if element.is_displayed() and element.is_enabled():
                    element.click()
                    print(f"[DEBUG] Clicked '{name}' (Standard).")
                    
                    # Verify: Wait for element to disappear or become stale
                    for _ in range(10): # Wait up to 1 second
                        try:
                            if not element.is_displayed():
                                print(f"[DEBUG] '{name}' disappeared. Success.")
                                return True
                        except StaleElementReferenceException:
                             print(f"[DEBUG] '{name}' became stale. Success.")
                             return True
                        time.sleep(0.1)
                    
                    print(f"[DEBUG] '{name}' still visible after click. Trying JS Click...")
                    
                    # 2. JS Click Fallback
                    self.chrome.execute_script("arguments[0].click();", element)
                    print(f"[DEBUG] Clicked '{name}' (JS).")
                    return True
                else:
                    print(f"[DEBUG] '{name}' visible: {element.is_displayed()}, enabled: {element.is_enabled()}")
                    return False
            except StaleElementReferenceException:
                print(f"[DEBUG] '{name}' is stale.")
                return False
            except Exception as e:
                print(f"[DEBUG] Failed to click '{name}': {e}")
                return False

        # Attempt 1: Direct button selectors
        selectors = [
            ("button[data-cy='new-game-index-play']", "New Game/Play"),
            ("button[data-cy='game-over-rematch']", "Rematch"),
            (".game-over-buttons-component button", "Game Over Button"), # Generic
            (".daily-game-footer-component button", "Daily Game Button")
        ]
        
        for selector, desc in selectors:
            try:
                btns = self.chrome.find_elements(By.CSS_SELECTOR, selector)
                # Filter visible only
                btns = [b for b in btns if b.is_displayed()]
                
                if btns:
                    print(f"[DEBUG] Found {len(btns)} buttons for selector: {selector}")
                    # Prioritize buttons with specific text if generic
                    for btn in btns:
                        text = btn.text.lower()
                        keywords = ["new", "play", "rematch", "новая", "играть", "реванш"]
                        if any(k in text for k in keywords):
                             if safe_click(btn, f"{desc} ({text})"): return
                        elif "game over" in desc.lower(): # For generic selectors, if no text match, try clicking anyway if it's the primary action
                             pass 
                             
                    # Fallback: Just click the first visible one if it's a specific data-cy
                    if "data-cy" in selector:
                         if safe_click(btns[0], desc): return

            except Exception as e:
                print(f"[DEBUG] Error checking selector {selector}: {e}")

        # Attempt 2: Search in sidebar container (Robust Loop)
        print("[DEBUG] interacting with sidebar...")
        for _ in range(3): # Retry loop for stale elements
            try:
                # Re-find container and buttons on every attempt
                sections = self.chrome.find_elements(By.CSS_SELECTOR, ".game-over-buttons-component, .daily-game-footer-component, .live-game-buttons-component")
                
                if not sections:
                    # print("[DEBUG] No sidebar buttons container found.")
                    continue

                for section in sections:
                    buttons = section.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        try:
                            text = btn.text.lower()
                            keywords = ["new", "play", "rematch", "новая", "играть", "реванш"]
                            if any(k in text for k in keywords):
                                if safe_click(btn, f"Sidebar Button ({text})"):
                                    return
                        except StaleElementReferenceException:
                            continue
                
            except Exception as e:
                 print(f"[DEBUG] Sidebar interaction error: {e}")
                 pass

        print("[DEBUG] Auto-match click failed after all attempts.")

    def make_mouseless_move(self, move, move_count):
        pass

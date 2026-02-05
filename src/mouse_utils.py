import numpy as np
import pyautogui
import time
import random
import scipy.interpolate as si

def bezier_curve(p0, p1, p2, p3, n=100):
    """
    Generate n points on a cubic Bezier curve.
    p0, p1, p2, p3 are tuples/lists of (x, y) coordinates.
    """
    t = np.linspace(0, 1, n)
    # Cubic Bezier formula
    # B(t) = (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)*t^2*P2 + t^3*P3
    
    x = (1-t)**3 * p0[0] + 3*(1-t)**2 * t * p1[0] + 3*(1-t) * t**2 * p2[0] + t**3 * p3[0]
    y = (1-t)**3 * p0[1] + 3*(1-t)**2 * t * p1[1] + 3*(1-t) * t**2 * p2[1] + t**3 * p3[1]
    
    return list(zip(x, y))

def human_move_to(x, y, duration=None, speed_multiplier=1.0):
    """
    Move the mouse to (x, y) in a human-like way using Bezier curves.
    """
    start_x, start_y = pyautogui.position()
    end_x, end_y = x, y
    
    # Randomize the control points to create an arc
    # Control point 1: random point between start and end
    dist = np.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
    
    # If distance is very small, just move directly
    if dist < 5:
        pyautogui.moveTo(x, y)
        return

    # Random offset for control points
    offset = dist * 0.2  # curve intensity
    
    cp1_x = start_x + (end_x - start_x) * 0.3 + random.uniform(-offset, offset)
    cp1_y = start_y + (end_y - start_y) * 0.3 + random.uniform(-offset, offset)
    
    cp2_x = start_x + (end_x - start_x) * 0.7 + random.uniform(-offset, offset)
    cp2_y = start_y + (end_y - start_y) * 0.7 + random.uniform(-offset, offset)
    
    # Target with slight jitter (overshoot/undershoot logic can be added here, 
    # but for now we land exactly on target to not break game logic)
    
    points = bezier_curve((start_x, start_y), (cp1_x, cp1_y), (cp2_x, cp2_y), (end_x, end_y), n=random.randint(40, 70))
    
    # Calculate duration if not provided
    if duration is None:
        # Base duration on distance, plus some randomness
        base_speed = random.uniform(800, 1200) # pixels per second
        duration = (dist / base_speed) + random.uniform(0.1, 0.3)
        
    # Apply speed multiplier (lower multiplier = faster)
    duration = duration * speed_multiplier
    
    # Variable sleep times between points to simulate acceleration/deceleration
    # Bell curve for speed (faster in middle, slower at ends)
    
    dt = duration / len(points)
    
    for px, py in points:
        pyautogui.platformModule._moveTo(int(px), int(py)) # Use internal _moveTo to avoid extra delays from pyautogui.moveTo wrapper if any
        # Randomize sleptime slightly
        time.sleep(max(0, dt + random.uniform(-0.001, 0.001)))
        
    # Ensure we land exactly
    pyautogui.moveTo(end_x, end_y)

def human_drag_to(x, y, duration=None, speed_multiplier=1.0):
    """
    Drag like a human. 
    Note: PyAutoGUI dragTo implementation usually just moves then releases.
    We need to hold mouse down, move humanly, then release.
    """
    # Simply mapping drag to move logic but with mouse down
    pyautogui.mouseDown()
    human_move_to(x, y, duration, speed_multiplier)
    pyautogui.mouseUp()

import sys
import os
import time
import itertools
import re
from typing import List, Tuple, Optional

class Frame:
    def __init__(self, name: str, content: str):
        self.name = name
        self.lines = content.splitlines()
        self.height = len(self.lines)
        self.width = max(len(self.strip_ansi(line)) for line in self.lines) if self.lines else 0
        
    @staticmethod
    def strip_ansi(text: str) -> str:
        """Remove ANSI escape sequences"""
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)
    
    def get_line(self, y: int) -> Optional[str]:
        """Get line at y position"""
        return self.lines[y] if 0 <= y < self.height else None

class DifferentialRenderer:
    def __init__(self, frame_delay=0.02):
        self.frame_delay = frame_delay
        self.frames: List[Frame] = []
        self.stdout = sys.stdout
        self.stdout.reconfigure(write_through=True) if hasattr(self.stdout, 'reconfigure') else None
        
        # ANSI sequences
        self.hide_cursor = "\033[?25l"
        self.show_cursor = "\033[?25h"
        self.clear = "\033[2J\033[H"
        self.erase_line = "\033[2K"
        self.enable_sync_rendering = "\033[?2026h"
        self.disable_sync_rendering = "\033[?2026l"
    
    def move_cursor(self, x: int, y: int) -> str:
        """Move cursor to position"""
        return f"\033[{y+1};{x+1}H"
    
    def enable_synchronized_mode(self):
        sys.stdout.write(self.enable_sync_rendering)
        sys.stdout.flush()

    def disable_synchronized_mode(self):
        sys.stdout.write(self.disable_sync_rendering)
        sys.stdout.flush()

    def find_line_differences(self, old_line: Optional[str], new_line: Optional[str]) -> List[Tuple[int, str]]:
        """Find differences between two lines"""
        if old_line is None and new_line is None:
            return []
        if old_line is None:
            return [(0, new_line)]
        if new_line is None:
            return [(0, '')]
        if old_line != new_line:
            return [(0, new_line)]
        return []

    def load_frames(self, folder_path: str) -> int:
        """Load frames from files"""
        frame_files = sorted(
            [
                f for f in os.listdir(f"{os.getcwd()}/{folder_path}")
                if f.startswith("frame_cleaned_") and f.endswith(".txt")
            ], 
            key=lambda f_name: int(f_name.split('_')[-1][:-4])
        )

        if not frame_files:
            raise ValueError("No frame files found")
        
        for frame_path in frame_files:
            with open(os.path.join(folder_path, frame_path), 'r', encoding='utf-8') as file:
                self.frames.append(Frame(frame_path, file.read()))
        
        return len(self.frames)

    def render_frame(self, frame: Frame):
        """Render full frame"""
        self.stdout.write(self.clear)
        for y, line in enumerate(frame.lines):
            self.stdout.write(self.move_cursor(0, y))
            self.stdout.write(line)
        self.stdout.flush()

    def render_frame_difference(self, current: Frame, next_frame: Frame):
        """Render only the differences between frames"""
        max_height = max(current.height, next_frame.height)

        for y in range(max_height):
            current_line = current.get_line(y)
            next_line = next_frame.get_line(y)
            
            differences = self.find_line_differences(current_line, next_line)
            
            if differences:
                self.stdout.write(self.move_cursor(0, y))
                self.stdout.write(self.erase_line)
                if next_line is not None:
                    self.stdout.write(next_line)
        
        # Clear any remaining lines if new frame is shorter
        if next_frame.height < current.height:
            for y in range(next_frame.height, current.height):
                self.stdout.write(self.move_cursor(0, y))
                self.stdout.write(self.erase_line)
        
        self.stdout.flush()

    def run_animation(self):
        """Run the animation"""
        if not self.frames:
            return

        try:
            self.stdout.write(self.hide_cursor)
            self.enable_synchronized_mode()

            # Render first frame
            self.render_frame(self.frames[0])
            current_frame = self.frames[0]
            
            # Animation loop
            for next_frame in itertools.cycle(self.frames[1:] + [self.frames[0]]):
                time.sleep(self.frame_delay)
                self.render_frame_difference(current_frame, next_frame)
                current_frame = next_frame

        except KeyboardInterrupt:
            pass
        finally:
            self.stdout.write(self.show_cursor)
            self.stdout.write(self.clear)
            self.disable_synchronized_mode()
            self.stdout.write("Animation stopped.\n")
            self.stdout.flush()

def main():
    renderer = DifferentialRenderer(frame_delay=0.02)
    folder_path = 'ghostty-animation-frames/'

    try:
        frame_count = renderer.load_frames(folder_path)
        print(f"Loaded {frame_count} frames. Starting animation...")
        time.sleep(1)
        renderer.run_animation()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
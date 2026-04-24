import sys
import os
import asyncio
import platform
import warnings

# Suppress the "I/O operation on closed pipe" errors common with Windows Proactor
warnings.filterwarnings("ignore", category=ResourceWarning)

# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.gui.app import App
from src.core.logger import setup_logging

if __name__ == "__main__":
    try:
        setup_logging()
        
        # Further suppress asyncio noise
        if platform.system() == 'Windows':
            # loop = asyncio.new_event_loop()
            # asyncio.set_event_loop(loop)
            pass

        app = App()
        # app.mainloop() - App constructor handles the loop now
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("Critical Crash. Press Enter...")

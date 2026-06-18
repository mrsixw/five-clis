"""Generate a man page for five-clis using click-man."""

import sys
from pathlib import Path

from click_man.core import man_pages

from fiveclis.cli import main

target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("man1")
target.mkdir(parents=True, exist_ok=True)
man_pages(main, target=str(target))

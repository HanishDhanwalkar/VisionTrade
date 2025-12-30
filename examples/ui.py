from pathlib import Path
from typing import Any
import sys

sys.path.append(str(Path(__file__).parent.parent / "freqtrade"))

from freqtrade.commands.deploy_ui import (
    clean_ui_subdir,
    download_and_install_ui,
    get_ui_download_url,
    read_ui_version,
)

def start_install_ui() -> None:
    dest_folder = Path(__file__).parents[1] / "freqtrade" / "rpc/api_server/ui/installed/"
    print(dest_folder)
    # First make sure the assets are removed.
    dl_url, latest_version = get_ui_download_url(
        "2.2.0", False
    )

    curr_version = read_ui_version(dest_folder)
    if curr_version == latest_version and not args.get("erase_ui_only"):
        print(f"UI already up-to-date, FreqUI Version {curr_version}.")
        return

    clean_ui_subdir(dest_folder)
    download_and_install_ui(dest_folder, dl_url, latest_version)
        
start_install_ui()
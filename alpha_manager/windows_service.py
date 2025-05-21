import time
import json
import shutil
import subprocess
from pathlib import Path

import servicemanager
import win32serviceutil
import win32service
import win32event

WATCH_DIRECTORY = Path("S:/ACE Dropbox/AUTOMATION/zapier")
SEEN_FILES_LOG = Path("S:/ACE Dropbox/AUTOMATION/logs/seen_files.txt")
DIRECTORY_MANAGER_SCRIPT = (
    Path("S:/ACE Dropbox/Adam Collins/github_repo/AlphApexManager") /
    "alpha_manager" / "directory_manager.py"
)
OUTPUT_DIR = Path("S:/ACE Dropbox/PROJECTS/_River-Division")


class JSONFileMonitorService(win32serviceutil.ServiceFramework):
    """Windows service that monitors a directory for new JSON files and
    invokes a directory generator script when new files are detected."""

    _svc_name_ = "JSONFileMonitorService"
    _svc_display_name_ = "JSON File Monitor Service"
    _svc_description_ = (
        "Monitors a directory for new JSON files and "
        "runs directory manager."
    )

    def __init__(self, args):
        """Initialize the Windows service and create the stop event."""
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

    def SvcStop(self):
        """Handle stop signal for the service."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.running = False
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        """Service entry point when started by the Windows SCM."""
        servicemanager.LogInfoMsg("JSONFileMonitorService started.")
        self.monitor_directory()
        servicemanager.LogInfoMsg("JSONFileMonitorService stopped.")

    def monitor_directory(self):
        """Main loop to monitor the directory for new JSON files.

        If new files are detected, it triggers the directory manager process
        and updates the seen files log.
        """
        seen_files = self.load_seen_files()
        while self.running:
            try:
                current_files = {
                    f.name for f in WATCH_DIRECTORY.glob("*.json")
                    if f.is_file()
                }
                new_files = current_files - seen_files

                for filename in new_files:
                    full_path = WATCH_DIRECTORY / filename
                    self.run_directory_manager(full_path)
                    seen_files.add(filename)

                self.save_seen_files(seen_files)
            except Exception as e:
                servicemanager.LogErrorMsg(f"Monitor error: {e}")
            time.sleep(10)

    def load_seen_files(self):
        """Load the set of already processed JSON filenames.

        Returns:
            set: A set of filenames read from the seen files log.
        """
        if SEEN_FILES_LOG.exists():
            try:
                return set(SEEN_FILES_LOG.read_text().splitlines())
            except Exception as e:
                servicemanager.LogErrorMsg(
                    f"Error reading seen files log: {e}"
                )
        return set()

    def save_seen_files(self, files_set):
        """Save the set of seen JSON filenames to the log file.

        Args:
            files_set (set): The set of filenames to persist.
        """
        try:
            SEEN_FILES_LOG.parent.mkdir(parents=True, exist_ok=True)
            SEEN_FILES_LOG.write_text("\n".join(sorted(files_set)))
        except Exception as e:
            servicemanager.LogErrorMsg(
                f"Error writing seen files log: {e}"
            )

    def run_directory_manager(self, json_file_path: Path):
        """Run the external directory manager script with parameters
        from the JSON file.

        Also waits for the expected project folder to be created and
        copies the original JSON file there as 'project_vars.json'.

        Args:
            json_file_path (Path): Path to the newly detected JSON file.
        """
        try:
            with json_file_path.open("r") as f:
                data = json.load(f)

            project_name = data.get("project_name")
            project_number = data.get("project_number")

            if project_name and project_number:
                subprocess.run(
                    [
                        "python",
                        str(DIRECTORY_MANAGER_SCRIPT),
                        "--generate",
                        "--template", "defaults/ace_basic.json",
                        "--output", str(OUTPUT_DIR),
                        "--project_name", project_name,
                        "--project_number", project_number,
                    ],
                    check=True
                )

                project_dir_name = f"{project_name}-{project_number}"
                project_dir_path = OUTPUT_DIR / project_dir_name
                output_json_path = project_dir_path / "project_vars.json"

                # Wait up to 20 seconds for the directory to appear
                for _ in range(40):  # 40 * 0.5s = 20 seconds
                    if project_dir_path.is_dir():
                        shutil.copyfile(json_file_path, output_json_path)
                        servicemanager.LogInfoMsg(
                            f"Copied JSON to {output_json_path}"
                        )
                        break
                    time.sleep(0.5)
                else:
                    servicemanager.LogErrorMsg(
                        f"Timeout waiting for directory: {project_dir_path}"
                    )

                servicemanager.LogInfoMsg(
                    f"Processed {project_name}-{project_number}"
                )
            else:
                servicemanager.LogErrorMsg(
                    f"Missing keys in {json_file_path}"
                )
        except Exception as e:
            servicemanager.LogErrorMsg(
                f"Error running directory manager: {e}"
            )


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(JSONFileMonitorService)

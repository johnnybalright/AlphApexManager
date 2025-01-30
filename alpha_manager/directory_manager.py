import os
import sys
import json
import shutil
from pathlib import Path
import argparse
import subprocess

script_dir = Path(__file__).parent

TEMPLATES_DIR = script_dir / "templates"
DEFAULT_TEMPLATES_DIR = TEMPLATES_DIR / "defaults"
LOG_FILE = script_dir / "directory_manager.log"
FILE_TEMPLATES_DIR = TEMPLATES_DIR / "file_templates"
USER_CREATED_DIR = TEMPLATES_DIR / "user_created"
CONFIG_FILE = script_dir / "config.json"


class TemplateManager:
    def __init__(self):
        self.ensure_directories()

    def restart(self):
        print("Returning to main menu...")
        os.execv(sys.executable, [sys.executable, __file__])

    def save_config(self, data):
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=4)
  
    def load_config(self):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        return None

    def ensure_directories(self):
        """Ensure required directories exist."""
        TEMPLATES_DIR.mkdir(exist_ok=True, parents=True)
        DEFAULT_TEMPLATES_DIR.mkdir(exist_ok=True, parents=True)
        FILE_TEMPLATES_DIR.mkdir(exist_ok=True, parents=True)
        USER_CREATED_DIR.mkdir(exist_ok=True, parents=True)

    def log(self, message):
        """Log actions to a file."""
        with open(LOG_FILE, "a") as log_file:
            log_file.write(message + "\n")

    def list_templates(self):
        """List available templates."""
        templates = []
        templates.extend(
            [
                f"defaults/{t.name}"
                for t in DEFAULT_TEMPLATES_DIR.glob("*.json")
            ]
        )
        templates.extend(
            [f"user_created/{t.name}" for t in TEMPLATES_DIR.glob("*.json")]
        )
        templates.extend(
            [f"user_created/{t.name}" for t in USER_CREATED_DIR.glob("*.json")]
        )
        return templates

    def create_template(self):
        """Create a new template."""
        template = {"main_directory": "", "subdirectories": {}}
        template["main_directory"] = input(
            "Enter the main directory name: "
        ).strip()
        while True:
            subdir = input(
                "Enter a subdirectory name (or press Enter to finish): "
            ).strip()
            if not subdir:
                break
            template["subdirectories"][subdir] = {"files": []}
            while True:
                file_name = input(
                    f"  Enter a file name for '{subdir}' \
                        (or press Enter to finish): "
                ).strip()
                if not file_name:
                    break
                file_type = input(
                    f"  Should the file '{file_name}' \
                        be [1] Empty or [2] Template-based? (Enter 1 or 2): "
                ).strip()
                if file_type == "1":
                    template["subdirectories"][subdir]["files"].append(
                        {"name": file_name, "type": "empty"}
                    )
                elif file_type == "2":
                    source_path = input(
                        f"  Enter the source path for the template file \
                            for '{file_name}': "
                    ).strip()
                    template["subdirectories"][subdir]["files"].append(
                        {
                            "name": file_name,
                            "type": "template",
                            "source": source_path,
                        }
                    )
                else:
                    print("Invalid choice. Please enter 1 or 2.")
        template_name = input(
            "Enter a name for this template (e.g., 'my_template.json'): "
        ).strip()
        self.save_template(template_name, template)

    def load_template(self, template_name):
        """Load a template."""
        if template_name.startswith("defaults/"):
            path = DEFAULT_TEMPLATES_DIR / template_name.replace(
                "defaults/", ""
            )
        else:
            path = TEMPLATES_DIR / template_name.replace("user_created/", "")
        if not path.exists():
            print(f"Template '{template_name}' does not exist.")
            return None
        with open(path, "r") as file:
            return json.load(file)

    def save_template(self, template_name, data, is_default=False):
        """Save a template."""
        path = (
            DEFAULT_TEMPLATES_DIR / template_name
            if is_default
            else TEMPLATES_DIR / template_name
        )
        with open(path, "w") as file:
            json.dump(data, file, indent=4)
        print(f"Template '{template_name}' saved successfully!")
        self.log(f"Template '{template_name}' saved.")

    def add_file_template(self):
        """Add a new file template to the FILE_TEMPLATES_DIR."""
        source_path = input(
            "Enter the full path of the file to add as a template: "
        ).strip()
        if not os.path.isfile(source_path):
            print(f"'{source_path}' is not a valid file.")
            return
        destination_path = FILE_TEMPLATES_DIR / Path(source_path).name
        try:
            shutil.copy(source_path, destination_path)
            print(f"File template '{destination_path}' added successfully!")
        except Exception as e:
            print(f"Error adding file template: {e}")

    def list_file_templates(self):
        """List all file templates in the FILE_TEMPLATES_DIR."""
        templates = list(FILE_TEMPLATES_DIR.iterdir())
        if not templates:
            print("No file templates available.")
        else:
            print("Available file templates:")
            for i, tmpl in enumerate(templates, start=1):
                print(f"  {i}) {tmpl.name}")
        return templates

    def validate_template(self, template, template_name):
        """Validate a template's structure and provide
        detailed error messages."""
        errors = []

        # Check for required keys
        required_keys = ["main_directory", "subdirectories"]
        for key in required_keys:
            if key not in template:
                errors.append(f"Missing required key: '{key}'")

        # Check 'subdirectories' is a dictionary
        if "subdirectories" in template and not isinstance(
            template["subdirectories"], dict
        ):
            errors.append("'subdirectories' must be a dictionary.")

        # Validate subdirectory structure
        if "subdirectories" in template and isinstance(
            template["subdirectories"], dict
        ):
            for subdir, contents in template["subdirectories"].items():
                if not isinstance(contents, dict):
                    errors.append(
                        f"Subdirectory '{subdir}' must be a dictionary."
                    )
                elif "files" not in contents:
                    errors.append(
                        f"Subdirectory '{subdir}' is missing a 'files' list."
                    )
                elif not isinstance(contents["files"], list):
                    errors.append(
                        f"'files' in subdirectory '{subdir}' must be a list."
                    )
                else:
                    for file_info in contents["files"]:
                        if not isinstance(file_info, dict):
                            errors.append(
                                f"File entry in '{subdir}' \
                                    must be a dictionary."
                            )
                        elif (
                            "name" not in file_info or "type" not in file_info
                        ):
                            errors.append(
                                f"File entry in '{subdir}' must have 'name' \
                                    and 'type' keys."
                            )
                        elif (
                            file_info["type"] == "template"
                            and "source" not in file_info
                        ):
                            errors.append(
                                f"Template file '{file_info['name']}' in \
                                    '{subdir}' is missing a 'source' key."
                            )
                        elif file_info["type"] not in ["empty", "template"]:
                            errors.append(
                                f"Invalid file type for '{file_info['name']}' \
                                    in '{subdir}'. Must be \
                                        'empty' or 'template'."
                            )

        # Output results
        if errors:
            print(f"Validation errors for template '{template_name}':")
            for error in errors:
                print(f"  - {error}")
            return False
        else:
            print(
                f"No errors generated during validation of '{template_name}'."
            )
            return True

    def preview_template(self, template):
        """Preview the template's structure."""
        self.display_template_tree(template)

    def validate_directory_path(self, path):
        """Validate a directory path and provide detailed feedback."""
        # Strip non-alphanumeric characters from the start and end of the path
        cleaned_path = path.strip("!@#$%^&*()_+={}[]|:;'<>,.?~`")

        if cleaned_path != path:
            print(f"DEBUG: Path cleaned from '{path}' to '{cleaned_path}'")

        if not os.path.exists(cleaned_path):
            return False, f"Path does not exist: '{cleaned_path}'"
        if os.path.isfile(cleaned_path):
            return False, f"Path is a file, not a directory: '{cleaned_path}'"
        if not os.path.isdir(cleaned_path):
            return False, f"Path is not a valid directory: '{cleaned_path}'"
        try:
            # Attempt to access the directory to check for permissions
            _ = os.listdir(cleaned_path)
        except PermissionError:
            return (
                False,
                f"Permission denied: Cannot access directory '{cleaned_path}'",
            )
        return True, f"Valid directory: '{cleaned_path}'", cleaned_path

    def clone_directory(self, source_dir, output_template_name):
        """Clone an existing directory structure into a template."""
        is_valid, message, cleaned_path = self.validate_directory_path(
            source_dir
        )

        if not is_valid:
            print(f"ERROR: {message}")
            return
        else:
            print(f"SUCCESS: {message}")

        template = {
            "main_directory": os.path.basename(cleaned_path),
            "subdirectories": {},
        }
        for root, dirs, files in os.walk(cleaned_path):
            relative_root = os.path.relpath(root, cleaned_path)
            if relative_root == ".":
                relative_root = ""
            if relative_root not in template["subdirectories"]:
                template["subdirectories"][relative_root] = {"files": files}
        self.save_template(output_template_name, template)

    def export_directory_map(self, root_dir, output_map_file):
        """Export the directory structure as a map."""
        with open(output_map_file, "w") as file:
            for root, dirs, files in os.walk(root_dir):
                level = root.replace(root_dir, "").count(os.sep)
                indent = " " * 4 * level
                file.write(f"{indent}{os.path.basename(root)}/\n")
                for f in files:
                    file.write(f"{indent}    {f}\n")
        print(f"Directory map exported to '{output_map_file}'")

    def search_template(self, template_name, query):
        """Search for a file or directory in a template."""
        template = self.load_template(template_name)
        if not template:
            return
        results = []
        for subdir, contents in template["subdirectories"].items():
            if query in subdir or any(query in f for f in contents["files"]):
                results.append(subdir)
        if results:
            print("Search Results:")
            for result in results:
                print(f"  - {result}")
        else:
            print("No matches found.")

    def generate_from_template(self, template_name, output_dir, project_number, project_name):
        """Generate directories and files from a template."""
        template = self.load_template(template_name)
        if project_number and project_name != "":
            template = self.modify_template(template, project_number, project_name)
        if not template:
            return
        if not self.validate_template(template, template_name):
            print("Generation aborted due to invalid template.")
            return
        main_dir = Path(output_dir) / template["main_directory"]
        os.makedirs(main_dir, exist_ok=True)
        for subdir, contents in template["subdirectories"].items():
            subdir_path = main_dir / subdir
            os.makedirs(subdir_path, exist_ok=True)
            for file_info in contents["files"]:
                file_path = subdir_path / file_info["name"]
                if file_info["type"] == "empty":
                    file_path.touch()  # Create an empty file
                elif file_info["type"] == "template":
                    source_path = Path(file_info["source"])
                    if source_path.exists():
                        shutil.copy(source_path, file_path)
                        # Copy the template file
                    else:
                        print(f"Template file not found: {source_path}")
                else:
                    print(f"Unknown file type: {file_info['type']}")
        print(f"Directory structure generated in: {main_dir}")
        self.log(f"Directory structure generated: {main_dir}")

    def display_template_tree(self, template):
        """Display the template as a tree structure."""

        def print_tree(subdir, contents, prefix=""):
            """Recursive helper to print subdirectories and files."""
            subdirs = list(contents.keys())
            for i, sub in enumerate(subdirs):
                is_last_subdir = i == len(subdirs) - 1
                connector = "└──" if is_last_subdir else "├──"
                print(f"{prefix}{connector} {sub}/")

                # Add an empty marker if the subdirectory has no files
                if not contents[sub]["files"]:
                    print(f"{prefix}    └── (empty)")
                    continue

                # Prepare the prefix for nested content
                sub_prefix = (
                    f"{prefix}    " if is_last_subdir else f"{prefix}│   "
                )

                # Print the files in the current subdirectory
                for j, file_name in enumerate(contents[sub]["files"]):
                    is_last_file = j == len(contents[sub]["files"]) - 1
                    file_connector = "└──" if is_last_file else "├──"
                    print(f"{sub_prefix}{file_connector} {file_name}")

        # Main directory
        print("")
        print(template["main_directory"], "Template Directory PREVIEW\n\n")
        print(template["main_directory"])
        print_tree("", template["subdirectories"])

    def modify_template(self, template, project_number, project_name):
        """
        Modify the given template by replacing 'xxxxx' in file names with the project_number
        and updating the main_directory key with "project_number-project_name".

        Args:
            template (dict): The template to modify.
            project_number (str): The project number to use.
            project_name (str): The project name to use.

        Returns:
            dict: The modified template.
        """
        # Update the main_directory
        template["main_directory"] = f"{project_name}-{project_number}"

        # Iterate over subdirectories to replace 'xxxxx' in file names
        for subdir, contents in template["subdirectories"].items():
            if "files" in contents:
                for file in contents["files"]:
                    if "name" in file and "xxxxx" in file["name"]:
                        file["name"] = file["name"].replace(
                            "xxxxx", project_number
                        )

        return template

    def generate_default(
        self,
        project_number,
        project_name,
        template_name="defaults/ace_basic.json",
        output_dir="output",
    ):
        """Generate a default template."""
        template = self.load_template(template_name)
        if not project_number and project_name == "":
            template = self.modify_template(template, project_number, project_name)
        if not template:
            return
        if not self.validate_template(template, template_name):
            print("Generation aborted due to invalid template.")
            return
        template = self.modify_template(template, project_number, project_name)
        main_dir = Path(output_dir) / template["main_directory"]
        os.makedirs(main_dir, exist_ok=True)
        for subdir, contents in template["subdirectories"].items():
            subdir_path = main_dir / subdir
            os.makedirs(subdir_path, exist_ok=True)
            for file_info in contents["files"]:
                file_path = subdir_path / file_info["name"]
                if file_info["type"] == "empty":
                    file_path.touch()


def main():
    parser = argparse.ArgumentParser(description="Template Manager")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate from a template"
    )
    parser.add_argument(
        "--template",
        type=str,
        default="defaults/ace_basic.json",
        help="Template to use (default: defaults/ace_basic.json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=False,
        default=".",
        help="Output directory"
    )
    parser.add_argument(
        "--project_name",
        type=str,
        required=False,
        help="Project name- not required"
    )
    parser.add_argument(
        "--project_number",
        type=str,
        required=False,
        help="Project number- not required"
    )

    args = parser.parse_args()

    manager = TemplateManager()

    if args.generate:
        print(
            f"Generating directory structure from template '{args.template}' into '{args.output}'"
        )
        manager.generate_default(
            project_number=args.project_number,
            project_name=args.project_name,
            template_name=args.template,
            output_dir=args.output,
        )
        return

    # while True:
    config = manager.load_config()

    if not config:
        dir_path = input("Enter new output directory location or press ENTER for default: ").strip()
        if dir_path == "":
            dir_path = USER_CREATED_DIR
        path = Path(dir_path)
        config = {
            "output_dir": f"{dir_path}"
        }
        if path.exists():
            manager.save_config(config)
            manager.restart()
        else:
            print("Invalid directory. Please enter a valid directory.")
        
    while True:
        print("\nAlphApex Directory Manager\n\nChoose an action:")
        print("  1) Manage/Create Templates")
        print("  2) Generate Directory Templates")
        print("  3) Clone Existing Directory to Template")
        print("  4) Search File/Directory in Templates")
        print("  5) Export Directory Map")
        print("  6) Exit")
        choice = input("Enter your choice (1-6): ").strip()

        if choice == "1":
            print("\nDirectory Template Management:")
            print("  1) Create Directory Template")
            print("  2) List Directory Templates")
            print("  3) Preview Directory Template")
            print("  4) Validate Directory Template")
            print("  5) File Template Management")
            print("  6) Return to Main Menu")
            print("  6) Exit")
            action = input("Choose an action (1-6): ").strip()

            if action == "1":
                manager.create_template()
                manager.restart()

            elif action == "2":
                templates = manager.list_templates()
                print("\nAvailable templates:")
                for tmpl in templates:
                    print(f"  {tmpl}")
                manager.restart()
                
            elif action == "3":
                templates = manager.list_templates()
                for i, tmpl in enumerate(templates):
                    print(f"  {i + 1}. {tmpl}")

                idx = int(input("Choose a template to preview: ")) - 1
                manager.preview_template(manager.load_template(templates[idx]))
                manager.restart()

            elif action == "4":
                templates = manager.list_templates()
                for i, tmpl in enumerate(templates):
                    print("\n", f"  {i + 1}. {tmpl}")

                try:
                    idx = int(input("\nChoose a template to validate: ")) - 1
                    if idx < 0 or idx >= len(templates):
                        print(
                            "Invalid selection. Please choose a valid template."
                        )
                        return

                    template_name = templates[idx]
                    template = manager.load_template(template_name)

                    if template:
                        manager.validate_template(template, template_name)
                    else:
                        print(
                            f"Template '{template_name}' could not be loaded."
                        )
                    manager.restart()
                except ValueError:
                    print("Invalid input. Please enter a number.")

            elif action == "5":
                print("\nFile Template Management:")
                print("  1) Add a New File Template")
                print("  2) List File Templates")

                action = input("Choose an action (1-2): ").strip()
                if action == "1":
                    manager.add_file_template()
                    manager.restart()
                elif action == "2":
                    manager.list_file_templates()
                    manager.restart()
            
            elif action == "6":
                manager.restart()

            elif action == "7":
                print("Exiting AlphApex Directory Manager. Goodbye!")
                break

        elif choice == "2":
            templates = manager.list_templates()
            print("\nAvailable templates:")

            for i, tmpl in enumerate(templates):
                print(f"  {i + 1}. {tmpl}")
#
#
#
#
#
            idx = int(input("Choose a template to generate: ")) - 1
            proj_num = input("Enter the project number or press ENTER for default: ").strip()
            proj_name = input("Enter the project name or press ENTER for default: ").strip()
            output_dir = input("Enter the output directory or press ENTER to use user_created directory in templates: ").strip()

            manager.generate_from_template(templates[idx], output_dir, proj_num, proj_name)
            manager.restart()

        elif choice == "3":
            source_dir = input("Enter the source directory to clone: ").strip()
            output_template_name = input(
                "Enter the output template name: "
            ).strip()

            manager.clone_directory(source_dir, output_template_name)

        elif choice == "4":
            templates = manager.list_templates()

            for i, tmpl in enumerate(templates):
                print(f"  {i + 1}. {tmpl}")

            idx = int(input("Choose a template to search: ")) - 1

            query = input(
                "Enter the file or directory to search for: "
            ).strip()

            manager.search_template(templates[idx], query)

        elif choice == "5":
            root_dir = input("Enter the root directory to map: ").strip()

            output_map_file = input(
                "Enter the output map filename (e.g., map.txt): "
            ).strip()

            manager.export_directory_map(root_dir, output_map_file)

        elif choice == "6":
            print("Exiting AlphApex Directory Manager. Goodbye!")
            break


if __name__ == "__main__":
    main()

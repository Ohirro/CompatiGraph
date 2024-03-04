import subprocess
from datetime import datetime

today_date = datetime.now()
formatted_date = today_date.strftime("%d.%m.%y")

package_name = "compatigraph"
version = "1.0.0"
distribution = "unstable"
urgency = "low"


def get_git_log():
    # Customize your git log command as needed
    git_log_command = ["git", "log", "--pretty=format:%h - %s (%ci)"]
    return subprocess.check_output(git_log_command).decode("utf-8")


def convert_to_debian_changelog(git_log):
    entries = git_log.split("\n")
    with open("debian/changelog", "w+") as changelog:
        changelog.write(f"{package_name} ({version}) {distribution}; urgency={urgency}\n")
        for entry in entries:
            # Format each commit as a changelog entry. Adjust the formatting as needed.
            changelog.write(f"  * {entry}\n")
        changelog.write("\n")
        changelog.write(f" -- Maintainer Ilya Kuksenok <kuksyenok.i.s@gmail.com>  {formatted_date}")


if __name__ == "__main__":
    git_log = get_git_log()
    convert_to_debian_changelog(git_log)

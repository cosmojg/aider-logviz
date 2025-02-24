#!/usr/bin/env python3
import json
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path


def run_command(command):
    """Run a shell command and return the output."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        text=True,
    )
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        print(f"Error executing command: {command}")
        print(f"Error: {stderr}")
        return None
    return stdout


def check_repo_exists():
    """Check if the aider repository exists in the current directory."""
    repo_path = Path("aider")
    git_path = repo_path / ".git"
    return repo_path.exists() and git_path.exists()


def clone_repo() -> bool:
    """Try to clone the aider repository using SSH, then HTTPS if SSH fails."""
    ssh_url = "git@github.com:Aider-AI/aider.git"
    https_url = "https://github.com/Aider-AI/aider.git"

    print("Aider repository not found. Attempting to clone...")

    # Try SSH first
    print(f"Attempting to clone from {ssh_url}...")
    ssh_command = f"git clone {ssh_url}"
    ssh_result = run_command(ssh_command)

    if ssh_result is not None:
        print("Successfully cloned Aider repository over SSH.")
        return True

    # If SSH fails, try HTTPS
    print(f"SSH clone failed. Attempting to clone from {https_url}...")
    https_command = f"git clone {https_url}"
    https_result = run_command(https_command)

    if https_result is not None:
        print("Successfully cloned Aider repository over HTTPS.")
        return True

    # If both fail, return False
    print("Failed to clone Aider repository. Please clone it manually and try again.")
    return False


def get_file_commits(file_path):
    """Get all commits that modified the specified file."""
    command = f"git --git-dir=aider/.git --work-tree=aider log --pretty=format:%H --follow -- {file_path}"
    output = run_command(command)
    if output is None:
        return []
    return output.strip().split("\n")


def get_file_content_at_commit(commit, file_path):
    """Get the content of the file at the specified commit."""
    command = f"git --git-dir=aider/.git --work-tree=aider show {commit}:{file_path}"
    return run_command(command)


def main() -> None:
    # Check if aider repository exists, try to clone if it doesn't
    if not check_repo_exists() and not clone_repo():
        print("Error: Aider repository is required but could not be cloned.")
        sys.exit(1)  # Exit with error code

    # Define the file path
    file_path = "aider/website/assets/sample-analytics.jsonl"
    output_file = "merged-analytics.jsonl"

    # Get all commits that modified the file
    print(f"Getting commits for {file_path}...")
    commits = get_file_commits(file_path)
    print(f"Found {len(commits)} commits")

    # Dictionary to store all unique events
    # Using OrderedDict to maintain chronological order
    all_events = OrderedDict()

    # Process each commit from oldest to newest
    n_unique = 0
    n_unique_last = 0
    n_skipped = 0
    n_skipped_last = 0
    n_lines = 0
    for commit in reversed(commits):
        print(f"Processing commit {commit[:8]}...")
        content = get_file_content_at_commit(commit, file_path)

        if content is None:
            print(f"Skipping commit {commit[:8]} - unable to retrieve content")
            continue

        # Parse each line and add to all_events dictionary
        content_by_line = content.strip().split("\n")
        line_count = len(content_by_line)
        n_lines += line_count
        print(f"...with {line_count} lines")
        for line in content_by_line:
            if not line.strip():
                continue

            try:
                event = json.loads(line)

                # Create a unique identifier for the event
                # Using a tuple of (event type, user_id, time) as the key
                event_key = (
                    event.get("event", ""),
                    event.get("user_id", ""),
                    event.get("time", 0),
                )

                # Add to dictionary if not already present
                if event_key not in all_events:
                    all_events[event_key] = event
                    n_unique += 1
                else:
                    n_skipped += 1
                    # print(f"Skipping duplicate event: {event_key}")
            except json.JSONDecodeError:
                print(f"Error parsing JSON in commit {commit[:8]}: {line[:50]}...")
        print(f"...and {n_unique - n_unique_last} unique events")
        print(f"...and {n_skipped - n_skipped_last} duplicate events")
        print(f"...and {n_unique + n_skipped - n_unique_last - n_skipped_last} events processed")
        n_unique_last = n_unique
        n_skipped_last = n_skipped
    print(f"{n_unique} total unique events merged")
    print(f"{n_skipped} total duplicate events skipped")
    print(f"{n_unique + n_skipped} total events processed")
    print(f"{n_lines} total lines processed")

    # Write all events to the output file
    if not all_events:
        print("Error: No events logged.")
        sys.exit(1)  # Exit with error code
    print(f"Writing {len(all_events)} events to {output_file}...")
    with open(output_file, "w") as f:
        for event in all_events.values():
            f.write(json.dumps(event) + "\n")

    print(f"Finished! Consolidated log written to {output_file}")


if __name__ == "__main__":
    main()

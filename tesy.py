import os
import requests
import json
import subprocess
import threading
import time
import git
from urllib.parse import urljoin

session = requests.Session()

# Function to download a file from a URL
def download_file(url, local_filename):
    with session.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"Downloaded {url} to {local_filename}")

# Function to download the master.blurl file from a URL
def download_master_blurl(url, destination_path):
    print(f"Downloading {url} to {destination_path}...")
    response = session.get(url, stream=True)
    response.raise_for_status()
    with open(destination_path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)
    print(f"Downloaded {url} to {destination_path}")

# Decompress the .blurl file to .json using blurl.py
def decompress_blurl_file(blurl_filename):
    print(f"Decompressing {blurl_filename}...")
    command = ["python", "blurl.py", "-d", blurl_filename]
    subprocess.run(command, check=True)

# Parse the decompressed JSON
def parse_master_blurl(content):
    playlists = json.loads(content)
    return playlists

# Download segments from m3u8 files with threading
def download_segment_thread(segment_url, segment_filename):
    download_file(segment_url, segment_filename)

def download_segments_from_variant(variant_url, output_folder):
    response = session.get(variant_url)
    response.raise_for_status()
    m3u8_content = response.text
    lines = m3u8_content.splitlines()
    segments = []
    threads = []
    for line in lines:
        if line.endswith(".m4s"):  # Find the segments
            segment_url = urljoin(variant_url, line.strip())  # Resolve relative URL to absolute
            segment_filename = os.path.join(output_folder, os.path.basename(segment_url))
            thread = threading.Thread(target=download_segment_thread, args=(segment_url, segment_filename))
            threads.append(thread)
            thread.start()
            segments.append(segment_filename)
    for thread in threads:
        thread.join()
    return segments

# Download INIT and M3U8 files
def download_init_and_m3u8_files(base_url, init_files, m3u8_files, output_folder):
    for init_file in init_files:
        init_url = urljoin(base_url, init_file)
        init_filename = os.path.join(output_folder, init_file)
        download_file(init_url, init_filename)
    for m3u8_file in m3u8_files:
        m3u8_url = urljoin(base_url, m3u8_file)
        m3u8_filename = os.path.join(output_folder, m3u8_file)
        download_file(m3u8_url, m3u8_filename)

# Run ffmpeg command to concatenate video segments
def concatenate_segments_with_ffmpeg(init_file, segments, output_file):
    concat_str = "|".join([init_file] + segments)
    command = [
        "ffmpeg", "-i", f"concat:{concat_str}", "-c", "copy", "-bsf:a", "aac_adtstoasc", output_file
    ]
    print(f"Running ffmpeg to concatenate: {concat_str}")
    subprocess.run(command, check=True)
    print(f"Output saved to {output_file}")

# Automatically overwrite files if they exist
def overwrite_file(file_path):
    if os.path.exists(file_path):
        print(f"Overwriting existing file: {file_path}")
        os.remove(file_path)

# Remove old .m4s, .mp4, and .m3u8 files before starting
def remove_old_files(output_folder):
    for file_name in os.listdir(output_folder):
        if file_name.endswith((".m4s", ".mp4", ".m3u8")):
            file_path = os.path.join(output_folder, file_name)
            overwrite_file(file_path)

import datetime

# Git push to the repository with proper error handling
def git_push():
    try:
        # Path to the output file
        output_file_path = r"C:\Users\cousin\Documents\Doc\Fortnite\blurl\download\new\output_merged.mp4"
        
        # Ensure the file exists
        if not os.path.exists(output_file_path):
            print(f"Error: {output_file_path} does not exist!")
            return
        
        # Initialize the repo
        repo = git.Repo(r"C:\Users\cousin\Documents\Doc\Fortnite\blurl\download\new")  # Path to your repo
        origin = repo.remotes.origin
        
        # Fetch the latest changes from the remote
        print("Fetching latest changes from the remote...")
        origin.fetch()

        # Ensure you're on the correct branch (main)
        current_branch = repo.active_branch.name
        if current_branch != "main":
            print(f"Warning: You are on branch '{current_branch}', switching to 'main'...")
            repo.git.checkout("main")
        
        # Pull the latest changes before pushing
        print("Pulling the latest changes from the remote repository...")
        origin.pull()

        # Add the output_merged.mp4 file to Git
        repo.git.add(output_file_path)

        # Commit the changes
        repo.index.commit("Added updated output_merged.mp4")

        # Push the changes to the remote repository
        print("Pushing changes to the remote repository...")
        origin.push()

        print("output_merged.mp4 pushed successfully!")

    except git.exc.GitCommandError as e:
        print(f"Error pushing changes: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

        
# Main workflow
def main():
    video_uuid = str(input("video: "))
    start_time = time.time()
    base_url = f"https://cdn-0001.qstv.on.epicgames.com/{video_uuid}/"
    output_folder = r"C:\Users\cousin\Documents\Doc\Fortnite\blurl\download\new"  # Use your repo folder for outputs
    master_blurl_url = f"https://cdn-0001.qstv.on.epicgames.com/{video_uuid}/master.blurl"
    master_blurl_file = "master.blurl"

    # INIT and M3U8 files to download
    INIT_FILES = ["init_0.mp4", "init_5.mp4"]
    M3U8_FILES = ["variant_0.m3u8", "variant_5.m3u8"]

    # Step 1: Remove old .m4s, .mp4, and .m3u8 files in the repository folder
    remove_old_files(output_folder)

    # Step 2: Download master.blurl file
    download_master_blurl(master_blurl_url, master_blurl_file)

    # Step 3: Decompress master.blurl to master.json
    overwrite_file("master.json")
    decompress_blurl_file(master_blurl_file)

    # Step 4: Load decompressed master.json file
    with open("master.json", "r") as file:
        master_blurl = file.read()
    playlist = parse_master_blurl(master_blurl)

    # Step 5: Download INIT and M3U8 files
    download_init_and_m3u8_files(base_url, INIT_FILES, M3U8_FILES, output_folder)

    # Step 6: Download segments for variant 0 using threading
    variant_0_url = urljoin(base_url, "variant_0.m3u8")
    segments_0 = download_segments_from_variant(variant_0_url, output_folder)

    # Step 7: Concatenate segments for variant 0
    init_file_0 = os.path.join(output_folder, "init_0.mp4")
    output_file_0 = os.path.join(output_folder, "output_0.mp4")
    concatenate_segments_with_ffmpeg(init_file_0, segments_0, output_file_0)

    # Step 8: Download segments for variant 5 using threading
    variant_5_url = urljoin(base_url, "variant_5.m3u8")
    segments_5 = download_segments_from_variant(variant_5_url, output_folder)

    # Step 9: Concatenate segments for variant 5
    init_file_5 = os.path.join(output_folder, "init_5.mp4")
    output_file_5 = os.path.join(output_folder, "output_5.mp4")
    concatenate_segments_with_ffmpeg(init_file_5, segments_5, output_file_5)

    # Step 10: Merge both variant outputs using MP4Box into output_merged.mp4 in the repo folder
    merged_output_file = os.path.join(output_folder, "output_merged.mp4")
    command = ["MP4Box", "-add", output_file_0, "-add", output_file_5, "-new", merged_output_file]
    print(f"Running MP4Box to merge: {output_file_0} and {output_file_5}")
    subprocess.run(command, check=True)
    print(f"Merged output saved to {merged_output_file}")

    # Step 11: Git commit and push only the output_merged.mp4 file
    git_push()

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Execution Time: {execution_time:.2f} seconds")

if __name__ == "__main__":
    main()

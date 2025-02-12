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

    # Wait for all threads to finish
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
    # Concatenate the segments (init file and video segments)
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
        if file_name.endswith((".m4s", ".mp4", ".m3u8")):  # Check .m4s, .mp4, and .m3u8 files
            file_path = os.path.join(output_folder, file_name)
            overwrite_file(file_path)

# Git push to the repository
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

        # Add the output_merged.mp4 file
        repo.git.add(output_file_path)

        # Commit the changes
        repo.index.commit("Added updated output_merged.mp4")

        # Check if the branch has an upstream and push
        if not repo.git.rev_parse("--abbrev-ref", "HEAD") == "main":
            repo.git.push("--set-upstream", "origin", "main")
        else:
            origin.push()

        print("output_merged.mp4 pushed successfully!")

    except git.exc.GitCommandError as e:
        print(f"Error pushing changes: {e}")

# Main workflow
def main():
    video_uuid = str(input("video: "))
    start_time = time.time()

    base_url = f"https://cdn-0001.qstv.on.epicgames.com/{video_uuid}/"
    output_folder = r"C:\Users\cousin\Documents\Doc\Fortnite\blurl\download\new"  # Path to 'new' directory for output files
    master_blurl_url = f"https://cdn-0001.qstv.on.epicgames.com/{video_uuid}/master.blurl"
    master_blurl_file = "master.blurl"

    # INIT and M3U8 files to download
    INIT_FILES = ["init_0.mp4", "init_5.mp4"]
    M3U8_FILES = ["variant_0.m3u8", "variant_5.m3u8"]

    # Step 1: 
    remove_old_files(output_folder)

    # Step 2: 
    download_master_blurl(master_blurl_url, master_blurl_file)

    # Step 3: 
    overwrite_file("master.json")
    decompress_blurl_file(master_blurl_file)

    # Step 4: 
    with open("master.json", "r") as file:
        master_blurl = file.read()

    playlist = parse_master_blurl(master_blurl)

    # Step 5: 
    download_init_and_m3u8_files(base_url, INIT_FILES, M3U8_FILES, output_folder)

    # Step 6: 
    variant_0_url = urljoin(base_url, "variant_0.m3u8")
    segments_0 = download_segments_from_variant(variant_0_url, output_folder)

    # Step 7: 
    init_file_0 = os.path.join(output_folder, "init_0.mp4")
    output_file_0 = os.path.join(output_folder, "output_0.mp4")
    concatenate_segments_with_ffmpeg(init_file_0, segments_0, output_file_0)

    # Step 8: 
    variant_5_url = urljoin(base_url, "variant_5.m3u8")
    segments_5 = download_segments_from_variant(variant_5_url, output_folder)

    # Step 9: 
    init_file_5 = os.path.join(output_folder, "init_5.mp4")
    output_file_5 = os.path.join(output_folder, "output_5.mp4")
    concatenate_segments_with_ffmpeg(init_file_5, segments_5, output_file_5)

    # Step 10: 
    merged_output_file = os.path.join(output_folder, "output_merged.mp4")
    command = ["MP4Box", "-add", output_file_0, "-add", output_file_5, "-new", merged_output_file]
    print(f"Running MP4Box to merge: {output_file_0} and {output_file_5}")
    subprocess.run(command, check=True)
    print(f"Merged output saved to {merged_output_file}")

    # Git commit and push after each update
    git_push()

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Execution Time: {execution_time:.2f} seconds")

if __name__ == "__main__":
    main()

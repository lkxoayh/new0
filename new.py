import os
import requests
import json
from urllib.parse import urljoin
import subprocess
import threading
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
    response.raise_for_status()  # Ensure we catch any errors during the download

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
    playlists = json.loads(content)  # Assuming it's JSON format after decompression
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

# Main workflow
def main():
    base_url = "https://cdn-0001.qstv.on.epicgames.com/aagBjrnVNGTKeNlSgk/"
    output_folder = r"C:\Users\cousin\Documents\Doc\Fortnite\blurl\download"
    master_blurl_url = "https://cdn-0001.qstv.on.epicgames.com/aagBjrnVNGTKeNlSgk/master.blurl"
    master_blurl_file = "master.blurl"  # Name of your .blurl file

    # INIT and M3U8 files to download
    INIT_FILES = ["init_0.mp4", "init_1.mp4", "init_5.mp4"]
    M3U8_FILES = ["variant_0.m3u8", "variant_5.m3u8", "variant_1.m3u8"]

    # Step 1: Download the master.blurl file
    download_master_blurl(master_blurl_url, master_blurl_file)

    # Step 2: Decompress the master.blurl file to master.json
    overwrite_file("master.json")  # Ensure that 'master.json' is overwritten
    decompress_blurl_file(master_blurl_file)

    # Step 3: Load the decompressed .json file
    with open("master.json", "r") as file:
        master_blurl = file.read()

    playlists = parse_master_blurl(master_blurl)

    # Step 4: Download INIT and M3U8 files
    download_init_and_m3u8_files(base_url, INIT_FILES, M3U8_FILES, output_folder)

    # Step 5: Download segments for variant 0 using threading
    variant_0_url = urljoin(base_url, "variant_0.m3u8")
    segments_0 = download_segments_from_variant(variant_0_url, output_folder)

    # Step 6: Concatenate segments for variant 0
    init_file_0 = os.path.join(output_folder, "init_0.mp4")
    output_file_0 = os.path.join(output_folder, "output_0.mp4")
    concatenate_segments_with_ffmpeg(init_file_0, segments_0, output_file_0)

    # Step 7: Download segments for variant 5 using threading
    variant_5_url = urljoin(base_url, "variant_5.m3u8")
    segments_5 = download_segments_from_variant(variant_5_url, output_folder)

    # Step 8: Concatenate segments for variant 5
    init_file_5 = os.path.join(output_folder, "init_5.mp4")
    output_file_5 = os.path.join(output_folder, "output_5.mp4")
    concatenate_segments_with_ffmpeg(init_file_5, segments_5, output_file_5)

    # Step 9: Merge both variant outputs using MP4Box
    merged_output_file = os.path.join(output_folder, "output_merged.mp4")
    command = ["MP4Box", "-add", output_file_0, "-add", output_file_5, "-new", merged_output_file]
    print(f"Running MP4Box to merge: {output_file_0} and {output_file_5}")
    subprocess.run(command, check=True)
    print(f"Merged output saved to {merged_output_file}")

if __name__ == "__main__":
    main()

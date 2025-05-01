import argparse
import subprocess
import sys

def get_video_comment(video_path):
    """Use ffprobe to extract the 'comment' metadata field."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format_tags=comment",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        print(f"ffprobe error: {proc.stderr.strip()}", file=sys.stderr)
        return None
    return proc.stdout.strip()

def main():
    parser = argparse.ArgumentParser(description="Decode watermark (metadata comment) from a video")
    parser.add_argument("-i", "--input", required=True, help="Path to video with embedded metadata")
    args = parser.parse_args()

    comment = get_video_comment(args.input)
    if comment:
        print("Extracted watermark/comment:", comment)
    else:
        print("No watermark/comment found or failed to extract.", file=sys.stderr)

if __name__ == "__main__":
    main()
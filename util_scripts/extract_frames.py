import os
from os.path import basename, dirname, join, splitext
from concurrent.futures import ThreadPoolExecutor
import argparse
import subprocess as sp
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s]:[%(levelname)s]:[%(filename)s:%(lineno)s:%(funcName)s]: %(message)s'
)


class FramesExtractor:
    def __init__(self, ffmpeg="/usr/bin/ffmpeg", workers=4, recursive=False, name=''):
        self.ffmpeg = ffmpeg
        self.workers = int(workers)
        self.recursive = bool(recursive)
        self.name = name

    def get_name(self, out_dir, video_dir, video_path):
        vid_name = splitext(basename(video_path))[0]
        if self.recursive:
            return join(out_dir, dirname(video_path).replace(video_dir.rstrip("/")+"/", ""), vid_name)
        return join(out_dir, vid_name)

    def list_videos(self, path, ext=['.mp4', '.mkv', '.avi', '.mov']):
        matches = []
        ext = tuple(ext + [e.upper() for e in ext])
        for root, dirnames, filenames in os.walk(path):
            for filename in filenames:
                if filename.endswith(ext):
                    matches.append(os.path.join(root, filename))
        return matches

    def vid_to_frame(self, vid_path, out_dir, fps, width, height, ext):
        if not out_dir:
            out_dir = splitext(basename(vid_path))[0]

        if not os.path.isfile(vid_path):
            # confirm if video file exists
            logging.error(f"file doesn't exists: {vid_path}")
            return

        frame_name = self.name or splitext(basename(vid_path))[0]
        os.makedirs(out_dir, exist_ok=True)
        if [str(fps), str(width), str(height)] == ['-1', '-1', '-1']:
            # only extract frames
            cmd = f"{self.ffmpeg} -y -i {vid_path} "
        else:
            cmd = f"ffmpeg -y -i {vid_path} "
            if (str(fps) == '-1') and (str(width) != '-1' or str(width) != '-1'):
                # only change resolution then extract frames
                cmd += f"-vf scale={width}:{height} "
            elif (str(fps) != '-1') and (str(width) == '-1' or str(width) == '-1'):
                # only change fps and then extract frames
                cmd += f"-vf fps={fps} "
            else:
                # change both resolution and fps then extract frames
                cmd += f"-vf scale=\"{width}:{height}\",minterpolate={fps} "

        cmd += f"{out_dir}/{frame_name}_%05d.jpg"
        sp.call(cmd, shell=True)

    def dir_to_frame(self, vid_path, out_dir, fps,  width, height, ext):
        if not os.path.isdir(vid_path):
            # confirm if it's a directory
            logging.error(f"directory doesn't exists: {vid_path}")
            return

        videos = self.list_videos(vid_path)
        if not videos:
            # confirm directory is not empty
            logging.error(f"directory is empty: {vid_path}")
            return

        if self.workers == 1:
            for v in videos:
                self.vid_to_frame(v, self.get_name(
                    out_dir, vid_path, v), fps, width, height, ext)
        else:
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                futures = [executor.submit(self.vid_to_frame, v, self.get_name(
                    out_dir, vid_path, v), fps, width, height, ext) for v in videos]
                [f.result() for f in futures]

    def run(self, vid_path, out_dir='', fps=30, shape='-1x-1', ext=['.mp4', '.mkv', '.avi', '.mov']):
        assert 'x' in shape, "Incorrect format for shape, example usage: --shape 240x240"
        width, height = shape.split('x')

        if os.path.isfile(vid_path):
            # extract a single video file
            self.vid_to_frame(vid_path, out_dir, fps, width, height, ext)
        else:
            self.dir_to_frame(vid_path, out_dir, fps, width, height, ext)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input",
                    help="input video directory", required=True)
    ap.add_argument("-o", "--output",
                    help="directory to store extracted frames ", required=True)
    ap.add_argument("-f", "--fps", help="force fps of video when extracting frames",
                    required=False, default=-1, type=int)
    ap.add_argument("-n", "--name", help="name for extracted frames",
                    required=False, default='')
    ap.add_argument("-s", "--shape", help="shape frames (WxH)",
                    required=False, default='-1x-1')
    ap.add_argument("-b", "--ffmpeg", help="path to ffmpeg binary",
                    required=False, default='/usr/bin/ffmpeg')
    ap.add_argument("-w", "--workers", help="number of workers to execute ffmpeg command",
                    required=False, default=1, type=int)
    ap.add_argument("-r", "--recursive", help="maintain directory recursive structure",
                    required=False, action='store_true')
    args = ap.parse_args()

    fe = FramesExtractor(args.ffmpeg, args.workers, args.recursive, args.name)
    fe.run(args.input, args.output, args.fps, args.shape)
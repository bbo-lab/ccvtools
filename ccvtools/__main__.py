import argparse
import os,sys
import imageio

from . import ccv
from . import rawio

def main():
    parser = argparse.ArgumentParser(description="Detect positions in multitrack file")
    parser.add_argument('CCV_FILE', type=str, help="CCV File to work on")
    parser.add_argument('--action', '-a', required=True, nargs=1, choices=("convert",))
    parser.add_argument('--outfile', '-o', required=False, nargs=1, type=str, help="Appropriate extension will be added if not given")
    
    parser.add_argument('--fps', required=False, default=[25], nargs=1, type=int)
    parser.add_argument('--codec', required=False, default=['libx264'], nargs=1, type=str)
    parser.add_argument('--quality', required=False, default=[10], nargs=1, type=str)
    parser.add_argument('--idxrange', required=False, nargs=2, type=int, help="Index range. Attention! Python indexing!")
    
    args = parser.parse_args()
    
    if not os.access(args.CCV_FILE, os.R_OK):
        print(f"File {args.CCV_FILE} does not exist or isn't readable", file=sys.stderr)
        sys.exit(1)
    
    reader = imageio.get_reader(args.CCV_FILE);
    
    if args.idxrange is None:
        idx_range = range(reader.header.frame_count)
    else:
        idx_range = range(args.idxrange[0],args.idxrange[1])
    
    if args.action[0]=='convert':
        print('Converting ...')
        if args.outfile is None:
            video_file = args.CCV_FILE
        else:
            video_file = args.outfile[0]

        if not video_file[-4:]=='.mp4': video_file = video_file + '.mp4'
        print(video_file)
        ccv.convert(args.CCV_FILE,video_file,idx_range,fps=args.fps[0],codec=args.codec[0],quality=10,min_contrast=0,max_contrast=None)
        

if __name__ == "__main__":
    main()

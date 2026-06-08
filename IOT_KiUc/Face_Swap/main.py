#!/usr/bin/env python
"""
Face Swap CLI: ho tro doi mat tren anh va video.
"""

import argparse
import os
import sys

from face_swapper import FaceSwapper


def build_parser():
    parser = argparse.ArgumentParser(
        description='Face Swap su dung dlib va OpenCV'
    )

    parser.add_argument(
        '--source', '-s',
        required=True,
        help='Duong dan den anh nguon (khuon mat can lay)'
    )

    parser.add_argument(
        '--target', '-t',
        help='Duong dan den anh dich (che do anh)'
    )

    parser.add_argument(
        '--target-video',
        help='Duong dan den video dich (che do video)'
    )

    parser.add_argument(
        '--output', '-o',
        default='output.jpg',
        help='Duong dan luu anh ket qua (mac dinh: output.jpg)'
    )

    parser.add_argument(
        '--output-video',
        default='output.mp4',
        help='Duong dan luu video ket qua (mac dinh: output.mp4)'
    )

    parser.add_argument(
        '--max-frames',
        type=int,
        default=None,
        help='Gioi han so frame xu ly khi test nhanh video'
    )

    return parser


def validate_args(args):
    if not os.path.exists(args.source):
        raise FileNotFoundError(f'File anh nguon khong ton tai: {args.source}')

    image_mode = bool(args.target)
    video_mode = bool(args.target_video)

    if image_mode == video_mode:
        raise ValueError('Can chon dung 1 trong 2: --target hoac --target-video')

    if image_mode and not os.path.exists(args.target):
        raise FileNotFoundError(f'File anh dich khong ton tai: {args.target}')

    if video_mode and not os.path.exists(args.target_video):
        raise FileNotFoundError(f'File video dich khong ton tai: {args.target_video}')


def run_image_mode(swapper, args):
    print('Bat dau xu ly anh...')
    success = swapper.swap_faces_from_files(args.source, args.target, args.output)

    if not success:
        raise RuntimeError('Khong the thuc hien doi mat tren anh')

    print(f'Hoan tat. Anh ket qua: {args.output}')


def run_video_mode(swapper, args):
    print('Bat dau xu ly video...')
    stats = swapper.swap_faces_in_video_from_files(
        source_path=args.source,
        target_video_path=args.target_video,
        output_video_path=args.output_video,
        max_frames=args.max_frames,
    )

    print(f"Hoan tat. Video ket qua: {stats['output_video']}")
    print(
        'Thong ke: '
        f"processed={stats['processed_frames']}, "
        f"swapped={stats['swapped_frames']}, "
        f"fps={stats['fps']:.2f}"
    )


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        validate_args(args)
        swapper = FaceSwapper()

        if args.target:
            run_image_mode(swapper, args)
        else:
            run_video_mode(swapper, args)

    except Exception as e:
        print(f'Loi: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()

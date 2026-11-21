"""重新生成技能中的十四张通用 SVG；默认输出到本技能 assets/examples。"""
from pathlib import Path
import argparse
from examples_power import build as power
from examples_analog import build as analog
from examples_digital import build as digital


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'assets/examples')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    paths=power(args.output)+analog(args.output)+digital(args.output)
    assert len(paths)==14 and len(set(paths))==14
    print(f'已生成 {len(paths)} 张独立 SVG：{args.output}')


if __name__=='__main__':main()

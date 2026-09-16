#!/usr/bin/env python3
"""Generate a robot-independent report from batch directories or single trials."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from robot_eval.reporting import wilson, summarize, write_report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("campaigns",nargs="+",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    report=write_report(args.campaigns,args.output)
    print("Reported",report["runs"],"attempts for",", ".join(report["robots"]),
          "at",args.output/"report.md")

if __name__=="__main__":main()

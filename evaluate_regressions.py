"""Offline detector regression suite. Does not call Groq or grade live quality."""
import argparse
import json
from pathlib import Path
from narrator import Scene, narration_issues
from evaluation import CHECK_VERSION


def run():
    cases=json.loads((Path(__file__).parent/'data/regression_cases.json').read_text())
    results=[]
    for case in cases:
        issues=narration_issues(Scene(title='Scene',text=case['text']),case['outcome'],case['story_id'])
        results.append(dict(case, actual_issues=issues, detector_matches_expected=set(issues)==set(case['expected_issues']), human_review_needed=case['human_label']=='fail' and not issues))
    return {'check_version':CHECK_VERSION,'cases':len(results),'detector_regressions':sum(not r['detector_matches_expected'] for r in results),'known_semantic_misses':sum(r['human_review_needed'] for r in results),'results':results}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='regression-report.json')
    args=parser.parse_args()
    report=run()
    Path(args.output).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f"{report['cases']} fixtures; {report['detector_regressions']} detector regressions; {report['known_semantic_misses']} known semantic miss(es).")
    raise SystemExit(bool(report['detector_regressions']))

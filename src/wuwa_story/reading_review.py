"""Export reviewed reading samples with evidence tied to exact input files."""
import argparse
import hashlib
import json
from pathlib import Path

from .export_task import write_result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_review(batch_directory, review_path, output_directory):
    review = json.loads(review_path.read_text(encoding='utf-8'))
    report = json.loads((batch_directory / '覆盖报告.json').read_text(encoding='utf-8'))
    tasks = {task['quest_id']: task for task in report['tasks']}
    prepared = []
    for assessment in review['tasks']:
        task = tasks[assessment['quest_id']]
        source_json = batch_directory / task['files'][0]
        source_txt = batch_directory / task['files'][1]
        if (digest(source_json) != assessment['source_json_sha256']
                or digest(source_txt) != assessment['source_txt_sha256']):
            raise ValueError(f"Review requires revalidation for task {task['quest_id']}")
        if assessment['verdict'] not in {'readable', 'readable_with_gaps', 'materials_only'}:
            raise ValueError('Unknown reading review verdict')
        if not assessment.get('checks') or not assessment.get('summary'):
            raise ValueError('Reading review requires checks and summary')
        result = json.loads(source_json.read_text(encoding='utf-8'))
        result['reading_review'] = assessment
        result['batch_coverage']['reading_acceptance'].update(
            status=assessment['verdict'], accepted=assessment['verdict'] == 'readable',
            review_id=review['review_id'], chapter_readthrough_verified=False,
            note=assessment['summary'])
        prepared.append(result)
    output_directory.mkdir(parents=True, exist_ok=True)
    for result in prepared:
        write_result(result, output_directory, quiet=True)
    (output_directory / '阅读验收.json').write_text(
        json.dumps(review, ensure_ascii=False, indent=2), encoding='utf-8')
    return prepared


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--batch', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    export_review(args.batch, args.review, args.output)

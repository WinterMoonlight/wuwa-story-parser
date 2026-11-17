import argparse
import runpy
import json
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description='鸣潮剧情数据库只读解析工具')
    parser.add_argument('command', choices=['inspect', 'inventory', 'index', 'export-task', 'export-mainline', 'export-reading-batch', 'export-recap', 'export-review', 'scan-mainline', 'refresh-reading'])
    parser.add_argument('--quest-id', type=int, default=211750002)
    parser.add_argument('--allow-incomplete', action='store_true', help='仅 export-task：输出明确标注缺口的待核验草稿')
    parser.add_argument('--choices', type=Path, help='export-recap 的选择索引 JSON')
    parser.add_argument('--output', type=Path, help='export-recap / export-review 输出目录')
    parser.add_argument('--batch', type=Path, help='export-review 对应的覆盖阅读版目录')
    parser.add_argument('--review', type=Path, help='export-review 的带源哈希审查记录')
    args = parser.parse_args(argv)
    if args.allow_incomplete and args.command != 'export-task':
        parser.error('--allow-incomplete is only valid for export-task')
    if args.choices and args.command != 'export-recap':
        parser.error('--choices is only valid for export-recap')
    if args.output and args.command not in {'export-recap', 'export-review'}:
        parser.error('--output is only valid for export-recap or export-review')
    if (args.batch or args.review) and args.command != 'export-review':
        parser.error('--batch and --review are only valid for export-review')
    if args.command == 'export-review':
        if not all((args.batch, args.review, args.output)):
            parser.error('export-review requires --batch, --review and --output')
        from .reading_review import export_review
        export_review(args.batch, args.review, args.output)
    elif args.command == 'export-recap':
        from .recap_backbone import export_task_backbone
        from .export_task import write_result
        from .paths import OUTPUT_DIR
        choices = json.loads(args.choices.read_text(encoding='utf-8-sig')) if args.choices else None
        write_result(export_task_backbone(args.quest_id, choices), args.output or OUTPUT_DIR/'回顾主干验证')
    elif args.command == 'export-reading-batch':
        from .reading_batch import export_reading_batch
        export_reading_batch()
    elif args.command == 'refresh-reading':
        from .refresh_reading import refresh_reading
        refresh_reading()
    elif args.command == 'export-task':
        from .export_task import Exporter, write_result
        write_result(Exporter(allow_incomplete=args.allow_incomplete).export(args.quest_id))
    elif args.command == 'export-mainline':
        from .batch import export_mainline
        export_mainline()
    elif args.command == 'scan-mainline':
        from .scan import scan_mainline
        scan_mainline()
    else:
        runpy.run_module('wuwa_story.' + args.command, run_name='__main__')


if __name__ == '__main__':
    main()

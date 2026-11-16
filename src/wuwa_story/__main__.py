import argparse
import runpy


def main():
    parser = argparse.ArgumentParser(description='鸣潮剧情数据库只读解析工具')
    parser.add_argument('command', choices=['inspect', 'inventory', 'index', 'export-task', 'export-mainline', 'export-reading-batch', 'scan-mainline', 'refresh-reading'])
    parser.add_argument('--quest-id', type=int, default=211750002)
    parser.add_argument('--allow-incomplete', action='store_true', help='仅 export-task：输出明确标注缺口的待核验草稿')
    args = parser.parse_args()
    if args.allow_incomplete and args.command != 'export-task':
        parser.error('--allow-incomplete is only valid for export-task')
    if args.command == 'export-reading-batch':
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

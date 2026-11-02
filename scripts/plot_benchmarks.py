"""Create standalone report figures/CSV from a successful saved benchmark run."""

import argparse
import csv
import json
from pathlib import Path
import random


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path, help='Path to the saved report.json')
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding='utf-8'))
    if not report.get('successful'):
        parser.error('Only successful, cleaned-up benchmark runs can be plotted')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    directory = args.report.resolve().parent
    targets = [directory / name for name in ('postgres_timings.png', 'postgres_timings.svg',
        'mongodb_timings.png', 'mongodb_timings.svg', 'summary.csv', 'figure_metadata.json')]
    if any(path.exists() for path in targets):
        parser.error('Figures/summary already exist; retain the historical evidence')
    labels = {'baseline': 'Primary keys\nonly', 'indexed': 'Vehicle lookup\nindexes',
              'current': 'Existing filter\nindex', 'candidate': 'Filter + stable\nsort index'}
    titles = {'pg_recall_lookup': 'Recall lookup',
              'pg_component_source_rows': 'STEERING source rows',
              'mongo_complaints_full_window': '2020-2026 window',
              'mongo_complaints_2026': '2026 window'}
    colors = ['#607086', '#137f76', '#465ac7']
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'svg.fonttype': 'none'})
    for database, filename in [('PostgreSQL', 'postgres_timings'), ('MongoDB', 'mongodb_timings')]:
        jobs = [job for job in report['workloads'] if job['database'] == database]
        figure, axes = plt.subplots(1, len(jobs), figsize=(11, 4.8), squeeze=False)
        for ax, job in zip(axes[0], jobs):
            rng = random.Random(23)
            for position, (phase, values) in enumerate(job['phases'].items()):
                samples = [sample for result in values['rounds'] for sample in result['samples_ms']]
                summary = values['summary']
                ax.scatter([position + rng.uniform(-0.09, 0.09) for _ in samples], samples,
                           alpha=0.35, s=15, color=colors[position], zorder=2)
                median = summary['median_ms']
                ax.errorbar(position, median, yerr=[[median - summary['p25_ms']], [summary['p75_ms'] - median]],
                            fmt='D', capsize=8, color=colors[position], markersize=7, linewidth=2, zorder=3)
                ax.annotate(f'{median:.3f} ms', (position, summary['max_ms']), xytext=(0, 12),
                            textcoords='offset points', ha='center', fontsize=10, fontweight='bold')
            ax.set_yscale('log')
            ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f'{value:g}'))
            ax.set_ylabel('Fetch + decode time (ms, logarithmic scale)')
            ax.set_xticks(range(len(job['phases'])), [labels[phase] for phase in job['phases']])
            result_count = next(iter(job['phases'].values()))['rounds'][0]['result_count']
            scope = f"{job['matched_documents']} matches" if 'matched_documents' in job else f'{result_count} results'
            ax.set_title(f"{titles[job['id']]} ({scope})", pad=14)
            ax.set_xlim(-0.5, len(job['phases']) - 0.5)
            ax.margins(y=0.38)
            ax.grid(axis='y', which='major', alpha=0.2)
            ax.spines[['top', 'right']].set_visible(False)
        figure.suptitle(f'{database}: the same query before/after indexing', fontsize=14, fontweight='bold')
        measured = report['method']['measured_samples_per_round'] * report['method']['rounds']
        warmups = report['method']['excluded_warmups_per_round']
        figure.text(0.5, 0.025, f'Dots: {measured} measured runs per phase. Diamonds: median; bars: interquartile range.\n'
                    f'{warmups} excluded warmups per round; two rounds in reverse phase order. Local warm cache; no concurrent load.',
                    ha='center', fontsize=9, color='#404959')
        figure.tight_layout(rect=(0, 0.12, 1, 0.94))
        for extension in ('png', 'svg'):
            figure.savefig(directory / f'{filename}.{extension}', dpi=240, bbox_inches='tight',
                           metadata={'Creator': 'scripts/plot_benchmarks.py'})
        plt.close(figure)
    with (directory / 'summary.csv').open('w', newline='', encoding='utf-8') as stream:
        fields = ['database', 'workload', 'phase', 'n', 'median_ms', 'p25_ms', 'p75_ms', 'min_ms', 'max_ms',
                  'returned_rows', 'pg_shared_hit_blocks_round_1', 'mongo_docs_examined_round_1', 'mongo_keys_examined_round_1']
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        for job in report['workloads']:
            for phase, values in job['phases'].items():
                metrics = values['rounds'][0]['metrics']
                writer.writerow({'database': job['database'], 'workload': job['id'], 'phase': phase,
                    **values['summary'], 'returned_rows': values['rounds'][0]['result_count'],
                    'pg_shared_hit_blocks_round_1': metrics.get('shared_hit_blocks', ''),
                    'mongo_docs_examined_round_1': metrics.get('totalDocsExamined', ''),
                    'mongo_keys_examined_round_1': metrics.get('totalKeysExamined', '')})
    (directory / 'figure_metadata.json').write_text(json.dumps({'source': 'report.json',
        'matplotlib_version': matplotlib.__version__, 'script': 'scripts/plot_benchmarks.py'}, indent=2) + '\n', encoding='utf-8')
    print('Created two PNG/SVG figures, summary.csv and figure metadata in', directory.name)


if __name__ == '__main__':
    main()

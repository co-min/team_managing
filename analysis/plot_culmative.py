import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'all_trials_with_chose_optimal.csv')
OUT_PATH  = os.path.join(os.path.dirname(__file__), 'cumulative_score_by_phase_block.png')

df = pd.read_csv(DATA_PATH)

# block number as int
df['block_num'] = df['block'].str.extract(r'(\d+)').astype(int)

# group definition: even blocks → phase1 group, odd blocks → phase2 group
# (data already encodes this via phase col, but we keep both axes explicit)
GROUPS = {
    'Phase 1\n(blocks 0,2,4)': {'phase': 'phase_1', 'blocks': [0, 2, 4]},
    'Phase 2\n(blocks 1,3,5)': {'phase': 'phase_2', 'blocks': [1, 3, 5]},
}

COLORS = {
    'Phase 1\n(blocks 0,2,4)': '#2196F3',
    'Phase 2\n(blocks 1,3,5)': '#E91E63',
}

BLOCK_ORDER = {
    'Phase 1\n(blocks 0,2,4)': [0, 2, 4],
    'Phase 2\n(blocks 1,3,5)': [1, 3, 5],
}

subjects = sorted(df['sub_id'].unique())

# ── Font sizes (before → after) ──────────────────────────────────────────────
# xlabel  : 12 → 16
# ylabel  : 12 → 16
# title   : 13 → 18
# legend  : 11 → 14
# tick    : (default ~10) → 13
# annotation : (new) → 13
# ─────────────────────────────────────────────────────────────────────────────
FS_TITLE  = 21
FS_AXIS   = 16
FS_TICK   = 13
FS_LEGEND = 14
FS_ANNOT  = 13

# maximum possible score per trial → used for % axis
max_score_per_trial = df['feedback_score'].max()

fig, ax = plt.subplots(figsize=(11, 5))

final_points = {}   # store (x_end, mean_end) for % annotation per group

for label, cfg in GROUPS.items():
    sub_curves = []
    block_order = BLOCK_ORDER[label]

    for sub in subjects:
        # collect trials in block order
        frames = []
        for blk in block_order:
            mask = (df['sub_id'] == sub) & (df['phase'] == cfg['phase']) & (df['block_num'] == blk)
            chunk = df.loc[mask].copy()
            chunk = chunk.sort_values('block_trial_id')
            frames.append(chunk['feedback_score'].values)

        if not any(len(f) > 0 for f in frames):
            continue

        scores = np.concatenate(frames)
        cumulative = np.cumsum(scores)
        sub_curves.append(cumulative)

    if not sub_curves:
        continue

    # align to same length (truncate to minimum)
    min_len = min(len(c) for c in sub_curves)
    mat = np.array([c[:min_len] for c in sub_curves])   # (n_subjects, n_trials)

    mean_curve = mat.mean(axis=0)
    sem_curve  = mat.std(axis=0) / np.sqrt(len(mat))
    x = np.arange(1, min_len + 1)

    color = COLORS[label]

    # individual subject curves
    for i, curve in enumerate(sub_curves):
        xi = np.arange(1, len(curve) + 1)
        ax.plot(xi, curve, color=color, linewidth=0.7, alpha=0.25,
                label='_nolegend_')

    ax.fill_between(x, mean_curve - sem_curve, mean_curve + sem_curve,
                    alpha=0.25, color=color)
    ax.plot(x, mean_curve, color=color, linewidth=2.5, label=label.replace('\n', ' '))

    # draw vertical lines at block boundaries
    block_sizes = [len(np.concatenate([
        df.loc[(df['sub_id'] == sub) & (df['phase'] == cfg['phase']) & (df['block_num'] == blk),
               'feedback_score'].values
        for sub in subjects if len(df.loc[(df['sub_id'] == sub) & (df['phase'] == cfg['phase']) &
                                           (df['block_num'] == blk)]) > 0
    ])) // len([s for s in subjects
                if len(df.loc[(df['sub_id'] == s) & (df['phase'] == cfg['phase']) &
                               (df['block_num'] == blk)]) > 0])
    for blk in block_order]

    boundary = 0
    for i, bsize in enumerate(block_sizes[:-1]):
        boundary += bsize
        ax.axvline(x=boundary + 0.5, color=color, linestyle='--', linewidth=0.9, alpha=0.5)

    # store endpoint for % annotation
    final_points[label] = (x[-1], mean_curve[-1], min_len, color)

# ── % annotations at end of each mean curve ──────────────────────────────────
for label, (x_end, mean_end, n_trials, color) in final_points.items():
    max_possible = max_score_per_trial * n_trials
    pct = mean_end / max_possible * 100 if max_possible > 0 else 0
    ax.annotate(f'{pct:.1f}%\nof max',
                xy=(x_end, mean_end),
                xytext=(0, 14), textcoords='offset points',
                color=color, fontsize=FS_ANNOT, fontweight='bold',
                ha='center', va='bottom')

# ── Right y-axis: % of overall max possible cumulative ───────────────────────
# Use the longest phase's trial count as the common denominator
max_n_trials = max(fp[2] for fp in final_points.values()) if final_points else 1
total_max = max_score_per_trial * max_n_trials

ax2 = ax.twinx()
y_left_min, y_left_max = ax.get_ylim()
ax2.set_ylim(y_left_min / total_max * 100, y_left_max / total_max * 100)
ax2.set_ylabel('% of Maximum Possible Score', fontsize=FS_AXIS)
ax2.tick_params(labelsize=FS_TICK)
ax2.spines['top'].set_visible(False)

ax.set_xlabel('Trial (within phase, concatenated across blocks)', fontsize=FS_AXIS)
ax.set_ylabel('Cumulative Feedback Score', fontsize=FS_AXIS)
ax.set_title('Total Cumulative Score by Phase & Block Group\n(mean ± SEM across subjects)', fontsize=FS_TITLE, fontweight="bold")
ax.legend(fontsize=FS_LEGEND, framealpha=0.85)
ax.tick_params(labelsize=FS_TICK)
ax.spines[['top', 'right']].set_visible(False)

print("Font size changes applied:")
print(f"  Title  : 13 → {FS_TITLE}")
print(f"  x/y label : 12 → {FS_AXIS}")
print(f"  Tick labels : ~10 (default) → {FS_TICK}")
print(f"  Legend : 11 → {FS_LEGEND}")
print(f"  % annotation : (new) {FS_ANNOT}")

plt.tight_layout()
plt.savefig(OUT_PATH, dpi=150)
print(f'Saved → {OUT_PATH}')
plt.show()

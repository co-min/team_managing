"""
plot_learning_curves.py
Build per-domain learning curves by averaging feedback scores across subjects.

For each domain, that domain's trials are concatenated across its three
repeated blocks (in block order) to form a learning trajectory, then
averaged across the four subjects.

  Individual phase (blocks 0,2,4):  cooking, repairing, tennis  -> 3 plots
  Synergy    phase (blocks 1,3,5):  cooking, repairing          -> 2 plots
  => 5 plots total.

Normalization: within each subject, each domain's scores are divided by
that domain's own max score (domains have different max scores).
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

SUBJECTS = ['sub-005', 'sub-006', 'sub-009', 'sub-010']

PLOTS = [
    ('phase_1', 'cooking',   ['block_0', 'block_2', 'block_4']),
    ('phase_1', 'repairing', ['block_0', 'block_2', 'block_4']),
    ('phase_1', 'tennis',    ['block_0', 'block_2', 'block_4']),
    ('phase_2', 'cooking',   ['block_1', 'block_3', 'block_5']),
    ('phase_2', 'repairing', ['block_1', 'block_3', 'block_5']),
]

SMOOTH_W = 5

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUT_DIR  = os.path.join(DATA_DIR, 'group')
os.makedirs(OUT_DIR, exist_ok=True)

# Load all subject tables once
tables = {}
for sub in SUBJECTS:
    path = os.path.join(DATA_DIR, sub, 'trials.csv')
    tables[sub] = pd.read_csv(path)

fig, axes = plt.subplots(2, 3, figsize=(15, 7), facecolor='white')
axes = axes.flatten()

SHADES = [
    (0.93, 0.93, 0.97),
    (0.97, 0.93, 0.93),
]

for p, (phase, domain, blks) in enumerate(PLOTS):
    ax = axes[p]

    # Build subject x trial matrix (normalized)
    subj_mat = []
    for sub in SUBJECTS:
        df = tables[sub]
        seq = []
        for blk in blks:
            mask = (df['block'] == blk) & (df['domain'] == domain)
            seq.append(df.loc[mask, 'feedback_score'].values)
        seq = np.concatenate(seq)
        m = np.nanmax(seq) if len(seq) > 0 else 0
        if m == 0 or np.isnan(m):
            m = 1.0
        subj_mat.append(seq / m)

    subj_mat = np.array(subj_mat, dtype=float)   # shape: (n_subjects, n_trials)
    n_trials = subj_mat.shape[1]
    x = np.arange(1, n_trials + 1)

    mean_curve = np.nanmean(subj_mat, axis=0)
    sem_curve  = np.nanstd(subj_mat, axis=0, ddof=1) / np.sqrt(subj_mat.shape[0])
    smooth_curve = pd.Series(mean_curve).rolling(SMOOTH_W, center=True, min_periods=1).mean().values

    per_blk = n_trials / len(blks)
    yl = (0, 1.08)

    # Shade block segments
    for b, blk in enumerate(blks):
        x0 = b * per_blk + 0.5
        x1 = (b + 1) * per_blk + 0.5
        ax.axvspan(x0, x1, ymin=0, ymax=1,
                   color=SHADES[b % 2], zorder=0, linewidth=0)
        ax.text((x0 + x1) / 2, yl[1], blk.replace('block_', 'B'),
                ha='center', va='top', fontsize=8, color=(0.4, 0.4, 0.4))

    # SEM band
    ax.fill_between(x, mean_curve - sem_curve, mean_curve + sem_curve,
                    color=(0.2, 0.45, 0.8), alpha=0.15, linewidth=0)

    # Individual subjects (faint)
    for row in subj_mat:
        ax.plot(x, row, '-', color=(0.7, 0.7, 0.7), linewidth=0.6)

    # Mean dots and smoothed curve
    ax.plot(x, mean_curve, 'o', color=(0.2, 0.45, 0.8),
            markerfacecolor=(0.2, 0.45, 0.8), markersize=4,
            label='Subject mean')
    ax.plot(x, smooth_curve, '-', color=(0.85, 0.25, 0.15), linewidth=2,
            label=f'Learning curve (movmean {SMOOTH_W})')

    # Block boundary lines
    for b in range(1, len(blks)):
        ax.axvline(b * per_blk + 0.5, color='k', linestyle=':', linewidth=0.8)

    ax.set_ylim(yl)
    ax.set_xlim(0.5, n_trials + 0.5)
    ax.set_xlabel('Trial (blocks concatenated)')
    ax.set_ylabel('Normalized score')
    ax.grid(True)
    ax.set_facecolor('white')

    if phase == 'phase_2':
        title = f'SYNERGY — {domain}'
    else:
        title = f'INDIVIDUAL — {domain}'
    ax.set_title(title)

    if p == 0:
        ax.legend(loc='lower right', fontsize=7)

# Hide the unused 6th tile
axes[5].set_visible(False)

fig.suptitle('Per-domain learning curves (mean ± SEM across subjects)',
             fontweight='bold')
fig.tight_layout()

out_path = os.path.join(OUT_DIR, 'learning_curves.png')
fig.savefig(out_path, dpi=150, bbox_inches='tight')
print(f'Saved {out_path} ({len(PLOTS)} panels)')
plt.show()

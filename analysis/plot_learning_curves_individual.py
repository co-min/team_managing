"""
plot_learning_curves_individual.py
Same 5 per-domain learning curves as the MATLAB version, but WITHOUT averaging
across subjects.  One figure per subject, each with 5 panels:

  Individual phase (blocks 0,2,4):  cooking, repairing, tennis  -> 3 plots
  Synergy    phase (blocks 1,3,5):  cooking, repairing          -> 2 plots

For each domain, trials are concatenated across its three repeated blocks (in
block order) to form the learning trajectory, then normalized by that domain's
own max score.

Usage:
    python analysis/plot_learning_curves_individual.py
"""

import os
import math
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

SHADES = [
    (0.93, 0.93, 0.97),
    (0.97, 0.93, 0.93),
]

BLUE = (0.2, 0.45, 0.8)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_root = os.path.join(script_dir, '..', 'data')

    for subj in SUBJECTS:
        csv_path = os.path.join(data_root, subj, 'trials.csv')
        df = pd.read_csv(csv_path)

        fig, axes = plt.subplots(2, 3, figsize=(15, 7))
        fig.patch.set_facecolor('white')
        fig.suptitle(f'{subj} — per-domain learning curves', fontweight='bold')

        ax_flat = axes.flatten()
        # last panel (position 5) is unused — hide it
        ax_flat[5].set_visible(False)

        for p, (phase, domain, blks) in enumerate(PLOTS):
            ax = ax_flat[p]

            # Concatenate this domain's trials in block order
            seq = []
            for blk in blks:
                mask = (df['block'] == blk) & (df['domain'] == domain)
                seq.append(df.loc[mask, 'feedback_score'].values)
            seq = np.concatenate(seq).astype(float)

            m = np.nanmax(seq) if len(seq) > 0 else 0
            if m == 0 or math.isnan(m):
                m = 1.0
            seq = seq / m

            n_trials = len(seq)
            x = np.arange(1, n_trials + 1)
            per_blk = n_trials / len(blks)

            yl = (0, 1.08)
            ax.set_ylim(yl)
            ax.set_xlim(0.5, n_trials + 0.5)

            # Shade block segments
            for b_i, blk in enumerate(blks):
                x0 = b_i * per_blk + 0.5
                x1 = (b_i + 1) * per_blk + 0.5
                color = SHADES[b_i % 2]
                ax.axvspan(x0, x1, color=color, linewidth=0)
                ax.text(
                    (x0 + x1) / 2, yl[1],
                    blk.replace('block_', 'B'),
                    ha='center', va='top',
                    fontsize=8, color=(0.4, 0.4, 0.4),
                )

            # Connect dots within each block (line cuts at boundaries)
            label_set = False
            for b_i in range(len(blks)):
                start = round(b_i * per_blk)
                end = min(round((b_i + 1) * per_blk), n_trials)
                idx = np.arange(start, end)
                label = 'Score' if not label_set else '_nolegend_'
                ax.plot(
                    x[idx], seq[idx],
                    '-o', color=BLUE,
                    markerfacecolor=BLUE, markersize=4,
                    linewidth=1.2, label=label,
                )
                label_set = True

            # Block boundary lines
            for b_i in range(1, len(blks)):
                ax.axvline(b_i * per_blk + 0.5, color='k', linestyle=':', linewidth=0.8)

            ax.set_xlabel('Trial (blocks concatenated)')
            ax.set_ylabel('Normalized score')
            title = f'individual — {domain}' if phase == 'phase_1' else f'SYNERGY — {domain}'
            ax.set_title(title)
            ax.grid(True)
            ax.set_facecolor('white')
            for spine in ax.spines.values():
                spine.set_visible(True)

            if p == 0:
                ax.legend(loc='lower right', fontsize=7)

        plt.tight_layout()

        out_png = os.path.join(data_root, subj, f'{subj}_learning_curves.png')
        fig.savefig(out_png, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f'Saved {out_png}')


if __name__ == '__main__':
    main()

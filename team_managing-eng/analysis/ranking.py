import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

BASE = r'c:\Users\niobi\OneDrive\Desktop\Project_ylab_2026\team_managing-v3\data'
OUT = r'c:\Users\niobi\OneDrive\Desktop\Project_ylab_2026\team_managing-v3\analysis\analysis_outfile'
os.makedirs(OUT, exist_ok=True)

records = []

for s in sorted(os.listdir(BASE)):
    sub_path = os.path.join(BASE, s)

    # sub-009 has a nested directory: data/sub-009/sub-009/
    inner = os.path.join(sub_path, s)
    if os.path.isdir(inner):
        sub_path = inner

    tp = os.path.join(sub_path, 'trials.csv')
    if not os.path.exists(tp):
        continue
    df = pd.read_csv(tp)

    total_time = df['elapsed_time'].max()

    op = os.path.join(sub_path, 'trials_with_chose_optimal.csv')
    if os.path.exists(op):
        dfo = pd.read_csv(op)
        optimal_rate = dfo['chose_optimal'].mean()
        rate_source = 'chose_optimal'
    else:
        # Fallback: proportion of trials where feedback_score == max
        max_score = df['feedback_score'].max()
        optimal_rate = (df['feedback_score'] >= max_score * 0.99).mean()
        rate_source = 'feedback_score'

    records.append({
        'sub': s,
        'total_time': total_time,
        'optimal_rate': optimal_rate,
        'rate_source': rate_source,
        'n_trials': len(df),
    })

df_rank = pd.DataFrame(records)
df_rank['time_rank'] = df_rank['total_time'].rank(ascending=True, method='min').astype(int)
df_rank['rate_rank'] = df_rank['optimal_rate'].rank(ascending=False, method='min').astype(int)

n = len(df_rank)
cmap = plt.cm.RdYlGn

df_time = df_rank.sort_values('time_rank').reset_index(drop=True)
df_rate = df_rank.sort_values('rate_rank').reset_index(drop=True)


def rank_color(rank, n_total):
    return cmap(1.0 - (rank - 1) / (n_total - 1))


fig, axes = plt.subplots(1, 2, figsize=(20, 8))
fig.subplots_adjust(wspace=0.55, bottom=0.12)

# ── Left: Total Time Ranking ──────────────────────────────────────────────────
ax1 = axes[0]
y = list(range(n))
colors_time = [rank_color(r, n) for r in df_time['time_rank']]

ax1.barh(y, df_time['total_time'], color=colors_time,
         edgecolor='white', height=0.6, linewidth=1.5)

ax1.set_yticks(y)
ax1.set_yticklabels(
    [f"#{int(r)}  {s}{'*' if src == 'feedback_score' else ''}"
     for r, s, src in zip(df_time['time_rank'], df_time['sub'], df_time['rate_source'])],
    fontsize=15
)
ax1.set_xlabel('Total Elapsed Time (s)', fontsize=18, labelpad=12)
ax1.set_title('Total Time Ranking\n(faster = better)',
              fontweight='bold', fontsize=21, pad=16)
ax1.invert_yaxis()

max_time = df_time['total_time'].max()
ax1.set_xlim(0, max_time * 1.25)
for i, row in df_time.iterrows():
    ax1.text(row['total_time'] + max_time * 0.02, i,
             f"{row['total_time']:.0f}s",
             va='center', fontsize=13, color='#333333')

ax1.tick_params(axis='x', labelsize=14)
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)

# ── Right: Optimal Rate Ranking ───────────────────────────────────────────────
ax2 = axes[1]
colors_rate = [rank_color(r, n) for r in df_rate['rate_rank']]

ax2.barh(y, df_rate['optimal_rate'] * 100, color=colors_rate,
         edgecolor='white', height=0.6, linewidth=1.5)

ax2.set_yticks(y)
ax2.set_yticklabels(
    [f"#{int(r)}  {s}{'*' if src == 'feedback_score' else ''}"
     for r, s, src in zip(df_rate['rate_rank'], df_rate['sub'], df_rate['rate_source'])],
    fontsize=15
)
ax2.set_xlabel('Optimal Choice Rate (%)', fontsize=18, labelpad=12)
ax2.set_title('Optimal Rate Ranking\n(higher = better)',
              fontweight='bold', fontsize=21, pad=16)
ax2.invert_yaxis()

ax2.set_xlim(0, 100)
ax2.xaxis.set_major_formatter(mticker.FormatStrFormatter('%g'))
for i, row in df_rate.iterrows():
    val = row['optimal_rate'] * 100
    x_text = min(val + 2, 97)
    ax2.text(x_text, i, f"{val:.1f}%",
             va='center', fontsize=13, color='#333333')

ax2.tick_params(axis='x', labelsize=14)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)

# ── Footnote ──────────────────────────────────────────────────────────────────
fig.text(
    0.5, 0.02,
    '* Optimal rate: proportion of max feedback_score trials (chose_optimal data unavailable)',
    ha='center', fontsize=11, color='gray', style='italic'
)

out_path = os.path.join(OUT, 'ranking_sub.png')
plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print(f"Saved → {out_path}")

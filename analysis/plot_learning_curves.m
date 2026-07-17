% plot_learning_curves.m
% Build per-domain learning curves by averaging feedback scores across subjects.
%
% For each domain, that domain's trials are concatenated across its three
% repeated blocks (in block order) to form a learning trajectory, then
% averaged across the three subjects.
%
%   Individual phase (blocks 0,2,4):  cooking, repairing, tennis  -> 3 plots
%   Synergy    phase (blocks 1,3,5):  cooking, repairing          -> 2 plots
%   => 5 plots total.
%
% Normalization: within each subject, each domain's scores are divided by
% that domain's own max score (domains have different max scores). This makes
% domains comparable while preserving the across-block learning trend.

clear; close all; clc;

subjects = {'sub-005', 'sub-006' , 'sub-009','sub-010'};

% Each plot = one (phase, domain, blocks) combination
plots = {
    'phase_1', 'cooking',   {'block_0','block_2','block_4'};
    'phase_1', 'repairing', {'block_0','block_2','block_4'};
    'phase_1', 'tennis',    {'block_0','block_2','block_4'};
    'phase_2', 'cooking',   {'block_1','block_3','block_5'};
    'phase_2', 'repairing', {'block_1','block_3','block_5'};
};
nPlots  = size(plots,1);
smoothW = 5;   % moving-average window for the learning-curve overlay

% Preload each subject's table once
T = cell(1,numel(subjects));
for s = 1:numel(subjects)
    T{s} = readtable(fullfile('..', 'data', subjects{s}, 'trials.csv'));
end

figure('Color','w','Position',[80 80 1500 700]);
tl = tiledlayout(2, 3, 'TileSpacing','compact', 'Padding','compact');

for p = 1:nPlots
    phase  = plots{p,1};
    domain = plots{p,2};
    blks   = plots{p,3};

    % Gather each subject's concatenated, normalized score trajectory
    subjMat = [];   % rows = subjects, cols = trial position
    for s = 1:numel(subjects)
        Ts  = T{s};
        seq = [];
        for b = 1:numel(blks)
            rows = strcmp(Ts.block, blks{b}) & strcmp(Ts.domain, domain);
            seq  = [seq; Ts.feedback_score(rows)];   % keep trial order
        end
        m = max(seq);
        if isempty(m) || m == 0 || isnan(m), m = 1; end
        seq = seq / m;                                % per-domain normalization
        subjMat = [subjMat; seq(:)'];                 %#ok<AGROW>
    end

    nTrials  = size(subjMat,2);
    meanCurve = mean(subjMat, 1, 'omitnan');
    semCurve  = std(subjMat, 0, 1, 'omitnan') ./ sqrt(size(subjMat,1));
    x = 1:nTrials;

    % Smoothed learning curve
    smoothCurve = movmean(meanCurve, smoothW);

    % Trials per block (for boundary lines / shading)
    perBlk = nTrials / numel(blks);

    nexttile; hold on;

    % Shade block segments
    yl = [0 1.08];
    shades = [0.93 0.93 0.97; 0.97 0.93 0.93];
    for b = 1:numel(blks)
        x0 = (b-1)*perBlk + 0.5;
        x1 = b*perBlk + 0.5;
        patch([x0 x1 x1 x0], [yl(1) yl(1) yl(2) yl(2)], ...
              shades(mod(b,2)+1,:), 'EdgeColor','none','HandleVisibility','off');
        text(mean([x0 x1]), yl(2), strrep(blks{b},'block_','B'), ...
             'HorizontalAlignment','center','VerticalAlignment','top', ...
             'FontSize',8,'Color',[0.4 0.4 0.4]);
    end

    % SEM band
    fill([x fliplr(x)], [meanCurve+semCurve fliplr(meanCurve-semCurve)], ...
         [0.2 0.45 0.8], 'FaceAlpha',0.15, 'EdgeColor','none', ...
         'HandleVisibility','off');

    % Individual subjects (faint)
    for s = 1:numel(subjects)
        plot(x, subjMat(s,:), '-', 'Color',[0.7 0.7 0.7], 'LineWidth',0.6, ...
             'HandleVisibility','off');
    end

    % Mean and smoothed learning curve
    plot(x, meanCurve, 'o', 'Color',[0.2 0.45 0.8], ...
         'MarkerFaceColor',[0.2 0.45 0.8], 'MarkerSize',4, ...
         'DisplayName','Subject mean');
    plot(x, smoothCurve, '-', 'Color',[0.85 0.25 0.15], 'LineWidth',2, ...
         'DisplayName',sprintf('Learning curve (movmean %d)',smoothW));

    % Block boundary lines
    for b = 2:numel(blks)
        xline((b-1)*perBlk + 0.5, 'k:', 'HandleVisibility','off');
    end

    ylim(yl); xlim([0.5 nTrials+0.5]);
    xlabel('Trial (blocks concatenated)');
    ylabel('Normalized score');
    ttl = sprintf('%s — %s', ...
        upper(strrep(phase,'phase_1','individual')), domain);
    if strcmp(phase,'phase_2'), ttl = sprintf('SYNERGY — %s', domain); end
    title(ttl, 'Interpreter','none');
    box on; grid on;
    if p == 1, legend('Location','southeast','FontSize',7); end
    hold off;
end

title(tl, 'Per-domain learning curves (mean \pm SEM across 3 subjects)', ...
      'FontWeight','bold');

exportgraphics(gcf, 'learning_curves.png', 'Resolution', 150);
fprintf('Saved learning_curves.png (%d panels)\n', nPlots);

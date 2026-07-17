% plot_learning_curves_individual.m
% Same 5 per-domain learning curves, but WITHOUT averaging across subjects.
% One figure per subject, each with 5 panels:
%
%   Individual phase (blocks 0,2,4):  cooking, repairing, tennis  -> 3 plots
%   Synergy    phase (blocks 1,3,5):  cooking, repairing          -> 2 plots
%
% For each domain, that domain's trials are concatenated across its three
% repeated blocks (in block order) to form the learning trajectory, then
% normalized by that domain's own max score (domains have different maxes).

clear; close all; clc;

subjects = {'sub-005', 'sub-006','sub-009','sub-010'};

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

for s = 1:numel(subjects)
    subj = subjects{s};
    Ts   = readtable(fullfile('..', 'data', subj, 'trials.csv'));

    figure('Color','w','Position',[80 80 1500 700], 'Name', subj);
    tl = tiledlayout(2, 3, 'TileSpacing','compact', 'Padding','compact');

    for p = 1:nPlots
        phase  = plots{p,1};
        domain = plots{p,2};
        blks   = plots{p,3};

        % Concatenate this domain's trials in block order
        seq = [];
        for b = 1:numel(blks)
            rows = strcmp(Ts.block, blks{b}) & strcmp(Ts.domain, domain);
            seq  = [seq; Ts.feedback_score(rows)];
        end
        m = max(seq);
        if isempty(m) || m == 0 || isnan(m), m = 1; end
        seq = seq / m;                                % per-domain normalization

        nTrials = numel(seq);
        x       = 1:nTrials;
        perBlk  = nTrials / numel(blks);

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

        % Connect the dots WITHIN each block (line cuts off at boundaries)
        for b = 1:numel(blks)
            idx = round((b-1)*perBlk) + (1:round(perBlk));
            idx = idx(idx <= nTrials);
            hc = plot(x(idx), seq(idx), '-o', 'Color',[0.2 0.45 0.8], ...
                      'MarkerFaceColor',[0.2 0.45 0.8], 'MarkerSize',4, ...
                      'LineWidth',1.2);
            if b == 1
                set(hc, 'DisplayName', 'Score');
            else
                set(hc, 'HandleVisibility','off');
            end
        end

        % Block boundary lines
        for b = 2:numel(blks)
            xline((b-1)*perBlk + 0.5, 'k:', 'HandleVisibility','off');
        end

        ylim(yl); xlim([0.5 nTrials+0.5]);
        xlabel('Trial (blocks concatenated)');
        ylabel('Normalized score');
        ttl = sprintf('individual — %s', domain);
        if strcmp(phase,'phase_2'), ttl = sprintf('SYNERGY — %s', domain); end
        title(ttl, 'Interpreter','none');
        box on; grid on;
        if p == 1, legend('Location','southeast','FontSize',7); end
        hold off;
    end

    title(tl, sprintf('%s — per-domain learning curves', subj), ...
          'FontWeight','bold', 'Interpreter','none');

    outPng = fullfile('..', 'data', subj, sprintf('%s_learning_curves.png', subj));
    exportgraphics(gcf, outPng, 'Resolution', 150);
    fprintf('Saved %s\n', outPng);
end

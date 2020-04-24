#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2018-2020 Fetch.AI Limited
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""Quick stats from data."""

import numpy as np
import pandas as pd
from scipy import stats  # type: ignore
import seaborn as sns  # type: ignore
import matplotlib.pyplot as plt  # type: ignore

sns.set(color_codes=True)


def analysis_scores_initial_and_final_vs_equilibrium():
    """Analyse the initial and final vs equilibrium scores for baseline agents only."""
    # load scores
    print("---------------\nAnalysis 1:")
    df1 = pd.read_csv("scores_final_ex2.csv")
    df1 = df1.drop(["Unnamed: 0"], axis=1)
    df2 = pd.read_csv("scores_final_ex3.csv")
    df2 = df2.drop(["Unnamed: 0"], axis=1)
    df_final = pd.concat([df1, df2], ignore_index=True, sort=False)
    df_final.reset_index(inplace=True)

    df3 = pd.read_csv("scores_equilibrium_ex2.csv")
    df3 = df3.drop(["Unnamed: 0"], axis=1)
    df4 = pd.read_csv("scores_equilibrium_ex3.csv")
    df4 = df4.drop(["Unnamed: 0"], axis=1)
    df_eq = pd.concat([df3, df4], ignore_index=True, sort=False)
    df_eq.reset_index(inplace=True)

    df5 = pd.read_csv("scores_initial_ex2.csv")
    df5 = df5.drop(["Unnamed: 0"], axis=1)
    df6 = pd.read_csv("scores_initial_ex3.csv")
    df6 = df6.drop(["Unnamed: 0"], axis=1)
    df_initial = pd.concat([df5, df6], ignore_index=True, sort=False)
    df_initial.reset_index(inplace=True)

    df_in_v_eq = df_initial.subtract(df_eq)
    df_fi_v_eq = df_final.subtract(df_eq)
    print("> Initial vs equilibrium and final vs equilibrium scores (only baseline)...")
    # sample:
    print(
        "Number agents: {}, number games: {}".format(
            df_in_v_eq.shape[1], df_in_v_eq.shape[0]
        )
    )
    # population: all games with the same config
    in_v_eq = np.array([])
    _in = np.array([])
    fi_v_eq = np.array([])
    _fi = np.array([])

    for column_name in df_in_v_eq.columns:
        if column_name == "index":
            continue
        elif column_name[-3:] == "_wm":
            continue
        else:
            in_v_eq = np.append(in_v_eq, df_in_v_eq[column_name].to_numpy())
            _in = np.append(_in, df_initial[column_name].to_numpy())

    for column_name in df_fi_v_eq.columns:
        if column_name == "index":
            continue
        elif column_name[-3:] == "_wm":
            continue
        else:
            fi_v_eq = np.append(fi_v_eq, df_fi_v_eq[column_name].to_numpy())
            _fi = np.append(_fi, df_final[column_name].to_numpy())

    # scipy.stats.ttest_ind(cat1['values'], cat2['values'], equal_var=False)
    # https://en.wikipedia.org/wiki/Welch%27s_t-test
    # https://stats.stackexchange.com/questions/305/when-conducting-a-t-test-why-would-one-prefer-to-assume-or-test-for-equal-vari
    alpha = 0.0001
    H_0 = "H_0: (baseline) agents mean of diff in final scores to equilibrium scores <= (baseline) agents mean of diff in initial scores to equilibrium scores (one-sided t-test)"
    print(H_0)
    result = stats.ttest_ind(in_v_eq, fi_v_eq)
    p_value = result.pvalue / 2.0
    reject = p_value < alpha
    print("One-sided t-test p-value: {}, reject H_0: {}".format(p_value, reject))
    means = [np.mean(fi_v_eq), np.mean(in_v_eq)]
    print("Mean: fi_v_eq={}, in_v_eq={}".format(means[0], means[1]))
    _plot(
        in_v_eq,
        fi_v_eq,
        "scores_in_d_eq_vs_fi_d_eq.png",
        label_one="Difference btw initial and equilibrium scores",
        label_two="Difference btw final and equilibrium scores",
    )


def analysis_scores_final_min_initial():
    """Analyse the final minus initial scores for both agent groups."""
    # load scores
    print("---------------\nAnalysis 2:")
    df1 = pd.read_csv("scores_final_ex2.csv")
    df1 = df1.drop(["Unnamed: 0"], axis=1)
    df2 = pd.read_csv("scores_final_ex3.csv")
    df2 = df2.drop(["Unnamed: 0"], axis=1)
    df_final = pd.concat([df1, df2], ignore_index=True, sort=False)
    df_final.reset_index(inplace=True)

    df3 = pd.read_csv("scores_initial_ex2.csv")
    df3 = df3.drop(["Unnamed: 0"], axis=1)
    df4 = pd.read_csv("scores_initial_ex3.csv")
    df4 = df4.drop(["Unnamed: 0"], axis=1)
    df_initial = pd.concat([df3, df4], ignore_index=True, sort=False)
    df_initial.reset_index(inplace=True)

    df = df_final.subtract(df_initial)

    print("> Initial minus final scores...")
    # sample:
    print("Number agents: {}, number games: {}".format(df.shape[1], df.shape[0]))
    # population: all games with the same config
    baseline = np.array([])
    w_model = np.array([])

    for column_name in df.columns:
        if column_name == "index":
            continue
        elif column_name[-3:] == "_wm":
            w_model = np.append(w_model, df[column_name].to_numpy())
        else:
            baseline = np.append(baseline, df[column_name].to_numpy())

    # scipy.stats.ttest_ind(cat1['values'], cat2['values'], equal_var=False)
    # https://en.wikipedia.org/wiki/Welch%27s_t-test
    # https://stats.stackexchange.com/questions/305/when-conducting-a-t-test-why-would-one-prefer-to-assume-or-test-for-equal-vari
    alpha = 0.0001
    H_0 = "H_0: world modelling agents diff mean scores <= baseline agents diff mean scores (one-sided t-test)"
    print(H_0)
    result = stats.ttest_ind(baseline, w_model)
    p_value = result.pvalue / 2.0
    reject = p_value < alpha
    print("One-sided t-test p-value: {}, reject H_0: {}".format(p_value, reject))
    means = [np.mean(w_model), np.mean(baseline)]
    print("Mean: w_model={}, baseline={}".format(means[0], means[1]))
    # sns.distplot(w_model)
    # plt.show()
    _plot(baseline, w_model, "scores_final_min_initial.png")


def analysis_scores():
    """Analyse the final scores."""
    # load scores
    print("---------------\nAnalysis 3:")
    df1 = pd.read_csv("scores_final_ex2.csv")
    df1 = df1.drop(["Unnamed: 0"], axis=1)
    df2 = pd.read_csv("scores_final_ex3.csv")
    df2 = df2.drop(["Unnamed: 0"], axis=1)
    df = pd.concat([df1, df2], ignore_index=True, sort=False)
    df.reset_index(inplace=True)

    print("> Final scores...")
    # sample:
    print("Number agents: {}, number games: {}".format(df.shape[1], df.shape[0]))
    # population: all games with the same config
    baseline = np.array([])
    w_model = np.array([])

    for column_name in df.columns:
        if column_name == "index":
            continue
        elif column_name[-3:] == "_wm":
            w_model = np.append(w_model, df[column_name].to_numpy())
        else:
            baseline = np.append(baseline, df[column_name].to_numpy())

    # scipy.stats.ttest_ind(cat1['values'], cat2['values'], equal_var=False)
    # https://en.wikipedia.org/wiki/Welch%27s_t-test
    # https://stats.stackexchange.com/questions/305/when-conducting-a-t-test-why-would-one-prefer-to-assume-or-test-for-equal-vari
    alpha = 0.0001
    H_0 = "H_0: world modelling agents mean scores <= baseline agents mean scores (one-sided t-test)"
    print(H_0)
    result = stats.ttest_ind(baseline, w_model)
    p_value = result.pvalue / 2.0
    reject = p_value < alpha
    print("One-sided t-test p-value: {}, reject H_0: {}".format(p_value, reject))
    means = [np.mean(w_model), np.mean(baseline)]
    print("Mean: w_model={}, baseline={}".format(means[0], means[1]))
    # sns.distplot(w_model)
    # plt.show()
    _plot(baseline, w_model, "scores.png")


def analysis_txs():
    """Analyse the txs."""
    # load scores
    for typ in ["seller", "buyer"]:
        print("---------------\nAnalysis of {} txs:".format(typ))
        df1 = pd.read_csv("transactions_{}_ex2.csv".format(typ))
        df1 = df1.drop(["Unnamed: 0"], axis=1)
        df2 = pd.read_csv("transactions_{}_ex3.csv".format(typ))
        df2 = df2.drop(["Unnamed: 0"], axis=1)
        df = pd.concat([df1, df2], ignore_index=True, sort=False)
        df.reset_index(inplace=True)
        # sample:
        print("Number agents: {}, number games: {}".format(df.shape[1], df.shape[0]))
        # population: all games with the same config
        baseline = np.array([])
        w_model = np.array([])

        for column_name in df.columns:
            if column_name == "index":
                continue
            elif column_name[-3:] == "_wm":
                w_model = np.append(w_model, df[column_name].to_numpy())
            else:
                baseline = np.append(baseline, df[column_name].to_numpy())

        # scipy.stats.ttest_ind(cat1['values'], cat2['values'], equal_var=False)
        # https://en.wikipedia.org/wiki/Welch%27s_t-test
        # https://stats.stackexchange.com/questions/305/when-conducting-a-t-test-why-would-one-prefer-to-assume-or-test-for-equal-vari
        alpha = 0.0001
        H_0 = "H_0: world modelling agents mean txs >= baseline agents mean txs (one-sided t-test)"
        print(H_0)
        # Alternate: world modelling agents mean txs < baseline agents mean txs
        result = stats.ttest_ind(baseline, w_model)
        p_value = result.pvalue / 2.0
        reject = p_value < alpha
        print(
            "One-sided t-test p-value: {}, reject H_0 (world modelling agents mean txs >= baseline agents mean txs): {}".format(
                p_value, reject
            )
        )
        means = [np.mean(w_model), np.mean(baseline)]
        print("Mean: w_model={}, baseline={}".format(means[0], means[1]))
        # sns.distplot(w_model)
        # plt.show()
        _plot(baseline, w_model, "txs_{}.png".format(typ))


def analysis_prices():
    """Analyse the prices."""
    print("---------------\nAnalysis of prices:")
    df1 = pd.read_csv("prices_ex2.csv", dtype=np.float64)
    df1 = df1.drop(["Unnamed: 0"], axis=1)
    df2 = pd.read_csv("prices_ex3.csv", dtype=np.float64)
    df2 = df2.drop(["Unnamed: 0"], axis=1)
    df = pd.concat([df1, df2], ignore_index=True, sort=False)
    df.reset_index(inplace=True)
    # sample:
    print("Number observations: {}".format(df.shape[0]))
    # population: all games with the same config
    baseline = df["baseline"].to_numpy()
    w_model = df["w_model"].to_numpy()
    w_model = w_model[~np.isnan(w_model)]

    # scipy.stats.ttest_ind(cat1['values'], cat2['values'], equal_var=False)
    # https://en.wikipedia.org/wiki/Welch%27s_t-test
    # https://stats.stackexchange.com/questions/305/when-conducting-a-t-test-why-would-one-prefer-to-assume-or-test-for-equal-vari
    alpha = 0.0001
    H_0 = "H_0: world modelling agents mean prices <= baseline agents mean prices (one-sided t-test)"
    print(H_0)
    result = stats.ttest_ind(baseline, w_model)
    p_value = result.pvalue / 2.0
    reject = p_value < alpha
    print(
        "One-sided t-test p-value: {}, reject H_0 (world modelling agents mean prices <= baseline agents mean prices): {}".format(
            p_value, reject
        )
    )
    means = [np.mean(w_model), np.mean(baseline)]
    print("Mean: w_model={}, baseline={}".format(means[0], means[1]))
    # sns.distplot(w_model)
    # plt.show()
    _plot(baseline, w_model, "prices.png")


def _plot(baseline, w_model, file, label_one="baseline", label_two="w_model"):
    """Plot helpert function."""
    min_bin = min(baseline.min(), w_model.min()) - 10
    max_bin = max(baseline.max(), w_model.max()) + 10
    bins = np.linspace(min_bin, max_bin, 100)
    plt.hist(baseline, bins, alpha=0.5, label=label_one)
    plt.hist(w_model, bins, alpha=0.5, label=label_two)
    plt.legend(loc="upper right")
    # plt.show()
    plt.savefig(file)
    plt.clf()


if __name__ == "__main__":
    analysis_scores_initial_and_final_vs_equilibrium()
    analysis_scores_final_min_initial()
    analysis_scores()
    analysis_txs()
    analysis_prices()

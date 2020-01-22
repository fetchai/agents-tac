import numpy as np
import pandas as pd
from scipy import stats
import seaborn as sns
import matplotlib.pyplot as plt

sns.set(color_codes=True)


def analysis_scores():
	# load scores
	print("---------------\nAnalysis of scores:")
	df1 = pd.read_csv('scores_ex2.csv')
	df1 = df1.drop(['Unnamed: 0'], axis=1)
	df2 = pd.read_csv('scores_ex3.csv')
	df2 = df2.drop(['Unnamed: 0'], axis=1)
	df = pd.concat([df1, df2], ignore_index=True, sort=False)
	df.reset_index(inplace=True)
	# sample:
	print("Number agents: {}, number games: {}".format(df.shape[0], df.shape[1]))
	# population: all games with the same config
	baseline = np.array([])
	w_model = np.array([])

	for column_name in df.columns:
		if column_name == 'index':
			continue
		elif column_name[-3:] == '_wm':
			w_model = np.append(w_model, df[column_name].to_numpy())
		else:
			baseline = np.append(baseline, df[column_name].to_numpy())

	
	# scipy.stats.ttest_ind(cat1['values'], cat2['values'], equal_var=False)
	# https://en.wikipedia.org/wiki/Welch%27s_t-test
	# https://stats.stackexchange.com/questions/305/when-conducting-a-t-test-why-would-one-prefer-to-assume-or-test-for-equal-vari
	alpha = 0.0001
	# H_0: world modelling agents mean scores <= baseline agents mean scores (one-sided t-test)
	result = stats.ttest_ind(baseline, w_model)
	p_value = result.pvalue / 2.0
	reject = p_value < alpha
	print('One-sided t-test p-value: {}, reject H_0: {}'.format(p_value, reject))
	means = [np.mean(w_model), np.mean(baseline)]
	print('Mean: w_model={}, baseline={}'.format(means[0], means[1]))
	# sns.distplot(w_model)
	# plt.show()
	plot(baseline, w_model, 'scores.png')

def analysis_txs():
	# load scores
	for typ in ['seller', 'buyer']:
		print("---------------\nAnalysis of {} txs:".format(typ))
		df1 = pd.read_csv('transactions_{}_ex2.csv'.format(typ))
		df1 = df1.drop(['Unnamed: 0'], axis=1)
		df2 = pd.read_csv('transactions_{}_ex3.csv'.format(typ))
		df2 = df2.drop(['Unnamed: 0'], axis=1)
		df = pd.concat([df1, df2], ignore_index=True, sort=False)
		df.reset_index(inplace=True)
		# sample:
		print("Number agents: {}, number games: {}".format(df.shape[0], df.shape[1]))
		# population: all games with the same config
		baseline = np.array([])
		w_model = np.array([])

		for column_name in df.columns:
			if column_name == 'index':
				continue
			elif column_name[-3:] == '_wm':
				w_model = np.append(w_model, df[column_name].to_numpy())
			else:
				baseline = np.append(baseline, df[column_name].to_numpy())

		# scipy.stats.ttest_ind(cat1['values'], cat2['values'], equal_var=False)
		# https://en.wikipedia.org/wiki/Welch%27s_t-test
		# https://stats.stackexchange.com/questions/305/when-conducting-a-t-test-why-would-one-prefer-to-assume-or-test-for-equal-vari
		alpha = 0.0001
		# H_0: world modelling agents mean txs >= baseline agents mean txs (one-sided t-test)
		# Alternate: world modelling agents mean txs < baseline agents mean txs
		result = stats.ttest_ind(baseline, w_model)
		p_value = result.pvalue / 2.0
		reject = p_value < alpha
		print('One-sided t-test p-value: {}, reject H_0 (world modelling agents mean txs >= baseline agents mean txs): {}'.format(p_value, reject))
		means = [np.mean(w_model), np.mean(baseline)]
		print('Mean: w_model={}, baseline={}'.format(means[0], means[1]))
		# sns.distplot(w_model)
		# plt.show()
		plot(baseline, w_model, 'txs_{}.png'.format(typ))

def analysis_prices():
	print("---------------\nAnalysis of prices:")
	df1 = pd.read_csv('prices_ex2.csv', dtype=np.float64)
	df1 = df1.drop(['Unnamed: 0'], axis=1)
	df2 = pd.read_csv('prices_ex3.csv', dtype=np.float64)
	df2 = df2.drop(['Unnamed: 0'], axis=1)
	df = pd.concat([df1, df2], ignore_index=True, sort=False)
	df.reset_index(inplace=True)
	# sample:
	print("Number agents: {}".format(df.shape[0]))
	# population: all games with the same config
	baseline = df['baseline'].to_numpy()
	w_model = df['w_model'].to_numpy()
	w_model = w_model[~np.isnan(w_model)]
	
	# scipy.stats.ttest_ind(cat1['values'], cat2['values'], equal_var=False)
	# https://en.wikipedia.org/wiki/Welch%27s_t-test
	# https://stats.stackexchange.com/questions/305/when-conducting-a-t-test-why-would-one-prefer-to-assume-or-test-for-equal-vari
	alpha = 0.0001
	# H_0: world modelling agents mean prices <= baseline agents mean prices (one-sided t-test)
	result = stats.ttest_ind(baseline, w_model)
	p_value = result.pvalue / 2.0
	reject = p_value < alpha
	print('One-sided t-test p-value: {}, reject H_0 (world modelling agents mean prices <= baseline agents mean prices): {}'.format(p_value, reject))
	means = [np.mean(w_model), np.mean(baseline)]
	print('Mean: w_model={}, baseline={}'.format(means[0], means[1]))
	# sns.distplot(w_model)
	# plt.show()
	plot(baseline, w_model, 'prices.png')

def plot(baseline, w_model, file):
	min_bin = max(min(baseline.min(), w_model.min()) - 10, 0)
	max_bin = max(baseline.max(), w_model.max()) + 10
	bins = np.linspace(min_bin, max_bin, 100)
	plt.hist(baseline, bins, alpha=0.5, label='baseline')
	plt.hist(w_model, bins, alpha=0.5, label='w_model')
	plt.legend(loc='upper right')
	# plt.show()
	plt.savefig(file)
	plt.clf()


if __name__ == '__main__':
	analysis_scores()
	analysis_txs()
	analysis_prices()

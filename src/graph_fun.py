import numpy as np
from statsmodels.tsa.stattools import pacf
from plotly.subplots import make_subplots
import plotly.graph_objects as go


def ts_decompose(ts, nlags: int, dates, ts_plot: bool = True, acf_plot: bool = True, pacf_plot: bool = True,
                 y_label: str = "Adj. Closing"):
    """

    :param y_label:
    :param dates:
    :param ts:
    :param nlags:
    :param ts_plot:
    :param acf_plot:
    :param pacf_plot:
    :return:
    """
    assert type(nlags) == int, "Number of lags must be an integer!"
    assert type(ts_plot) == bool, "Whether to include a time series plot must be True or False!"
    assert type(acf_plot) == bool, "Whether to include a ACF plot must be True or False!"
    assert type(pacf_plot) == bool, "Whether to include a PACF plot must be True or False!"

    nlags = nlags

    num_plots = ts_plot + acf_plot + pacf_plot
    if not num_plots:
        return

    plot_titles = []
    if ts_plot:
        plot_titles.append(f"Daily {y_label}")
    if acf_plot:
        plot_titles.append("ACF")
    if pacf_plot:
        plot_titles.append("Partial ACF")

    my_fig = make_subplots(rows=num_plots, cols=1,
                           subplot_titles=plot_titles)
    plot_num = 1

    if ts_plot:
        my_fig.add_trace(
            go.Scatter(x=dates.iloc[:len(ts)], y=ts, mode='lines'),
            row=plot_num, col=1
        )

        my_fig.update_xaxes(title_text="Date", row=plot_num, col=1)
        my_fig.update_yaxes(title_text=y_label, row=plot_num, col=1)
        plot_num += 1

    if acf_plot:
        acf_mean = np.mean(ts)
        acf_var = np.var(ts)
        acf_arr = [1]

        for n in range(1, nlags + 1):
            my_cov = 0
            for m in range(ts[:-n].shape[0]):
                my_cov += (ts[:-n].iloc[m] - acf_mean) * (ts[n:].iloc[m] - acf_mean)
            my_cov = my_cov / (ts.shape[0] * acf_var)
            acf_arr.append(my_cov)

        my_fig.add_trace(
            go.Bar(x=np.arange(int(nlags + 1)), y=acf_arr),
            row=plot_num, col=1
        )

        my_fig.update_xaxes(title_text="nlags", row=plot_num, col=1)
        my_fig.update_yaxes(title_text="ACF", row=plot_num, col=1)
        plot_num += 1

    if pacf_plot:
        my_pacf = pacf(ts, nlags)
        my_fig.add_trace(
            go.Bar(x=np.arange(int(nlags + 1)), y=my_pacf),
            row=plot_num, col=1
        )
        my_fig.update_xaxes(title_text="nlags", row=plot_num, col=1)
        my_fig.update_yaxes(title_text="PACF", row=plot_num, col=1)
        plot_num += 1

    my_fig.update(layout_showlegend=False)

    return my_fig

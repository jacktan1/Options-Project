import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from statsmodels.tsa.stattools import pacf


def interest_vs_volume(input_dict):
    complete_df = input_dict["complete"]

    my_fig = make_subplots(rows=1, cols=2,
                           subplot_titles=["Day n Volume vs. |Delta Open Interest|",
                                           "Day n+1 Volume vs. |Delta Open Interest|"])

    my_fig.add_trace(go.Scatter(x=complete_df["abs delta"],
                                y=complete_df["volume 1"],
                                mode='markers', showlegend=False,
                                marker=dict(size=5, color="red", opacity=0.5)),
                     row=1, col=1)

    my_fig.add_trace(go.Scatter(x=complete_df["abs delta"],
                                y=complete_df["volume 2"],
                                mode='markers', showlegend=False,
                                marker=dict(size=5, color="blue", opacity=0.5)),
                     row=1, col=2)

    my_fig.update_layout(
        shapes=[
            dict(type="line", xref="x", yref="y",
                 x0=0, y0=0,
                 x1=np.max(complete_df["abs delta"]), y1=np.max(complete_df["abs delta"]),
                 line_width=1),
            dict(type="line", xref="x2", yref='y2',
                 x0=0, y0=0,
                 x1=np.max(complete_df["abs delta"]), y1=np.max(complete_df["abs delta"]),
                 line_width=1),
        ])

    my_fig.update_yaxes(title_text="Volume")
    my_fig.update_xaxes(title_text="$|\Delta Open~Interest|$")

    return my_fig


def voi_dividends_ts(input_dict):
    # Unpack variables
    min_year = input_dict["min year"]
    max_year = input_dict["max year"]
    options_agg_df = input_dict["voi agg"]
    dividends_df = input_dict["dividends"]

    options_agg_df = options_agg_df[(options_agg_df["year"] >= min_year) &
                                    (options_agg_df["year"] <= max_year)]

    start_date = np.min(options_agg_df["date"])
    end_date = np.max(options_agg_df["date"])

    sorted_doi = sorted(options_agg_df["abs delta"])
    sorted_vol = sorted(options_agg_df["volume"])

    doi_max = sorted_doi[-1]
    vol_max = sorted_vol[-1]

    # Can't be 0th index because we are using log axis, and 0 is often the min value
    doi_min = sorted_doi[10]
    vol_min = sorted_vol[10]

    my_fig = make_subplots(rows=2, cols=1,
                           subplot_titles=["|Delta Open Interest| Time Series",
                                           "Volume Time Series"])

    my_fig.add_trace(go.Scatter(x=options_agg_df["date"],
                                y=options_agg_df["abs delta"],
                                name="|Delta Open Interest|",
                                marker={"color": "blue"},
                                opacity=0.8,
                                connectgaps=True),
                     row=1, col=1)

    my_fig.add_trace(go.Scatter(x=options_agg_df["date"],
                                y=options_agg_df["volume"],
                                name="Volume",
                                marker={"color": "red"},
                                opacity=0.8,
                                connectgaps=True),
                     row=2, col=1)

    # Plotting dividend vertical lines
    div_line_list = []

    for div_date in list(dividends_df["div start"]):
        if (div_date < start_date) or (div_date > end_date):
            continue
        else:
            div_line_list.extend([
                dict(type="line", xref="x", yref="y",
                     x0=div_date, y0=doi_min,
                     x1=div_date, y1=doi_max,
                     line_width=1),
                dict(type="line", xref="x2", yref='y2',
                     x0=div_date, y0=vol_min,
                     x1=div_date, y1=vol_max,
                     line_width=1)
            ])

    my_fig.update_yaxes(type="log",
                        range=[np.floor(np.log10(doi_min)), np.ceil(np.log10(doi_max))],
                        row=1, col=1)

    my_fig.update_yaxes(type="log",
                        range=[np.floor(np.log10(vol_min)), np.ceil(np.log10(vol_max))],
                        row=2, col=1)

    my_fig.update_layout(shapes=div_line_list,
                         font={"size": 15})

    return my_fig


def ts_decompose(ts, nlags: int, dates, ts_plot: bool = True, acf_plot: bool = True, pacf_plot: bool = True,
                 y_label: str = "Adj. Closing"):
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

import plotly.express as px

# Make sure data is sorted by date
nightly = nightly.sort_values("sleep_date").copy()

# Calculate a 7-night moving average
nightly["7_day_avg"] = (
    nightly["total_sleep"]
    .rolling(window=7, min_periods=1)
    .mean()
)

# Optional: only show the most recent 60 nights
chart_data = nightly.tail(60).copy()

fig = px.line(
    chart_data,
    x="sleep_date",
    y=["total_sleep", "7_day_avg"],
    title="Total Sleep per Night with 7-Day Moving Average",
    labels={
        "sleep_date": "Date",
        "value": "Hours of Sleep",
        "variable": "Measure"
    }
)

fig.update_traces(mode="lines+markers")

fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Hours of Sleep",
    hovermode="x unified"
)

fig.show()
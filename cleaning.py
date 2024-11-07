import re

FORMAT_WORDS = [
    "bar graph", "bar chart", "horizontal bar chart", "vertical bar chart", "stacked bar chart", 
    "grouped bar chart", "clustered bar chart",
    "column graph", "column chart", "vertical column chart", "stacked column chart", 
    "grouped column chart", "clustered column chart",
    "line graph", "line chart", "line plot", "trend line", "time series chart",
    "pie chart", "donut chart", "doughnut chart", "circular chart", "ring chart",
    "area chart", "stacked area chart", "stacked area graph", "filled line chart",
    "scatter plot", "scatter diagram", "dot plot", "xy plot",
    "histogram", "frequency distribution chart",
    "box plot", "box-and-whisker plot", "box and whisker plot",
    "bubble chart", "bubble plot",
    "heatmap", "heat map", "density plot",
    "radar chart", "spider chart", "web chart", "star plot",
    "tree map", "treemap",
    "waterfall chart", "bridge chart",
    "gantt chart", "gantt diagram",
    "donut chart", "doughnut chart", "ring chart",
    "sparkline", "sparkline chart",
    "table", "data table", "tabular data",
    "dashboard", "data dashboard",
    "map", "geographical map", "location map", "geo map",
    "timeline", "time line",
    "network diagram", "network graph", "node-link diagram",
    "funnel chart", "sales funnel chart", "conversion funnel chart",
    "violin plot", "violin chart",
    "word cloud", "tag cloud", "geo chart"
]

def clean_query(query):
    pattern = re.compile("|".join(map(re.escape, FORMAT_WORDS)), re.IGNORECASE)
    query = pattern.sub("", query)
    return query
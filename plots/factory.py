from solariat_bottle.plots.trends_posts import (ResponseTimePlotter, ResponseVolumePlotter, 
                                                CallVolumePlotter, BasePlotter)
from solariat_bottle.plots.trends_topics import BaseTopicPlotter, SentimentPlotter

    
PLOTS_MAPPING = {'response-time': ResponseTimePlotter,
                 'response-volume': ResponseVolumePlotter, 
                 'inbound-volume': CallVolumePlotter,
                 'sentiment': SentimentPlotter,
                 'top-topics': BaseTopicPlotter,
                 'topics': BaseTopicPlotter,
                 'missed-posts': BaseTopicPlotter}

def get_plotter(plot_type, **kwargs):
    _plotter_ = PLOTS_MAPPING.get(plot_type, BasePlotter)
    return _plotter_(**kwargs)

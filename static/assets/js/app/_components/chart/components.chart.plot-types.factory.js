(function () {
  'use strict';

  angular
    .module('slr.chart')
    .factory("PlotTypes", PlotTypes);

  // Move out from here $rootScope
  function PlotTypes($rootScope, MetadataService) {
    var PlotTypes = {};

    var getPlotFiltersVisibility = function () {
      return {
        "inbound": {time: ['intention', 'topic', 'status'], share: ['intention', 'topic', 'status']},
        "outbound": {time: ['intention', 'topic', 'agent'], share: ['intention', 'topic', 'agent']},
        "response-time": {time: ['agent'], share: ['agent']},
        "response-volume": {time: ['agent'], share: ['agent']},
        "sentiment": {time: ['sentiment'], share: ['sentiment']},
        "missed-posts": {time: [], share: []},
        "inbound-volume": {time: [], share: []},
        "top-topics": {time: ['topic'], share: ['topic']},
        "customers": {share: ['segment', 'industry', 'Status', 'location', 'gender']},
        "agents": {share: ['location', 'gender']},
        "predictors": {time: ['Mean Error', 'Mean Latency', 'Mean Reward']}
      };
    };

    var plot_filters = MetadataService.getPlotFilters();

    // plot types
    var plot_types = [
      {type: 'time', enabled: true, label: 'Trends'},
      {type: 'share', enabled: false, label: 'Distribution'}
    ];
    var plot_stats_type = "";
    var plot_location = "inbound";

    PlotTypes.ON_PLOT_TYPE_CHANGE = 'on_plot_type_change';
    PlotTypes.ON_PLOT_GET_ACTIVE = 'on_plot_get_active';
    PlotTypes.ON_PLOT_FILTER_CHANGE = 'on_plot_filter_change';
    PlotTypes.ON_PLOT_REPORT_CHANGE = 'on_plot_report_change';

    var setPlotTypeOrFilter = function (which, type, silent) {
      var list = which == 'plot' ? plot_types : plot_filters;
      var plot_event = which == 'plot' ? PlotTypes.ON_PLOT_TYPE_CHANGE : PlotTypes.ON_PLOT_FILTER_CHANGE;
      angular.forEach(list, function (val) {
        val.enabled = (val.type === type);
      });
      if (typeof silent === 'undefined') {
        $rootScope.$broadcast(plot_event)
      }
    };

    PlotTypes.setType = function (type, silent) {
      setPlotTypeOrFilter('plot', type, silent);
    };

    PlotTypes.setFilter = function (type, silent) {
      setPlotTypeOrFilter('filter', type, silent);
    };

    PlotTypes.resetPlotFilters = function () {
      _.each(plot_filters, function (item) {
        item.enabled = false
      });
    };

    PlotTypes.updatePlotTypes = function (newTypes) {
      if (newTypes)
        plot_types = newTypes;
    };

    PlotTypes.setPlotTypes = function (plotTypes) {
      plot_types = plotTypes;
      return plot_types;
    };

    PlotTypes.getActiveType = function () {
      return _.filter(plot_types, function (el) {
        return el.enabled == true
      })[0]['type'];
    };

    PlotTypes.getActiveFilter = function () {
      var active_filter = _.filter(plot_filters, function (el) {
        return el.enabled == true
      });
      return active_filter.length > 0 ? active_filter[0]['type'] : null;
    };

    PlotTypes.getList = function () {
      return plot_types;
    };

    PlotTypes.getPage = function () {
      return plot_location;
    };

    PlotTypes.setPage = function (page) {
      plot_location = page;
      $rootScope.$broadcast(PlotTypes.ON_PLOT_REPORT_CHANGE);
    };

    PlotTypes.getYAxisLabel = function (page) {
      var section = page ? page : PlotTypes.getPage();
      var label = {
        'inbound': 'Posts',
        'outbound': 'Responses',
        'response-time': 'Response Time',
        'response-volume': 'Responses',
        'sentiment': 'Posts',
        'inbound-volume': 'Posts',
        'top-topics': 'Posts',
        'missed-posts': 'Posts'
      }[section];
      return label;
    };

    PlotTypes.getDefaultLegendLabel = function (page) {
      var section = page ? page : PlotTypes.getPage();
      var label = {
        'inbound': 'Posts',
        'outbound': 'Responses',
        'response-time': 'Average Response Time',
        'response-volume': 'All Responses',
        'sentiment': 'Number of Posts',
        'inbound-volume': 'Number of Posts',
        'top-topics': 'Number of Posts',
        'missed-posts': 'Number of Posts'
      }[section];
      return label;
    };

    PlotTypes.getFilters = function (plot_type) {
      var page = PlotTypes.getPage();
      plot_type = PlotTypes.getActiveType();
      if (!page || !plot_type) return [];

      var visibility = getPlotFiltersVisibility();
      return _.filter(plot_filters, function (item) {
        return _.contains(visibility[page][plot_type], item.type);
      });
    };

    PlotTypes.setPlotStatsType = function (type) {
      //return termStats or channelStats to indicate which plot is currently shown
      plot_stats_type = type
    };

    PlotTypes.getPlotStatsType = function () {
      return plot_stats_type
    };

    PlotTypes.isAverageTimeReport = function () {
      return PlotTypes.getActiveType() == 'time' && PlotTypes.getPage() == 'response-time';
    };

    return PlotTypes
  }
})();
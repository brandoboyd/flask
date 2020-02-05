(function () {
  'use strict';

  angular
    .module('predictors')
    .factory('PredictorsTabRenderFactory', PredictorsTabRenderFactory);

  /**
   * Common Factory for Trends, Distribution controllers
   */
  /** @ngInject */
  function PredictorsTabRenderFactory($resource) {
    var Factory = {};
    var Resource = $resource('/predictors/facets/json', {}, {getGraphData: {method: 'POST', isArray: false}});

    Factory.initGroupings = function (facets) {
      //plot_bys derived from the actual feature facets
      var features = _.extend({},
          {'all': 'all', 'models': 'models', 'ab testing': 'ab testing'},
          facets.context_vector,
          facets.action_vector);
      var groupings = _.map(features, function (val, key) {
        return {
          type: key,
          value: key,
          active: false || key == 'all'
        }
      });

      return groupings;
    };

    Factory.render = function (attrs, cb) {
      if (!attrs.predictor) return;

      var charts = [{data: [], settings: {}}];
      var params = attrs.params;
      var settings = attrs.chart_settings;

      attrs.flags.rendering = true;
      attrs.tab_options.type = 'metrics';

      Resource.getGraphData({}, params, function (res) {
        attrs.flags.rendering = false;
        if (res.list.length) {
          // if there is negative value, then distribute as Discrete Bar Chart, otherwise as Pie Chart
          var isBar = _.some(res.list, function (each) {
            return each.value < 0;
          });

          if (isBar) {
            settings.chart_type = 'DISCRETEBAR';
          }

          charts = [{data: res.list, settings: settings}];
        }

        cb({
          charts: charts,
          flags: attrs.flags,
          tab_options: attrs.tab_options
        });
      });
    };

    return Factory;
  }
})();
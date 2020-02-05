'use strict';

angular.module('dashboard', [
  'ngRoute',
  'ark-dashboard',
  'ark-components',
  'ui.slimscroll',
  'ui.bootstrap',
  'slr.components',
  'omni',
  'infinite-scroll',
  'gridster',
  'ng.jsoneditor',
  'bt.jsonValidator'
])
  .config(function ($routeProvider) {
    $routeProvider
      .when('/', {
        templateUrl: '/partials/dashboard/view',
        controller: 'JourneysMultiDashboardsCtrl'
      })
      .otherwise({
        redirectTo: '/'
      });
  })

  .filter('moment', [
    function () {
      return function (date, format) {
        return moment(date).format(format);
      };
    }
  ])

  .factory('RestTimeSeriesDataModel', function (WidgetDataModel, $http, FilterService, Topics) {
    function RestTimeSeriesDataModel() {
    }

    RestTimeSeriesDataModel.prototype = Object.create(WidgetDataModel.prototype);

    RestTimeSeriesDataModel.prototype.init = function (callback) {
      WidgetDataModel.prototype.init.call(this);

      var params = this.dataModelOptions ? this.dataModelOptions.params : {};
      var wAttrs = this.widgetScope.widget.attrs;
      var range_alias = wAttrs.extra_settings.range_alias;
      var settings    = _.extend({}, wAttrs.settings);
      var date_range  = FilterService.getDateRangeByAlias(range_alias);

      var old_from = wAttrs.settings.from;
      var old_to   = wAttrs.settings.to;

      //amend settings
      settings.from = date_range ? date_range.from.toString("MM/dd/yyyy") : old_from;
      settings.to   = date_range ? date_range.to.toString("MM/dd/yyyy")   : old_to;

      var get_topic_type = function(el) {
        if (el.hasOwnProperty('term_count')) {
          return (el.term_count === el.topic_count ? "leaf" : "node");
        } else if (el.hasOwnProperty('topic_type')) {
          return el.topic_type;
        }
      };

      var chartModel = this;
      var fetchTrendsData = function(settings) {
        var request_url = settings.request_url || 'trends/json';
        delete settings.request_url;
        $http.post(request_url, settings).success(function(d) {
          var chart = { data      : d.list, settings  : wAttrs.settings, widget_id : wAttrs.id, extra_settings : wAttrs.extra_settings };
          WidgetDataModel.prototype.updateScope.call(chartModel, chart);
          callback();
        }.bind(chartModel))
      }

      if(wAttrs.extra_settings.topics != null) {
        var topicParams = wAttrs.extra_settings.topics;
        var limit = 10;

        topicParams.from = date_range ? date_range.from.toString("MM/dd/yyyy") : old_from;
        topicParams.to   = date_range ? date_range.to.toString("MM/dd/yyyy")   : old_to;

        Topics.fetch(topicParams, limit).then(function(res) {
          if(angular.isArray(res)) {
            var topics = [];
            _.each(res, function(el) {
              topics.push({
                'topic'      : el.topic,
                'topic_type' : get_topic_type(el),
                'parent'     : el.parent,
                'level'      : el.level
              })
            })
            settings.topics = topics;
            fetchTrendsData(settings);
          }
        });
      } else {
        fetchTrendsData(settings);
      }

    };

    return RestTimeSeriesDataModel;
  })

  .directive('wtPlotter', function ($interval, $compile) {
    return {
      replace: true,
      template: '<div style="height:100%;width:100%;"></div>',
      scope : {
        chart   : '='
      },
      link: function (scope, el) {

        scope.$watch('chart', function (chart) {

          if (chart) {
            el.empty();
            if (chart.extra_settings.widget_type && chart.extra_settings.widget_type == 'topics') {
              var topics = $compile("<div widget-topics-cloud settings='chart' widget-id='widget_id' style='height:100%; width:100%'></div>")(scope);
              el.append(topics);

            } else if (['OMNI', 'OMNI_AGENTS', 'OMNI_CUSTOMERS', 'PREDICTORS'].indexOf(chart.extra_settings.target) !== -1) {
              el.html("<journey-chart chart-data='data' widget-id='widget_id' plot-options='plot_options' extra-settings='extra_settings'>");
              $compile(el.contents())(scope);
              scope.extra_settings = chart.extra_settings || null;
            } else {
              var plot = $compile("<div widget-plotter='data' widget-id='widget_id' plot-options='plot_options' style='height:100%; width:100%'></div>")(scope);
              el.append(plot);
            }

            scope.data = chart.data;
            scope.plot_options = chart.settings ? chart.settings : null;
            scope.widget_id = chart.widget_id ? chart.widget_id : null;
          }
        });
      }
    };
  })

  .directive('widgetTopicsCloud', function ($interval, $compile, Topics) {
    function fetch(scope, params) {
      var limit = params.plot_type ? 15 : null;
      return Topics.fetch(params, limit).then(function(d) {
        scope.topics = _.defaults(d, {active : ''});
        scope.count_max = _.max(scope.topics, function(topic) { return topic.term_count} )['term_count'];
        scope.count_min = _.min(scope.topics, function(topic) { return topic.term_count} )['term_count'];
      });
    }

    return {
      replace: false,
      scope : {
        settings : '='
      },
      template: '<div class="tagcloud maincloud widget-tagcloud"><ul><li ng-repeat="item in topics | orderBy:\'topic\':reverse"  ng-style="getTopicSize(item.term_count)[\'log\']"><span ng-bind="item.topic"></span></li></ul></div>',
      link: function (scope, el) {
        scope.getTopicSize = function(count) {
          var fontMin = 12,
            fontMax = 40;
          var size = count == scope.count_min ? fontMin
            : (Math.log(count) / Math.log(scope.count_max)) * (fontMax - fontMin) + fontMin;
          var styles = {log : { 'font-size' : size + 'px'}};
          return styles;
        };
        scope.$watch('settings', function(nVal, oldVal) {
          if (nVal) {
            //console.log(nVal.extra_settings.topics_params);
            if (!nVal.extra_settings.topics_params) {
              return;
            }
            fetch(scope, nVal.extra_settings.topics_params);
          }

        })

      }
    };
  });


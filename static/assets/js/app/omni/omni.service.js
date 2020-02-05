(function () {
  'use strict';

  angular
    .module('omni')
    .factory('OmniChannel', OmniChannel)
    .factory('Customer', Customer)
    .factory('Agent', Agent)
    .factory('CallIntent', CallIntent)
    .factory('Segment', Segment)
    .factory('Industry', Industry)
    .factory('CustomerEvents', CustomerEvents)
    .factory('Crossfilter', Crossfilter)
    .factory('JourneysTimelineFactory', JourneysTimelineFactory)
    .factory('PathAnalysisFactory', PathAnalysisFactory)

  /** @ngInject */
  function PathAnalysisFactory() {
    var F = {};
    var path_settings;

    F.get_path_settings = function() {
      return path_settings;
    };

    F.set_path_settings = function(c) {
      path_settings = c;
    };

    return F;
  }


  /** @ngInject */
  function JourneysTimelineFactory($http, $timeout, MetadataService) {

    var buildHorizontalTimeline = function (arr, data) {
      var dateInfo = [];

      _.each(arr, function (s) {
        var temp = {
          id: s.id,
          startDate: validDate(s.startDate),
          endDate: validDate(s.endDate),
          headline: s.headline
        };
        dateInfo.push(temp);
      });
      return {
        "timeline": {
          "type": "default",
          "date": dateInfo,
          "era": [{
            startDate: validDate(data.startDate),
            endDate: validDate(data.endDate)
          }]
        }
      };
    };

    var buildOutcome = function (journey) {
      var outcome = '';
      var start = moment(journey.startDate);
      var end = moment(journey.endDate);
      var nps = journey['NPS'];
      var lastedDays = moment.duration(end.diff(start)).asDays();
      if (lastedDays === 0) lastedDays = 1;
      outcome += 'Journey lasted for ' + lastedDays;
      lastedDays > 1 ? outcome += ' days' : outcome += ' day';
      outcome += ' with the status "' + journey.status + '".';
      if (nps !== null) {
        outcome += ' CSAT is ' + journey.CSAT + '.';
        if (nps >= 9) { // promoter
          outcome += ' Customer satisfied.';
        } else if (6 <= nps && nps < 9) { // passive
          outcome += ' Customer somewhat satisfied.';
        } else if (nps < 6) { // detractor
          outcome += ' Customer unsatisfied.';
        }
      }
      return outcome;
    };

    var buildVisualization = function (journey) {
      nv.addGraph(function () {
        var chart = nv.models.discreteBarChart()
            .x(function (d) {
              return d.label
            })    //Specify the data accessors.
            .y(function (d) {
              return d.value
            })
            .staggerLabels(true)    //Too many bars and not enough room? Try staggering labels.
            .showValues(true)       //...instead, show the bar value right on top of each bar.
          ;

        chart.tooltip.enabled(false);        //Don't show tooltips

        d3.select('#scoresChart svg')
          .datum(loadData())
          .call(chart);
        nv.utils.windowResize(chart.update);
        return chart;
      });

      function loadData() {
        return [
          {
            key: "Cumulative Return",
            values: [
              {
                "label": "NPS",
                "value": journey.NPS
              },
              {
                "label": "CSAT",
                "value": journey.CSAT
              }
            ]
          }
        ]
      }
    };

    var buildVerticalTimeline = function (data, journey, callback) {
      var verticalTimeline = [];
      angular.element('#noResults').hide();

      if (_.isUndefined(data.events) || !data.events.length) {
        angular.element('#noResults').show();
        return;
      }

      _.each(data.events, function (event, index) {
        var extraFields = null;
        var icon = MetadataService.getEventTypeIcon(event.platform);

        //define the icon
        try {
          switch (event.platform) {
            case('Twitter'):
              extraFields = JSON.parse(event.content[0].extra_fields.twitter._wrapped_data);
              break;
            case('Facebook'):
              extraFields = JSON.parse(event.content[0].extra_fields.facebook._wrapped_data);
              break;
          }
        } catch (e) {
          extraFields = null;
        }

        var assignedTags = [];

        _.each(event.content, function(c) {
          /** give to intention by its type the right css class name */
          c.speech_acts = _.map(c.speech_acts, function(sa) {
            return _.extend(sa, {
              className: MetadataService.getIntentionClass(sa.intention_type)
            });
          });

          if (c.journey_tags.length) {
            assignedTags.push(_.pluck(c.journey_tags, 'id'));
          }
        });

        _.extend(event, {
          icon: icon,
          extraFields: extraFields,
          assignedTags: _.flatten(assignedTags),
          class: 'class' + index
        });

        verticalTimeline.push(event);
      });

      // JOURNEY STARTED
      verticalTimeline.unshift({
        time: journey.startDate,
        content: [{
          content: 'Journey started on',
          time: moment(journey.startDate).format('LLLL')
        }],
        isFirstOrLast: true
      });
      // JOURNEY ENDED
      verticalTimeline.push({
        content: [{
          content: 'Journey ' + journey.status + ' on',
          time: moment(journey.endDate).format('LLLL')
        }],
        isFirstOrLast: true
      });
      callback(verticalTimeline);
    };

    var getEvents = function (index, journey, callback) {
      var stage = journey.stages[index];
      stage.headline = stage.stageName;

      var res = {
        verticalTimeline: [],
        stage: stage
      };

      $http.get('/journey/' + journey.id + '/' + stage.id + '/events')
        .success(function (events) {
          clearPrevExpands();

          buildVerticalTimeline(events.item, journey, function (data) {
            res.verticalTimeline = data;
          });

          if (journey.status === 'ongoing') {
            $timeout(function () {
              angular.element('.timeline > li:last-child').hide();
              angular.element('.timeline').addClass('ongoingJourney');
            });
          } else {
            angular.element('.timeline').removeClass('ongoingJourney');
          }
          callback(res);
        });
    };

    function clearPrevExpands() {
      var panel = angular.element('.eventPanel');
      panel.hide(); // hide all prev expanded panels
      if (panel.hasClass('marginBottom')) {
        angular.element(panel).removeClass('marginBottom');
      }
      angular.element('.extraInfo').hide(); // hide all prev expanded extra info
    }

    function validDate(date) {
      var d;
      if (date === 'None') {
        d = moment().format(); // current date
      } else {
        d = moment(date).format();
      }
      return d;
    }

    return {
      buildHorizontalTimeline: buildHorizontalTimeline,
      buildOutcome: buildOutcome,
      buildVisualization: buildVisualization,
      buildVerticalTimeline: buildVerticalTimeline,
      getEvents: getEvents
    }
  }

  // TODO: Do we need this??
  function Crossfilter() {

    var parseTrends = function (response) {
      var plot_d3_data = _.map(response, function (item) {
        return {key: item.label, values: item.data}
      });

      if (plot_d3_data.length > 1) {
        var timestamps = [];
        _.each(plot_d3_data, function (series) {
          _.each(series.values, function (point) {
            timestamps.push(point[0]);
          })
        });
        timestamps = _.chain(timestamps)
          .uniq()
          .sortBy(function (n) {
            return n;
          })
          .value();

        _.each(plot_d3_data, function (series) {
          var newValues = [];
          _.each(timestamps, function (time) {
            var newPoint = _.find(series.values, function (point) {
              return point[0] == time;
            });
            if (!newPoint) newPoint = [time, 0];
            newValues.push(newPoint);
          });
          series.values = newValues;
        });
      }
      return plot_d3_data;
    };

    var metricByDim = function (metric, dim) {
      return dim.group().reduce(
        function (p, d) {
          p.count++;
          if (metric === 'count') {
            p.metric = p.count;
          } else {
            p.metric = d[metric];
          }
          p.metricName = metric;

          return p;
        },
        function (p, d) {
          p.count--;
          if (metric === 'count') {
            p.metric = p.count;
          } else {
            p.metric = d[metric];
          }
          p.metricName = metric;
          return p;
        },
        function () {
          return {
            metric: 0,
            metricName: metric,
            count: 0
          }
        }
      )
    };

    var buildMetricTimelineInBars = function (id, group, config) {
      var chart = dc.barChart(id);
      chart
        .width(config.width).height(config.height)
        .dimension(config.dim)
        .group(group, function (d) {
          return d.value.metric;
        })
        .gap(10)
        .centerBar(true)
        .elasticY(true)
        .renderTitle(true)
        .title(function (p) {
          return p.value.metricName + ' : ' + p.value.metric;
        })
        .xAxisLabel(config.xAxisLabel)
        .renderHorizontalGridLines(true)
        .x(d3.time.scale().domain(config.xRange))
        .on("preRedraw", function (chart) {
          chart.rescale();
        });

      chart.on("preRender", function (chart) {
        chart.rescale();
      });

      chart.xAxis().tickFormat(function (d) {
        return moment(d).format('DD');
      });

      chart.yAxis().tickFormat(function (d) {
        return d3.round(d);
      });

      // FIXME: duplicated Y axis values
      //chart.yAxis.tickValues([_.min(allYAxisValues), _.max(allYAxisValues)]);

      chart.on('renderlet', function (chart) {
        chart.selectAll('rect.bar').each(function (d, i) {
          if (d.data.value.metricName !== 'effort' && d.data.value.metricName !== 'count') {
            var m = d.data.value.metric;

            if (m >= 8) {
              d3.select(this).attr("fill", "#4AC764");
            } else if (m >= 5 && m < 8) {
              d3.select(this).attr("fill", "#203B73");
            } else if (m >= 3 && m < 5) {
              d3.select(this).attr("fill", "#F8A740");
            } else if (m < 3) {
              d3.select(this).attr("fill", "#EA4F6B");
            } else {
              d3.select(this).attr("fill", "#EA4F6B");
            }

          } else {
            d3.select(this).attr("fill", "#2E69DB");
          }
        });
      });
    };

    var buildTable = function (id, dim, config) {
      var chart = dc.dataTable(id);
      chart
        .dimension(dim)
        .group(function (d) {
          return 'dc.js insists on putting a row here so I remove it using JS';
        })
        .size(config.size)
        .columns(config.columns)
        .sortBy(config.sortBy)
        .order(d3.descending)
        .on('renderlet', function (table) {
          // each time table is rendered remove nasty extra row dc.js insists on adding
          table.select('tr.dc-table-group').remove();
        });
    };

    var buildDonutChart = function (id, dim, group, config) {
      var chart = dc.pieChart(id);
      chart.width(config.width).height(config.height)
        .dimension(dim)
        .group(group)
        .innerRadius(config.innerRadius);
      if (config.colors) {
        chart.ordinalColors(config.colors);
      }
    };

    var buildRowChart = function (id, dim, group, config) {
      var chart = dc.rowChart(id);
      chart.width(config.width).height(config.height)
        .dimension(dim)
        .group(group)
        .ordinalColors(config.colors)
    };

    return {
      parseTrends: parseTrends,
      metricByDim: metricByDim,
      buildMetricTimelineInBars: buildMetricTimelineInBars,
      buildTable: buildTable,
      buildDonutChart: buildDonutChart,
      buildRowChart: buildRowChart
    }
  }

  /* @ngInject */
  function OmniChannel($rootScope, $resource, Customer, Agent) {

    var customers = [];
    var agents = [];

    var OmniChannel = {
      Customer: Customer,
      Agent: Agent
    };

    OmniChannel.ON_CUSTOMERS_FETCHED = 'on_customers_fetched';
    OmniChannel.ON_AGENTS_FETCHED = 'on_agents_fetched';

    OmniChannel.getCustomers = function () {
      return customers;
    };

    OmniChannel.getAgents = function () {
      return agents;
    };

    OmniChannel.searchCustomers = function (params) {
      Customer.fetch({}, params, function (res) {
        var items = res.list;
        customers.length = 0;
        Array.prototype.push.apply(customers, items);
        $rootScope.$broadcast(OmniChannel.ON_CUSTOMERS_FETCHED);
      });
    };

    OmniChannel.searchAgents = function (params) {
      Agent.fetch({}, params, function (res) {
        var items = res.list;
        agents.length = 0;
        Array.prototype.push.apply(agents, items);
        $rootScope.$broadcast(OmniChannel.ON_AGENTS_FETCHED);
      });
    };

    return OmniChannel;
  }

  function Customer($rootScope, $resource) {
    var Customer = $resource('/customer-profiles/json', {}, {
      fetch: {method: 'POST', isArray: false}
    });
    return Customer;
  }


  function Agent($rootScope, $resource) {
    var Agent = $resource('/agent-profiles/json', {}, {
      fetch: {method: 'POST', isArray: false}
    });
    return Agent;
  }


  function CallIntent($rootScope, $resource) {
    return $resource('/call_intents/json');
  }

  function Segment($rootScope, $resource) {
    return $resource('/customer_segments');
  }

  function Industry($rootScope, $resource) {
    return $resource('/customer_industries/json');
  }

  function CustomerEvents($rootScope, $resource) {
    return $resource('/customer_events/json', {}, {
      fetch: {method: 'POST', isArray: false}
    });
  }


})();

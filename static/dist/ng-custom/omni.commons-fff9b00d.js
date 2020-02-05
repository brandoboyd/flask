(function () {
  'use strict';

  var dependencies = [
      'ngSanitize',
      'ngRoute',
      'ui.router',
      'ngResource',
      'ng-drag-scroll',
    
      'slr.components'
  ];
  angular
    .module('omni', dependencies)

    .filter("unwrapAsHtml", function () {
        return function (items) {
            var html = "";
            _(_.unique(items)).each(function (item) {
                html += "- " + item + "<br>";
            });
            return html;
        };
    })

    .filter("countUniqueIndustries", function () {
        return function (industries) {
            return _.unique(industries).length;
        };
    })

    .filter("countUniqueAgents", function () {
        return function (journeys) {
            return _.union.apply(_, _.pluck(journeys, 'agents')).length;
        };
    })

    .filter("countUniqueCustomers", function () {
        return function (journeys) {
            return _.unique(_.pluck(journeys, 'customer_id')).length;
        };
    })

    .value('uiJqConfig', {
        tooltip: {
            animation: false,
            placement: 'bottom',
            container: 'body'
        }
    })

    .controller('InteractionCtrl', ["$scope", "$modalInstance", "events", function ($scope, $modalInstance, events) {
        $scope.events = events.list;

        $scope.close = function () {
            $modalInstance.dismiss('close');
        };
    }])
})();

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
  JourneysTimelineFactory.$inject = ["$http", "$timeout", "MetadataService"];

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
  OmniChannel.$inject = ["$rootScope", "$resource", "Customer", "Agent"];

  function Customer($rootScope, $resource) {
    var Customer = $resource('/customer-profiles/json', {}, {
      fetch: {method: 'POST', isArray: false}
    });
    return Customer;
  }
  Customer.$inject = ["$rootScope", "$resource"];


  function Agent($rootScope, $resource) {
    var Agent = $resource('/agent-profiles/json', {}, {
      fetch: {method: 'POST', isArray: false}
    });
    return Agent;
  }
  Agent.$inject = ["$rootScope", "$resource"];


  function CallIntent($rootScope, $resource) {
    return $resource('/call_intents/json');
  }
  CallIntent.$inject = ["$rootScope", "$resource"];

  function Segment($rootScope, $resource) {
    return $resource('/customer_segments');
  }
  Segment.$inject = ["$rootScope", "$resource"];

  function Industry($rootScope, $resource) {
    return $resource('/customer_industries/json');
  }
  Industry.$inject = ["$rootScope", "$resource"];

  function CustomerEvents($rootScope, $resource) {
    return $resource('/customer_events/json', {}, {
      fetch: {method: 'POST', isArray: false}
    });
  }
  CustomerEvents.$inject = ["$rootScope", "$resource"];


})();

(function () {
  'use strict';

  angular.module('omni')
    .directive('journeyTimeline', journeyTimeline);

  function journeyTimeline($modal, $http) {
    return {
      restrict: 'A',
      scope: {
        journeyTimeline: '@',
        journeyTimelineParams: '@'
      },
      link: function (scope, el) {
        el.bind('click', function () {
          var journey, params;

          try {
            journey = JSON.parse(scope.journeyTimeline); // item from customer/journey
            params = JSON.parse(scope.journeyTimelineParams); // contains journey tags

          } catch (e) {
            console.error(e);
            return;
          }

          $http.post('/customer/journeys', {
              customer_id: params.customer_id,
              from: params.from,
              to: params.to
            })
            .success(function (data) {
              if (data.journeys.length) {
                if (_.has(params, 'assignedTags')) {
                 _.extend(journey, {assignedTags: params.assignedTags});
                }
                if (_.has(params, 'journey_stages')) {
                 _.extend(journey, {journey_stages: params.journey_stages});
                }

                $modal.open({
                  scope: scope.$new(),
                  templateUrl: '/static/assets/js/app/omni/directives/journey-timeline/omni.journey-timeline.html',
                  controller: TimelineController,
                  size: 'lg',
                  windowClass: 'app-modal-window',
                  resolve: {
                    journeys: function () {
                      return data.journeys;
                    },
                    selected: function () {
                      return journey;
                    }
                  }
                });
              }
            });
        });

        function TimelineController($scope, $modalInstance, journeys, selected, JourneysTimelineFactory,
                                           $http, $timeout, $q, $location, $anchorScroll) {
          $scope.flags = resetFlags();

          if (angular.isDefined(selected)) {
            $scope.assignedTags = selected.assignedTags;
          }

          function getJourneys() {
            var deferred = $q.defer();
            var items = {
              customer: {},
              journeys: []
            };

            _.each(journeys, function (journey) {
              $http.get('/journey/' + journey.id + '/stages')
                .success(function (data) {
                  _.extend(data.item.journey, {typeId: journey.typeId});
                  items.customer = data.item.customer;
                  items.journeys.push(data.item.journey);

                  if (items.journeys.length === journeys.length) {
                    deferred.resolve(items);
                  }
                });
            });

            return deferred.promise;
          }

          function getDefaultStageIndex() {
            // get first selected stage in facet list
            var rv = 0;
            if (angular.isDefined(selected.journey_stages)) {
              _.each(selected.journey_stages.list, function (stage) {
                if (stage.enabled) {
                  // selected stage might not be present in the current journey
                  rv = _.findIndex($scope.journey.stages, {stageName: stage.display_name});
                  if (rv > -1) {
                    return true;
                  }
                }
              });
            }
            // journey timeline might contain journeys that do not match the filter criteria at all
            // so in case selected jouney do not contain filtered stage, set first stage as default stage
            if (rv === -1) {
              rv = 0;
            }
            return rv;
          }

          function getStages(index) {
            $scope.journey = $scope.journeys[index];
            $scope.outcome = JourneysTimelineFactory.buildOutcome($scope.journey);

            $timeout(function () {
              var decorator = angular.element('.decoratorStage');
              var arr = decorator.toArray();
              decorator.removeClass('finished-back');
              decorator.removeClass('abandoned-back');
              angular.element(arr[arr.length - 1]).addClass($scope.journey.status + '-back');
            }, 50);

            getEvents(getDefaultStageIndex());

            $timeout(function () {
              /** SCORES VISUALIZATION BUILD */
              if ($scope.journey.NPS !== null && $scope.journey.CSAT !== null) {
                JourneysTimelineFactory.buildVisualization($scope.journey);
              }
            }, 50);
          }

          function getEvents(index) {
            $scope.selectedStage = $scope.journey.stages[index];
            $scope.flags.isEventsFetched = true;
            JourneysTimelineFactory.getEvents(index, $scope.journey, function (res) {
              $scope.stage = res.stage;
              $scope.flags.isEventsFetched = false;
              $scope.verticalTimeline = res.verticalTimeline;
            });
          }
;
          getJourneys().then(function (items) {
            $scope.journeys = _.sortBy(items.journeys, 'startDate');
            $scope.customer = items.customer;
            // $scope.customer_name = $scope.customer.customer_full_name ? $scope.customer.customer_full_name
            //   : $scope.customer.first_name + ' ' + $scope.customer.last_name;
            // $scope.customer = _.omit($scope.customer, ['full_name', 'last_name', 'first_name', 'customer_full_name']);

            $scope.verticalTimeline = [];
            $scope.outcome = '';

            /** Horizontal Timeline - Journeys */
            if ($scope.journeys.length) {
              _.each($scope.journeys, function (journey, index) {
                $scope.journeys[index].startDate = moment(journey.startDate).format('YYYY-MM-DD');
                $scope.journeys[index].endDate = moment(journey.endDate).format('YYYY-MM-DD');
                _.extend(journey, {headline: journey.type});
              });

              var journeyDateRange = {
                startDate: $scope.journeys[0].startDate, // min
                endDate: $scope.journeys[$scope.journeys.length - 1].endDate // max
              };

              $scope.horizontalTimeline = JourneysTimelineFactory.buildHorizontalTimeline($scope.journeys, journeyDateRange);
              $scope.zoomAdjust = $scope.journeys.length - 1;

              if (angular.isDefined(selected)) {
                var found = _.findWhere($scope.journeys, {id: selected.id});
                $scope.startAt = angular.isDefined(found) ? $scope.journeys.indexOf(found) : 0;
                getStages($scope.startAt);
              } else {
                $scope.startAt = 1;
                getStages(0);
              }

            } else {
              $scope.flags.showEmptyMsg = true;
            }
          });

          // show stages
          $scope.showData = function (index) {
            if (index || index === 0) {
              getStages(index);
            } else {
              $scope.flags.showErrMsg = true;
            }
          };

          $scope.showEvents = function (index) {
            if (index || index === 0) {
              getEvents(index);
            } else {
              $scope.flags.showErrMsg = true;
            }
          };

          $scope.showEventContent = function (index) {
            $timeout(function () {
              angular.element('.' + index).slideToggle();
            });
          };

          $scope.getEventAssignedTagId = function (event, index) {
            var found = _.findWhere(event.assignedTags, {index: (index)});
            if (typeof found !== 'undefined') {
              return found.id;
            }
          };

          $scope.navigateToTag = function (id) {
            var found = angular.element('[id*="' + id + '"]');
            found.show();

            var foundId = found.attr('id');

            $location.hash(foundId);
            $anchorScroll();
            angular.element('#' + foundId).addClass('highlighter');
            $timeout(function () {
              angular.element('#' + foundId).removeClass('highlighter');
            }, 500);
          };

          $scope.getNPSIcon = function (event) {
            var nps = event.content[0].reward_data.nps;

            if (nps >= 9) {
              return 'face-happy';
            } else if (7 < nps && nps > 9) {
              return 'face-neutral';
            } else if (nps < 7) {
              return 'face-sad';
            } else {
              return 'face-unknown';
            }
          };

          function resetFlags() {
            return {
              showErrMsg: false,
              showEmptyMsg: false,
              isEventsFetched: false,
              stagesPipeline: true
            }
          }

          $scope.close = function () {
            $modalInstance.dismiss('close');
          };
        }
        TimelineController.$inject = ["$scope", "$modalInstance", "journeys", "selected", "JourneysTimelineFactory", "$http", "$timeout", "$q", "$location", "$anchorScroll"];
      }
    }
  }
  journeyTimeline.$inject = ["$modal", "$http"];
})();
(function () {
  'use strict';
  angular
    .module('omni')
    .directive('omniSmartTag', omniSmartTag)

  function omniSmartTag() {
    return {
      scope: {
        tag           : '=omniSmartTag',
        resolveTagName: '&',
        targetFacet   : '='
      },
      restrict: 'A',
      templateUrl: '/partials/omni/smart-tags-template',
      link: function (scope, element, attrs, ngModel) {
        scope.selected_tags = _.pluck(_.filter(scope.targetFacet, function(i) {return i.enabled == true}), 'id');
        scope.isActive = false;
        scope.$watch('selected_tags', function(nVal, oVal) {
          if(nVal.length > 0) {
            if (_.indexOf(nVal, scope.tag) != -1) {
              scope.isActive = true;
            } else {
              scope.isActive = false;
            }
          }
        })
      }
    };
  }

})();
(function () {
  'use strict';

  angular
    .module('omni.journeys')
    .controller('JourneysPathAnalysisCtrl', JourneysPathAnalysisCtrl);

  /** @ngInject */
  function JourneysPathAnalysisCtrl($scope, $state, $http, $modal, $q, $timeout,
                                    toaster,
                                    JourneyTypesRest,
                                    MetadataService,
                                    PathAnalysisFactory) {
    var _JourneyTypesRest = new JourneyTypesRest();
    var common_path = {label: 'Common Path', measure: 'max', display_name: 'Most Common Path'};
    var configure_settings = [];
    var paths_settings = [];

    var path_settings_cache;

    var debounce = _.debounce(function () {
      if ($scope.loading) return;
      $scope.paths = [];
      $scope.initPage();
    }, 300);

    var off = [];

    var init = function () {
      angular.element('#analysis').hide();
      $scope.loading = false;

      $scope.flags = {
        isEmpty: false,
        isOverview: false,
        settingUp: false
      };

      $scope.selected = [];
      $scope.limit_list = [
        {limit: 3}, {limit: 5}, {limit: 10}, {limit: 20}, {limit: 50}
      ];

      registerShiftToDrillDownMode();

      off.push($scope.$on("ON_JOURNEY_FACETS_UPDATE", debounce));
      $scope.flags.settingUp = true;
    };

    // initialized on Facetting, State switching...
    $scope.initPage = function () {
      if (!$scope.filters.journey_type || $scope.loading) return;
      $scope.topKpaths = 1;
      paths_settings = $scope.filters.journey_type.mcp_settings || [];

      paths_settings = _.filter(paths_settings, function (p) {
        return ['Common Path', 'most_common_path'].indexOf(p.label) < 0;
      });

      var schema = _.filter($scope.filters.journey_type.journey_attributes_schema, function (s) {
        return ['integer', 'double', 'float'].indexOf(s.type) >= 0;
      });

      if (!paths_settings.length) {
        paths_settings = _.map(schema, function (each) {
          return {label: each.label, measure: 'min'};
        });
        updateJourneyType(paths_settings);
      }

      if (path_settings_cache && path_settings_cache.length) {
        paths_settings = path_settings_cache;
      }
      configure_settings = paths_settings.concat(schema);

      setTabs(paths_settings);
    };

    $scope.$on('$stateChangeSuccess',
      function (event, toState) {
        if ($scope.flags.settingUp) return;  // current state has not been set
        path_settings_cache = PathAnalysisFactory.get_path_settings();
        setTabs(path_settings_cache);
      }
    );

    function registerShiftToDrillDownMode() {
      $timeout(function () {
        $scope.analysisMode = true;
        $scope.drillDownMode = false;
      }, 0);

      d3.select('body').on('keydown', function (e) {
        if (d3.event.keyCode == 16) {
          $timeout(function () {
            $scope.analysisMode = false;
            $scope.drillDownMode = true;
          }, 0);
        }
      });

      d3.select('body').on('keyup', function (e) {
        if (d3.event.keyCode == 16) {
          $timeout(function () {
            $scope.analysisMode = true;
            $scope.drillDownMode = false;
          }, 0);
        }
      });
    }

    $scope.drillDown = function (path, index) {
      if (!$scope.drillDownMode) {
        return;
      }
      var params = {
        stagePaths: path.node_sequence_agr.join('&')
      };
      $state.go('journeys.details.mcp', params)
    };

    $scope.getNodeIcon = function (platform) {
      return MetadataService.getEventTypeIcon(platform.toLowerCase());
    };

    $scope.selectPaths = function (path, index) {
      if ($scope.drillDownMode) {
        return $scope.drillDown(path, index);
      }

      // if ($scope.flags.isOverview) return;
      if ($scope.selected.length === 2) {
        disselect();
      }
      var found = _.findWhere($scope.selected, path);
      if (!found) {
        $scope.selected.push(path);

        if ($scope.selected.length === 2 && _.uniq(_.pluck($scope.selected, 'group_by')).length === 2) {
          toaster.pop('error', 'Can not compare 2 paths with different metrics');
          disselect();
          return;
        }

        $scope.paths[index].selected = true;
      } else {
        disselect();
      }
    };

    function disselect() {
      $scope.selected = [];
      _.each($scope.paths, function (p) {
        p.selected = false;
      });
      angular.element('#analysis').hide();
    }

    $scope.configure = function () {
      var modalScope = $scope.$new();
      var _paths_labels = _.uniq(_.pluck(configure_settings, 'label'));

      modalScope.mcp_settings = _.map(_paths_labels, function (path_label) {
        var founds = _.where(configure_settings, {label: path_label});
        return _.extend({label: path_label}, {
          maxselected: angular.isDefined(_.findWhere(founds, {measure: 'max'})),
          minselected: angular.isDefined(_.findWhere(founds, {measure: 'min'}))
        });
      });

      $modal.open({
        scope: modalScope,
        templateUrl: '/omni/partials/journeys/mcp_settings'
      }).result
        .then(function (settings) {
          var selected_settings = [];
          var edited_configure_settings = [];

          _.each(_paths_labels, function (label) {
            var found = _.find(settings, {label: label});
            var _measures = [];
            if (found.maxselected) {
              _measures.push('max');
            }
            if (found.minselected) {
              _measures.push('min');
            }

            if (!found.minselected && !found.maxselected) {
              edited_configure_settings.push({label: label, measure: ''});
            }

            _.each(_measures, function (m) {
              edited_configure_settings.push({label: label, measure: m});
              selected_settings.push({label: label, measure: m});
            });
          });

          var jt_mcp_settings = _.without(selected_settings, common_path);
          updateJourneyType(jt_mcp_settings);

          configure_settings = edited_configure_settings;
          PathAnalysisFactory.set_path_settings(jt_mcp_settings);
          setTabs(jt_mcp_settings);
        });
    };

    $scope.selectTab = function (tab) {
      _.each($scope.subtabs, function (each) {
        each.active = false;
        if (tab.label === each.label) {
          each.active = true;
          tab.active = true;
        }
      });
      $scope.selectedTab = tab;
      $scope.flags.isOverview = (tab.label === 'Overview');
      $scope.selectK();
    };

    $scope.selectK = function (k) {
      var _settings = paths_settings;

      if ($scope.selectedTab.label !== 'Overview') {
        $scope.topKpaths = k || 5;
        _settings = [_.pick($scope.selectedTab, 'label', 'measure')];
        $scope.flags.isOverview = false;
      } else {
        $scope.topKpaths = 1;
        $scope.flags.isOverview = true;
      }

      getPaths(_settings);
    };

    function setTabs(list) {
      $scope.topKpaths = 1;
      var selectedTab = _.find($scope.subtabs, {active: true});
      paths_settings = list;

      $scope.subtabs = [{label: 'Overview', active: _.isUndefined(selectedTab)}];

      $scope.subtabs = $scope.subtabs.concat(_.map(list, function (p) {
        var active = (angular.isDefined(selectedTab) && selectedTab.label === p.label);
        return _.extend(p, {active: active, measure: p.measure});
      }));
      $scope.subtabs.push(common_path);

      var toSelect = selectedTab ? selectedTab : $scope.subtabs[0];
      $scope.selectTab(toSelect);
    }

    function updateJourneyType(settings) {
      var params = $scope.getJourneySearchParams();
      params.id = $scope.filters.journey_type.id;
      _.extend(params, {mcp_settings: settings});

      _JourneyTypesRest.save(params).success(function () {
        getPaths(settings);
      });
    }

    function getPaths(settings) {
      if ($scope.loading) return;
      $scope.loading = true;

      var promises = [];
      var params = $scope.getJourneySearchParams();
      $scope.paths = [];

      _.each(settings, function (each) {
        var params_copy = _.clone(params);
        _.extend(params_copy, {
          path: each,
          limit: $scope.topKpaths
        });
        promises.push($http.post('/journeys/mcp', params_copy));
      });

      $q.all(promises)
        .then(function (res) {
          var responses = _.map(res, function (r) {
            return r.data.paths.data;
          });

          $scope.paths = _.chain(_.flatten(responses))
            .map(function (each) {
              return _.extend(each, {selected: false})
            })
            .value();

          if (!$scope.paths.length) {
            $scope.loading = false;
            return;
          }

          if ($scope.selectedTab.label === 'Overview') {
            $scope.paths = _.sortBy($scope.paths, function (each) {
              return each.metrics.percentage.value;
            }).reverse();
          } else if ($scope.selectedTab.label === 'Common Path') {
            // need to verify that results are sorted - because they do not come in right queue from server
            $scope.paths = _.sortBy($scope.paths, function (each) {
              return each.metrics.percentage.value;
            });
            if ($scope.selectedTab.measure === 'max') {
              $scope.paths = $scope.paths.reverse();
            }
          } else {
            var group_by = $scope.paths[0].group_by;
            $scope.paths = _.sortBy($scope.paths, function (each) {
              return each.metrics[group_by].value;
            });
            if ($scope.selectedTab.measure === 'max') {
              $scope.paths = $scope.paths.reverse();
            }
          }

          $scope.loading = false;
          $scope.flags.settingUp = false;
        });
    }

    $scope.getGridNumber = function (stagesLength) {
      if (stagesLength === 0) return;
      var n = 12 / stagesLength;
      if (n >= 1 && n <= 3) {
        n = 2;
      }
      return n;
    };

    off.push($scope.$watch('selected', function (n) {
      if (!n) return;
      if (n.length === 2) {
        $scope.$emit("OnPathsSelected", n);
      }
    }, true));

    var destructor = function () {
      off.forEach(function (unbind) {
        unbind();
      });
      off = null;
    };

    init();
    off.push($scope.$on('$destroy', destructor));
  }
})();

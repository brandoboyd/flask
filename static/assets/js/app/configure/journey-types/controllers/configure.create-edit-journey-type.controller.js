(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateEditJourneyTypeCtrl', CreateEditJourneyTypeCtrl);

  /** @ngInject */
  function CreateEditJourneyTypeCtrl($location,
                                     $timeout,
                                     $modal,
                                     $q,
                                     $routeParams,
                                     $scope,
                                     SystemAlert,
                                     MetadataService,
                                     JourneyFacetConfig,
                                     JourneyTypesRest) {
    var JourneyTypes = new JourneyTypesRest();
    var id = $routeParams.id;
    var stage = {
      // filtering and table settings
      filters: {
        title: null
      },
      table: {
        sort: {
          predicate: 'display_name',
          reverse: false
        }
      },
      "create": function () {
        $location.path('/journey_types/edit/' + id + '/stage/');
      },
      "editPath": function (stage) {
        return '#/journey_types/edit/' + id + '/stage/' + stage.id;
      }
    };
    stage.filterPredicate = JourneyFacetConfig.makeFilter($scope);

    $scope.selectedStages = [];
    $scope.selectStage = function (selected) {
      var found = _.find($scope.selectedStages, {id: selected.id});

      if (found) {
        _.remove($scope.selectedStages, selected)
      } else {
        $scope.selectedStages.push(selected)
      }
    };

    var journeyTypeCrud = _.extend({}, {
      "save": function () {
        _.each($scope.item.journey_attributes_schema, function (each) {
          _.extend(each, {name: each.label});  // TODO: for time being, we use label as origin name
        });

        var promises = [];
        _.each($scope.stage.items, function(stage) {
          promises.push( $scope.saveStage(null, stage));
        });

        $q.all(promises)
          .then(function() {
            return JourneyTypes.save($scope.item).success(function (res) {
              SystemAlert.success('Journey type was saved', 5000);
              if(res.data && res.data.id) {
                $location.path('/journey_types/edit/' + res.data.id);
              } else {
                $scope.journeyTypeForm.$setPristine();
                $scope.redirectAll();
              }
            });
          });
      },
      "remove": function () {
        _.each($scope.selected, function(item) {
          JourneyTypes.remove(item.id).success(function() {
            _.remove($scope.items, item);
          })
        });
      }
    });

    _.extend($scope,
      {
        "saveStage": function (event, stage) {
          console.log("SAVING A STAGE...", stage);
          try {
            var eventTypesIds = _.pluck(stage.event_types, 'id');
            var stageToSave = _.extend({}, stage);
            stageToSave['event_types'] = eventTypesIds;
          } catch(e) {
            SystemAlert.error('Error while saving the stage ' + e, 5000);
            return;
          }

          var params = {
            data: stageToSave,
            id: $scope.item.id
          };

          if (stage && stage.id) {
            _.extend(params, {stageId: stage.id});
          }
          return JourneyTypes.saveStage(params)
            .success(function () {
              console.log('Stage ' + stage.display_name + ' was saved');
            })
            .error(function (data, status) {
              SystemAlert.error('Error while saving the stage ' + status, 2000);
            });
        }
      }
    );
    _.extend(stage, {
      "removeStage": function (event, stage, index) {
        console.log("removing stage", stage);
        if("id" in stage) {
          //The stage was persisted and needs to be removed from the backend
          JourneyTypes.removeStage(id, stage.id).success(function () {
            loadJourneyStages();
            SystemAlert.success('Journey Stage "' + stage.display_name + '" removed', 3000);
          });
        } else {
          //stage has no id, it exists only in UI until saved
          event.preventDefault();
          $scope.stage.items.splice(index, 1);
        }
      }
    });

    function loadJourneyType() {
      JourneyTypes.getOne(id).success(function(res) {
        $scope.item = res.data;
        $scope.availableFields = $scope.item.expression_context.context;
      });
    }



    _.extend($scope,
      {stage: stage},
      journeyTypeCrud,
      {
        redirectAll: function () {
          $location.path('/journey_types/')
        },
        load: function (id) {
          if (id) {
            return $q.all([loadOptions(), loadEventTypes(), loadJourneyType(), loadJourneyStages()]);
          }

        }
      }
    );

    $scope.title = id ? 'Update' : 'Create';


    function loadOptions() {
      JourneyFacetConfig.getOptions(function (opts) {
        $scope.options = {stageStatuses: opts.journey_type.stageStatuses};
      });
    }

    function loadEventTypes() {
      JourneyFacetConfig.getEventTypes(function (opts) {
        $scope.options = _.extend($scope.options, {eventTypes: opts.eventTypes});
      });
    }

    function loadJourneyStages() {
      JourneyTypes.getStages(id).success(function(res) {
        console.log("GET JOURNEY STAGES", res);
        var items = res.data;
        var evTypes = $scope.options.eventTypes;

        _.each(items, function(el) {
          _.each(el.event_types, function(ev, idx) {
            var t = _.filter(evTypes, function(tt) {
              return tt.id == ev
            });
            if(t.length > 0) {
              el.event_types[idx] = t[0];
            }

          })
        });
        $scope.stage.items = items;
      })
    }

    $scope.fieldTypes = MetadataService.getSchemaFieldTypes();

    $scope.onAddFeature    = onAddFeature;
    $scope.onAddStage      = onAddStage;
    $scope.onRemoveFeature = onRemoveFeature;
    $scope.searchExpressions = searchExpressions;

    //$scope.availableEvents = ['Tweet', 'Comment', 'Score'];


    function onRemoveFeature(evt, collection, index) {
      evt.preventDefault();
      collection.splice(index, 1);
    }

    function onAddFeature(evt, type) {
      evt.preventDefault();
      $scope.item[type].push({
        label: '',
        type: '',
        field_expr: ''
      });
    }


    function onAddStage(evt, type) {
      evt.preventDefault();
      $scope.stage.items.push({
        label: '',
        type: '',
        field_expr: ''
      });
    }

    //MENTIO
    $scope.getTextRaw = function(item) {
      return item;
    };

    function searchSuggestions(term, suggestionsList, searchResultsList) {
      _.each(suggestionsList, function(item) {
        if (item.toUpperCase().indexOf(term.toUpperCase()) >= 0) {
          searchResultsList.push(item);
        }
      });
      return searchResultsList;
    }

    function searchExpressions(term) {
      var list = [];
      $scope._availableFields = searchSuggestions(term, $scope.availableFields, list);
    }

    var openEventTypeModal = function (data) {
      var d = $modal.open({
        backdrop: true,
        keyboard: true,
        templateUrl: '/partials/journey/type/event_type_modal',
        controller: function ($scope) {
          $scope.data = data;
          $scope.close = $scope.$close;
        }
      });
    };

    $scope.showEventTypeModal = function (item) {
      openEventTypeModal(item);
    };

    $scope.load(id);
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('NewPredictorV2Ctrl', NewPredictorV2Ctrl)
    .directive('animateOnChange', function($animate,$timeout) {
    return function(scope, elem, attr) {
      scope.$watch(attr.animateOnChange, function(nv,ov) {
        //if (nv!=ov) {
          var c = 'change-up';

          if(elem.hasClass(c)) {
            $animate.removeClass(elem, c);
          } else {
            $animate.addClass(elem, c);
          }


        //}
      })
    }
  });

  /** @ngInject */
  function NewPredictorV2Ctrl($scope, $routeParams, $q, $timeout, $location, toaster, DatasetsRest, PredictorsRest, MetadataService) {

    var _DatasetsRest = new DatasetsRest();
    var _PredictorsRest = new PredictorsRest();

    $scope.predictorId = null;
    $scope.datasets = [];
    $scope.selectedDataset = null;
    $scope.predictor = null;
    $scope.availableFields = [];
    $scope.metricFields = []; //metric fields should contain only integers and booleans - PRR-296
    $scope.actionIDFields = [];
    $scope.featureLabelFields = [];
    $scope.hasError = false;
    $scope.action_types = [{k:'agents', l:'Agents'}, {k:'dataset_generated',l:'Dataset generated'}];


    $scope.flags = {
      generating: false
    };

    $scope.fieldTypes = MetadataService.getSchemaFieldTypes();
    $scope.featureTypes = [
      { key: 'action_features_schema', text: 'Action Features', tooltip: 'Attributes of the target action (e.g. agent profile). Using action attributes allows for generalization across per action data sets.' },
      { key: 'context_features_schema', text: 'Context Features', tooltip: 'Attributes of the customer and/or interaction context.' }
    ];
    var metricFieldTypes = ['boolean', 'integer'];

    $scope.onSelectDataset = onSelectDataset;
    $scope.onSave = onSavePredictor;
    $scope.onAddFeature = onAddFeature;
    $scope.onRemoveFeature = onRemoveFeature;
    $scope.onClickPurge = onPurgeData;
    $scope.onClickGenerate = onGenerateData;
    $scope.onFeatureLabelInput = onFeatureLabelInput;
    $scope.generateAvailableFields = generateAvailableFields;
    $scope.searchExpressions = searchExpressions;

    var searchSuggestions = function(term, suggestionsList, searchResultsList) {
      _.each(suggestionsList, function(item) {
        if (item.toUpperCase().indexOf(term.toUpperCase()) >= 0) {
          searchResultsList.push(item);
        }
      });
      return searchResultsList;
    };

    $scope.getTextRaw = function(item) {
      return item;
    };

    activateController();

    function searchExpressions(term) {
      var list = [];
      $scope._availableFields = searchSuggestions(term, $scope.availableFields, list);
    }

    function onGenerateData(evt) {
      $scope.flags.generating = true;
        _PredictorsRest.generatePredictorData($scope.predictorId, $scope.predictor.from_dt, $scope.predictor.to_dt).success(function(result) {
            console.log(result);
            toaster.pop('info', result['message']);
            $scope.predictor.status = result['status'];
            $timeout(checkStatus, 2000);
          }).catch(function(err) {
            console.log(err);
          });
      }

    function checkStatus() {
        _PredictorsRest.checkGenerationStatus($scope.predictorId, $scope.predictor.from_dt, $scope.predictor.to_dt).success(function(result) {
            console.log(result);
            if (result['status'] == 'GENERATING DATA') {
                $timeout(checkStatus, 2000);
            } else {
                if (result['status'] == 'IN ERROR') {
                    toaster.pop('error', result['message']);
                } else {
                    toaster.pop('info', result['message'])
                }
                $scope.flags.generating = false;
            }
            $scope.predictor.status = result['status'];
          }).catch(function(err) {
            console.log(err);
          });
    }

    function onPurgeData(evt) {
        _PredictorsRest.purgePredictorData($scope.predictorId).success(function(result) {
            toaster.pop('info', result['message']);
            $scope.predictor.status = result['status'];
          }).catch(function(err) {
            console.log(err);
          });
    }

    function onSelectDataset(notFromUI) {
      $scope.selectedDataset = _.find($scope.datasets, { id: $scope.predictor.dataset });

      if (!$scope.selectedDataset) { return }

      $scope.availableFields = _.pluck($scope.selectedDataset.schema, 'name');
      generateAvailableFields();

      _DatasetsRest.getDistributionData($scope.selectedDataset.name)
        .then(function(data) {
          angular.extend($scope.selectedDataset, data);

          // reset predictor settings only when dataset is selected from UI
          // preserve predictor settings if it's called after loading list of datasets
          if (!notFromUI) {
            angular.extend($scope.predictor, {
              metric: null,
              action_id_expression: null,
              action_features_schema: [],
              context_features_schema: [],
            });
            
            angular.extend(
              $scope.predictor,
              _.pick($scope.selectedDataset, ['sync_status', 'from_dt', 'to_dt'])
            );
          }

          // Redraw date range section
          drawDateRange();
        });
    }

    function drawDateRange() {
      var chart;
      var data = $scope.selectedDataset.distribution;

      if (!data) { return }

      // d3.select('#daterange-filter svg').selectAll('*').remove();
      nv.addGraph({
          generate: drawGraph,
          callback: callback
      });

      function drawGraph() {
        var chart = nv.models.linePlusBarChart()
          .duration(0)
          .x(function(d) { return d[0] })
          .y(function(d) { return d[1] })
          .margin({right: 50})
          .showLegend(false)
          .focusHeight(100);

        // Focus View Finder
        chart.x2Axis.tickFormat((function(d) {
          return d3.time.format('%b %d')(new Date(d * 1000));
          //return;
        }));

        d3.select('#daterange-filter svg').selectAll('text').remove();
        d3.select('#daterange-filter svg').selectAll('*').remove();

        d3.select('#daterange-filter svg')
          .datum(data)
          .call(chart);

        //listen form mousedown events on brush container to be able to disable changing brushes
        d3.select('#daterange-filter svg .nv-x.nv-brush')
          .on("mousedown", mousedowned);

        nv.utils.windowResize(chart.update);
        chart.dispatch.on('stateChange', function(e) { nv.log('New State:', JSON.stringify(e)); });

        return chart;
      }


      function mousedowned() {
        //disable changing the date-range if predictor's generated data is in sync
        if($scope.predictor && $scope.predictor.status === 'IN SYNC') {
          d3.event.stopImmediatePropagation();
        }
      }

      function callback(chart) {
        var values = data[0].values;

        // Show view finder with full range by default
        var len = values.length;
        var start = values[0][0];
        var end = values[len - 1][0];

        if ($scope.predictorId === null) {
          chart.brushExtent([start, end]).update();
        } else {
          chart.brushExtent([$scope.predictor.from_dt, $scope.predictor.to_dt]).update();
        }

        var debouncedBrushUpdate =  brushUpdate; //_.debounce(brushUpdate, 100);

        function brushUpdate(data) {
          var from = parseInt(data.extent[0]);
          var to = parseInt(data.extent[1]);

          $timeout(function() {
            $scope.predictor.from_dt = from;
            $scope.predictor.to_dt = to;
          });
          /*
          // range variable doesn't get updated well on the view, need manual change
          $scope.hidePredictorDateRange = true;
          $timeout(function() {
            $scope.hidePredictorDateRange = false;
          }, 10);
          */
        }
        chart.dispatch.on('brush', debouncedBrushUpdate);
      }
    }

    function onSavePredictor() {
      // Validate predictor
      if ($scope.predictor.context_features_schema.length < 1) {
        toaster.pop('error', 'Must have at least one context feature.');
        $scope.hasError = true;
        return;
      }

      var hasMissingExpr =
        _.some($scope.predictor.action_features_schema, function (feature) {
          return (!feature.type || (feature.type && !feature.field_expr));
        })
      hasMissingExpr = hasMissingExpr ||
        _.some($scope.predictor.context_features_schema, function (feature) {
          return (!feature.type || (feature.type && !feature.field_expr));
        });

      if (hasMissingExpr) {
        toaster.pop('error', 'Some features have missing type or expression.');
        $scope.hasError = true;
        return;
      }

      $scope.hasError = false;

      var saveFn;
      if ($scope.predictorId) {
        saveFn = _PredictorsRest.update($scope.predictorId, $scope.predictor);
      } else {
        saveFn = _PredictorsRest.create($scope.predictor);
      }

      saveFn.success(function(res) {
        toaster.pop('info', 'Saved successfully!');

        if (res.obj) {
          $scope.predictorId = res['obj']['id'];
          $scope.predictor = res['obj'];
        } else {
          $scope.predictorId = res.predictor.id;
          $scope.predictor = res.predictor;
        }



        //if the predictor is new - redirect to predictors' list
        if(!$scope.predictorId) {
          $location.path('/predictors');
        }

      }).catch(function(err) {
        console.log(err);
        // toaster.pop('error', 'Failed to save!');
      })
    }

    function onAddFeature(evt, type) {
      evt.preventDefault();

      $scope.predictor[type].push({
        label: '',
        type: '',
        field_expr: '',
      });

      // Automatically open the label selector which saves a click.
      $timeout(function() {
        var count = $scope.predictor[type].length;
        var elementClass = '.' + type + '-' + (count - 1) + ' a';
        angular.element(elementClass).click();
      });
    }

    function onRemoveFeature(evt, type, index) {
      evt.preventDefault();

      $scope.predictor[type].splice(index, 1);

      generateAvailableFields();
    }

    function getFieldTypeByName(fieldName) {
      var schemaItem = _.find($scope.selectedDataset.schema, { name: fieldName });
      return (schemaItem) ? schemaItem.type : 'string';
    }

    function onFeatureLabelInput(featureType, index) {
      // Pre-populate `type` and `field/expression` fields
      // if a label is selected from the predictor's schema fields
      var featureSchema = $scope.predictor[featureType];
      if ($scope.availableFields.indexOf(featureSchema[index].label) >= 0) {
        featureSchema[index].type = getFieldTypeByName(featureSchema[index].label);
        // featureSchema[index].type = 'label';
        featureSchema[index].field_expr = featureSchema[index].label;
        generateAvailableFields();
        delete featureSchema[index].is_expression;
      } else {
        featureSchema[index].type = '';
        featureSchema[index].is_expression = true;
      }
    }

    function generateAvailableFields() {
      var predictor = $scope.predictor || {};

      $scope.metricFields = _.pluck(
        _.filter($scope.selectedDataset.schema, function(item) {
          return ( metricFieldTypes.indexOf(item.type) !== -1 )
            && ( item.name !== predictor['action_id_expression'] )
        }),'name');

      $scope.actionIDFields = _.filter($scope.availableFields, function(field) {
        return field !== predictor['metric'];
      });

      $scope.featureLabelFields = _.filter($scope.availableFields, function(field) {
        var alreadyUsed = false;
        _.each($scope.featureTypes, function(type) {
          _.each($scope.predictor[type.key], function (feature) {
            if (alreadyUsed) {
              return;
            }
            if (!feature.is_expression && feature.field_expr === field) {
              alreadyUsed = true;
            }
          });
        });
        return alreadyUsed === false;
      });
    }

    function loadPredictor() {
      if ($routeParams.new_or_id === 'new') {
        $scope.predictor = {
          name: "",
          dataset: null,
          metric: null,
          action_id_expression: null,
          action_features_schema: [],
          context_features_schema: [],
        };
        return $q.when();
      } else {
        $scope.predictorId = $routeParams.new_or_id;
        return _PredictorsRest.getOne($scope.predictorId)
          .then(function(res) {
            $scope.predictor = res.data.predictor;
          });
      }
    }

    function loadDatasets() {
      return _DatasetsRest.list()
       .success(function(res) {
         $scope.datasets = _.filter(res.data, { 'sync_status': 'IN_SYNC' });
         onSelectDataset(true);
       });
    }

    function activateController() {
      loadPredictor()
        .then(loadDatasets)
    }
  }
})();

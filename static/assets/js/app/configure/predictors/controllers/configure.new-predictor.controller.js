(function () {
  'use strict';

  angular
    .module('slr.configure')
    .filter('removeSpaces', [function() {
      return function(string) {
        if (!angular.isString(string)) {
          return string;
        }
        return string.replace(/[\s]/g, '');
      };
    }])
    .controller('NewPredictorCtrl', NewPredictorCtrl);

  /** @ngInject */
  function NewPredictorCtrl($scope, $http, $location, $routeParams, $q, PredictorService, AccountsService, FilterService) {

    $scope.validation = {};
    $scope.usedCollections = [];
    $scope.currentDate = FilterService.getSelectedDateRangeName();

    //Predictors suggestion
    // var _getPredictorsFeatures = function() {
    //   $scope.account = AccountsService.getCurrent();
    //   $http.get("/account/predictor-configuration/" + $scope.account.id)
    //     .success(function (response) {
    //       $scope.schemaList = response.data;
    //     })
    //     .error(function (data) {
    //       //toaster.pop('error', data);
    //     });
    // };

    var action_url;

    (function checkCreateOrUpdate() {
      if ($routeParams.new_or_id === 'new') {
        $scope.is_new_predictor = true;
        action_url = '/predictors/json';
      } else {
        $scope.is_new_predictor = false;
        action_url = '/predictors/' + $routeParams.new_or_id;
      }
    })();

    var getMetadata = function(params) {
      return $http.post( "/predictors/expressions/metadata", params);
    };

    var searchSuggestions = function(term, suggestionsList, searchResultsList) {
      angular.forEach(suggestionsList, function(item) {
        if (item.name.toUpperCase().indexOf(term.toUpperCase()) >= 0) {
          searchResultsList.push(item);
        }
      });
      return searchResultsList;
    };

    var initMetaData = function() {

      $scope.collections = [];
      $scope.fields      = [];

      $scope.operators = [
        {"name" : "union()"},
        {"name" : "collect()"}
      ];

      var collectionsParams = {
        "expression_type" : "feedback_model"
      };

      var operatorsParams = {
        "expression_type" : "action_id"
      };

      //COLLECTIONS
      getMetadata(collectionsParams).then(function(res) {
        $scope.collections = _.map(res.data.metadata, function (item) {
          return {"name": item}
        });
      });

      //OPERATORS
      getMetadata(operatorsParams).then(function(res) {
        var ops = _.map(res.data.metadata, function (item) {
          return {"name": item + "()"}
        });
        Array.prototype.push.apply($scope.operators, ops);
      });
    }();

    $scope.validateExpression = function(expr, model) {
      if (!_.isEmpty(expr) || !_.isUndefined(expr) ) {
        $http.post('/predictors/expressions/validate', {
          "expression" : expr
        }).success(function(res) {
          $scope.validation[model] = { error : false }
        }).error(function onError(res) {
          $scope.validation[model] = { error : true, msg: res.error}
        })
      }
    }

    $scope.getCollectionsTextRaw = function(item) {
        $scope.usedCollections.push(item.name);
        return item.name
    };

    $scope.getSuggestionTextRaw = function(item) {
      return item.name;
    };

    $scope.$watch("usedCollections.length", function(nVal) {
      //FIELDS
      var fieldsParams = {
        "collections" : $scope.usedCollections,
        "expression_type": "reward",
        "suggestion_type":  "fields"
      };
      if(nVal > 0) {
        getMetadata(fieldsParams).then(function(res) {
          $scope.fields = [];
          var metadata = res.data.metadata;
          _.each(metadata, function(data) {
            var col =  _.sortBy(_.map(data.fields, function (item) {
              return {"name": item, "collection" : data.collection}
            }), 'name');
            Array.prototype.push.apply($scope.fields, col);
          });//each
        });
      }
    });

    $scope.searchOperators = function(term) {
      var operatorsList = [];
      $scope._operators = searchSuggestions(term, $scope.operators, operatorsList);
    };

    $scope.searchCollections = function(term) {
      var collectionsList = [];
      angular.forEach($scope.collections, function(item) {
        if (item.name.toUpperCase().indexOf(term.toUpperCase()) >= 0) {
          collectionsList.push(item);
        }
      });
      $scope._collections = collectionsList;
      return collectionsList;
    };

    $scope.searchFields = function(term) {
      var fieldsList = [];
      angular.forEach($scope.fields, function(item) {
        if (item.name.toUpperCase().indexOf(term.toUpperCase()) >= 0) {
          fieldsList.push(item);
        }
      });
      $scope._fields = fieldsList;
      return fieldsList;
    };

    $scope.searchPredictors = function(term) {
      var predictorsList = [];
      angular.forEach($scope.compositePredictors, function(item) {
        if (item.name.toUpperCase().indexOf(term.toUpperCase()) >= 0) {
          predictorsList.push(item);
        }
      });

      $scope._predictors = predictorsList;
      return predictorsList;
    };

    // $scope.getFieldsTextRaw = function(item) {
    //   return item.name;
    // };

    $scope.getPredictorTextRaw = function(item) {
      return item.name;
    };

    $scope.getExpression = function(expr) {
      if (expr) {
        return expr.split(' ').join('');
      }
    };

    (function loadDefaultTemplate () {
      $http({
        method: 'GET',
        url: '/predictors/default-template'
      }).then(function (res) {
        $scope.template = res.data.template;

        /* TODO: extend predictor types for now, should be done on the server */
        $scope.template['Composite Predictor'] = {
          predictor_type: 'Composite Predictor',
          description: '',
          rewards: $scope.template['Agent Matching'].rewards //just copy rewards from other predictor
        };
        $scope.template.types.push('Composite Predictor');

        $scope.$watch('predictor.raw_expression', function(expr) {
          if (expr) {
            $scope.predictor.raw_expression = expr.split(' ').join('');
          }
        });

        if ($location.search() && !_.isEmpty($location.search()['ids'])) {
          PredictorService.getSelectedPredictors($location.search()['ids']).then(function (predictors) {
            $scope.compositePredictors = predictors;
            $scope.predictor = {
              predictor_type: 'Composite Predictor',
              name: "",
              reward: null,
              description: null,
              raw_expression : "",
              predictors_list : _.pluck(predictors, "id")
            };
            listSimplePredictors();
          })
        }
      });
    })();

    (function initializePredictorModel () {
      if ($scope.is_new_predictor) {
        $scope.predictor = {
          predictor_type: null,
          name: "",
          reward: null,
          description: "",
          context_features: [],
          action_features: []
        };
      } else {
        $http.get(action_url).then(function (res) {
          $scope.predictor = res.data.predictor;
          $scope.predictor.predictor_type ='Composite Predictor'

          if (!_.isEmpty($scope.predictor.predictors_list)) {
            var ids = $scope.predictor.predictors_list;

            PredictorService.getSelectedPredictors(ids).then(function (predictors) {
              $scope.compositePredictors = predictors;

              listSimplePredictors();
            })
          }
        });
      }
    })();

    $scope.setForm = function (form) {
      $scope.PredictorsForm = form;
    };

    $scope.shouldShow = function (option) {
      return option !== 'Composite Predictor' && !_.has($scope.predictor, 'predictors_list') ||
        option === 'Composite Predictor' && _.has($scope.predictor, 'predictors_list');
    }

    $scope.deletePredictorFromComposite = function (predictor) {
      $scope.compositePredictors = _.filter($scope.compositePredictors, function (pr) {
        return pr.id !== predictor.id;
        });
        $scope.predictor.predictors_list = _.pluck($scope.compositePredictors, "id");
        $scope.predictor.raw_expression = "";
        listSimplePredictors();
    };

    $scope.addPredictor = function (id) {
      PredictorService.getSelectedPredictors([id]).then(function (predictor) {
        var pr = predictor[0];
        //simple predictors the complex one comprised of
        $scope.compositePredictors.push(pr);

        $scope.predictor.predictors_list.push(pr.id);
        listSimplePredictors();
      })
    };

    $scope.save = function () {
      $scope.currentDate = FilterService.getSelectedDateRangeName();
      var selectedPeriod = FilterService.getDateRangeObj();
      $scope.predictor.from_dt = moment(selectedPeriod.from).unix();
      $scope.predictor.to_dt = moment(selectedPeriod.to).unix();

      $http({
        method: 'POST',
        url: action_url,
        data: $scope.predictor
      }).then(function (res) {
        $location.path('/predictors');
      });
    };

    if ($scope.is_new_predictor) {
      $scope.$watch('predictor.predictor_type', function (newVal) {
        if (!newVal)
          return;

        var selected_predictor_type = $scope.predictor.predictor_type;
        $scope.predictor.description = $scope.template[selected_predictor_type].description;
        $scope.predictor.context_features = $scope.template[selected_predictor_type].all_context_features;
        $scope.predictor.action_features = $scope.template[selected_predictor_type].all_action_features;
      });
    }

    function listSimplePredictors () {
      PredictorService.listAllPredictors().then(function (res) {
        var existingPredictorsIds = _.pluck($scope.compositePredictors, 'id');
        $scope.simplePredictors = _.filter(res, function (pr) {
          //return simple predictors only which are not yet included in this composite predictor
          return pr.predictor_type !== 'Composite Predictor' &&
            _.indexOf(existingPredictorsIds, pr.id) === -1;
        });
      })
    }

  }
})();

angular.module('test', [
  'ark-ui-bootstrap', 'ui.select2', 'ngResource', 'ngRoute', 'ngSanitize', 'slr.components']);


angular.module('test').config(function($routeProvider) {
  $routeProvider.
    when('/new_agent', {
      templateUrl:'/partials/agents/create_agent',
      controller:'AgentCtrl',
      name: 'new_agent' }).
    when('/list_agents', {
      templateUrl:'/partials/agents/agents',
      controller:'ListAgentsCtrl',
      name: 'list_agents' }).
    when('/new_segment', {
      templateUrl:'/partials/agents/create_segment',
      controller:'SegmentCtrl',
      name: 'new_segment' }).
    when('/list_segments', {
      templateUrl:'/partials/agents/segments',
      controller:'ListSegmentsCtrl',
      name: 'list_segments' }).
    when('/new_customer', {
      templateUrl:'/partials/agents/create_customer',
      controller:'CustomerCtrl',
      name: 'new_customer' }).
    when('/list_customers', {
      templateUrl:'/partials/agents/customers',
      controller:'ListCustomersCtrl',
      name: 'list_customers' }).

    otherwise({redirectTo:'/list_agents'});
});

angular.module('test').controller('NavCtrl', function($scope, $rootScope, $route, $http) {
  $rootScope.$on('$viewContentLoaded', function(e) {
    $scope.current = $route.current.name;
  });
  $scope.getCurrent = function(name) {
    return $scope.current && $scope.current.indexOf(name) == 0 ? 'active' : '';
  }

  /* Channels Selector */
  $rootScope.channels = [];
  $rootScope.channel = null;
  $rootScope.channel_id = undefined;


  var Channels = {};
  Channels.load = function() {
    var promise = $http({
      method : 'POST',
      url    : '/channels_by_type/json',
      data : {
        type          : ['inbound', 'outbound'],
        serviced_only : false,
        parent_names  : true }
    }).then(function (res) {
      return _.filter(res.data.list, function(el) {
        return el.parent_id == null && el.is_compound == false ||
          el.parent_id != null && el.type == 'inbound' })
    });
    return promise;
  };

  Channels.load().then(function(channels) {
    $rootScope.channels = channels;
    $rootScope.channel =  channels[0];
  });

  $rootScope.$watch('channel', function(newVal, oldVal) {
    //console.log($scope.channel);
    if (newVal != oldVal) {
      $rootScope.channel_id = $rootScope.channel ? $rootScope.channel.id : null;
    } else {
      $rootScope.channel_id = null;
    }
  });

});


angular.module('test')
  .controller('CustomerCtrl', function($rootScope, $scope, $resource, $http) {
    $scope.customer = {
      channel    : $rootScope.channel_id,
      first_name : null,
      last_name  : null,
      age        : null,
      location   : null,
      num_calls  : null,
      call_intent: null,
      account_balance: null,
      sex        : null,
      seniority  : null
    };

    $scope.options = {
      intent : []
    }
    console.log($scope.customer);

    var Customers = $resource('/customers/', {}, {
      create_customer: {method: 'POST', isArray: false},
      list_customers: {method: 'GET', isArray: false}
    });


    $scope.createCustomer = function() {

      var res = Customers.create_customer({}, $scope.customer, function() {
        item_id = res['item']['id'];
        Customers.list_customers({"customer_id": item_id}, {}, function() {});
        Customers.list_customers({"channel": $scope.channel_id}, {}, function() {});
      })
    }

//    $http.get('/agent_labels', {
//      params: {
//        channel  : $rootScope.channel_id,
//        type     : 'intent'
//      }
//    }).
//      success(function(data) {
//        $scope.options.intent = _.map(data.list, function(obj, key) {
//          return {title:obj.intent, id:obj.id}
//        });
//      });
//
//    $http.get('/agent_labels', {
//      params: {
//        channel  : $rootScope.channel_id,
//        type     : 'seniority_customer'
//      }
//    }).
//      success(function(data) {
//        $scope.options.customer_seniority = _.map(data.list, function(obj, key) {
//          return {title:obj.display_name, id:obj.id}
//        });
//      });
//
//     $http.get('/agent_labels', {
//      params: {
//        channel  : $rootScope.channel_id,
//        type     : 'location'
//      }
//    }).
//      success(function(data) {
//        $scope.options.location_labels = _.map(data.list, function(obj, key) {
//          return {title:obj.display_name, id:obj.id}
//        });
//      });

  });



angular.module('test')
  .controller('AgentCtrl', function($scope, $rootScope, $resource, $http) {
    $scope.agent = {
      channel    : $rootScope.channel_id,
      first_name : null,
      last_name  : null,
      age        : null,
      sex        : null,
      seniority  : null,
      occupancy  : null,
      english_fluency: null,
      location   : null,
      products   : null,
      skills     : null
    };
    $scope.options = {
      intent : []
    }
    console.log($scope.agent);

    var AgentsService = $resource('/agents/', {}, {
      create_agent: {method: 'POST', isArray: false},
      list_agents: {method: 'GET', isArray: false}
    });


    $scope.createAgent = function() {

      var res = AgentsService.create_agent({}, $scope.agent, function() {
        item_id = res['item']['id'];
        AgentsService.list_agents({"agent_id": item_id}, {}, function() {});
        AgentsService.list_agents({"channel": $scope.channel_id}, {}, function() {});
      })
    };


//    $http.get('/agent_labels', {
//      params: {
//        channel  : $rootScope.channel_id,
//        type     : 'intent'
//      }
//    }).
//      success(function(data) {
//        $scope.options.intent = _.map(data.list, function(obj, key) {
//          return {title:obj.intent, id:obj.id}
//        });
//      });
//
//    $http.get('/agent_labels', {
//      params: {
//        channel  : $rootScope.channel_id,
//        type     : 'fluency'
//      }
//    }).
//      success(function(data) {
//        $scope.options.english_fluency = _.map(data.list, function(obj, key) {
//          return {title:obj.display_name, id:obj.id}
//        });
//      });
//
//     $http.get('/agent_labels', {
//      params: {
//        channel  : $rootScope.channel_id,
//        type     : 'seniority_agent'
//      }
//    }).
//      success(function(data) {
//        $scope.options.agent_seniority = _.map(data.list, function(obj, key) {
//          return {title:obj.display_name, id:obj.id}
//        });
//      });
//
//     $http.get('/agent_labels', {
//      params: {
//        channel  : $rootScope.channel_id,
//        type     : 'location'
//      }
//    }).
//      success(function(data) {
//        $scope.options.location_labels = _.map(data.list, function(obj, key) {
//          return {title:obj.display_name, id:obj.id}
//        });
//      });


  });


angular.module('test')

  .controller('ListCustomersCtrl', function($scope, $rootScope, $http, $modal) {
    $scope.customers = [];

    $scope.labels = {
      intent: []
    }




//    $http.get('/agent_labels', {
//      params: {
//        channel  : $rootScope.channel_id,
//        type     : 'intent'
//        }
//    }).
//      success(function(data) {
//        $scope.labels.intent = data.list
//      }).
//      error(function(data) {
//        console.log(data);
//      });

    $scope.openAgentsModal = function(data, options) {
      $modal.open({
        backdrop: true,
        keyboard: true,
        backdropClick: true,
        size: 'lg',
        templateUrl: '/partials/agents/agentModal',
        controller : function($scope) {
          $scope.modal_title = data.error ? 'No agent matched' : "Selected Agents";
          $scope.agents = data.considered_agents;
          $scope.customer = options.customer;
          $scope.call_intent_id = options.call_intent_id;
          $scope.error = data.error;
          $scope.selected_agent_id = data.selected_agent_id;
          $scope.isRating = false;
          $scope.rating = {
            value : 10
          }

          $scope.getStar = function(num) {
            return new Array(num);
          }

          $scope.getScore = function() {
            return 1
          }

          $scope.customerCallTable = {
            sort: {
              predicate: 'customer_name',
              reverse: false
            }
          };

          $scope.rate = function(agent_id, rating) {

            $http.post('/customer/call/rating', {
              customer_id: options.customer.id,
              selected_agent_id: agent_id,
              reward_rating: rating
            }).
              success(function(data) {
                console.log(data);
                $http.post('/customer/call', {call_intent_id:options.call_intent_id, customer_id: options.customer.id}).
                  success(function(data) {
                    $scope.agents = data.considered_agents;
                  })
              }).
              error(function(data) {
                console.log(data);
              });
          }
          $scope.close = function(result){
            console.log(result);
            $scope.$close(result);
          };
        }
      })
    }

    $scope.labels = [{
      display_name: 'Closing an account',
    },
      {
        display_name: 'Upgrading an account',
      },
      {
        display_name: 'Reporting a bug',
      },
      {
        display_name: 'Disputing a bill'
      }]

    $scope.callAgent = function(customer, call_intent) {

      $http.post('/customer/call', {customer_id : customer.id, call_intent: call_intent }).
        success(function(data) {
          console.log(data);
          $scope.openAgentsModal(data,
            {customer: customer, call_intent_id: call_intent}
          );

        }).
        error(function(data) {
          console.log(data);
        });
    }

    $http.get('/customers',
      {params : {'channel' : $rootScope.channel_id} }
    ).
      success(function(data) {
        console.log(data);
        $scope.customers = _.defaults(data.list, {
          is_new_intent : false,
          new_intent    : ""
        } );
      }).
      error(function(data) {
        console.log(data);
      });
  });


angular.module('test')
  .controller('ListAgentsCtrl', function($scope, $rootScope, $resource, $http) {

    $scope.agents = [];

    $http.get('/agents',
      {params : {'channel' : $rootScope.channel_id} }
    ).
      success(function(data) {
        console.log(data);
        $scope.agents = data.list;
      }).
      error(function(data) {
        console.log(data);
      });




  });

angular.module('test')
  .controller('SegmentCtrl', function($scope, $rootScope, $resource, $http) {
    $scope.customer_segment = {
      channel_id        : $rootScope.channel_id,
      display_name      : null,
      precondition      : null,
      acceptance_rule   : null
    };

    var CustomerSegment = $resource('/customer_segments/', {}, {
      create_segment: {method: 'POST', isArray: false},
      list_segments: {method: 'GET', isArray: false}
    });

    var CustomerMultiSegment = $resource('/customer_multi_segments/', {}, {
      create_segment: {method: 'POST', isArray: false},
      list_segments: {method: 'GET', isArray: false}
    });


    $scope.createSegment = function() {

      var res = CustomerSegment.create_segment({}, $scope.customer_segment, function() {
      });

      var multiSegment = {
        display_name: 'Multi-' + $scope.customer_segment.display_name,
        channel_id: $rootScope.channel_id,
        segment_options: [{
          channel_id        : $rootScope.channel_id,
          display_name      : $scope.customer_segment.display_name + '1',
          precondition      : $scope.customer_segment.precondition,
          acceptance_rule   : $scope.customer_segment.acceptance_rule
        },
          {
            channel_id        : $rootScope.channel_id,
            display_name      : $scope.customer_segment.display_name + 2,
            precondition      : $scope.customer_segment.precondition,
            acceptance_rule   : $scope.customer_segment.acceptance_rule
          }]
      }
      var res = CustomerMultiSegment.create_segment({}, multiSegment, function() {
      });

    };
  });

angular.module('test')
  .controller('ListSegmentsCtrl', function($scope, $rootScope, $resource, $http) {

    $scope.segments = [];
    $scope.multi_segments = [];

    $http.get('/customer_segments',
      {params : {'channel_id' : $rootScope.channel_id} }
    ).
      success(function(data) {
        console.log(data);
        $scope.segments = data.list;
      }).
      error(function(data) {
        console.log(data);
      });

    $http.get('/customer_multi_segments',
      {params : {'channel_id' : $rootScope.channel_id} }
    ).
      success(function(data) {
        console.log(data);
        $scope.multi_segments = data.list;
      }).
      error(function(data) {
        console.log(data);
      });
  });

angular.module('test')
  .directive("rateit", function() {
    var directive = { };
    directive.restrict = 'AE';

    directive.scope = {
      score: '=score',
      max: '=max',
      step: '=step',
      agent: '=agent',
      onRate : '&'
    };

    directive.templateUrl = "app/templates/rating.html";

    directive.link = function(scope, elements, attr) {

      scope.updateStars = function() {
        var idx = 0;
        scope.stars = [ ];
        for (idx = 0; idx < scope.max; idx += 1) {
          scope.stars.push({
            full: scope.score > (idx * scope.step)
          });
        }
      };

      scope.hover = function(/** Integer */ idx) {
        scope.hoverIdx = idx;
      };

      scope.stopHover = function() {
        scope.hoverIdx = -1;
      };

      scope.starColor = function(/** Integer */ idx) {
        var starClass = 'rating-normal';
        if (idx <= scope.hoverIdx) {
          starClass = 'rating-highlight';
        }
        return starClass;
      };

      scope.starClass = function(/** Star */ star, /** Integer */ idx) {
        var starClass = 'icon-star-outline';
        if (star.full || idx <= scope.hoverIdx) {
          starClass = 'icon-stars';
        }
        return starClass;
      };

      scope.getStarHalf = function(/** Integer */ idx) {
        return idx % 2 === 0 ?  'left-half' : 'right-half';
      };

      scope.setRating = function(idx) {
        idx = idx + 1;
        scope.score = idx * scope.step;
        scope.stopHover();
        console.log("SET RATING!!!", scope.agent);
        scope.onRate({agentId:scope.agent.id, rating:scope.score});
      };

      scope.$watch('score', function(newValue, oldValue) {
        if (newValue !== null && newValue !== undefined) {
          scope.updateStars();
        }
      });
    };

    return directive;
  });
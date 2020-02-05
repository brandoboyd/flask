angular.module('wizard-signup', ['mgo-angular-wizard', 'ark-ui-bootstrap', 'ngSanitize', 'ngResource' ])
  .factory('TwitterHandle', ['$resource', function($resource) {
    return $resource('/twitter/users', {}, {
      check: { method:'GET', isArray:false }
    });
  }])
  .factory('TagsMessages', function() {
    var error   = $("<span class='help-inline'></span>");
    var success = $("<span class='help-inline'>OK!</span>");
    var spinner = $("<span class='help-inline'><img src='/static/assets/img/ajax-loader-small.gif' /> Checking if user exists...</span>");

    var messages = error.add(success).add(spinner);
    return {
      init : function(el) {
        messages.insertAfter(el);
        messages.hide();
      },
      showMessages : function(res) {
        if (res && res.ok) {
          spinner.hide();
          error.hide();
          success.show();
        } else if (res && !res.ok) {
          spinner.hide();
          success.hide();
          //var er = angular.fromJson((res.error).replace(/u'/g, "'").replace(/'/g, '"'));
          var er = res.error[0];
          if (er.code == 34) {
            error.text("This is not a valid Twitter account.");
          } else {
            error.text(er.message);
          }
          error.show();
        } else {
          messages.hide();
        }
      },
      spin : function() {
        messages.hide();
        spinner.show();
      }
    }
  })
  .controller('WizardCtrl', function($log, $window, $scope, $http, WizardHandler, TwitterHandle, TagsMessages) {

    $scope.account = {
      full_name   : 'John Doe',
      email       : 'john_doe@gmail.com',
      password    : '',
      channel     : {
        title    : '',
        keywords : [],
        handles  : []
      }
    }

    $scope.finished = function() {
      return $http({
        method : 'POST',
        url    : '/signup',
        data   : $scope.account,
        headers: {'Content-Type': 'application/json'}
      }).then(function (res) {
        console.log('redirecting');
        $window.location = "/inbound#/?start=true"
      });
    }

    $scope.logStep = function() {
      console.log("Step continued");
      console.log($scope.account);
    }

    $scope.goBack = function() {
      WizardHandler.wizard().goTo(0);
    }

    $scope.$watch('account.channel.handles', function(nVal, oVal) {
      if(nVal !== oVal) {
        if(_.isArray(nVal) && nVal.length > 0 ) {

          TwitterHandle.check({'twitter_handle' :  _.last(nVal)}, function(res) {
            TagsMessages.showMessages(res);
            console.log(res);
          });
        }
      }
    }) // watch

  })
  .directive('checkSpinner', function(TagsMessages) {
    return {
      link:function(scope, element, attrs) {
        TagsMessages.init(element);
      }
    }
  })
  .directive( 'popoverHtmlUnsafePopup', function ($sce) {
    return {
      restrict: 'EA',
      replace: true,
      scope: { content: '@', title: '@', placement: '@', animation: '&', isOpen: '&' },
      template: '<div class="popover {{placement}}" ng-class="{ in: isOpen(), fade: animation() }">\
                <div class="arrow"></div>\
                <div class="popover-inner">\
                  <h3 class="popover-title" ng-bind="title" ng-show="title"></h3>\
                  <div class="popover-content" ng-bind-html="content"></div>\
                </div>\
               </div>'
    };
  })

  //.directive( 'popoverHtmlUnsafe', function ( $compile, $timeout, $parse, $window, $tooltip ) {
  //  return $tooltip( 'popoverHtmlUnsafe', 'popover', 'click' );
  //})

  .directive('equalsto', function() {
    return {
      restrict:'A',
      require: 'ngModel',
      link: function(scope, elm, attrs, ctrl) {
        var validate = function(thisValue, equalToValue){
          if (!(thisValue && equalToValue)) {
            ctrl.$setValidity('equal', true);
            return;
          }
          if (thisValue == equalToValue) {
            ctrl.$setValidity('equal', true);
          } else {
            ctrl.$setValidity('equal', false);
          }
          return thisValue;
        };

        ctrl.$parsers.unshift(function(viewValue){
          return validate(viewValue, scope.$eval(attrs.equalsto));
        });

        ctrl.$formatters.unshift(function(modelValue){
          return validate(modelValue, scope.$eval(attrs.equalsto));
        });

        scope.$watch(attrs.equalsto, function(equalsToValue){
          validate(ctrl.$viewValue, equalsToValue);
        });

      }
    };
  })

  .directive('strongpassword', function(){
    var reg = {
      lower:   /[a-z]/,
      upper:   /[A-Z]/,
      numeric: /[0-9]/,
      special: /[\W_]/
    };
    var testPassword = function(pwd) {
      var strength = 0;
      reg.lower.test(pwd) && strength++;
      reg.upper.test(pwd) && strength++;
      reg.numeric.test(pwd) && strength++;
      reg.special.test(pwd) && strength++;
      return (strength >= 3);
    };
    return {
      restrict: 'A',
      require: 'ngModel',
      link: function(scope, elm, attrs, ctrl) {
        ctrl.$parsers.unshift(function(viewValue){
          if (!viewValue || viewValue.length < 8) {
            ctrl.$setValidity('strongpassword', true);
            return viewValue;
          }
          ctrl.$setValidity('strongpassword', testPassword(viewValue));
          return viewValue;
        });
      }
    };
  })
  .directive('uiSelectUsers', function($log, TwitterHandle, TagsMessages) {
    var noFoundMessage = 'Hit Enter or Tab to add a new value';
    var is_valid_handle = function(el) {return el.substring(0, 1) == '@'};
    function isEmpty(value) {
      return angular.isUndefined(value) || (angular.isArray(value) && value.length === 0) || value === '' || value === null || value !== value;
    }
    return {
      require: '?ngModel',
      link : function(scope, element, attrs, ngModel) {
        var validator = function(value) {
          console.log(value);
          if (attrs.required && _.isEmpty(value)) {
            //console.log("EMPTY!");
            ngModel.$setValidity('required', false);
            ngModel.$setValidity('error', true);
            return;
          } else if(value === '!error!') {
            ngModel.$setValidity('error', false);
            return value;

          } else {
            //console.log("NOT EMPTY!");
            ngModel.$setValidity('required', true);
            ngModel.$setValidity('error', true);
            return value;
          }
        };

        ngModel.$formatters.push(validator);
        ngModel.$parsers.unshift(validator);

        attrs.$observe('ngRequired', function() {
          validator(ngModel.$viewValue);
        });
        TagsMessages.init(element);
        var sel = element.select2({
          formatNoMatches : function(term) { return noFoundMessage},
          tags: [],
          escapeMarkup: function(m) { return m; }
        }).select2("val", []);
        //scope.usernames = res.item;
        jQuery(sel).bind("change", function(e) {
          TagsMessages.spin();
          if (e.added) {
            TwitterHandle.check({'twitter_handle' : e.added.text }, function(res) {
              TagsMessages.showMessages(res);
            }, function onError(res) {
              TagsMessages.showMessages(res);
              var labels = element.select2('data');
              var indx = (_.indexOf(labels, e.added));
              labels[indx]['text'] = '<span style="color:red">' + e.added.text + ':ERROR' + '</span>';
              sel.select2('data', labels);
              validator('!error!');
            })
          } else if (e.removed) {
            validator(ngModel.$viewValue);
            TagsMessages.showMessages(null);
          }
        });

      }

    }

  })

  .directive('uiSelectKeywords', function() {
    var noFoundMessage = 'Hit Enter or Tab to add a new value';
    function isEmpty(value) {
      return angular.isUndefined(value) || (angular.isArray(value) && value.length === 0) || value === '' || value === null || value !== value;
    }
    return {
      require: '?ngModel',
      link: function (scope, element, attr, ctrl) {
        var validator = function (value) {
          if (attr.required && (isEmpty(value) || value === false)) {
            ctrl.$setValidity('required', false);
            return;
          }
          else {
            ctrl.$setValidity('required', true);
            return value;
          }
        };

        ctrl.$formatters.push(validator);
        ctrl.$parsers.unshift(validator);

        attr.$observe('ngRequired', function () {
          validator(ctrl.$viewValue);
        });

        var sel = element.select2({
          formatNoMatches: function (term) {
            return noFoundMessage
          },
          tags: []
        }).select2("val", []);
        //scope.keywords = res.item;
        jQuery(sel).bind("change", function (e) {
          if (e.added) {

          } else if (e.removed) {
            validator(ctrl.$viewValue);
          }
        });
      }
    }
  });



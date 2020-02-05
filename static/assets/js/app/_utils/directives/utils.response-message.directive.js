(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('responseMessage', responseMessage);

  /** @ngInject */
  function responseMessage($compile, AccountsService, $rootScope) {
    return {
      replace: true,
      template: '<div class="responseText"  ng-model="scope.message">'
      + '<span class="respondTo"   ng-bind="respondTo"></span>'
      + '<span ng-show="!isEditMode && isEmpty()" class="placeholder respondFrom">Please type a response...&nbsp;</span>'
      + '<span class="respondFrom" ng-bind="signature"></span>'
      + '</div>',
      require: '?ngModel',
      scope: {
        responseMessage: '=',
        model: '=ngModel',
        focus: '=responseMessageFocus'
      },

      link: function (scope, element, attrs, ngModel) {
        var acc = AccountsService.getCurrent();
        var response = scope.responseMessage;
        if (scope.responseMessage.platform == 'Twitter') {
          // Twitter limit is 140 chars
          scope.limit = 140;
        } else if (scope.responseMessage.platform == 'Facebook') {
          // Facebook has no clear limit, need to check what actually makes sense
          // for our inbox.
          scope.limit = 400;
        } else {
          // This should NEVER be the case. Just a safety precaution.
          scope.limit = 100;
        }

        scope.respondTo = response.post.user.user_name + ' ';
        scope.message = ' ';
        scope.signature = acc ? ' ' + acc.signature : '';
        scope.isEditMode = false;
        scope.responseMessage.custom_response = _.extend({}, scope.message);
        scope.responseMessage.prefix = scope.respondTo;
        scope.responseMessage.suffix = scope.signature;
        scope.isEmpty = function () {
          return !(scope.message || "").trim().replace('&nbsp;').length;
        };

        $rootScope.$watch('showMatches', function (nVal) {
          if (!nVal) {
            scope.message = response.match ? response.match.matchable.creative : response.matchable.creative;
            ngModel.$render(false);
          } else {
            scope.message = '&nbsp;';
            ngModel.$render(false);
            m.focus();
          }

        })
        scope.cancelEdit = function (el) {
          element.removeClass("beingEdited");
          m.attr({'contenteditable': false});
          scope.isEditMode = false;
          scope.$parent.isEditMode = false;
          scope.message = scope.message;
          ngModel.$render(false);

        }

        element.on('click', function () {
          if (scope.$parent.responseType && scope.$parent.responseType != 'posted') {

            m.attr({'contenteditable': true});
            m.focus();
            if (!scope.$parent.$$phase) {
              scope.$apply(scope.$parent.isEditMode = true);
            }
            if (!element.hasClass("beingEdited")) {
              ngModel.$render(true);
            } else {
              angular.noop();
            }
            element.addClass("beingEdited");

          } else {
            angular.noop();
          }

        });

        scope.$watch('focus', function (nVal, oVal) {
          if (nVal != oVal) {
            if (nVal == true) {
              element.trigger('click');
              scope.isEditMode = true;
            } else {
              scope.isEditMode = false;
            }
          }
        })

        scope.submitCustomResponse = function (message_type) {
          scope.$parent.submitCustomResponse(response, message_type)
        }

        scope.postCustomResponseCreateCase = function () {
          scope.$parent.postCustomResponseCreateCase(response)
        }

        scope.$watch('$parent.isEditMode', function (nVal) {
          scope.isEditMode = nVal;
        });

        scope.isLimitExceeded = function () {
          return scope.count <= -1 || scope.model.trim().length == 0 || scope.model.trim() == scope.message.trim()
        }

        scope.caseButtonVisibility = function () {
          return !response.is_conversation_synced && acc.is_sf_auth;
        }

        scope.postButtonVisibility = function () {
          if (typeof hsp != "undefined") {
            return false;
          }
          return scope.responseMessage.has_both_pub_and_dm || scope.responseMessage.message_type == 0;
        }

        scope.postHSButtonVisibility = function () {
          if (typeof hsp != "undefined") {
            return response.message_type == 0;
          } else {
            return false
          }
        }

        scope.isOriginalResponse = function () {
          if (scope.message == scope.responseMessage.custom_response) {
            return false
          } else {
            return scope.isLimitExceeded();
          }
        }

        scope.submitHSResponse = function (message_type) {
          if (!message_type) message_type = 'public';
          if (scope.message == scope.responseMessage.custom_response) {
            // TODO: do we also allow direct?
            scope.$parent.postResponse(response, message_type);
          } else {
            scope.submitCustomResponse(message_type);
          }
        }

        scope.dmButtonVisibility = function () {
          return response.message_type == 1
        }

        var btns = $compile('<div ng-show="isEditMode" class="editPanel">\
                              <span ng-bind="count" class="counter"></span>\
                              <button class="btn btn-xs btn-default" \
                                      ng-click="cancelEdit(this)">Cancel</button>\
                              <button class = "btn btn-xs btn-default" \
                                      ng-click = "postCustomResponseCreateCase()"\
                                      ng-disabled = "isLimitExceeded()"\
                                      ng-show  = "caseButtonVisibility()">Post&ensp;&amp;&ensp;Create Case</button>\
                              <button class="btn btn-xs btn-default" \
                                      ng-click="submitCustomResponse(\'public\')"\
                                      ng-disabled = "isLimitExceeded()"\
                                      ng-show = "postButtonVisibility()">Post</button>\
                              <button class="btn btn-xs btn-default" \
                                      ng-click="submitHSResponse()"\
                                      ng-disabled = "isOriginalResponse()"\
                                      ng-show = "postHSButtonVisibility()">Post</button>\
                              <button class="btn btn-xs btn-default" \
                                      ng-click="submitCustomResponse(\'direct\')"\
                                      ng-disabled = "isLimitExceeded()"\
                                      ng-show = "dmButtonVisibility()">DM</button>\
                            </div>')(scope);

        element.after(btns);
        var m = $compile('<span class="message" ng-model="scope.message">' + twttr.txt.autoLink(scope.message) + '</span>')(scope);

        element.find('.respondTo').after(m);

        var messageEl = m;

        ngModel.$render = function (edit) {
          if (edit) {
            messageEl.html(scope.message);
          } else {
            messageEl.html(twttr.txt.autoLink(scope.message));
          }
          scope.model = scope.message;
        };

        // Listen for change events to enable binding
        messageEl.on('blur keyup change', function () {
          scope.$apply(read);
        });

        //read();
        // Write data to the model
        function read() {
          var html = messageEl.text();
          ngModel.$setViewValue(html);
          scope.model = ngModel.$viewValue;
        }

        var message_length = 0;
        var counter = element.next('.editPanel').find('.counter');
        var filler = '0123456789123456789'

        scope.$watch('model', function (nVal) {
          var extractedUrls = twttr.txt.extractUrlsWithIndices(nVal);
          var virtualTweet = nVal;
          //add 1 for '@' which we don't display but need to count
          message_length = (1 + scope.respondTo.length) + virtualTweet.length + scope.signature.length;

          if (nVal.length > 0) {
            if (extractedUrls.length > 0) {
              _.each(extractedUrls, function (el) {
                virtualTweet = virtualTweet.replace(el.url, filler);
              })
            }
            scope.responseMessage.custom_response = nVal;
            scope.count = scope.limit - message_length;
            if (scope.count <= 3) {
              counter.addClass('counter-red');
            } else if (scope.count > 3 && counter.hasClass('counter-red')) {
              counter.removeClass('counter-red');
            }
          } else {
            messageEl.html('&nbsp;');
            scope.count = scope.limit - message_length;
          }
        })
      }
    }
  }
})();
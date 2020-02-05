(function () {
  'use strict';

  angular
    .module('slr.configure',
      [ 'ngRoute',
        'ngResource',
        'ngSanitize',
        'ngAnimate',
        'ng.jsoneditor',
        'ngFileUpload',
        'angular-svg-round-progress',
        'ui.select2',
        'ui.select',
        'ui.slimscroll',
        'ui.jq',
        'ark-ui-bootstrap',
        'ark-components',
        'ui.ace',
        'ui.bootstrap',
        'ui.bootstrap-slider',
        'infinite-scroll',

        'slr.components', 'mentio', 'xeditable'])
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider.otherwise({redirectTo: '/channels'});
    }]);
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('SocialService', ['$rootScope', '$http', 'SystemAlert', function ($rootScope, $http, SystemAlert) {
      var sharedService = {POPUP_CLOSE: 'PopupCloseEvent'};

      sharedService.twitterGetProfile = function (channel_id, callback) {
        if (!channel_id) {
          //alert('No channel provided.');
          return;
        }
        return $http.get('/twitter_profile/' + channel_id, {},
          {headers: {'Content-Type': 'application/x-www-form-urlencoded'}}).success(callback);
      };

      sharedService.fbGetProfile = function (channel_id, callback) {
        if (!channel_id) {
          //alert('No channel provided.');
          return;
        }
        return $http.get('/facebook_profile/' + channel_id, {},
          {headers: {'Content-Type': 'application/x-www-form-urlencoded'}}).success(callback);
      };

      var onPopupClose = function (action, who) {
        // broadcast event to update twitter_profile
        if (!who) {
          $rootScope.$broadcast(sharedService.POPUP_CLOSE, {type: 'twitter', action: action});
        } else {
          $rootScope.$broadcast(sharedService.POPUP_CLOSE, {type: 'facebook', action: action});
        }
      };

      sharedService.twitterRequestToken = function (channel_id) {
        if (!channel_id) {
          SystemAlert.error('No channel provided.');
          return;
        }
        var url = "/twitter_request_token/" + channel_id;
        var windowName = "Twitter";
        var windowSize = "width=300,height=400,scrollbars=yes";

        sharedService.twitterPopup = window.open(url, windowName, windowSize);
        var watchClose = setInterval(function () {
          try {
            if (sharedService.twitterPopup.closed) {
              clearTimeout(watchClose);
              onPopupClose('request_token');
            }
          } catch (e) {
          }
        }, 1000);

      };


      sharedService.facebookRequestToken = function (channel_id) {
        if (!channel_id) {
          SystemAlert.error('No channel provided.');
          return;
        }
        var url = "/facebook_request_token/" + channel_id;
        var windowName = "Facebook";
        var windowSize = "width=300,height=400,scrollbars=yes";

        sharedService.fbPopup = window.open(url, windowName, windowSize);
        var watchClose = setInterval(function () {
          try {
            if (sharedService.fbPopup.closed) {
              clearTimeout(watchClose);
              onPopupClose('request_token', 'facebook');
            }
          } catch (e) {
          }
        }, 1000);

      };

      sharedService.twitterLogout = function (channel_id) {
        if (!channel_id) {
          SystemAlert.error('No channel provided.');
          return;
        }
        var url = "/twitter_logout/" + channel_id;
        var windowName = "Twitter";
        var windowSize = "width=300,height=400,scrollbars=yes";

        sharedService.twitterPopup = window.open(url, windowName, windowSize);
        var watchClose = setInterval(function () {
          try {
            if (sharedService.twitterPopup.closed) {
              clearTimeout(watchClose);
              onPopupClose('logout');
            }
          } catch (e) {
          }
        }, 1000);
      };

      sharedService.facebookLogout = function (channel_id) {
        if (!channel_id) {
          SystemAlert.error('No channel provided.');
          return;
        }
        var url = "/facebook_logout/" + channel_id;
        var windowName = "Facebook";
        var windowSize = "width=300,height=400,scrollbars=yes";

        sharedService.facebookPopup = window.open(url, windowName, windowSize);
        var watchClose = setInterval(function () {
          try {
            if (sharedService.facebookPopup.closed) {
              clearTimeout(watchClose);
              onPopupClose('logout', 'facebook');
            }
          } catch (e) {
          }
        }, 1000);
      };


      return sharedService;
    }])
    .factory('TwitterHandle', ['$resource', function ($resource) {
      return $resource('/twitter/users', {}, {
        check: {method: 'GET', isArray: false}
      });
    }])
    .factory('TagsMessages', ["$timeout", function ($timeout) {
      var error = $("<span class='help-inline text-important' style='color:red'></span>");
      var success = $("<span class='help-inline'>OK!</span>");
      var spinner = $("<span class='help-inline'><img src='/static/assets/img/ajax-loader-small.gif' /> Checking if twitter user exists...</span>");

      var messages = error.add(success).add(spinner);
      return {
        init: function (el) {
          messages.insertAfter(el);
          messages.hide();
        },
        showMessages: function (res, user) {
          if (res && res.ok) {
            $timeout(function () {
              spinner.hide();
              error.hide();
              success.show();
            }, 0)
          } else if (res && !res.ok) {
            $timeout(function () {
              spinner.hide();
              success.hide();
              error.show();
            }, 0)
            //var er = angular.fromJson((res.error).replace(/u'/g, "'").replace(/'/g, '"'));
            var er = res.error[0];
            if (er.code == 34) {
              error.html('<b>' + user + '</b>' + ' is not valid Twitter account. It won\'t be added.');
            } else {
              error.text(er.message);
            }
          } else {
            $timeout(function () {
              messages.hide();
            }, 0)
          }
        },
        spin: function () {
          messages.hide();
          spinner.show();
        }
      }
    }])
    .service('fbUserDataProvider', ["$http", function ($http) {
      var $ = jQuery;
      var modeEnum = {
        'PAGE': 'pages',
        'EVENT': 'events',
        'GROUP': 'groups'
      };

      function FbUserDataProvider() {
        this.adopt = function (el) {
          el.text = el.name;
          return el;
        };
      }

      FbUserDataProvider.instance = function () {
        return new FbUserDataProvider();
      };

      FbUserDataProvider.prototype = {
        sel: null,
        current: null,
        modes: modeEnum,
        ngModel: null,

        setDataModel: function (type, ngModel) {
          this.mode = type;
          this.ngModel = ngModel;
        },

        _getUrl: function (channel_id) {
          if (this.mode) {
            return ['/channels/', channel_id, '/fb/', this.mode].join('');
          } else {
            throw new Error("Data mode for request should be selected.")
          }
        },
        setCurrent: function (value) {
          this.current = value;
          this.ngModel && this.ngModel.$setViewValue(_.pluck(this.current, 'id'));
        },
        getItems: function (element, channel_id) {
          var self = this;
          return $http({
            method: 'GET',
            url: this._getUrl(channel_id),
            params: {all: 'yes'}
          }).then(function (response) {
            var res = response.data,
              available = _.map(res.data, self.adopt);
            self.current = _.map(res.current, self.adopt);
            //TODO: Refactor to class and unified usage for any type of requests
            self.sel = element.select2({
              data: available,
              multiple: true,
              placeholder: self.current.length > 0 ? null : ["Select ", self.mode, " to track"].join(''),

              initSelection: function (element, callback) {
                callback(self.current);
              },

              formatResult: function (item) {
                return item.text;
              },

              formatSelection: function (item) {
                return item.text;
              }
            }).select2("val", _.pluck(self.current, 'id'));

            $(self.sel).off("change");
            $(self.sel).on("change", function (e, el) {
              if (e.added) {
                self.addItem(channel_id, e.added);
              } else if (e.removed) {
                self.removeItem(channel_id, e.removed);
              }
            });
          });
        },

        addItem: function (channel_id, item) {
          var self = this;
          var params = {};
          params[this.mode] = item;
          var promise = $http({
            method: 'POST',
            url: this._getUrl(channel_id),
            data: params
          }).then(function onSuccess(res) {
            var data = res.data;
            self.setCurrent(_.map(data.data, self.adopt));
          }, function onError() {
            if (self.sel != null) {
              self.sel.select2("val", _.pluck(self.current, 'id'));
            }
          });
          return promise;
        },

        removeItem: function (channel_id, item) {
          var self = this;
          var params = {};
          params[this.mode] = item;
          var promise = $http({
            headers: {'Content-Type': 'mimetype=application/xml'},
            method: 'DELETE',
            url: this._getUrl(channel_id),
            params: params
          }).then(function (res) {
            var data = res.data;
            self.setCurrent(_.map(data.data, self.adopt));
          }, function onError() {
            if (self.sel != null) {
              self.sel.select2("val", _.pluck(self.current, 'id'));
            }
          });
          return promise;
        }
      };
      return FbUserDataProvider;

    }])
    .factory('LanguageUtils', ["$http", "TrackingChannel", function ($http, TrackingChannel) {
      var url_all_languages = '/languages/all/json';
      var supportedLanguages = {
        all: [],
        twitter: []
      };

      var langPromise = null;
      var LanguageUtils = {
        getSupportedLanguages: function (languageSet) {
          languageSet = languageSet || 'all';
          return supportedLanguages[languageSet];
        },
        fetchSupportedLanguages: function (languageSet) {
          if (langPromise !== null) {
            return langPromise;
          }
          languageSet = languageSet || 'all';
          langPromise = $http({
            method: 'GET',
            url: url_all_languages,
            params: {languageSet: languageSet}
          }).then(function (res) {
            return res.data.list;
          });
          return langPromise;
        },

        getLanguageCssClass: function (data) {
          if (data.text.indexOf('lang: English') != -1) {
            return "enTagsKlass"
          } else if (data.text.indexOf('lang: Spanish') != -1) {
            return "esTagsKlass"
          } else {
            //console.log("NO CUSTOM CLASS");
          }
        },

        prepareLanguageData: function (rawData) {
          var data = [];
          _.each(rawData, function (el) {
            data.push({id: el, text: el});
          });
          var groupedData = _.groupBy(data, function (el) {
            var sIdx = el.text.indexOf('lang:'),
              eIdx = el.text.length,
              lang = sIdx != -1 ? el.text.substring(sIdx, eIdx) : 'none';
            return lang
          });
          return _.flatten(_.values(groupedData));
        },
        getOptionsList: function (query, channel_id) {
          //var supportedLangs = LanguageUtils.getSupportedLanguages();
          return TrackingChannel.get_languages({'channel_id': channel_id},
            function (res) {
              var supportedLangs = res.item;
              var data = {results: []}, i, j, s;
              if (query.term.indexOf(' lang:') != -1) {
                for (i = 0; i < supportedLangs.length; i++) {
                  var eIdx = (query.term).indexOf('lang:'),
                    term = query.term.substring(0, eIdx);
                  data.results.push(
                    {
                      id: term + " lang: " + supportedLangs[i].title,
                      text: term + " lang: " + supportedLangs[i].title
                    });
                }
                query.callback(data);
              } else {
                data = {
                  results: [
                    {
                      id: query.term,
                      text: query.term
                    }
                  ]
                };
                query.callback(data);
              }

            })

        },

        removeLanguageTags: function (removed, sel, channel_id, type) {

          var data = sel.select2("data");
          var lang_filter = 'lang: ' + removed.text;


          //remove only the keywords with 'lang:' filter
          if (_.isArray(data) && data.length > 0) {
            var preserve_data = _.filter(data, function (el) {
              return el.text.indexOf(lang_filter) == -1
            });


            var remove_data = _.difference(data, preserve_data, channel_id);

            var getRemoveParams = function (type, remove_data, channel_id) {
              var key = type == 'remove_watchword' ? 'watchword' : 'keyword';
              var obj = {};
              obj[key] = _.pluck(remove_data, 'text');
              obj['channel_id'] = channel_id
              return obj
            }


            if (remove_data.length > 0) {
              TrackingChannel[type](
                getRemoveParams(type, remove_data, channel_id)
                , function () {
                  jQuery(sel).select2("data", preserve_data)
                });
            }
          } else {
            return
          }
        }
      }

      _(['twitter', 'all']).forEach(function(languageScope) {
        LanguageUtils.fetchSupportedLanguages(languageScope).then(function (result) {
          supportedLanguages[languageScope] = result;
        });
      });

      return LanguageUtils;
    }])
    .factory('ComplianceReview', ['$resource', function ($resource) {
      var res = $resource('/configure/outbound_review/:action/json', {}, {
        lookupUsers: {method: 'POST', params: {action: "lookup"}},
        fetchUsers: {method: 'POST', params: {action: "fetch_users"}},
        addUsers: {method: 'POST', params: {action: "add_users"}},
        removeUsers: {method: 'POST', params: {action: "del_users"}}
      });
      res.lookupCache = {};
      return res;
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .directive('uiSlider2', uiSlider2)
    .directive('uiSliderCreate', uiSliderCreate)
    .directive('uiChannelProgress', uiChannelProgress)
    .directive('equalsto', equalsto)
    .directive('strongpassword', strongpassword)
    .directive('uiSelectLanguages', uiSelectLanguages)
    .directive('uiSelectKeywords', uiSelectKeywords)
    .directive('uiSelectSkipwords', uiSelectSkipwords)
    .directive('uiSelectWatchwords', uiSelectWatchwords)
    .directive('uiSelectFacebookPages', uiSelectFacebookPages)
    .directive('uiSelectFacebookGroups', uiSelectFacebookGroups)
    .directive('uiSelectFacebookEvents', uiSelectFacebookEvents)
    .directive('uiTwitterHandle', uiTwitterHandle)
    .directive('uiSelectTagUsers', uiSelectTagUsers)
    .directive('uiSelectUsers', uiSelectUsers)
    .directive('uiSelectReviewTeam', uiSelectReviewTeam)
    .directive('focusHere', focusHere);

  /**@ngInject */
  function uiSlider2($timeout) {
      return function (scope, elm, attrs) {
        var elID = elm.attr('id').split("_")[0];
        var str_id = "#" + elID + "_threshold";
        $timeout(function () {
          var channel = scope.channel;
          if (channel) {
            var intention_values = [channel.moderated_intention_threshold,
              channel.auto_reply_intention_threshold];
            var relevance_values = [channel.moderated_relevance_threshold,
              channel.auto_reply_relevance_threshold];
            var values = elID == 'intention' ? intention_values : relevance_values;
            $(str_id).val(values[0] + " - " + values[1]);
            elm.slider(
              {
                range: true,
                min: 0,
                max: 1,
                step: 0.01,
                values: values,
                slide: function (event, ui) {
                  //console.log(ui);
                  $(str_id).val(ui.values[0] + " - " + ui.values[1]);
                },
                stop: function (e, ui) {
                  if (elID == 'intention') {
                    channel.moderated_intention_threshold = ui.values[0];
                    channel.auto_reply_intention_threshold = ui.values[1];
                  } else {
                    channel.moderated_relevance_threshold = ui.values[0];
                    channel.auto_reply_relevance_threshold = ui.values[1];
                  }
                  scope.$apply();
                }
              }
            );
          }
        }, 1000)
      };

    }
    uiSlider2.$inject = ["$timeout"];

  /**@ngInject */
  function uiSliderCreate($timeout) {
        return function (scope, elm, attrs) {
          var elID = elm.attr('id').split("_")[0];
          var str_id = "#" + elID + "_threshold";
          $timeout(function () {
            var intention_values = [0.25, 1];
            var relevance_values = [0.25, 1];
            var values = elID == 'intention' ? intention_values : relevance_values;
            $(str_id).val(values[0] + " - " + values[1]);
            elm.slider(
              {
                range: true,
                min: 0,
                max: 1,
                step: 0.01,
                values: values,
                slide: function (event, ui) {
                  //console.log(ui);
                  $(str_id).val(ui.values[0] + " - " + ui.values[1]);
                },
                stop: function (e, ui) {
                  if (elID == 'intention') {
                    scope.moderated_intention_threshold = ui.values[0];
                    scope.auto_reply_intention_threshold = ui.values[1];
                  } else {
                    scope.moderated_relevance_threshold = ui.values[0];
                    scope.auto_reply_relevance_threshold = ui.values[1];
                  }
                  scope.$apply();
                }
              }
            );
          }, 1000)
        };
      }
      uiSliderCreate.$inject = ["$timeout"];

  /**@ngInject */
  function uiChannelProgress($timeout, $resource, $location) {

      var Progress = $resource('/progress/json', {}, {
        fetch: {method: 'GET', params: {channel_id: "@id"}, isArray: false}
      });
      var followers_processed = '<div style="text-align:center">Followers processed &mdash; {{progress}}%</div>';
      var progress_bar = '<div class="progress progress-striped active" >' +
        '<div class="bar" style="width:{{progress}}%" ></div>' +
        '</div>';
      return {

        link: function (scope, element, attr, ctrl) {
          scope.progress = 0;

          var section = $location.path().split("/")[1];
          var stop;
          scope.getProgress = function (timeout) {

            stop = $timeout(function () {

              if (scope.progress < 100) {
                Progress.fetch({"channel_id": scope.channel_id}, function (res) {
                  if (res.item.sync_status_followers != "idle") {
                    scope.progress = Math.floor(100 / res.item.followers_count * res.item.followers_synced);
                  } else {
                    scope.progress = 100;
                    jQuery(element).find(".progress").removeClass("active");
                    $timeout.cancel(stop);
                  }
                });

                scope.getProgress(5000);

              } else {
                $timeout.cancel(stop);
              }
            }, timeout);

          };

          scope.$watch('channel', function (newVal, oldVal) {
            if (newVal != oldVal) {
              if (section == 'update_channel'
                && (scope.channel.type == 'EnterpriseTwitterChannel' || scope.channel.type == 'FollowerTrackingChannel')
                && scope.channel.status.toLowerCase() == 'active') {
                scope.getProgress(500);

              }
            }
          });


        },
        template: followers_processed + progress_bar
      }
    }
    uiChannelProgress.$inject = ["$timeout", "$resource", "$location"];

  /**@ngInject */
  function equalsto() {
      return {
        restrict: 'A',
        require: 'ngModel',
        link: function (scope, elm, attrs, ctrl) {
          var validate = function (thisValue, equalToValue) {
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

          ctrl.$parsers.unshift(function (viewValue) {
            return validate(viewValue, scope.$eval(attrs.equalsto));
          });

          ctrl.$formatters.unshift(function (modelValue) {
            return validate(modelValue, scope.$eval(attrs.equalsto));
          });

          scope.$watch(attrs.equalsto, function (equalsToValue) {
            validate(ctrl.$viewValue, equalsToValue);
          });

        }
      };
    }

  /**@ngInject */
  function strongpassword() {
      var reg = {
        lower: /[a-z]/,
        upper: /[A-Z]/,
        numeric: /[0-9]/,
        special: /[\W_]/
      };
      var testPassword = function (pwd) {
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
        link: function (scope, elm, attrs, ctrl) {
          ctrl.$parsers.unshift(function (viewValue) {
            if (!viewValue || viewValue.length < 8) {
              ctrl.$setValidity('strongpassword', true);
              return viewValue;
            }
            ctrl.$setValidity('strongpassword', testPassword(viewValue));
            return viewValue;
          });
        }
      };
    }

  /**@ngInject */
  function uiSelectLanguages($rootScope, $modal, TrackingChannel, SystemAlert, LanguageUtils) {
      var noFoundMessage = 'Hit Enter or Tab to add a new value';

      function isEmpty(value) {
        return angular.isUndefined(value) || (angular.isArray(value) && value.length === 0) || value === '' || value === null || value !== value;
      }


      var confirmModal = function (e) {
        var modal = $modal.open({
          backdrop: true,
          keyboard: true,
          backdropClick: true,
          templateUrl: '/partials/languages/confirmModal',
          controller: ["$scope", function ($scope) {
            $scope.modal_title = ("Confirm removing {lang} keywords").replace('{lang}', e.removed.text);
            $scope.language = e.removed.text;
            $scope.close = function () {
              $scope.$close(e.removed);
            };
            $scope.dismiss = function () {
              $scope.$dismiss('cancel');
            };
          }]
        });
        return modal
      }
      var current_data = null;
      return {
        //require: '?ngModel',
        link: function (scope, element, attr, ctrl) {
          if (scope.channel_id) {
            TrackingChannel.get_languages({'channel_id': scope.channel_id},
              function (res) {
                var supportedLangs = LanguageUtils.getSupportedLanguages(attr.languageSet);
                var sel = element.select2({
                  formatNoMatches: function (term) {
                    return noFoundMessage
                  },
                  multiple: true,
                  data: function () {
                    var data = {results: []};
                    for (var i = 0; i < supportedLangs.length; i++) {
                      data.results.push({
                        id: supportedLangs[i].code,
                        text: supportedLangs[i].title
                      });
                    }
                    return data;
                  },
                  initSelection: function (element, callback) {
                    var data = [],
                      is_locked = res.item.length == 1 ? true : false;
                    _.each(res.item, function (el) {
                      data.push({id: el.code, text: el.title, locked: is_locked});
                    });
                    current_data = res.item;
                    callback(data);

                  }
                }).select2("val", res.item);
                //scope.keywords = res.item;
                jQuery(sel).bind("change", function (e) {
                  if (e.added) {
                    TrackingChannel.add_language(
                      {'language': e.added.text, 'channel_id': scope.channel_id},
                      function () {
                        var data = [],
                          is_locked = e.val.length == 1 ? true : false;

                        _.each(supportedLangs, function (el) {
                          if (_.indexOf(e.val, el.code) != -1) {
                            data.push({id: el.code, text: el.title, locked: is_locked});
                          }
                        });
                        current_data = data;
                        jQuery(sel).select2("data", data);
                      });
                  } else if (e.removed) {

                    confirmModal(e).result.then(function (result) {
                      $rootScope.$emit('CONFIRM_LANGUAGE_REMOVE', result);
                    }, function () {
                      $rootScope.$emit('CANCEL_LANGUAGE_REMOVE');
                    })

                    $rootScope.$on('CONFIRM_LANGUAGE_REMOVE', function (event, removed) {
                      TrackingChannel.remove_language(
                        {'language': removed.text, 'channel_id': scope.channel_id}, function () {
                          var data = [],
                            is_locked = e.val.length == 1 ? true : false;
                          _.each(supportedLangs, function (el) {
                            if (_.indexOf(e.val, el.code) != -1) {
                              data.push({id: el.code, text: el.title, locked: is_locked});
                            }
                          });
                          jQuery(sel).select2("data", data);
                        });
                    });

                    $rootScope.$on('CANCEL_LANGUAGE_REMOVE', function () {
                      jQuery(sel).select2("val", current_data);
                    });


                  }
                });
              },
              function onError() {
                SystemAlert.error("Error getting keywords!");
              }
            );


          }
        }
      };
    }
    uiSelectLanguages.$inject = ["$rootScope", "$modal", "TrackingChannel", "SystemAlert", "LanguageUtils"];

  /**@ngInject */
  function uiSelectKeywords($rootScope, $timeout, $modal, TrackingChannel, SystemAlert, LanguageUtils) {
      var noFoundMessage = 'Hit Enter or Tab to add a new value';
      var sel = null;
      var lu = _.extend({}, LanguageUtils);

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

          if (scope.channel_id) {
            TrackingChannel.get_keywords({'channel_id': scope.channel_id},
              function (res) {
                sel = element.select2({
                  formatNoMatches: function (term) {
                    return noFoundMessage
                  },
                  formatSelectionCssClass: function (data, container) {
                    return LanguageUtils.getLanguageCssClass(data);
                  },

                  query: function (query) {
                    LanguageUtils.getOptionsList(query, scope.channel_id);
                  },
                  tags: [],
                  initSelection: function (element, callback) {
                    var data = LanguageUtils.prepareLanguageData(res.item);
                    callback(data);
                  }
                }).select2("val", res.item);
                scope.keywords = res.item;
                jQuery(sel).bind("change", function (e) {
                  if (e.added) {
                    TrackingChannel.add_keyword(
                      {'keyword': e.added.text, 'channel_id': scope.channel_id},
                      function () {
                        //group keywords by language and update the field on success
                        var data = LanguageUtils.prepareLanguageData(e.val);
                        jQuery(sel).select2("data", data);
                      });
                  } else if (e.removed) {
                    TrackingChannel.remove_keyword(
                      {'keyword': e.removed.text, 'channel_id': scope.channel_id}, function () {
                      });
                  }
                });
              },

              function onError() {
                SystemAlert.error("Error getting keywords!");
              }
            );

            $rootScope.$on('CONFIRM_LANGUAGE_REMOVE', function (event, removed) {
              lu.removeLanguageTags(removed, sel, scope.channel_id, 'remove_keyword');
            })
          }
        }
      };
    }
    uiSelectKeywords.$inject = ["$rootScope", "$timeout", "$modal", "TrackingChannel", "SystemAlert", "LanguageUtils"];

  /**@ngInject */
  function uiSelectSkipwords($log, $rootScope, TrackingChannel, LanguageUtils) {
      var noFoundMessage = 'Hit Enter or Tab to add a new value';
      var sel;
      var lu = _.extend({}, LanguageUtils);
      return {
        require: '?ngModel',
        link: function (scope, element) {
          if (scope.channel_id) {
            TrackingChannel.get_skipwords({'channel_id': scope.channel_id},
              function (res) {
                sel = element.select2({
                  formatNoMatches: function (term) {
                    return noFoundMessage
                  },
                  formatSelectionCssClass: function (data, container) {
                    return LanguageUtils.getLanguageCssClass(data);
                  },
                  query: function (query) {
                    LanguageUtils.getOptionsList(query, scope.channel_id);
                  },
                  tags: [],
                  initSelection: function (element, callback) {
                    var data = LanguageUtils.prepareLanguageData(res.item);
                    callback(data);
                  }
                }).select2("val", res.item);
                scope.skipwords = res.item;
                jQuery(sel).bind("change", function (e) {
                  if (e.added) {
                    TrackingChannel.add_skipword(
                      {'keyword': e.added.text, 'channel_id': scope.channel_id}, function () {
                        //group keywords by language and update the field on success
                        var data = LanguageUtils.prepareLanguageData(e.val);
                        jQuery(sel).select2("data", data);
                      });
                  } else if (e.removed) {
                    TrackingChannel.remove_skipword(
                      {'keyword': e.removed.text, 'channel_id': scope.channel_id}, function () {

                      });
                  }
                });
              }
            );
            $rootScope.$on('CONFIRM_LANGUAGE_REMOVE', function (event, removed) {
              lu.removeLanguageTags(removed, sel, scope.channel_id, 'remove_skipword');
            })
          }
        }
      };
    }
    uiSelectSkipwords.$inject = ["$log", "$rootScope", "TrackingChannel", "LanguageUtils"];

  /**@ngInject */
  function uiSelectWatchwords($rootScope, TrackingChannel, SystemAlert, LanguageUtils) {
      var noFoundMessage = 'Hit Enter or Tab to add a new value';
      var sel = null;
      var lu = _.extend({}, LanguageUtils);
      return {
        require: '?ngModel',
        link: function (scope, element) {
          if (scope.channel_id) {
            TrackingChannel.get_watchwords({'channel_id': scope.channel_id},
              function (res) {
                sel = element.select2({
                  formatNoMatches: function (term) {
                    return noFoundMessage
                  },
                  formatSelectionCssClass: function (data, container) {
                    return LanguageUtils.getLanguageCssClass(data);
                  },
                  query: function (query) {
                    LanguageUtils.getOptionsList(query, scope.channel_id);
                  },
                  tags: [],
                  initSelection: function (element, callback) {
                    var data = LanguageUtils.prepareLanguageData(res.item);
                    callback(data);
                  }
                }).select2("val", res.item);
                scope.watchwords = res.item;
                jQuery(sel).bind("change", function (e) {
                  if (e.added) {
                    TrackingChannel.add_watchword(
                      {'watchword': e.added.text, 'channel_id': scope.channel_id}, function () {
                        var data = LanguageUtils.prepareLanguageData(e.val);
                        jQuery(sel).select2("data", data);
                      });
                  } else if (e.removed) {
                    TrackingChannel.remove_watchword(
                      {'watchword': e.removed.text, 'channel_id': scope.channel_id}, function () {

                      });
                  }
                });
              },
              function onError() {
                SystemAlert.error("Error getting watchwords!");
              }
            );
            $rootScope.$on('CONFIRM_LANGUAGE_REMOVE', function (event, removed) {
              lu.removeLanguageTags(removed, sel, scope.channel_id, 'remove_watchword');
            })
          }
        }
      };
    }
    uiSelectWatchwords.$inject = ["$rootScope", "TrackingChannel", "SystemAlert", "LanguageUtils"];

  /**@ngInject */
  function uiSelectFacebookPages(fbUserDataProvider, $parse) {
      return {
        require: '?ngModel',
        link: function (scope, element, attrs, ngModel) {
          var channel_id = scope.channel.id;
          var provider = fbUserDataProvider.instance();
          provider.setDataModel(provider.modes.PAGE, ngModel);

          if (attrs.uiSelectFacebookPages) {
            scope.$watch(function () {
              return $parse(attrs.uiSelectFacebookPages)(scope);
            }, function (n) {
              if (n) {
                provider.getItems(element, channel_id);
              }
            });
          } else {
            provider.getItems(element, channel_id);
          }
        }
      };
    }
    uiSelectFacebookPages.$inject = ["fbUserDataProvider", "$parse"];

  /**@ngInject */
  function uiSelectFacebookGroups(fbUserDataProvider) {
      return {
        require: '?ngModel',
        link: function (scope, element, attrs, ngModel) {
          var channel_id = scope.channel.id;
          var provider = fbUserDataProvider.instance();
          provider.setDataModel(provider.modes.GROUP, ngModel);
          provider.getItems(element, channel_id);
        }
      };
    }
    uiSelectFacebookGroups.$inject = ["fbUserDataProvider"];

  /**@ngInject */
  function uiSelectFacebookEvents(fbUserDataProvider, $parse) {
      return {
        require: '?ngModel',
        link: function (scope, element, attrs, ngModel) {
          var channel_id = scope.channel.id;
          var provider = fbUserDataProvider.instance();
          provider.setDataModel(provider.modes.EVENT, ngModel);

          if (attrs.uiSelectFacebookEvents) {
            scope.$watch(function () {
              return $parse(attrs.uiSelectFacebookEvents)(scope);
            }, function (n) {
              if (n) {
                provider.getItems(element, channel_id);
              }
            });
          } else {
            provider.getItems(element, channel_id);
          }
        }
      };
    }
    uiSelectFacebookEvents.$inject = ["fbUserDataProvider", "$parse"];

  /**@ngInject */
  function uiTwitterHandle(TwitterHandle, TagsMessages) {
      return {
        require: '?ngModel',
        link: function (scope, element, attrs, ctrl) {
          TagsMessages.init(element);
          var sel = null;
          element.bind("change", function (e) {
            TagsMessages.spin();
            var val = element.select2('val');
            if (val.length != 0) {
              TwitterHandle.check({'twitter_handle': val}, function (res) {
                TagsMessages.showMessages(res);

                ctrl.$setViewValue(val[0]);
              }, function onError() {
                var labels = element.select2('data');
                labels[0]['text'] = "<span style='color:red'>" + e.added.text + ":error</span>";
                element.select2('data', labels);
              });
            } else {
              TagsMessages.showMessages(null);
              scope.$apply(function () {
                ctrl.$setViewValue("");
              });
            }
          });
          element.val(scope.$eval(attrs.ngModel));
          setTimeout(function () {
            sel = element.select2({
              tags: [], escapeMarkup: function (m) {
                return m;
              }, maximumSelectionSize: 1
            });
          });
        }
      };
    }
    uiTwitterHandle.$inject = ["TwitterHandle", "TagsMessages"];

  /**@ngInject */
  function uiSelectTagUsers($timeout, TrackingChannel, TwitterHandle, TagsMessages) {

      function format(item) {
        var text = item.text;
        if (item.invalid) {
          text = '<span style="color:red">_:ERROR</span>'.replace('_', text);
        }
        return text;
      }

      function tagsToObjects(val) {
        return _(val).map(function (v) {
          return {id: v, text: v, invalid: false}
        }).value();
      }

      function objectsToTags(objs) {
        return _(objs).filter(function (item) {
          return !item.invalid;
        }).map(function (item) {
          return item.id;
        }).value();
      }


      return {
        require: '?ngModel',
        link: function (scope, el, attrs, ctrl) {

          function valueToAngular() {
            var data = el.select2('data'),
              tags = objectsToTags(data);
            validate(tags);
            ctrl.$setViewValue(tags);
            if (scope.$$phase || scope.$root.$$phase) {
              return;
            }
            scope.$apply(function () {
              ctrl.$setViewValue(tags);
            });
          }

          function validate(value) {
            var isValid = !(attrs.required && _.isEmpty(value));
            ctrl.$setValidity('required', isValid);
            return isValid ? value : [];
          }

          function render() {
            var data = el.select2('data'),
              viewValue = ctrl.$viewValue;
            el.select2('data', angular.extend(tagsToObjects(viewValue), data));
          }

          ctrl.$render = render;
          ctrl.$formatters.push(validate);
          ctrl.$parsers.unshift(validate);

          TagsMessages.init(el);
          $timeout(function () {
            el.select2({
              tags: [],
              multiple: true,
              data: {results: []},
              query: function (query) {
                var data = {results: query.term ? tagsToObjects([query.term]) : []};
                query.callback(data);
              },
              formatResult: format,
              formatSelection: format,
              escapeMarkup: function (m) {
                return m;
              }
            });

            el.select2('data', ctrl.$modelValue);
            render();
          });

          el.bind("$destroy", function () {
            el.select2("destroy");
          });

          el.bind("change", function (e) {
            e.stopImmediatePropagation();
            if (e.added) {
              TagsMessages.spin();
              TwitterHandle.check({'twitter_handle': e.added.text}, function (res) {
                TagsMessages.showMessages(res);
                valueToAngular();
              }, function onError(res) {
                TagsMessages.showMessages(res.data);
                var data = el.select2('data'),
                  obj = _.find(data, function (item) {
                    return item.id == e.added.id;
                  });
                obj.invalid = true;
                el.select2('data', data);
              });
            } else if (e.removed) {
              TagsMessages.showMessages(null);
              valueToAngular();
            }
          });

          scope.$watch(attrs.ngModel, function (val, prev) {
            if (!val || val === prev) {
              return;
            }
            render();
          }, true);
        }

      };
    }
    uiSelectTagUsers.$inject = ["$timeout", "TrackingChannel", "TwitterHandle", "TagsMessages"];

  /**@ngInject */
  function uiSelectUsers(TrackingChannel, TwitterHandle, TagsMessages, $timeout, SystemAlert) {
      var noFoundMessage = 'Hit Enter or Tab to add a new value';
      var is_valid_handle = function (el) {
        return el.substring(0, 1) == '@'
      };

      function isEmpty(value) {
        return angular.isUndefined(value) || (angular.isArray(value) && value.length === 0) || value === '' || value === null || value !== value;
      }

      return {
        require: '?ngModel',
        link: function (scope, element, attrs, ngModel) {
          var validator = function (value) {
            if (attrs.required && _.isEmpty(value)) {
              //console.log("EMPTY!");
              ngModel.$setValidity('required', false);
              return;
            } else {
              //console.log("NOT EMPTY!");
              ngModel.$setValidity('required', true);
              return value;
            }
          };

          ngModel.$formatters.push(validator);
          ngModel.$parsers.unshift(validator);

          attrs.$observe('ngRequired', function () {
            validator(ngModel.$viewValue);
          });

          TagsMessages.init(element);
          if (scope.channel_id) {
            TrackingChannel.get_usernames({'channel_id': scope.channel_id},
              function (res) {
                var sel = element.select2({
                  formatNoMatches: function (term) {
                    return noFoundMessage
                  },
                  tags: [],
                  initSelection: function (element, callback) {
                    var data = [];
                    _.each(res.item, function (el) {
                      // Assert user name begins with '@'
                      //var is_valid = el.substring(0, 1) == '@';
                      if (is_valid_handle(el)) {
                        data.push({id: el, text: el});
                      }
                    });
                    callback(data);
                  },
                  escapeMarkup: function (m) {
                    return m;
                  }
                }).select2("val", res.item);
                scope.usernames = res.item;
                jQuery(sel).bind("change", function (e) {
                  TagsMessages.spin();
                  if (e.added) {
                    TwitterHandle.check({'twitter_handle': e.added.text}, function (res) {
                      TagsMessages.showMessages(res);
                      TrackingChannel.add_username({'username': e.added.text, 'channel_id': scope.channel_id});
                    }, function onError(err) {

                      console.log("CALL ERROR");
                      console.log(err);
                      TagsMessages.showMessages(err.data, e.added.text);
                      var labels = element.select2('data');
                      var indx = (_.indexOf(labels, e.added));
                      //labels[indx]['text'] = '<span style="color:red">' + e.added.text + ':ERROR' + '</span>';
                      labels.splice(indx, 1);
                      sel.select2('data', labels);
                    });
                  } else if (e.removed) {
                    //scope.usernames = scope.usernames.replace(e.removed.text.substring(1), '');
                    TagsMessages.showMessages(null);
                    TrackingChannel.remove_username(
                      {'username': e.removed.text, 'channel_id': scope.channel_id});
                    validator(ngModel.$viewValue);
                  }
                });

              }, function onError() {
                SystemAlert.error("Error getting users!");
              }
            );
          }
        }
      };
    }
    uiSelectUsers.$inject = ["TrackingChannel", "TwitterHandle", "TagsMessages", "$timeout", "SystemAlert"];

  /**@ngInject */
  function uiSelectReviewTeam(ComplianceReview, SystemAlert) {
      return {
        require: '?ngModel',
        link: function (scope, element, attrs, ngModel) {
          if (scope.channel && scope.channel.is_dispatchable && scope.channel_id) {
            ComplianceReview.fetchUsers({'channel_id': scope.channel_id},
              function (res) {
                var sel = element.select2({
                  tags: [],
                  initSelection: function (element, callback) {
                    callback(res.users);
                  },
                  query: function (options) {
                    //console.log(options);
                    if (ComplianceReview.lookupCache[options.term]) {
                      options.callback(ComplianceReview.lookupCache[options.term]);
                      return;
                    }

                    ComplianceReview.lookupUsers({term: options.term}, function (r) {
                      var result = {more: false, results: r.users};
                      ComplianceReview.lookupCache[options.term] = result;
                      options.callback(result);
                    });
                  }

                }).select2("val", res.users);

                jQuery(sel).bind("change", function (e) {
                  var params = {'channel_id': scope.channel_id};
                  if (e.added) {
                    params.users = [e.added.text];
                    ComplianceReview.addUsers(params, function (res) {
                      //console.log('added');
                    });
                  } else if (e.removed) {
                    params.users = [e.removed.text];
                    ComplianceReview.removeUsers(params, function (res) {
                      //console.log('removed');
                    });
                  }
                });
              }, function onError() {
                SystemAlert.error("Error getting users!");
              }
            );
          }
        }
      };
    }
    uiSelectReviewTeam.$inject = ["ComplianceReview", "SystemAlert"];

  /**@ngInject */
  function focusHere($timeout) {
      return {
        link: function (scope, element, attrs) {
          $timeout(function () {
            element.focus();
          }, 100);
        }
      }
    }
    focusHere.$inject = ["$timeout"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('NavCtrl', NavCtrl);

  /** @ngInject */
  function NavCtrl($scope, $rootScope, $route, AccountsService, $window) {
    $rootScope.$on(AccountsService.ACCOUNTS_EVENT, function () {
      $scope.currentAccount = AccountsService.getCurrent();
    });

    $scope.getScrollHeight = function () {
      return $window.innerHeight - 45;
    };

    $scope.layout = {
      slimscroll: {
        height: $scope.getScrollHeight + 'px',
        width: '210px',
        wheelStep: 25
      }
    };

    $rootScope.$on('$viewContentLoaded', function (e) {
      $scope.current = $route.current.name;
    });

    $scope.getCurrent = function (name) {
      return $scope.current && $scope.current === name ? 'active' : '';
    };
  }
  NavCtrl.$inject = ["$scope", "$rootScope", "$route", "AccountsService", "$window"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('ACLCtrl', ACLCtrl);

  /** @ngInject */
  function ACLCtrl($scope, ACLService, DialogService, AccountsService, ConfigureAccount) {
    $scope.sharingTitle = function () {
      var n = " ", p = "";
      if ($scope.objectIds.length > 1) {
        n = " " + $scope.objectIds.length + " ";
        p = "s";
      }
      var title = {
        'bookmark': 'Sharing{n}Bookmark{p}',
        'channel': 'Sharing{n}Channel{p}',
        'SmartTag': 'Sharing{n}Smart Tag{p}',
        'ContactLabel': 'Sharing{n}Contact Label{p}',
        'account': 'Add Users to Account',
        'matchable': 'Sharing{n}Message{p}',
        'group': 'Sharing{n}Group{p}'
      }[$scope.shareDialogScope];
      if (title)
        return title.replace('{n}', n).replace('{p}', p);
      else
        return "";
    };

    $scope.usersAndPermsList = [];
    $scope.groupsAndPermsList = [];
    $scope.objectIds = [];

    $scope.addPermsList = [{id: 'r', name: 'Can view'}, {id: 'rw', name: 'Can edit'}];
    $scope.editPermsList = [{id: 'r', name: 'Can view'}, {id: 'rw', name: 'Can edit'}, {id: 'd', name: 'Delete'}];
    $scope.permission = 'r';
    $scope.newUsers = '';
    $scope.currentAccount = AccountsService.getCurrent();

    // fetch all users for account and populate newUsers with users with whom channel is not shared
    $scope.fetchUsersForAccount = function (account) {
      ConfigureAccount.getUsers({account: account.id}, function (result) {
        $scope.newUsers = [];
        $scope.errorMessages = [];
        angular.forEach(result.users, function (u) {
          // do not push if user is already in usersAndPermsList or is superuser
          if (u.perm != 's' && !_.find($scope.usersAndPermsList, function (u_shared) {
              return u_shared.email == u.email
            })) {
            $scope.newUsers.push(u.email);
          }
        });
        $scope.newUsers = $scope.newUsers.join(', ');
      });
    };

    $scope.addPeople = function () {
      if (!$scope.newUsers) return;
      var newPeopleList = $scope.newUsers.split(/[,;:\s\n\t]+/);
      newPeopleList = _.uniq(newPeopleList);
      var existEmails = _.pluck($scope.usersAndPermsList, 'email');

      _.each(newPeopleList, function (email) {
        if (email && $scope.addPermission) {  // if email is valid and permission set
          var userPerm = {
            email: email,
            perm: $scope.addPermission,
            isChanged: true,
            isNew: true
          };

          if (!_.include(existEmails, email))
            $scope.usersAndPermsList.push(userPerm);
        }
      });
    };

    var findChanged = function (lst) {
      var changed = _.filter(lst, function (item) {
        return item.isChanged
      });
      return _.map(changed, function (item) {
        var o = {
          perm: item.perm,
          is_new: item.isNew
        };
        if (item.hasOwnProperty('email')) { //user
          o.email = item.email;
        } else { //group
          o.id = item.id;
        }
        return o;
      })
    };

    $scope.shareAndSave = function () {
//        var changedUsersList = _.filter($scope.usersAndPermsList, function(u) { return u.isChanged });
//        changedUsersList = _.map(changedUsersList, function(u) {
//            return u.email + ':' + u.perm + ':' + (u.isNew ? 'add' : 'change');
//        });

      ACLService.shareAndSave({
        up: findChanged($scope.usersAndPermsList),
        gp: findChanged($scope.groupsAndPermsList),
        id: $scope.objectIds,
        ot: $scope.shareDialogScope
      }, function (result) {
        if (result)
          $scope.modalShown = false;
      });
    };

    var loaded = function (result) {
      if (!(result.users || result.groups)) {
        // no permission or other error
        $scope.modalShown = false;
        return;
      }
      $scope.usersAndPermsList = [];
      $scope.usersAndPermsList = _.map(result.users, function (item) {
        var u = item;
        u.isChanged = false;
        u.isNew = false;
        return u;
      });

      $scope.groupsAndPermsList = _.map(result.groups, function (g) {
        g.isChanged = false;
        g.isNew = false;
        return g;
      });

      $scope.fetchUsersForAccount($scope.currentAccount);
    };

    $scope.load = function () {
      ACLService.getUsersAndPerms({ot: $scope.shareDialogScope, id: $scope.objectIds}, loaded);
    };

    $scope.$on(DialogService.OPEN_DIALOG_EVENT, function (evt, data) {
      if (data.target == 'acl') {
        $scope.objectIds = data.objectIds;
        $scope.shareDialogScope = data.objectType;

        $scope.errorMessage = "";
        $scope.modalShown = true;
        $scope.load();
      }
    });

    $scope.$watch('modalShown', function (visible, old) {
      if (!visible) {
        DialogService.closeDialog({dialog: 'acl', ot: $scope.shareDialogScope, id: $scope.objectIds});
      }
    });

    //tabs
    $scope.tab = 'users';
    $scope.switchTab = function (tab) {
      $scope.tab = tab;
    };
    $scope.css_tab = function (tab) {
      if ($scope.tab == tab) return 'active';
      return '';
    };

  }
  ACLCtrl.$inject = ["$scope", "ACLService", "DialogService", "AccountsService", "ConfigureAccount"];

})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/accounts', {
          templateUrl: '/partials/accounts/list',
          controller: 'AccountsCtrl',
          name: 'accounts'
        })
        .when('/accounts/:account_id', {
          templateUrl: '/partials/accounts/edit',
          controller: 'AccountEditCtrl',
          name: 'account'
        })
        .when('/new_account', {
          templateUrl: '/partials/accounts/new_account',
          controller: 'AccountsCtrl',
          name: 'account'
        })
    }])
    .value('uiJqConfig', {
      datepicker: {
        dateFormat: 'dd/MM/YY'
      }
    })
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('PackageDetailsMixin', PackageDetailsMixin);

  /** @ngInject */
  function PackageDetailsMixin() {
    var defaultPackageDetails = {
        'Bronze': false,
        'Silver': false,
        'Gold': false,
        'Platinum': false
      },
      mixin = {
        notInternalAccount: false,
        show_pricing_package_details: defaultPackageDetails,
        onPackageChange: onPackageChange
      };

    function onPackageChange(val) {
      if (!val) {
        return;
      }
      var self = this;
      self.notInternalAccount = val != 'Internal';
      _.forEach(self.show_pricing_package_details, function (val, key) {
        self.show_pricing_package_details[key] = false;
      });
      self.show_pricing_package_details[val] = true;
    }

    return mixin;
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .directive('checkAccountEndDate', checkAccountEndDate);

  /** @ngInject */
  function checkAccountEndDate() {
    var name = 'checkAccountEndDate',
      packageOption = null;

    return {
      require: 'ngModel',
      link: function (scope, elm, attrs, ctrl) {
        function endDateIsValid(date, packageOption) {
          var now = new Date();
          return (packageOption != 'Trial' || date && new Date(date) > now);
        }

        function validateSelf(viewValue) {
          if (endDateIsValid(viewValue, packageOption)) {
            ctrl.$setValidity(name, true);
            return viewValue;
          } else {
            ctrl.$setValidity(name, false);
            return undefined;
          }
        }

        function validateAccount(acct) {
          packageOption = acct && acct.package;
          ctrl.$setValidity(name, endDateIsValid(ctrl.$modelValue, packageOption));
        }

        ctrl.$parsers.unshift(validateSelf);
        scope.$watch(attrs[name], validateAccount, true);
      }
    };
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('AccountEditCtrl', AccountEditCtrl);

  /** @ngInject */
  function AccountEditCtrl($scope, $http, $routeParams, $window, $modal, $filter, $timeout,
                           FilterService,
                           StaffUsersService,
                           AccountHelper,
                           AccountsService,
                           ChannelsRest,
                           DialogService,
                           SystemAlert,
                           PackageDetailsMixin) {
    var _ChannelsRest = new ChannelsRest();

    angular.extend($scope, AccountHelper);
    angular.extend($scope, angular.copy(PackageDetailsMixin));

    $scope.alertCandidateEmails = [];
    $http.get('/alert_user_candidates', {}).success(function (data) {
      $scope.alertCandidateEmails = data.list;
    });

    $scope.account = null;
    $scope.channels = [];
    $scope.staff_users = {};
    $scope.account_id = $routeParams.account_id;

    FilterService.setDateRangeByAlias('this_month');
    $scope.dateRange = FilterService.getDateRange();

    $scope.$watch('account.package', $scope.onPackageChange.bind($scope));

    $scope.$watch('account.account_type', function (nVal) {
      // ng-options accountTypeOptions is not observing ng-model account.account_type
      // See https://github.com/angular/angular.js/issues/8651
      // Workaround to trigger change in accountTypeOptions
      var _poped = $scope.accountTypeOptions.pop();
      $timeout(function () {
        $scope.accountTypeOptions.push(_poped);
      });
    });

    $scope.getCurrentAccount = function () {
      return AccountsService.get({account_id: $scope.account_id, stats: true}, function (res) {
        var account = res.account || (res.data && res.data[0]);
        if (account) {
          $scope.setCurrentAccount(account);
          return account;
        }
      })
    };

    $scope.executeAccountStatus = function () {
      $scope.account.is_locked ? lock() : unlock();
    };

    $scope.channelsTable = {
      sort: {
        predicate: 'title',
        reverse: false
      }
    };


    function lock() {
      $http.post("/account/lock", {id: $scope.account_id})
        .success(function (data, status, headers, config) {
          $scope.getCurrentAccount();
        })
        .error(function (data, status, headers, config) {
          console.log(data);
        });
    }

    function unlock() {
      $http.post("/account/unlock", {id: $scope.account_id})
        .success(function (data, status, headers, config) {
          $scope.getCurrentAccount();
        })
        .error(function (data, status, headers, config) {
          console.log(data);
        });
    }

    var openAuditModal = function (data, accountId) {
      var d = $modal.open({
        backdrop: true,
        keyboard: true,
        templateUrl: '/partials/audit/auditModal',
        controller: ["$scope", function ($scope) {
          $scope.audit = {loading: false};
          $scope.data = data.data;
          $scope.cursor = data.cursor;
          $scope.close = $scope.$close;
          $scope.loadMoreAccountEvents = function () {
            if ($scope.audit.loading) return;
            $scope.audit.loading = true;
            return $http.post("/account/events", {id: accountId, cursor: $scope.cursor}).success(function (data) {
              $scope.data.push.apply($scope.data, data.data);
              $scope.cursor = data.cursor;
              $scope.audit.loading = false;
            });
          }
        }]
      });
      //return d.result;
    };

    $scope.showAuditTrail = function () {
      $http.post("/account/events", {id: $scope.account_id}).success(function (data, status, headers, config) {
        openAuditModal(data, $scope.account_id);
      }).error(function (data, status, headers, config) {
        console.log(data);
      });
    };


    $scope.setCurrentAccount = function (account) {

      if ((account != null) && (account != $scope.account)) {
        account.end_date = account.end_date ? new Date(account.end_date).format('mm/dd/yyyy') : '';  // merger: prefer this
        $scope.account = account;
        $scope.fetchChannels();
        $scope.fetchStaffUsers();
        AccountsService.accountUpdate(account);
      }
    };

    $scope.getCurrentAccount();

    $scope.fetchChannels = function () {
      //console.log("Fetching channels");
      var postData = {
        widget: false,
        stats: true,
        from: $scope.dateRange.from,
        to: $scope.dateRange.to,
        account: $scope.account_id
      };
      _ChannelsRest.fetchChannels(postData).success(function (res) {
        $scope.channels = res.list;
      });
    };

    $scope.fetchStaffUsers = function () {
      return StaffUsersService.query(function (res) {
        $scope.staff_users = res.users;
      });
    };

    $scope.update = function (reload) {
      return AccountsService.update($scope.account).$promise.then(function () {
        //SystemAlert.success("The Account '{name}' has been updated".replace('{name}', $scope.account.name), 5000);
        $window.location.href = '/configure#/accounts/';
        if (reload) {
          $window.location.reload(true);
        }
      });
    };

    $scope.isChannelsEmpty = function () {
      return angular.equals([], $scope.channels);
    };

    $scope.createAccount = function () {
      $window.location.href = '/configure#/new_account';
    };

    $scope.createChannel = function () {
      $window.location.href = '/configure#/new_channel';
    };

    $scope.$on(DialogService.CLOSE_DIALOG_EVENT, function (evt, data) {
      if (data.dialog == 'account') {
        AccountsService.accountUpdate(data.account);
        if (data.fromPage != '/configure#/accounts/') {
          setTimeout(function () {
            // let the popup close
            $window.location.href = "/configure#/accounts/";
          }, 0);
        }
      }
    });
  }
  AccountEditCtrl.$inject = ["$scope", "$http", "$routeParams", "$window", "$modal", "$filter", "$timeout", "FilterService", "StaffUsersService", "AccountHelper", "AccountsService", "ChannelsRest", "DialogService", "SystemAlert", "PackageDetailsMixin"];
})();

(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('AccountsCtrl', AccountsCtrl);

  /** @ngInject */
  function AccountsCtrl($route, $scope, $timeout, $http, $modal, SystemAlert,
                        AccountHelper, AccountsService, AppState, DialogService, FilterService) {

    angular.extend($scope, AccountHelper);

    $scope.table = {
      sort: {
        predicate: 'name',
        reverse: false
      }
    };

    $scope.filters = {
      name: ''
    };

    var getSelectedItems = function () {
      return _.filter($scope.accounts, function (item) {
        return item['is_selected'];
      });
    };

    var findItems = function (param) {
      var update = [];
      if (param) {
        update = [param];
      } else {
        update = getSelectedItems();
      }
      return update;
    };

    $scope.dateRange = FilterService.getDateRange();

    $scope.showDeleteConfirmIf = function (account) {
      return account.channels_count == 0 && account.users_count > 0;
    };

    $scope.$on(DialogService.CLOSE_DIALOG_EVENT, function (evt, data) {
      if (data.dialog == 'account') {
        AccountsService.accountUpdate(data.account);
        applyAccounts();
      } else if (data.dialog == 'acl') {
        var acctId = data.id[0];
        if (acctId)
        // TODO: reload only account with acctId
          $scope.fetchAccounts();
      }
    });

    $scope.loadAccounts = function (dates) {
      $scope.dateRange = dates;
      $scope.fetchAccounts();
    };

    $scope.changeDate = function () {
      AppState.store('configureAccountsDateRange', $scope.dateRangeObj);
      FilterService.updateDateRange($scope.dateRangeObj);
      $scope.dateRange = FilterService.getDateRange();
      $scope.fetchAccounts();
    };

    $scope.fetchAccounts = function () {
      var postData = {
        stats: true,
        from: $scope.dateRange.from,
        to: $scope.dateRange.to
      };
      AccountsService.query(postData, applyAccounts);
    };

    $scope.createAccount = function () {
      //console.log("new account");
      var newAcct = {
        account_type: 'Native',
        "package": 'Internal'
      };
      DialogService.openDialog({action: 'create', target: 'account', account: newAcct});
    };

    $scope.deleteAccount = function (account) {
      AccountsService.delete({id: account.id}, function () {
        AccountsService.accountUpdate(account, 'delete');
        applyAccounts();
      });
    };

    $scope.switchAccount = function (account) {
      $scope.selectedAccount = account;
      // Switch the selected account to the current
      AccountsService.switchAccount(account, $route.reload);
    };

    $scope.manageUsers = function (account) {
      var update = findItems(account),
        ids = _.pluck(update, 'id');
      if (!ids.length) return;
      DialogService.openDialog({target: 'acl', objectType: 'account', objectIds: ids});
    };

    $scope.$on(AccountsService.ACCOUNTS_EVENT, applyAccounts);
    $scope.fetchAccounts();

    function applyAccounts() {
      $timeout(function () {
        $scope.selectedAccount = AccountsService.getCurrent();
        $scope.accounts = AccountsService.getList();
        _.each($scope.accounts, function (item) {
          item.is_selected = item.id === $scope.selectedAccount.id;
        });
      }, 0);
    }

    var openEmailModal = function (data) {
      var d = $modal.open({
        backdrop: true,
        keyboard: true,
        templateUrl: '/partials/accounts/send_email',
        controller: ["$scope", function ($scope) {
          $scope.data = data.data;
          $scope.close = $scope.$close;

          $scope.chosen = {
              accounts: [],
              roles: [],
              templateIdx: null,
              subject: '',
              body: ''
          };

          $scope.$watch('chosen.templateIdx', function (n) {
              if (n === null) {
                  return;
              }
              var _chosenTemplate = $scope.data.templates[n];
              $scope.chosen.subject = _chosenTemplate.subject;
              $scope.chosen.body = _chosenTemplate.body;
          });

          $scope.sendMail = function () {
              $http.post('/account/send-mail', {
                  accounts: $scope.chosen.accounts,
                  roles: $scope.chosen.roles,
                  subject: $scope.chosen.subject,
                  body: $scope.chosen.body
              })
              .success(function (data) {
                  SystemAlert.success("Email notification has been sent to {count} user."
                                       .replace('{count}', data.recipients.length),
                                       2000);
                  $timeout(function () {
                      $scope.close();
                  }, 2000);
              });
          };
        }]
      });
    };

    $scope.showEmailForm = function () {
      $http.get("/account/email-data").
        success(function (data, status, headers, config) {
          openEmailModal(data);
        }).
        error(function (data, status, headers, config) {
          console.log(data);
        });
    };
  }
  AccountsCtrl.$inject = ["$route", "$scope", "$timeout", "$http", "$modal", "SystemAlert", "AccountHelper", "AccountsService", "AppState", "DialogService", "FilterService"];
})();

(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('ConfigureAccountCtrl', ConfigureAccountCtrl);

  /** @ngInject */
  function ConfigureAccountCtrl($scope, $resource, $routeParams,
                                AccountsService, ACLService,
                                ConfigureAccount,
                                DialogService,
                                SystemAlert) {
    $scope.users = [];
    $scope.selectedAccount = '';
    $scope.accountsList = []; // All accounts available to this user.
    $scope.editableAccountsList = []; // The accounts that this user has edit rights to.

    $scope.editPermsList = [{id: 'r', name: 'Can view'}, {id: 'rw', name: 'Can edit'}, {id: 'd', name: 'Delete'}];
    $scope.permsList = [{id: 'r', name: 'Can view'}, {id: 'rw', name: 'Can edit'}];
    $scope.newUserPermission = 'r';
    $scope.state = 'normal';
    $scope.accountId = $routeParams.acct_id;
    $scope.NOAccount = null;

    $scope.fetchUsers = function () {
      $scope.users = [];
      angular.forEach($scope.accountsList, function (acc) {
        if ($scope.NOAccount == null || acc.id != $scope.NOAccount.id) {
          $scope.fetchUsersForAccount(acc);
        }
      });
      if ($scope.NOAccount != null) {
        $scope.fetchOrphanedUsers();
      }
    };

    $scope.fetchUsersForAccount = function (account) {
      ConfigureAccount.getUsers({account: account.id}, function (result) {
        $scope.errorMessages = [];
        angular.forEach(result.users, function (u) {
          u.origPerm = u.perm;
          u.action = 'change';
          if (account.is_admin) {
            // This user will be editable, so make sure he can only be moved to account with permission
            u.currentAccount = _.find($scope.editableAccountsList, function (item) {
              return item.id == u.currentAccount.id;
            });
          } else {
            // This user will only be viewable, pick account from entire account list
            u.currentAccount = _.find($scope.accountsList, function (item) {
              return item.id == u.currentAccount.id;
            });
          }
          $scope.users.push(u);
        });
      }, function onError() {
        // no permission or other error
        $scope.accountsList = _.filter($scope.accountsList, function (acc) {
          return acc.id != account.id;
        });
      });
    };

    $scope.fetchOrphanedUsers = function () {
      $resource("/configure/users/json", {}).get({orphaned: true}, function (res) {
        angular.forEach(res.result, function (orphan) {
          orphan.origPerm = -1;
          orphan.perm = -1;
          orphan.action = 'change';
          var NO_ACCOUNT = orphan.accounts[0];
          orphan.currentAccount = _.find($scope.accountsList, function (item) {
            return item.id == NO_ACCOUNT.id;
          });
          $scope.users.push(orphan);
        });
      });
    };

    $scope.loadAccountsList = function () {
      AccountsService.get({}, function (res) {
        $scope.accountsList = res.data;
        $scope.editableAccountsList = _.filter($scope.accountsList, function (item) {
          return item.is_admin;
        });
      }).$promise.finally(function () {
        AccountsService.noAccount({}, function (res) {
          $scope.accountsList.push(res.account);
          $scope.editableAccountsList.push(res.account);
          $scope.NOAccount = res.account;
        }).$promise.finally(function () {
          $scope.selectedAccount = _.find($scope.accountsList, function (item) {
            return item.name == $scope.accountName;
          });
          $scope.fetchUsers();
        });
      });
    };

    $scope.EMAIL_REGEXP = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}$/; //Same regex that angular uses

    $scope.addUsers = function (emails) {
      if (!$scope.newUsers) return;
      if (!$scope.selectedAccount) return;
      var emails = _.uniq($scope.newUsers.split(/[,;:\s\n\t]+/));
      var existEmails = _.pluck($scope.users, 'email');
      var usersInfo = [];
      _.each(emails, function (email) {
        if ($scope.EMAIL_REGEXP.test(email)) {
          if (email && $scope.newUserPermission && !_.include(existEmails, email)) {  // if email is valid and permission set
            usersInfo.push(email + ':' + $scope.newUserPermission + ':' + 'add');
          } else if (_.include(existEmails, email)) {
            angular.forEach($scope.users, function (u) {
              if (u.email == email) {
                if (u.action == 'change') {
                  $scope.setUserAccount(u, $scope.selectedAccount);
                  usersInfo.push(email + ':' + $scope.newUserPermission + ':' + 'change');
                } else {
                  // u.currentAccount = $scope.selectedAccount;
                  usersInfo.push(email + ':' + $scope.newUserPermission + ':' + 'add');
                }
              }
            });
          }
        } else {
          SystemAlert.info("Invalid email " + email + " will be ignored.");
        }

      });
      ACLService.shareAndSave({
        up: usersInfo,
        id: [$scope.selectedAccount.id],
        ot: 'account'
      }, function (result) {
        $scope.fetchUsers();
      });
      $scope.newUsers = "";
    };

    $scope.filterAccount = function (user) {
      var ret = (user.currentAccount != undefined && $scope.selectedAccount.id == user.currentAccount.id);
      //console.log(ret);
      return ret;
    };

    $scope.saveButtonDisabled = function () {
      var changedUsersList = _.filter($scope.users, function (u) {
        return u.perm != u.origPerm
      });
      return !(changedUsersList && changedUsersList.length);
    };

    $scope.isEditDisabled = function (isCurrentSuper, currentUserEmail, targetUser) {
      if (targetUser.perm == 's' && currentUserEmail != targetUser.email) {
        // One super user should not be able to reset the password of another
        return true;
      }
      if (!isCurrentSuper && targetUser.perm == 's') {
        // A regular user should not be able to reset password of superuser
        return true;
      }
      return false;
    };

    $scope.resetPassword = function (email) {
      DialogService.openDialog({dialog: 'password_change', email: email});
    };

    /*
     * Do a sync in database, setting the currently selected user account as users current account.
     * Called on any change in the 'Account select' entry from the collections table.
     */
    $scope.setCurrentAccount = function (user) {
      $scope.setUserAccount(user, user.currentAccount);
    };

    /*
     * Change the permissions for this given user, on his current account.
     */
    $scope.changePermissions = function (user) {
      var userInfo = user.email + ':' + user.perm + ':' + user.action;
      ACLService.shareAndSave({
        up: [userInfo],
        id: [user.currentAccount.id],
        ot: 'account'
      }, function (result) {
        $scope.fetchUsers();
      });
    };

    /*
     * For a give user, set account as the current one.
     */
    $scope.setUserAccount = function (user, account) {
      if (!(account.is_admin || account.is_super)) {
        SystemAlert.info("You only have view permissions in account " + account.name + "!");
      }
      if (user.action == 'change') {
        if ($scope.NOAccount == null || account.id != $scope.NOAccount.id) {
          // Switch from one account to another. Either keep the permissions
          // or in case we brough a user from NO_ACCOUNT'land give him the
          // permissions that are currently set for new users.
          var perm = user.perm;
          if (user.perm == -1) perm = $scope.newUserPermission; // Switched from NO_ACCOUNT land
          ConfigureAccount.save({
            account_id: account.id,
            email: user.email,
            perms: perm
          }, function (res) {
            user.origPerm = $scope.newUserPermission;
            user.perm = $scope.newUserPermission;
            user.currentAccount = globals.account;
          });
        } else {
          // We just switched a user to NO_ACCOUNT land. Remove his current account.
          $resource("/configure/accounts/remove", {}).save({email: user.email},
            function (res) {
              user.perm = -1;
              user.origPerm = -1;
            });
        }
      }
    };

    $scope.editUser = function (user) {
      DialogService.openDialog({target: 'user_edit', email: user.email});
    };

    $scope.$on(DialogService.CLOSE, function (event, data) {
      if (data.target == 'user_edit') {
        $scope.fetchUsers();
      }
    });

    $scope.loadAccountsList();
  }
  ConfigureAccountCtrl.$inject = ["$scope", "$resource", "$routeParams", "AccountsService", "ACLService", "ConfigureAccount", "DialogService", "SystemAlert"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateUpdateDialogCtrl', CreateUpdateDialogCtrl);

  /** @ngInject */
  function CreateUpdateDialogCtrl($window, $scope, DialogService, AccountHelper, AccountsService, PackageDetailsMixin) {
    $scope.action = 'create';
    $scope.modalShown = false;

    angular.extend($scope, AccountHelper);
    angular.extend($scope, PackageDetailsMixin);
    $scope.$watch('account.package', $scope.onPackageChange.bind($scope));

    $scope.$on(DialogService.OPEN_DIALOG_EVENT, function (evt, data) {
      if (data.target == 'account') {
        //Clear form
        $scope.accountForm.$setPristine(true);
        $scope.action = data.action;
        $scope.account = data.account || {
            account_type: "Native",
            "package": "Internal"
          };
        $scope.errorMessage = "";
        $scope.modalShown = true;
      }
    });

    $scope.save = function () {
      var Request = AccountsService['save'];

      Request($scope.account, function (res) {

        $scope.accountForm.$setPristine(true);
        //SystemAlert.success("The Account '{name}' has been created"
        //    .replace('{name}', $scope.account.name), 5000);

        $window.location.href = '/configure#/accounts/';
      });
    };

    $scope.close = function () {
      $scope.modalShown = false;
    }
  }
  CreateUpdateDialogCtrl.$inject = ["$window", "$scope", "DialogService", "AccountHelper", "AccountsService", "PackageDetailsMixin"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('UpdateAccountCtrl', UpdateAccountCtrl);

  /** @ngInject */
  function UpdateAccountCtrl($log,
                             $scope,
                             $routeParams,
                             $location,
                             $http,
                             ConfigureAccount,
                             AccountHelper,
                             SystemAlert) {

    angular.extend($scope, AccountHelper);
    $scope.account = null;
    $scope.account_id = $routeParams.account_id;
    $scope.package = "Internal";
    $scope.span_bronze = false;
    $scope.span_silver = false;
    $scope.span_gold = false;
    $scope.span_platinum = false;


    $scope.$watch('package', function () {
      if ($scope.package == "Bronze") {
        $scope.span_bronze = true;
        $scope.span_silver = false;
        $scope.span_gold = false;
        $scope.span_platinum = false;
      }
      else if ($scope.package == "Silver") {
        $scope.span_bronze = false;
        $scope.span_silver = true;
        $scope.span_gold = false;
        $scope.span_platinum = false;
      }
      else if ($scope.package == "Gold") {
        $scope.span_bronze = false;
        $scope.span_silver = false;
        $scope.span_gold = true;
        $scope.span_platinum = false;
      }
      else if ($scope.package == "Platinum") {
        $scope.span_bronze = false;
        $scope.span_silver = false;
        $scope.span_gold = false;
        $scope.span_platinum = true;
      }
      else {
        $scope.span_bronze = false;
        $scope.span_silver = false;
        $scope.span_gold = false;
        $scope.span_platinum = false;
      }
    });

    $scope.load = function () {
      return ConfigureAccount.fetch({accountId: $scope.account_id}, function (res) {
        var data = res.data;
        $scope.account_id = data.accountId;
        $scope.account_name = data.accountName;
        $scope.account_type = data.accountType;
        $scope.package = data.pricingPackage;
        $scope.oauth = data.hasoAuth;
      }, function onError(res) {
        if (!res.error) {
          SystemAlert.error("No channel found!");
        }
      });
    };
    $scope.load();

    $scope.update = function () {
      return ConfigureAccount.update(
        {
          accountId: $scope.account_id,
          accountName: $scope.account_name,
          accountType: $scope.account_type,
          pricingPackage: $scope.package
        },
        function () {
          $location.path('/accounts/');
        });
    };

    $scope.setupSalesforce = function () {
      var url = "/accounts/salesforce/" + $scope.account_id;
      var windowName = "Salesforce";
      var windowSize = "width=700,height=500,scrollbars=yes";
      $scope.salesforcePopup = window.open(url, windowName, windowSize);
      var watchClose = setInterval(function () {
        try {
          if ($scope.salesforcePopup.closed) {
            clearTimeout(watchClose);
            $scope.load();
            $scope.salesforcePopup = null;
          }
        } catch (e) {
          $log.error(e);
        }
      }, 1000);
    };

    $scope.disableSalesforce = function () {
      var url = "/accounts/salesforcerevoke/" + $scope.account_id;
      $http({
        method: 'POST',
        url: url
      }).error(function (data) {
        SystemAlert.error(data.message);
      }).finally(function () {
        $scope.load();
      });
    };
  }
  UpdateAccountCtrl.$inject = ["$log", "$scope", "$routeParams", "$location", "$http", "ConfigureAccount", "AccountHelper", "SystemAlert"];;
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/channels', {
          templateUrl: '/partials/channels/list',
          controller: 'ChannelsListCtrl',
          name: 'channels'
        })
        .when('/new_channel', {
          templateUrl: '/partials/channels/new_channel2',
          controller: 'ChannelConfigureCtrl',
          name: 'channels'
        })

        .when('/new_channel/no-channels', {
          templateUrl: '/partials/channels/new_channel2',
          controller: 'ChannelConfigureCtrl',
          name: 'channels-no-channels'
        })

        .when('/update_channel/:channel_id', {
          templateUrl: '/partials/channels/update_channel',
          controller: 'UpdateChannelCtrl',
          name: 'channels'
        })
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('CompoundChannelService', CompoundChannelService);

  /** @ngInject*/
  function CompoundChannelService($rootScope, ChannelsRest) {
    var _ChannelsRest = new ChannelsRest();
    var sharedService = {
      compound: null,
      LOADED: "ChannelsLoadedEvent",
      CHANGED: "PrimitiveChannelsListChanged",
      channels: [],
      channelsOptions: [],
      channelsByPlatform: {},
      channelsById: {},
      channelsByDispatchability: {}
    };

    var pluckChannelData = function (item) {
      return {
        id: item.id,
        title: item.title
      }
    };

    sharedService.isReady = function () {
      return !!sharedService.channels.length;
    };

    sharedService.prepare = function () {
      if (sharedService.isReady()) {
        $rootScope.$broadcast(sharedService.LOADED);
        return;
      }

      var res = _ChannelsRest.fetchChannels({primitive: true}, function () {
        sharedService.channels = res.list;
        sharedService.channelsOptions = _.map(sharedService.channels, pluckChannelData);
        sharedService.channelsByPlatform = _.groupBy(sharedService.channels, 'platform');
        sharedService.channelsById = _.groupBy(sharedService.channels, 'id');
        sharedService.channelsByDispatchability = _.groupBy(sharedService.channels, 'is_dispatchable');
        $rootScope.$broadcast(sharedService.LOADED);
      });
    };

    sharedService.setCompound = function (channel) {
      if (channel.is_compound || channel.is_service) {
        sharedService.compound = channel;
      }
    };

    sharedService.primitivesChanged = function (data) {
      $rootScope.$broadcast(sharedService.CHANGED, data);
    };

    sharedService.filterOptionsByPlatform = function (options, force, dispatchable) {
      //filter channel options by platform of the first channel in the selected list
      if (options.selected.length == 0) {
        if (arguments.length <= 2) {
          options.options = sharedService.channelsOptions;
        } else {
          options.options = _.map(sharedService.channelsByDispatchability[dispatchable], pluckChannelData);
        }
      } else if (options.selected.length == 1 || force) {
        // show channels of all available platforms
        var selected = options.selected[0],
          channel = sharedService.channelsById[selected][0],
          platform = channel.platform,
          is_dispatchable = channel.is_dispatchable; // should equal dispatchable

        var channels = sharedService.channelsByPlatform[platform];
        if (arguments.length == 3) {
          channels = _.filter(channels, function (item) {
            return item.is_dispatchable === dispatchable;
          });
        }

        options.options = _.map(channels, pluckChannelData);
      }
      return options;
    };

    return sharedService;
  }
  CompoundChannelService.$inject = ["$rootScope", "ChannelsRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('ChannelConfigureCtrl', ChannelConfigureCtrl);

  /** @ngInject */
  function ChannelConfigureCtrl($location,
                                $resource,
                                $rootScope,
                                $route,
                                $routeParams,
                                $scope,
                                $window,
                                AccountsService,
                                ChannelsRest,
                                CompoundChannelService,
                                FilterService,
                                SocialService,
                                SystemAlert) {

    var _ChannelsRest = new ChannelsRest();
    var updateData = {};
    $scope.channel_types = [];
    $scope.channel_name = '';
    $scope.channel_description = '';
    $scope.channel_id = null;
    $scope.channel = {};
    $scope.intentions_filter = FilterService.getIntentions();

    $scope.moderated_intention_threshold = 0;
    $scope.auto_reply_intention_threshold = 1;
    $scope.moderated_relevance_threshold = 0;
    $scope.auto_reply_relevance_threshold = 1;

    $scope.twitter_test_option = 'account';
    $scope.twitter_handle = null;

    AccountsService.query({}, function (res) {
      $scope.accounts = _.sortBy(_.pluck(res.data, 'name'), function (item) {
        return item.toLowerCase();
      });
      $scope.accountsObjs = angular.copy(res.data);

      if ($routeParams.account_id) {
        $scope.account = _.find($scope.accountsObjs, function (item) {
          return item.id == $routeParams.account_id;
        });
      } else {
        $scope.account = AccountsService.getCurrent();
      }
    });

    var ChannelTypes = $resource('/configure/channel_types/json', {}, {
      fetch: {method: 'GET', isArray: false}
    });

    $scope.channel_type = null;

    $scope.load = function () {
      var res = ChannelTypes.fetch({}, function () {
        $scope.channel_types = _.sortBy(res.list, 'title');
      }, function onError() {
        SystemAlert.error("Error loading channel types!");
      });

    };

    $scope.$watch('channel_type', function (newValue, oldValue) {
      if ((newValue == 'compound' || newValue == 'service') && newValue != oldValue) {
        CompoundChannelService.prepare();

        $scope.$on(CompoundChannelService.CHANGED, function (event, data) {
          _.forEach(data, function (item) {
            $scope.update_params[item.key] = item.value;
          });
        });
      }
    });


    $rootScope.$on('$viewContentLoaded', function (e) {
      if ($route.current.name == 'channels-no-channels') {
        $scope.isNoChannels = true;
      }
    });

    $scope.$on(SocialService.POPUP_CLOSE, function (evt, data) {
      if (data.type == 'twitter') {
        // popup closed - fetch profile
        $scope.getTwitterProfile();

      } else {
        $scope.getFacebookProfile();

      }
    });

    $scope.getTwitterProfile = function () {
      SocialService.twitterGetProfile($scope.channel_id, function (res) {
        $scope.twitter_profile = res.twitter_profile;
        if ($scope.channel != undefined) {
          if (res.twitter_profile != null) {
            $scope.channel.twitter_handle = res.twitter_profile.screen_name;
          }
          else $scope.channel.twitter_handle = null;
        }
      }, function onError() {
        $scope.twitter_profile = null;
        if ($scope.channel != undefined) $scope.channel.twitter_handle = null;
      });
    };

    $scope.getFacebookProfile = function () {
      SocialService.fbGetProfile($scope.channel_id, function (res) {
        $scope.facebook_profile = res.facebook_profile;
      }, function onError() {
        $scope.facebook_profile = null;
      });
    };


    $scope.twitter_request_token = function () {
      SocialService.twitterRequestToken($scope.channel_id);
    };

    $scope.facebook_request_token = function () {
      SocialService.facebookRequestToken($scope.channel_id);
    };

    $scope.twitter_logout = function () {
      SocialService.twitterLogout($scope.channel_id);
    };

    $scope.facebook_logout = function () {
      SocialService.facebookLogout($scope.channel_id);
    };

    var _channelIds = [];
    $scope.create = function () {
      _ChannelsRest.saveNewChannel({
        type: $scope.channel_type,
        title: $scope.channel_name,
        description: $scope.channel_description,
        account_id: $routeParams.account_id
      }).success(function (res) {
        $location.path('/channels');
        _channelIds.push(res.id);
        if (_.indexOf(['voc', 'emailservice', 'chatservice'],
            $scope.channel_type) !== -1) {
          $location.path('/channels');
        } else {
          $scope.channel_id = res.id;
          $scope.loadChannel(res.id);
        }
      });
    };

    $scope.update_params = {};
    $scope.childScope = null;
    $scope.isAdvancedState = false;
    //need this to get to a child scope, the function is triggered from within ng-switch directive
    $scope.passTheScope = function (scope) {
      $scope.childScope = scope;
    };

    $scope.$watch('channel', function (newVal, oldVal) {
      if (newVal != oldVal) {
        $scope.account = _.find($scope.accountsObjs, function (item) {
          return item.name == $scope.channel.account
        });
        $scope.update_params = {
          channel_id: $scope.channel_id,
          title: $scope.channel.title,
          description: $scope.channel.description,
          account: $scope.channel.account,

          moderated_intention_threshold: $scope.moderated_intention_threshold,
          auto_reply_intention_threshold: $scope.auto_reply_intention_threshold,
          moderated_relevance_threshold: $scope.moderated_relevance_threshold,
          auto_reply_relevance_threshold: $scope.auto_reply_relevance_threshold,

          review_outbound: $scope.channel.review_outbound,
          history_time_period: $scope.channel.history_time_period,
          auto_refresh_followers: $scope.channel.auto_refresh_followers,
          skip_retweets: $scope.channel.skip_retweets,
          auto_refresh_friends: $scope.channel.auto_refresh_friends,
          dispatch_channel: $scope.channel.dispatch_channel,
          grouping_timeout: $scope.channel.grouping_timeout,
          grouping_enabled: $scope.channel.grouping_enabled
//                fb_pull_mode                   : $scope.channel.fb_pull_mode
        }

        if ($scope.channel.is_compound || $scope.channel.is_service) {
          CompoundChannelService.setCompound($scope.channel);
        }
      }
      ;
    }, true);

    var onError = function () {
      SystemAlert.error("No Channels Available");
    };

    $scope.last_item = null;
    
    function isNewService(channel) {
      var id = angular.isString(channel) ? channel : channel.id;
      return _channelIds.indexOf(id) !== -1 && channel.is_service;
    }

    $scope.update = function () {
      return _ChannelsRest.updateConfigureChannel($scope.update_params)
        .success(function (res) {
          if (isNewService(res.item)) {
            $scope.last_item = res.item;
            //SystemAlert.success("Your channel has been created. Genesys Social Analytics has begun gathering posts and comments.", 5000, 'service');
            $window.location.href = '/inbound#/?channel=' + res.item.id + '&isNew';
          } else {
            $location.path('/channels');
            SystemAlert.success("Your reply channel has been created.", 5000, 'account');
          }
        })
        .error(function(res) {
          onError();
        });
    };

    $scope.loadChannel = function (channel_id) {
      return _ChannelsRest.getOne(channel_id)
        .success(function (res) {
          $scope.channel = res.item;
          if (res.item.type == 'EnterpriseTwitterChannel' || res.item.type == 'TwitterChannel') {
            $scope.getTwitterProfile();
          }
          $location.path('/update_channel/' + res.item.id);
        })
        .error(function (res) {
          onError();
        });
    };

    // load at once to populate channel types chooser
    $scope.load();

    //Add this logic for the Advanced element, so it hides the ActionWords field
    $scope.evaluate = function () {
      return $scope.isAdvancedState;
    }
    $scope.evaluateIcon = function () {
      if ($scope.isAdvancedState) {
        return "icon-expand-down";
      }
      else {
        return "icon-expand-right";
      }
    }
    $scope.changeStatus = function () {
      $scope.isAdvancedState = !$scope.isAdvancedState;
    }
  }
  ChannelConfigureCtrl.$inject = ["$location", "$resource", "$rootScope", "$route", "$routeParams", "$scope", "$window", "AccountsService", "ChannelsRest", "CompoundChannelService", "FilterService", "SocialService", "SystemAlert"];
})();

(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('ChannelsListCtrl', ChannelsListCtrl);

  /** @ngInject */
  function ChannelsListCtrl($scope, $resource, $timeout, $location,
                            DialogService, AccountsService, FilterService, ChannelsRest, SystemAlert) {
    var _ChannelsRest = new ChannelsRest();
    $scope.filteredChannels = $scope.channels = [];
    $scope.noChannelsAlert = false;
    $scope.noChannelsShared = false;

    $scope.filterOptions = {
      platform: ["Twitter", "Facebook", "VOC", "Chat", "Web", "FAQ", "Email"]
    };

    $scope.filters = {
      channel: null,
      platform: '',
      status: '',
      title: '',
      limit: 30,
      offset: 0
    };

    $scope.table = {
      sort: {
        predicate: 'title',
        reverse: false
      }
    };
    angular.extend($scope.filters, $scope.table);

    var channelTypes = [];
    _ChannelsRest.getChannelTypes()
        .success(function (res) {
          channelTypes = res.list;
        });

    function filterChannels() {
      var opts = $scope.table.sort,
        filterFn = $scope.filterPredicate,
        channels = $scope.channels;

      var groupedByParent = _.groupBy(channels, function (ch) {
        return ch.parent || ch.id;
      });

      function sortGroup(group) {
        return _.sortBy(group, function (ch) {
          return ch.title;  // expected order: service, inbound, outbound
        });
      }

      function combineStats(group) {
        return _.reduce(group, function (result, item) {
          _.forEach(item.stats, function (val, key) {
            if (result.hasOwnProperty(key)) {
              result[key] += val;
            } else {
              result[key] = val || 0;
            }
          });
          return result;
        });
      }

      var groups = _(groupedByParent).map(function (group, id) {
        group = sortGroup(group);
        return {
          id: id,
          title: group[0].title,
          description: group[0].description,
          created_at: group[0].created_at,
          status: group[0].status,
          platform: group[0].platform,
          stats: combineStats(group),
          list: group
        }
      }).filter(filterFn);
      if (opts.reverse) {
        groups = groups.reverse();
      }


      var result = [];
      groups.forEach(function (item) {
        result.push.apply(result, item.list);
      });

      _.each(result, function (item, i) {
        var text = item.type_name;
        var txt = text.substring(0, text.indexOf("Channel"));
        var type = _.find(channelTypes, function (el) {
          return el.key == txt.toLowerCase()
        });

        if (type) {
          result[i].type_name = type.display;
        } else {
          result[i].type_name = text;
        }
      });


      $scope.filteredChannels = result;
    }

    $scope.$watch('filters', filterChannels, true);

    AccountsService.query({}, function (res, code) {
      $scope.accounts = _.sortBy(_.pluck(res.data, 'name'), function (item) {
        return item.toLowerCase();
      });
    });

    $scope.currentAccount = AccountsService.getCurrent();

    $scope.acctPredicate = function (channel) {
      if (!$scope.search || !$scope.search.account || $scope.search.account == '') return true;
      if ($scope.search.account == '* Null Accounts') return (channel.account == null);
      return (channel.account == $scope.search.account);
    };

    $scope.toggleChannel = function (channel) {
      if (channel.isActive) {
        suspendChannel(channel);
      } else {
        activateChannel(channel);
      }
      $scope.filteredChannels[$scope.filteredChannels.indexOf(channel)].isActive = !channel.isActive;
    };

    var ChannelCommands = $resource('/commands/:action', {}, {
      activate: {method: 'POST', params: {action: "activate_channel"}, isArray: false},
      suspend: {method: 'POST', params: {action: "suspend_channel"}, isArray: false},
      delete: {method: 'POST', params: {action: "delete_channel"}, isArray: false}
    });

    var loadChannels = function () {

      var postData = {
        widget: false,
        stats: true,
        from: $scope.dateRange.from,
        to: $scope.dateRange.to
      };
      //Make the first filters.status to -- All Statuses -- for channels
      //$scope.filters.status = "-- All Statuses --";
      _ChannelsRest.fetchChannels(postData).success(function (res) {
        $scope.channels = _.map(res.list, function(channel) {
          return _.extend(channel, {isActive: channel.status === 'Active'});
        });
        $scope.filterOptions.platform = _($scope.channels).pluck('platform').unique().pick(_.identity).values().value();
        filterChannels();
        //$scope.noChannelsAlert = $scope.channels.length == 0;
        if (res.list.length == 0) {
          $location.path('/new_channel/no-channels');
        }
        $scope.noChannelsShared = _.any(res.list, function (item) {
            if (item.perm == 'rw' || item.perm == 's')
              return true;
            else return false;
          }
        );
      }, function onError() {
        $scope.noChannelsAlert = true;
        $scope.noChannelsShared = true;
      });
    };

    $scope.$on(FilterService.DATE_RANGE_CHANGED, function () {
      $scope.dateRange = FilterService.getDateRange();
      loadChannels();
    });

    $scope.filterPredicate = function (tag) {
      var result = true;
      if ($scope.filters.title) {
        var title = tag.title || '';
        var description = tag.description || '';
        result = result && (title.toLowerCase().indexOf($scope.filters.title.toLowerCase()) != -1 ||
          description.toLowerCase().indexOf($scope.filters.title.toLowerCase()) != -1);
      }
      if ($scope.filters.status) {
        result = result && tag.status == $scope.filters.status;
      }
      if ($scope.filters.platform) {
        result = result && tag.platform == $scope.filters.platform;
      }
      return result;
    };

    $scope.loadChannels = function (dates) {
      $scope.dateRange = dates;
      loadChannels();
    };

    function activateChannel(channel) {
      ChannelCommands.activate({"channels": [channel.id]}, function () {
        _.each($scope.filteredChannels, function (ch) {
          if (ch.id == channel.id) {
            ch.status = 'Active';
          }
        });
      });
    }

    function suspendChannel(channel) {
      ChannelCommands.suspend({"channels": [channel.id]}, function () {
        _.each($scope.filteredChannels, function (ch) {
          if (ch.id == channel.id) {
            ch.status = 'Suspended';
          }
        });
      });
    }

    $scope.deleteChannel = function (channel) {
      ChannelCommands.delete({"channels": [channel.id]}, loadChannels);     
    };


    $scope.all_selected = false;

    // Items Selection
    $scope.selectAll = function () {
      _.forEach($scope.channels, function (item) {
        item.is_selected = $scope.all_selected;
      });
    };

    $scope.deselectAll = function () {
      $scope.selectAll();
    };

    var getSelectedItems = function () {
      return _.filter($scope.channels, function (item) {
        return item['is_selected'];
      });
    };

    var findItems = function (list, item) {
      var items = [];
      if (item) {
        items = [item];
      } else {
        items = getSelectedItems(list);
      }
      return items;
    };


    var findItemIds = function (label) {
      var items = findItems($scope.channels, label);
      return _.pluck(_.filter(items, function (el) {
        return el.perm == 's' || el.perm == 'rw'
      }), 'id');
    };


    $scope.shareChannel = function (channel) {
      var ids = findItemIds(channel);

      if (!ids.length) return;
      DialogService.openDialog({target: 'acl', objectType: 'channel', objectIds: ids});

      $scope.$on(DialogService.CLOSE, function () {
        $scope.deselectAll();
      });
    }

    $scope.updateChannelAccount = function (channel) {
      channel._loadingState = 'loading';

      var _params = {
        channel_id: channel.id,
        account: channel.account
      };

      _ChannelsRest.updateConfigureChannel(_params)
        .success(function (res) {
          channel._loadingState = 'loaded';
          $timeout(function () {
            channel._loadingState = 'normal';
          }, 1000);
        })
        .error(function () {
        SystemAlert.info("Can not set account");
      });
    }
  }
  ChannelsListCtrl.$inject = ["$scope", "$resource", "$timeout", "$location", "DialogService", "AccountsService", "FilterService", "ChannelsRest", "SystemAlert"];

})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('EventsImportModalCtrl', EventsImportModalCtrl);

  /** @ngInject */
  function EventsImportModalCtrl($scope, $modalInstance, _channelId, _eventTypes, _uploadFunc, MetadataService, SystemAlert) {

    angular.extend($scope, {
      progress: 0,
      form: {
        separator: null,
        selectedFile: null,
        eventTypeName: null,
      },
      uploadingFile: false,
      fileType: null,

      onImportFile: onImportFile,
      onUploadFile: onUploadFile,
      onCloseDialog: onCloseDialog,
      canSubmit: canSubmit,

      eventTypes: _eventTypes,
      separtors: MetadataService.getCSVSeparators(),
      fileTypes: MetadataService.getDataFileTypes(),
    });

    function onImportFile(files) {
      if(!files.length) return;
      $scope.form.selectedFile = files[0];

      if (_.indexOf(['text/csv',  'application/vnd.ms-excel'], files[0].type) !== -1) {
        $scope.fileType = 'CSV';
      } else if (files[0].type === 'application/json') {
        $scope.fileType = 'JSON';
      }
    }

    function onUploadFile() {
      $scope.uploadingFile = true;
      var params = {
        channel_id: _channelId,
        name: $scope.form.eventTypeName,
        sep: $scope.form.separator,
        file: $scope.form.selectedFile,
      };

      var updateProgressBar = setInterval(function increase() {
        $scope.progress += 1;
        if ($scope.progress > 100) {
          $scope.progress = 0;
        }
        $scope.$digest();
      }, 30);

      _uploadFunc(params)
        .success(function(res) {
          SystemAlert.info('Uploaded file successfully!');
        })
        .catch(function(err) {
          SystemAlert.error('Failed to upload file!');
        })
        .finally(function() {
          $scope.uploadingFile = false;
          clearInterval(updateProgressBar);
          $modalInstance.close();
        });
    }

    function canSubmit() {

      console.log("fileType" + $scope.fileType);

      if ($scope.fileType === 'JSON') {
        return true;
      } else if ($scope.fileType === 'CSV') {
        return (!!$scope.form.separator && $scope.form.selectedFile
          && !!$scope.form.eventTypeName);
      }
      return false;
    }

    function onCloseDialog() {
      $modalInstance.dismiss('cancel');
    };
  }
  EventsImportModalCtrl.$inject = ["$scope", "$modalInstance", "_channelId", "_eventTypes", "_uploadFunc", "MetadataService", "SystemAlert"];
})();
(function() {
  'use strict';

  angular
    .module('slr.configure')
    .controller('PrimitiveChannelSelectCtrl', PrimitiveChannelSelectCtrl);

  /** @ngInject */
  function PrimitiveChannelSelectCtrl($scope, CompoundChannelService){
        $scope.options = {
            'selected': [],
            'options': []
        };

        var filterOptionsByPlatform = function(force) {
            $scope.options = CompoundChannelService.filterOptionsByPlatform($scope.options, force);
        };

        var setup = function() {
            var compound = CompoundChannelService.compound;
            if (compound)
                $scope.options.selected = _.pluck(compound.primitive_channels, 'id');

            filterOptionsByPlatform(true);
        };

        if (CompoundChannelService.isReady()) {
            setup();
        } else {
            $scope.$on(CompoundChannelService.LOADED, setup);
        }

        $scope.$watch('options.selected', function(newValue, oldValue){
            if (newValue != oldValue) {
                filterOptionsByPlatform();
                CompoundChannelService.primitivesChanged([{key: 'primitive_channels', value: newValue}]);
            }
        }, true);
    }
    PrimitiveChannelSelectCtrl.$inject = ["$scope", "CompoundChannelService"];;
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('UpdateChannelCtrl', UpdateChannelCtrl);

  /** @ngInject */
  function UpdateChannelCtrl($http,
                             $interval,
                             $scope,
                             $routeParams,
                             $location,
                             $modal,
                             $timeout,
                             $window,
                             FilterService,
                             SocialService,
                             AccountsService,
                             ChannelsRest,
                             ChannelTypesRest,
                             EventTypesRest,
                             CompoundChannelService,
                             SystemAlert) {
    var _ChannelsRest = new ChannelsRest();
    var _ChannelTypesRest = new ChannelTypesRest();
    var _EventTypesRest = new EventTypesRest();

    $scope.channel = null;
    $scope.account = null;
    $scope.options = {};
    $scope.channel_id = $routeParams.channel_id;
    $scope.channelTypeSchema = null;
    $scope.eventTypes = [];

    $scope.intentions_filter = FilterService.getIntentions();

    AccountsService.query({}, function (res, code) {
      $scope.accounts = _.sortBy(_.pluck(res.data, 'name'), function (item) {
        return item.toLowerCase();
      });
      $scope.accountsObjs = angular.copy(res.data);

      $scope.$watch('channel', function (newVal, oldVal) {
        if (!newVal)
          return;
        $scope.account = _.find($scope.accountsObjs, function (item) {
          return item.name == $scope.channel.account;
        });
        setRecoveryDateLimits();
      });
    });

    $scope.outboundChannelConfigured = false;
    $http.get('/get_outbound_channel/' + $scope.channel_id).then(function (data) {
      var channel = data.data.channel;
      if (channel && channel.is_authenticated) {
        $scope.outboundChannelConfigured = true;
      }
    });

    var setRecoveryDateLimits = function () {
      var minDate = new Date().add({days: -$scope.account.recovery_days});
      $scope.recoveryFromOptions = {
        minDate: minDate,
        maxDate: 0
      };
      $scope.recoveryToOptions = {
        minDate: 0,
        maxDate: 0,
        defaultDate: new Date()
      };
    };


    $scope.$on(SocialService.POPUP_CLOSE, function (evt, data) {
      if (data.type == 'twitter') {
        // popup closed - fetch profile
        $scope.getTwitterProfile();
      } else {
        $scope.getFacebookProfile();
      }
    });

    $scope.isChannelTypeValid = function () {
      var isValid = true;
      if ($scope.channel.type === 'FacebookServiceChannel') {
        isValid = ($scope.channel.facebook_page_ids && $scope.channel.facebook_page_ids.length) || ($scope.channel.facebook_event_ids && $scope.channel.facebook_event_ids.length);
      }
      return !!isValid;
    };

    $scope.isHistoryPeriodValid = function (value) {
      return (value !== 'undefined') && (value >= 1800 && value <= 1209600);
    };

    $scope.isRefreshIntervalValid = function (value) {
      return (value !== 'undefined') && (value == 0 || (value >= 5 && value <= 1440) || value == 100000);
    };

    $scope.isAutoRefreshConfigValid = function () {
      if ($scope.channel.type !== 'TwitterServiceChannel') {
        return true;
      }
      if (!$scope.refreshRelations.isOpened) return true;
      //if (!$scope.refreshRelations.isOpened && $scope.isHistoryPeriodValid($scope.channel.history_time_period)) return true;

      return $scope.isRefreshIntervalValid($scope.channel.auto_refresh_followers) && $scope.isRefreshIntervalValid($scope.channel.auto_refresh_friends) && $scope.isHistoryPeriodValid($scope.channel.history_time_period);
    };


    $scope.getTwitterProfile = function () {
      SocialService.twitterGetProfile($scope.channel_id, function (res) {
        $scope.twitter_profile = res.twitter_profile;
        if ($scope.channel != undefined) {
          if (res.twitter_profile != null) {
            $scope.channel.twitter_handle = res.twitter_profile.screen_name;
          }
          else $scope.channel.twitter_handle = null;
        }
      }, function onError() {
        $scope.twitter_profile = null;
        if ($scope.channel != undefined) $scope.channel.twitter_handle = null;
      });
    };

    $scope.getFacebookProfile = function () {
      SocialService.fbGetProfile($scope.channel_id, function (res) {
        $scope.facebook_profile = res.facebook_profile;
      }, function onError() {
        $scope.facebook_profile = null;
      });
    };

    $scope.twitter_request_token = function () {
      SocialService.twitterRequestToken($scope.channel_id);
    };

    $scope.facebook_request_token = function () {
      SocialService.facebookRequestToken($scope.channel_id);
    };

    $scope.twitter_logout = function () {
      SocialService.twitterLogout($scope.channel_id);
    };

    $scope.facebook_logout = function () {
      SocialService.facebookLogout($scope.channel_id);
    };

    $scope.load = function () {
      _ChannelsRest.getOne($scope.channel_id)
        .success(function (res) {
        $scope.channel = res.item;

        if ($scope.channel.is_dynamic) {
          fetchChannelTypeSchema($scope.channel.platform);
          fetchEventTypes($scope.channel.channel_type_id);
          return;
        } else {
            fetchEventTypes($scope.channel.id);
            return;
        }

        if ($scope.channel.type == "EnterpriseTwitterChannel") {
          $scope.getTwitterProfile();
        } else if ($scope.channel.type == "EnterpriseFacebookChannel") {
          $scope.getFacebookProfile();
        } else if ($scope.channel.is_service) {
          if ($scope.channel.type === "FacebookServiceChannel") {
            $http.get('/account_channels/' + $scope.channel_id).then(function (data) {
              $scope.options.dispatch_channels = data.data.data;
              if (!$scope.options.dispatch_channels) {
                SystemAlert.error('Please configure a channel of type "Facebook : Account" first.');
              }
            });
          }
        }

        // init for compound channel
        if ($scope.channel.is_compound || $scope.channel.is_service) {
          //console.log($scope.channel);
          CompoundChannelService.setCompound($scope.channel);
          CompoundChannelService.prepare();
          $scope.$on(CompoundChannelService.CHANGED, function (event, data) {
            _.forEach(data, function (item) {
              $scope.update_params[item.key] = item.value;
            });
          });
        }
      })
        .error(function () {
          SystemAlert.info('No channels availbale');
        });
    }();

    $scope.update_params = {};
    if ($scope.channel_id) {
      $scope.update_params = {channel_id: $scope.channel_id}
    }
    $scope.childScope = null;
    $scope.isAdvancedState = false;

    //need this to get to a child scope, the function is triggered from within ng-switch directive
    $scope.passTheScope = function (scope) {
      $scope.childScope = scope;
    };


    $scope.$watch('channel', function (newVal, oldVal) {
      if (newVal != oldVal) {
        $scope.account = _.find($scope.accountsObjs, function (item) {
          return item.name == $scope.channel.account
        });

        if ($scope.channel.is_dynamic) {
          var defaultFields = ['title', 'description', 'account'];
          var schemaFields = _.pluck($scope.channelTypeSchema, 'name');
          var fields = defaultFields.concat(schemaFields);
          angular.extend($scope.update_params, _.pick($scope.channel, fields));
          return;
        }
        $scope.update_params = {
          channel_id: $scope.channel_id,
          title: $scope.channel.title,
          description: $scope.channel.description,
          account: $scope.channel.account,
          moderated_intention_threshold: $scope.channel.moderated_intention_threshold,
          auto_reply_intention_threshold: $scope.channel.auto_reply_intention_threshold,
          moderated_relevance_threshold: $scope.channel.moderated_relevance_threshold,
          auto_reply_relevance_threshold: $scope.channel.auto_reply_relevance_threshold,
          adaptive_learning_enabled: $scope.channel.adaptive_learning_enabled,
          review_outbound: $scope.channel.review_outbound,
          history_time_period: $scope.channel.history_time_period,
          skip_retweets: $scope.channel.skip_retweets,
          auto_refresh_friends: $scope.channel.auto_refresh_friends,
          dispatch_channel: $scope.channel.dispatch_channel,
          remove_personal: $scope.channel.remove_personal,
          posts_tracking_enabled: $scope.channel.posts_tracking_enabled,
          grouping_timeout: $scope.channel.grouping_timeout,
          grouping_enabled: $scope.channel.grouping_enabled
//                fb_pull_mode                   : $scope.channel.fb_pull_mode
        };
        if ($scope.childScope) {
          $scope.update_params['twitter_handle'] = $scope.childScope.channel.twitter_handle;
          $scope.update_params['tracking_mode'] = $scope.childScope.channel.tracking_mode;
        }
      }
    }, true);

    var _channelIds = [];
    function isNewService(channel) {
      var id = angular.isString(channel) ? channel : channel.id;
      return _channelIds.indexOf(id) !== -1 && channel.is_service;
    }

    $scope.update = function () {
      return _ChannelsRest.updateConfigureChannel($scope.update_params)
        .success(function(res) {
          if (res.item.is_dynamic) {
            SystemAlert.success("Channel has been updated.", 5000);
            return;
          }
          $scope.currentAccount = AccountsService.getCurrent();
          var selected_app = $scope.currentAccount.selected_app;
          if (isNewService(res.item) && selected_app !== 'GSE') {
            $window.location.href = '/inbound#/?channel=' + res.item.id + '&isNew';
          } else {
            $location.path('/channels');
            SystemAlert.success("Your reply channel has been updated.", 5000, 'account');
          }
      });
    };

    //Add this logic for the Advanced element, so it hides the ActionWords field
    $scope.evaluate = function () {
      return $scope.isAdvancedState;
    }
    $scope.evaluateIcon = function () {
      if ($scope.isAdvancedState) {
        return "icon-expand-down";
      }
      else {
        return "icon-expand-right";
      }
    }
    $scope.changeStatus = function () {
      $scope.isAdvancedState = !$scope.isAdvancedState;
    };

    $scope.changeStatus();

    $timeout(function () {
      $scope.changeStatus()
    }, 1000);

    var extend = angular.extend;
    var BaseHistorics = {
      list: function (data) {
        if (!data.channel) return;
        return $http.get(this.baseUrl, {params: {channel: data.channel}});
      },
      postParams: ['channel', 'from_date', 'to_date', 'type'],
      start: function (data) {
        var params = _.pick(data, this.postParams);
        if (Object.keys(params).length != this.postParams.length) return;
        return $http.post(this.baseUrl, params);
      }
    };

    var Recovery = extend({}, BaseHistorics, {
      baseUrl: '/api/v2.0/historics',
      stop: function (id) {
        if (!id) return;
        return $http.put(this.baseUrl + '/' + id, {action: 'stop'});
      },
      resume: function (id) {
        if (!id) return;
        return $http.put(this.baseUrl + '/' + id, {action: 'resume'});
      }
    });

    var RelationsRefresh = extend({}, BaseHistorics, {
      baseUrl: '/api/v2.0/refresh_followers_friends',
      postParams: ['channel']
    });

    var Toggle = {
      isOpened: false,
      toggle: function () {
        this.isOpened = !this.isOpened;
        if (this.isOpened && !this.loaded) {
          this.load()
        }
      }
    };
    var Polling = {
      intervalPromise: null,
      startPolling: function () {
        var interval = 5000,
          self = this;

        if (self.intervalPromise !== null) return;
        if (!this.isRunning()) return;
        this.intervalPromise = $interval(function () {
          if (!self.isOpened) return;
          self.load().then(function () {
            if (!self.isRunning()) {
              $interval.cancel(self.intervalPromise);
              self.intervalPromise = null;
            }
          });
        }, interval);
      }
    };

    $scope.refreshRelations = extend({}, Toggle, Polling, {
      progressBars: [],
      current: {},

      load: function () {
        var self = this,
          postData = {channel: $scope.channel.id};

        return RelationsRefresh.list(postData).then(function (res) {
          self.current = res.data.item;
          self.loaded = true;
          self.progressBars = self.getProgressBars();
          self.lastSync = new Date(self.current.status_update * 1000).format('yyyy/mm/dd HH:MM Z');
          if (self.current.sync_status_friends == 'idle' && self.current.sync_status_followers == 'idle') {
            self.syncStatus = 'idle';
          } else {
            self.syncStatus = 'sync';
          }
          self.startPolling();
        });
      },

      canStart: function () {
        var ch = this.current;
        return (!this.isRunning() ||
        (ch.status == 'Active' &&
        ch.followers_synced >= ch.followers_count &&
        ch.friends_synced >= ch.friends_count));
      },

      isRunning: function () {
        return (this.current.status == 'Active' && (this.current.sync_status_friends != 'idle' || this.current.sync_status_followers != 'idle'));
      },

      isFinished: function () {
        return (this.current.sync_status_followers == 'idle' && this.current.sync_status_friends == 'idle');
      },

      start: function () {
        if (!this.canStart()) return;
        var postData = {channel: $scope.channel.id};
        return RelationsRefresh.start(postData).then(function (res) {
          var defaultMsg = 'The followers/friends refresh has been started. Please be patient.',
            message = res.data.message || defaultMsg;
          SystemAlert.success(message, 5000);
        }).then(this.load.bind(this));
      },

      getProgressBars: function () {
        var ch = this.current;
        return [{
          hint: 'followers',
          max: ch.followers_count,
          title: ch.followers_synced + '/' + ch.followers_count,
          value: ch.followers_synced
        },
          {
            hint: 'friends',
            max: ch.friends_count,
            title: ch.friends_synced + '/' + ch.friends_count,
            value: ch.friends_synced
          }];
      }
    });
    var timezoneOffsetMinutes = (new Date()).getTimezoneOffset(),
      tzOffsetHours = timezoneOffsetMinutes / 60,
      formattedOffset = tzOffsetHours > 0 ? "-" + tzOffsetHours : (tzOffsetHours < 0 ? "+" + -tzOffsetHours : "");

    $scope.recovery = extend({}, Toggle, Polling, {
      setDefault: function () {
        return (this.current = {
          channel: $scope.channel && $scope.channel.id,
          from_date: '',
          to_date: '',
          status: false,
          type:''
        });
      },
      label: {
        from: 'From (UTC' + formattedOffset + ')',
        to: 'To (UTC' + formattedOffset + ')'
      },
      current: {
        channel: $scope.channel && $scope.channel.id,
        from_date: '',
        to_date: '',
        type:''
      },

      canStart: function () {
        return !this.isRunning() && this.isFinished() || this.current.status === false;
      },
      isResumable: function () {
        var isResumableStatus = function (status) {
          return ['stopped', 'error'].indexOf(status) > -1;
        };
        return isResumableStatus(this.current.status);
      },
      isFinished: function () {
        return this.current.status == 'finished';
      },
      startNew: function () {
        this.setDefault();
        this.progressBars = this.getProgressBars();
      },
      isRunning: function () {
        return this.current.is_active;
      },
      canStop: function () {
        return this.current.is_stoppable;
      },
      load: function () {
        /* Load previous recovery list for current channel */
        var self = this;
        this.current.channel = $scope.channel.id;
        return Recovery.list(this.current).then(function (res) {
          var data = res.data,
            parseDate = function (d) {
              var dt = new Date(d * 1000 - timezoneOffsetMinutes * 60 * 1000);
              return dt.format('yyyy/mm/dd HH:MM');
            };

          if (data.items.length) {
            self.current = data.items[0];
            self.current.from_date = parseDate(self.current.from_date);
            self.current.to_date = parseDate(self.current.to_date);
          } else {
            self.setDefault();
          }
          self.loaded = true;
          self.progressBars = self.getProgressBars();
          self.startPolling();
        });
      },
      start: function () {
        if (!this.canStart()) return;
        this.loaded = false;
        this.current.channel = $scope.channel.id;
        var postData = extend({}, this.current);
        postData.from_date = (new Date(postData.from_date + ' UTC')).getTime() + timezoneOffsetMinutes * 60 * 1000;
        postData.to_date = (new Date(postData.to_date + ' UTC')).getTime() + timezoneOffsetMinutes * 60 * 1000;
        return Recovery.start(postData).then(function (res) {
          var defaultMsg = 'The recovery process has been started. Please be patient.',
            message = res.data.message || defaultMsg;
          SystemAlert.success(message, 5000);
        }).then(this.load.bind(this));
      },
      resume: function () {
        this.current.channel = $scope.channel.id;
        return Recovery.resume(this.current.id).then(this.load.bind(this));
      },
      stop: function () {
        this.current.channel = $scope.channel.id;
        return Recovery.stop(this.current.id).then(this.load.bind(this));
      },
      progressBars: [],
      getProgressBars: function () {
        if (this.isRunning() || this.isFinished() || this.isResumable()) {
          var p = this.current.progress;

          if (['TwitterHistoricalSubscription', 'TwitterRestHistoricalSubscription'].indexOf(this.current.type) > -1) {
            var pbs = [{
              hint: 'public tweets & direct messages',
              status: p.status,
              title: p.fetchers.progress + '%',
              value: p.fetchers.progress
            }];
            if (p.loader && p.loader.progress > 0) {
              pbs.push({
                hint: 'loading posts',
                status: p.status,
                title: p.loader.progress + '%',
                value: p.loader.progress
              });
            }
            return pbs;
          } else {
            return [{
              hint: '',
              status: this.current.status,
              title: '0%',
              value: 0
            }];
          }
        }
        return [];
      }
    });
  
    function fetchChannelTypeSchema(channel_type_name) {
      _ChannelTypesRest.getOne(channel_type_name).success(function(res) {
        $scope.channelTypeSchema = res.data.schema;
      });
    }

    function fetchEventTypes(channel_type_id) {
      _EventTypesRest.list(channel_type_id).success(function(res) {
        $scope.eventTypes = res.data;
      });
    }

    $scope.showImportDialog = function() {
      var modalInstance = $modal.open({
        templateUrl: 'partials/channels/events-import-modal',
        controller: 'EventsImportModalCtrl',
        size: 'md',
        resolve: {
          _channelId: function() { return $scope.channel.id },
          _eventTypes: function() { return $scope.eventTypes },
          _uploadFunc: function() { return _EventTypesRest.importData.bind(_EventTypesRest) },
        }
      });

      modalInstance.result.finally(function() {
        reloadEntity();
      });
    }
  }
  UpdateChannelCtrl.$inject = ["$http", "$interval", "$scope", "$routeParams", "$location", "$modal", "$timeout", "$window", "FilterService", "SocialService", "AccountsService", "ChannelsRest", "ChannelTypesRest", "EventTypesRest", "CompoundChannelService", "SystemAlert"];
})();

(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/customer_segments', {
          templateUrl: '/partials/customer_segments/list',
          controller: 'CustomerSegmentListCtrl',
          name: 'customer_segments'
        })
        .when('/customer_segments/edit/:id?', {
          templateUrl: '/partials/customer_segments/edit',
          controller: 'CreateEditCustomerSegmentCtrl',
          name: 'customer_segments'
        })
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateEditCustomerSegmentCtrl', CreateEditCustomerSegmentCtrl);

  /** @ngInject */
  function CreateEditCustomerSegmentCtrl($routeParams, $scope, CustomerSegmentsRest) {
    var CustomerSegments = new CustomerSegmentsRest();
    var id = $routeParams.id;
    $scope.title = id ? 'Update' : 'Create';
    $scope.item = {};
    $scope.formState = {};

    if (id) {
      CustomerSegments.getOne(id).success(function (res) {
        $scope.item = res.data;
      });
    } else {
      $scope.item = {
        display_name: "",
        description: "",
        locations: [],
        age_range: [],
        account_balance_range: [],
        num_calls_range: [],
      };
    }

    $scope.save = function () {
      $scope.formState.isSaved = false;
      CustomerSegments.save($scope.item).success(function (res) {
        $scope.title = 'Update';
        $scope.item = res.data;
        $scope.formState.isSaved = true;
      });
    };

    $scope.createNewSegment = function () {
      window.location.reload();
    }
  }
  CreateEditCustomerSegmentCtrl.$inject = ["$routeParams", "$scope", "CustomerSegmentsRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CustomerSegmentListCtrl', CustomerSegmentListCtrl);

  /** @ngInject */
  function CustomerSegmentListCtrl($scope, CustomerSegmentsRest) {
    var CustomerSegments = new CustomerSegmentsRest();
    $scope.table = {
      sort: {
        predicate: 'display_name',
        reverse: false
      }
    };
    $scope.filters = {
      display_name: ''
    };
    $scope.selected = [];
    $scope.selectRow = function (selected) {
      var found = _.find($scope.selected, {id: selected.id});

      if (found) {
        _.remove($scope.selected, selected)
      } else {
        $scope.selected.push(selected)
      }
    };

    var resolveCtrl = function () {
      CustomerSegments.list().success(function (res) {
        $scope.items = res.data;
      });
    };

    $scope.remove = function () {
      _.each($scope.selected, function (item) {
        CustomerSegments.remove(item.id).success(function () {
          _.remove($scope.items, {id: item.id});
        });
      });
    };

    resolveCtrl();
  }
  CustomerSegmentListCtrl.$inject = ["$scope", "CustomerSegmentsRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/datasets', {
          templateUrl: '/partials/datasets/list',
          controller: 'DatasetsListCtrl',
          name: 'datasets'
        })
        .when('/datasets/edit/:name*', {
          templateUrl: '/partials/datasets/edit',
          controller: 'EditDatasetsCtrl',
          name: 'datasets'
        })
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateDatasetCtrl', CreateDatasetCtrl);

  /** @ngInject */

  /** @ngInject */
  function CreateDatasetCtrl($scope, $modalInstance, toaster, _saveFunc, MetadataService, datasetName, isAppending) {
    $scope.datasetName = datasetName || '';
    $scope.isAppending = isAppending;
    $scope.separator = null;
    $scope.selectedFile = null;
    $scope.uploading = false;
    $scope.progress = 0;

    $scope.separtors = MetadataService.getCSVSeparators();

    $scope.import = function (files) {
      if(!files.length) return;
      $scope.selectedFile = files[0];
    }

    $scope.createOrAppend = function () {
      var params = {
        'name': $scope.datasetName,
        'csv_file': $scope.selectedFile,
        'sep': $scope.separator,
        'type': isAppending? 'append': 'create',
      };

      $scope.uploading = true;
      var updateProgressBar = setInterval(function increase() {
        $scope.progress += 1;
        if ($scope.progress > 100) {
          $scope.progress = 0;
        }
        $scope.$digest();
      }, 30);

      _saveFunc(params)
        .then(function() {
          if (isAppending) {
            toaster.pop('info', 'Appended data successfully.');
          } else {
            toaster.pop('info', 'Created successfully.');
          }
        })
        .catch(function(err) {
          console.log('Dataset create/append failed! ', err);
        })
        .finally(function() {
          $scope.uploading = false;
          clearInterval(updateProgressBar);
          $modalInstance.close();
        });
    };

    $scope.cancel = function () {
      $modalInstance.dismiss('cancel');
    };
  }
  CreateDatasetCtrl.$inject = ["$scope", "$modalInstance", "toaster", "_saveFunc", "MetadataService", "datasetName", "isAppending"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('EditDatasetsCtrl', EditDatasetsCtrl);

  /** @ngInject */
  function EditDatasetsCtrl($scope, $routeParams, $modal, $interval, DatasetsRest, MetadataService, toaster) {
    var _DatasetsRest = new DatasetsRest();
    var datasetName = encodeURIComponent($routeParams.name);
    var createdAtFieldType = 'timestamp';
    var pageRefresher;

    $scope.types = MetadataService.getSchemaFieldTypes();
    $scope.isFetched = false;

    $scope.showData = function (field) {
      var dialogScope = $scope.$new();

      dialogScope.data = {
        title: "All values in '" + field + "' column",
        field: field
      };

      var pagination = {
        offset: 0,
        limit: 20,
        currentPage: 1,
        totalItems: 0,
        pages: 0,
        maxSize: 10,
        setPage: function () {
          pagination.offset = parseInt(pagination.limit) * (pagination.currentPage - 1);
          fetchData();
        }
      };

      dialogScope.pagination = pagination;

      var fetchData = function () {
        var params = {skip: pagination.offset, limit: pagination.limit};
        _DatasetsRest.fetchFieldData(datasetName, field, params)
          .success(function (res) {
            dialogScope.data.values = res.data.list;
            pagination.totalItems = res.data.total_items;
            pagination.pages = Math.ceil(pagination.totalItems/pagination.limit);
          });
      };

      fetchData();

      var modalInstance = $modal.open({
        scope: dialogScope,
        size: 'lg',
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.column-values.html'
      });
    };

    $scope.showDetails = function (field, values) {
      var dialogScope = $scope.$new();

      dialogScope.data = {
        title: "Unique values in '" + field + "' column",
        field: field,
        values: values
      };

      var modalInstance = $modal.open({
        scope: dialogScope,
        size: 'lg',
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.column-values.html'
      });
    };

    $scope.onShowErrors = function() {
      var dialogScope = $scope.$new();

      dialogScope.data = {
        errors: $scope.dataset.sync_errors,
        options: {
          name: "Fields resulted in errors",
          mode: "tree",
        }
      };

      dialogScope.title = $scope.dataset.name;

      var modalInstance = $modal.open({
        scope: dialogScope,
        backdrop: true,
        keyboard: true,
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.sync-errors.html'
      });
    }

    $scope.select = function (selected) {
      if (!selected) {
        // for all selection
        _.each($scope.dataset.schema, function(each, index) {
          $scope.dataset.schema[index].selected = !$scope.flags.selectedAll;
        });

        if ($scope.flags.selectedAll) {
          $scope.selected = [];
        } else {
          $scope.selected = _.clone($scope.dataset.schema);
        }
        $scope.flags.selectedAll = !$scope.flags.selectedAll;
      } else {
        _.each($scope.dataset.schema, function(each, index) {
          if (selected.name === each.name) {
            var found = _.findWhere($scope.selected, {name: selected.name});
            if (found) {
              _.remove($scope.selected, selected);
            } else {
              $scope.selected.push(selected)
            }
            $scope.dataset.schema[index].selected = !selected.selected;
          }
        });
        $scope.flags.selectedAll = ($scope.selected.length === $scope.dataset.schema.length);
      }
    };

    $scope.changeDescription = function(field, $event) {
      $event.currentTarget.lastElementChild.blur();
    };

    $scope.onEditStart = function() {
      $scope.isSchemaChanged = true;
    };

    $scope.setAsCreatedTime = function() {
        if ($scope.selected.length !== 1) { return }

        var selected = $scope.selected[0];

        if (selected.type !== createdAtFieldType) {
          toaster.pop('warning', 'You need to select a field of timestamp type.');
          return;
        }

        _.each($scope.dataset.schema, function(field, index) {
          if (field.name === selected.name) {
            field.created_time = true;
          } else {
            delete field.created_time;
          }
        });
        $scope.isSchemaChanged = true;
    };

    $scope.saveSchema = function() {
      _.each($scope.dataset.schema, function(field) {
        delete field.selected;
      });
      _DatasetsRest.updateSchema(datasetName, _.pick($scope.dataset, 'schema'))
        .success(function(res) {
          toaster.pop('info', 'Updated schema successfully.');
          reloadDataset();
        });
    };

    $scope.applySchema = function() {
      _DatasetsRest.applySchema(datasetName)
        .success(function(res) {
          toaster.pop('info', 'Synchronization started.');
          startRefresh();
        });
    };

    $scope.acceptSchema = function() {
      _DatasetsRest.acceptSchema(datasetName)
        .success(function(res) {
          toaster.pop('info', 'Accepted schema successfully.');
          reloadDataset();
        });
    };

    $scope.cancelSchema = function() {
      _DatasetsRest.cancelSchema(datasetName)
        .success(function(res) {
          toaster.pop('info', 'Cancelled schema successfully.');
          reloadDataset();
        });
    };

    $scope.appendData = function(files) {
      var modalInstance = $modal.open({
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.create.html',
        controller: 'CreateDatasetCtrl',
        size: 'md',
        resolve: {
          _saveFunc: function() { return _DatasetsRest.save.bind(_DatasetsRest) },
          isAppending: function() { return true },
          datasetName: function() { return $routeParams.name },
        }
      });

      modalInstance.result.then(function() {
        startRefresh();
      });
    };

    activateController();

    function activateController() {
      $scope.selected = [];
      $scope.flags = {
        search: '',
        selectedAll: false
      };
      $scope.table = {
        sort: {
          predicate: 'type',
          reverse: true
        }
      };
      $scope.hasTimetampField = false;

      reloadDataset();
    }

    function startRefresh() {
      if ( angular.isDefined(pageRefresher) ) return;
      reloadDataset();
      pageRefresher = $interval(reloadDataset, 2000);
    }

    function stopRefresh() {
      if ( angular.isDefined(pageRefresher) ) {
        $interval.cancel(pageRefresher);
        pageRefresher = undefined;
      }
    }

    function reloadDataset() {
      _DatasetsRest.getOne(datasetName)
        .success(onLoadDataset);
    }

    function onLoadDataset(res) {
      $scope.isFetched = true;
      $scope.dataset = res.data;
      $scope.dataset.status_display = MetadataService.getBeautifiedStatus(res.data);
      if ($scope.dataset.cardinalities) {
        $scope.dataset.schema.forEach(function (field) {
          field.cardinality = $scope.dataset.cardinalities[field.name].count || 0;
        });
      }
      $scope.selected = [];
      $scope.isSchemaChanged = false;
      _.each($scope.dataset.schema, function(each, index) {
        $scope.dataset.schema[index] = _.extend(each, { selected: false });
      });

      $scope.hasTimetampField = _.some($scope.dataset.schema, { created_time: true });

      // Stop refresh when it finishes applying schema
      if ( $scope.dataset.sync_status === 'SYNCED' ) {
        $scope.rowsLost = $scope.dataset.rows - $scope.dataset.items_synced;
        stopRefresh();
      }
      // Stop refresh when it finishes appending data
      if ($scope.dataset.sync_status === 'IN_SYNC' && $scope.dataset.status === 'LOADED') {
        stopRefresh();
      }
    }
  }
  EditDatasetsCtrl.$inject = ["$scope", "$routeParams", "$modal", "$interval", "DatasetsRest", "MetadataService", "toaster"];
})();

(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('DatasetsListCtrl', DatasetsListCtrl);

  /** @ngInject */

  function DatasetsListCtrl($scope, $modal, $q, $interval, $timeout, DatasetsRest, MetadataService, FilterService, SystemAlert) {
    var _DatasetsRest = new DatasetsRest();
    var pageRefresher;

    $scope.delete = function (dataset) {
      stopRefresh();

      var promises = [];
      _.each($scope.selectedList, function(e) {
        promises.push(deleteEntity(e.name));
      });

      $q.all(promises).then(function() {
        $timeout(function() {
          activateController();
        });
      });
    };

    $scope.openDatasetModal = function() {
      var modalInstance = $modal.open({
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.create.html',
        controller: 'CreateDatasetCtrl',
        size: 'md',
        resolve: {
          _saveFunc: function() { return _DatasetsRest.save.bind(_DatasetsRest) },
          datasetName: null,
          isAppending: null,
        }
      });

      modalInstance.result.finally(function() {
        startRefresh();
      });
    };

    $scope.$on('$destroy', function() {
      stopRefresh();
    });

    function startRefresh() {
      if ( angular.isDefined(pageRefresher) ) return;
      fetch();
      pageRefresher = $interval(fetch, 2000);
    }

    function stopRefresh() {
      if ( angular.isDefined(pageRefresher) ) {
        $interval.cancel(pageRefresher);
        pageRefresher = undefined;
      }
    }

    function hasPendingDatasets(datasets) {
      return _.some(datasets, function(dataset) {
        return ['IMPORTING', 'SYNCING'].indexOf(dataset.sync_status) > -1;
      });
    }

    activateController();

    function activateController() {
      $scope.table = {
        sort: {
          predicate: 'created_at',
          reverse: false,
        }
      };
      $scope.selectedList = [];
      $scope.flags = {
        searchTerm: '',
        selectedAll: false,
      }
      startRefresh();
    }

    function fetch() {
      _DatasetsRest.list().success(function(res) {
        $scope.entityList = res.data;
        _.each($scope.entityList, function(dataset) {
          dataset.status_display = MetadataService.getBeautifiedStatus(dataset);
          dataset.encoded_name = encodeURIComponent(dataset.name);
        });

        if ( !hasPendingDatasets(res.data) ) {
          stopRefresh();
        }
      });
    }

    function deleteEntity(name) {
      return _DatasetsRest.delete(name).success(function() {
        startRefresh();
        SystemAlert.info('Deleted `' + name + '`');
      })
      .catch(function() {
        // SystemAlert.error('Failed to delete `' + entity.name + '`');
      });
    }

    $scope.select = function (entity) {
      if (!entity) { // global selection
        _.each($scope.entityList, function(e) {
          e.selected = !$scope.flags.selectedAll;
        });

        if ($scope.flags.selectedAll) {
          $scope.selectedList = [];
        } else {
          $scope.selectedList = _.clone($scope.entityList);
        }
        $scope.flags.selectedAll = !$scope.flags.selectedAll;

      } else {
        _.each($scope.entityList, function(item) {
          if (entity.id === item.id) {
            if (_.findWhere($scope.selectedList, { id: entity.id })) {
              _.remove($scope.selectedList, entity);
            } else {
              $scope.selectedList.push(entity)
            }
            item.selected = !entity.selected;
          }
        });

        $scope.flags.selectedAll = ($scope.selectedList.length === $scope.entityList.length);
      }
    };
  }
  DatasetsListCtrl.$inject = ["$scope", "$modal", "$q", "$interval", "$timeout", "DatasetsRest", "MetadataService", "FilterService", "SystemAlert"];
})();

(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
    $routeProvider
      .when('/outbound_channels/', {
        templateUrl: '/partials/configure/outbound_channels',
        controller: 'OutboundChannelsCtrl',
        name: 'profile_channels',
        title: 'User Profile - Default Channels'
      })
      .when('/outbound_channels/:acct_id', {
        templateUrl: '/partials/configure/outbound_channels',
        controller: 'OutboundChannelsCtrl',
        name: 'account_channels',
        title: 'Account - Default Channels'
      })
  }])
})();
(function() {
  'use strict';

  angular
    .module('slr.configure')
    .controller('OutboundChannelsCtrl', OutboundChannelsCtrl);

  /** @ngInject */
  function OutboundChannelsCtrl($scope, $resource, $routeParams, $timeout, $rootScope, $route, toaster) {
    $scope.defaultOutboundChannels = [];
    $scope.accountId = $routeParams.acct_id;
    $scope.selectedChannels = {};
    $scope.state = 'normal';

    $rootScope.$on('$viewContentLoaded', function(e) {
        $scope.header = $route.current.$$route.title;
        //console.log($scope.header);
    });

    var OutboundChannels = $resource('/configure/outbound_channels/json', {}, {
        //TODO: add user:"@user" to params
        fetch: { method:'GET', isArray:false, params:{account_id:"@account_id"}},
        update: { method:'POST', isArray:false, params:{account_id:"@account_id"} }
    });

    $scope.fetchOutboundChannelDefaults = function(account_id) {
        var res = OutboundChannels.fetch({account_id:account_id}, function(){
            $scope.defaultOutboundChannels = res.data;
            $scope.noDefaultOutboundChannels = _.isEmpty($scope.defaultOutboundChannels);
            for (var platform in $scope.defaultOutboundChannels) {
                var selected = _.find($scope.defaultOutboundChannels[platform], function(item) {return item.selected; });
                if (selected)
                    $scope.selectedChannels[platform] = selected.id;
            }
        });
    };

    $scope.updateOutboundChannelDefaults = function(account_id) {
        $scope.state = 'loading';
        OutboundChannels.update({account_id:account_id, oc:$scope.selectedChannels}, function() {
            // Close Dialog
            $scope.modalShown = false;
            toaster.pop('success', 'Default Channels successfully changed.');
        }).$promise.finally(function(){
              $scope.state = 'loaded';
              $timeout(function(){$scope.state="normal";}, 2000);
          });
    };

    //$scope.watch('modalShown', function(visible, oldValue) {
    //   if (visible) {
    //       $scope.fetchOutboundChannelDefaults($scope.accountName);
    //   }
    //});

    $scope.fetchOutboundChannelDefaults($scope.accountId);
}
OutboundChannelsCtrl.$inject = ["$scope", "$resource", "$routeParams", "$timeout", "$rootScope", "$route", "toaster"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/events/all', {
          templateUrl: '/partials/events/events',
          controller: 'EventsCtrl',
          name: 'events'
        })
        .when('/event/view/:event_id', {
          templateUrl: '/partials/events/view',
          controller: 'EventViewCtrl',
          name: 'events'
        })
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('EventsList', EventsList);

  /** @ngInject */
  function EventsList($http) {
    return {
      list: function (params) {
        var promise = $http({
          method: 'GET',
          url: '/events/json',
          params: params
        }).then(function (res) {
          return res.data;
        });
        return promise;
      },
      getById: function (event_id) {
        return $http({
          method: 'GET',
          url: '/events/json',
          params: {id: event_id}
        }).then(function (res) {
          //console.log(res);
          return res.data.item;
        });
      }
    };
  }
  EventsList.$inject = ["$http"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('EventViewCtrl', EventViewCtrl);

  /** @ngInject */
  function EventViewCtrl($scope, $routeParams, EventsList) {
    $scope.event_id = $routeParams.event_id;
    EventsList.getById($scope.event_id).then(function (res) {
      $scope.item = res;
    });

  }
  EventViewCtrl.$inject = ["$scope", "$routeParams", "EventsList"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('EventsCtrl', EventsCtrl);

  /** @ngInject */
  function EventsCtrl($scope, FilterService, EventsList) {

    $scope.filters = {
      'title': '',
      'limit': 30,
      'offset': 0
    };

    $scope.events = [];
    $scope.noEventsAlert = false;
    $scope.filters.currentPage = 0;
    $scope.pages = 0;
    $scope.maxSize = 10;

    $scope.loadEvents = function (dates) {
      $scope.dateRange = dates || FilterService.getDateRange();
      var params = {
        offset: $scope.filters.offset,
        limit: $scope.filters.limit,
        filter: {'title': $scope.filters.title}
      };
      EventsList.list(params).then(
        function (res) {
          $scope.events = res.list;
          $scope.noEventsAlert = $scope.events.length == 0;
          $scope.filters.offset = res.offset;
          $scope.filters.limit = res.limit;
          $scope.size = res.size;
          var pages = res.size / res.limit;
          $scope.pages = Math.ceil(pages);
        },
        function (d) {
          $scope.noEventsAlert = true;
        }
      );
    }

    $scope.setPage = function () {
      $scope.filters.offset = (parseInt($scope.filters.limit) * ($scope.filters.currentPage - 1));
      $scope.loadEvents();
    }

    $scope.loadEvents();

  }
  EventsCtrl.$inject = ["$scope", "FilterService", "EventsList"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/event_types', {
          templateUrl: '/partials/event-types/list',
          controller: 'EventTypesListCtrl',
          name: 'event_types'
        })
        .when('/event_types/edit/:name', {
          templateUrl: '/partials/event-types/edit',
          controller: 'EditEventTypeCtrl',
          name: 'event_types'
        })
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('EditEventTypeCtrl', EditEventTypeCtrl);
  
    /** @ngInject */
  function EditEventTypeCtrl($scope, $modal, $q, $timeout, $interval, $location, $routeParams, ChannelTypesRest, EventTypesRest, MetadataService, SystemAlert) {

    var _ChannelTypesRest = new ChannelTypesRest();
    var _EventTypesRest = new EventTypesRest();
    var pageRefresher;

    $scope.entityName = null;
    $scope.entity = null;
    $scope.hasError = false;
    $scope.hasSchema = false;
    $scope.channelTypes = [];
    $scope.availableFields = [];
    $scope.schemaFieldTypes = MetadataService.getSchemaFieldTypes();
    $scope.schemaFieldFlags = MetadataService.getEventTypeFieldFlags();

    $scope.onCreateEntity = onCreateEntity;
    $scope.onSaveSchema = onSaveSchema;
    $scope.onApplySchema = onApplySchema;
    $scope.onAcceptSchema = onAcceptSchema;
    $scope.onCancelSchema = onCancelSchema;
    $scope.showUploadDialog = showUploadDialog;
    $scope.onShowErrors = onShowErrors;
    $scope.onSelectTab = onSelectTab;
    $scope.onAddField = onAddField;
    $scope.onRemoveField = onRemoveField;
    $scope.onFieldNameInput = onFieldNameInput;
    $scope.searchExpressions = searchExpressions;
    $scope.getTextRaw = function(item) { return item; };
    $scope.$on('$destroy', function() { stopRefresh() });


    $scope.flags = { search: '', selectedAll: false },
    $scope.table = {
      sort: { predicate: 'is_id', reverse: false }
    },
    $scope.schemaTabs = [
      { name: 'Discovered Fields',  active: false,  templateUrl: 'partials/event-types/schema-discovery' },
      { name: 'Schema',             active: false,  templateUrl: 'partials/event-types/schema-edit' }
    ],

    activateController();

    function activateController() {
      fetchChannelTypes().then(function() {
        loadEntity();
      });

      onSelectTab($scope.schemaTabs[0]);
    }

    function fetchChannelTypes() {
      var deferred = $q.defer();
      _ChannelTypesRest.list().success(function(res) {
        $scope.channelTypes = _.map(res.data, function(type) {
          return _.pick(type, ['id', 'name', 'sync_status']);
        });
        // $scope.channelTypes = _.filter(res.data, { 'sync_status': 'IN_SYNC' });
      }).finally(function() {
        deferred.resolve();
      });
      return deferred.promise;
    }

    function loadEntity() {
      if ($routeParams.name === 'new') {
        $scope.entity = {
          name: "",
          //channel_type_id: null,
          platform : null
        };
        return $q.when();

      } else { 
        $scope.entityName = $routeParams.name;
        return reloadEntity();
      }
    }

    function afterLoadEntity(res) {
      $scope.entity = res.data;
      $scope.entity.status_display = MetadataService.getBeautifiedStatus(res.data);
      $scope.hasSchema = ($scope.entity.schema && $scope.entity.schema.length > 0);

      $scope.originalFields = _.pluck($scope.entity.discovered_schema, 'name');
      resetAvailableFields();

      $scope.rowsLostAfterSync = 0;
      if ($scope.entity.items_synced !== null) {
        $scope.rowsLostAfterSync = $scope.entity.rows - $scope.entity.items_synced;
      }

      if (isPendingEntity(res.data)) {
        startRefresh();
      } else {
        triesCount = 0;
        stopRefresh();
      }
    }

    function onCreateEntity() {
      _EventTypesRest.create($scope.entity).success(function(res) {
        SystemAlert.info('Created successfully!');
        $location.path('/event_types');
      });
    }

    function showUploadDialog() {
      var modalInstance = $modal.open({
        templateUrl: 'partials/event-types/file-upload-modal',
        controller: 'FileUploadCtrl',
        size: 'md',
        resolve: {
          _entityName: function() { return $scope.entityName },
          _uploadFunc: function() { return _EventTypesRest.discoverSchema.bind(_EventTypesRest) },
        }
      });

      modalInstance.result.finally(function() {
        reloadEntity();
      });
    }

    function onAddField(evt) {
      evt.preventDefault();
      $scope.entity.schema.push({
        name: '',
        type: '',
        expression: '',
      });

      // Automatically open the label selector which saves a click.
      $timeout(function() {
        var count = $scope.entity.schema.length;
        var elementClass = '.field-name-' + (count - 1) + ' a';
        angular.element( elementClass ).click();
      });
    }

    function onRemoveField(evt, index) {
      evt.preventDefault();
      $scope.entity.schema.splice(index, 1);

      resetAvailableFields();
    }

    function resetAvailableFields() {
      $scope.availableFields = _.filter($scope.originalFields, function(fieldName) {
        var usedFields = _.pluck($scope.entity.schema, 'name');
        return usedFields.indexOf(fieldName) < 0;
      });
    }
    
    function getFieldTypeByName( fieldName ) {
      var field = _.find( $scope.entity.discovered_schema, { name: fieldName } );
      return( field ? field.type : '' );
    }

    function onFieldNameInput(index) {
      // Pre-populate `type` and `field/expression` fields
      // if a label is selected from the predictor's schema fields
      var fields = $scope.entity.schema;
      if ($scope.availableFields.indexOf(fields[index].name) >= 0) {
        fields[index].type = getFieldTypeByName(fields[index].name);
        delete fields[index].is_expression;
      } else {
        fields[index].is_expression = true;
      }

      resetAvailableFields();
    }

    var searchSuggestions = function(term, suggestionsList, searchResultsList) {
      _.each(suggestionsList, function(item) {
        if (item.toUpperCase().indexOf(term.toUpperCase()) >= 0) {
          searchResultsList.push(item);
        }
      });
      return searchResultsList;
    };

    function searchExpressions(term) {
      var list = [];
      $scope._availableFields = searchSuggestions(term, $scope.availableFields, list);
    }

    function onSaveSchema() {
      var missingTypeOrExp = _.some($scope.entity.schema, function(field) {
        return (field.is_expression && !field.expression) || !field.type;
      });

      if (missingTypeOrExp) {
        SystemAlert.error('Some fields have missing type or expression');
        $scope.hasError = true;
        return;
      }

      console.log('Saving event type schema...', $scope.entity.schema);
      $scope.hasError = false;

      _EventTypesRest.updateSchema($scope.entityName, _.pick($scope.entity, 'schema'))
        .success(function(res) {
          SystemAlert.info('Updated schema successfully!');
          afterLoadEntity(res);
        });
    }

    function onApplySchema() {
      _EventTypesRest.applySchema($scope.entityName).success(function() {
        SystemAlert.info('Synchronization started');
        startRefresh();
      });
    }

    function onAcceptSchema() {
      _EventTypesRest.acceptSchema($scope.entityName).success(function() {
        SystemAlert.info('Accepted schema');
        startRefresh();
      });
    }

    function onCancelSchema() {
      _EventTypesRest.cancelSchema($scope.entityName).success(function() {
        SystemAlert.info('Cancelled schema');
        startRefresh();
      });
    }

    function reloadEntity() {
      return _EventTypesRest.getOne($scope.entityName).success(afterLoadEntity);
    }

    function startRefresh() {
      
      
      if ( angular.isDefined(pageRefresher) ) return;
      reloadEntity();
      pageRefresher = $interval(reloadEntity, 2000);
    }

    function stopRefresh() {
      if ( angular.isDefined(pageRefresher) ) {
        $interval.cancel(pageRefresher);
        pageRefresher = undefined;
      }
    }

    var triesCount = 0;
    function isPendingEntity(entity) {
      triesCount++;
      return (entity.sync_status == 'SYNCING' || entity.sync_status == 'IMPORTING') && triesCount < 10;
    }

    function onShowErrors() {
      var dialogScope = $scope.$new();

      dialogScope.data = {
        errors: $scope.entity.sync_errors,
        options: {
          name: "Fields resulted in errors",
          mode: "tree",
        }
      };

      dialogScope.title = "Event type '" + $scope.entityName + "'";

      var modalInstance = $modal.open({
        scope: dialogScope,
        backdrop: true,
        keyboard: true,
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.sync-errors.html'
      });
    }

    function onSelectTab(tab) {
      if ($scope.currentTab) {
        $scope.currentTab.active = false;
      }
      $scope.currentTab = tab;
      $scope.currentTab.active = true;
    }
  }
  EditEventTypeCtrl.$inject = ["$scope", "$modal", "$q", "$timeout", "$interval", "$location", "$routeParams", "ChannelTypesRest", "EventTypesRest", "MetadataService", "SystemAlert"];

})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('EventTypesListCtrl', EventTypesListCtrl);

  /** @ngInject */
  function EventTypesListCtrl($scope, $q, $interval, EventTypesRest, ChannelTypesRest, MetadataService, SystemAlert) {

    var _ChannelTypesRest = new ChannelTypesRest();
    var _EventTypesRest = new EventTypesRest();
    var pageRefresher;

    $scope.channelTypeNamesById = {};

    function startRefresh() {
      if ( angular.isDefined(pageRefresher) ) return;
      fetchEntityList();
      pageRefresher = $interval(fetchEntityList, 2000);
    }

    function stopRefresh() {
      if ( angular.isDefined(pageRefresher) ) {
        $interval.cancel(pageRefresher);
        pageRefresher = undefined;
      }
    }

    $scope.$on('$destroy', function() {
      stopRefresh();
    });

    $scope.delete = function() {
      stopRefresh();

      var promises = [];
      _.each($scope.selectedList, function(e) {
        promises.push(deleteEntity(e.name));
      });

      $q.all(promises)
        .then(function() {
          fetchEntityList();
        });
    };

    $scope.applySync = function() {
      stopRefresh();

      var promises = [];
      _.each($scope.selectedList, function(e) {
        promises.push(applySync(e.name));
      });

      $q.all(promises)
        .then(function() {
          fetchEntityList();
        });
    }


    var triesCount = 0;
    function hasPendingEntities(entities) {
      triesCount++;
      return _.some(entities, function(e) {
        return (e.sync_status == 'SYNCING' || e.sync_status == 'IMPORTING') && triesCount < 10;
      });
    }

    function fetchEntityList() {
      _EventTypesRest.list()
        .success(function(res) {
          $scope.selectedList = [];
          $scope.entityList = res.data;
          _.each($scope.entityList, function(e) {
            e.status_display = MetadataService.getBeautifiedStatus(e);
            e.has_error = !!e.sync_errors;
            e.channel_type_name = $scope.channelTypeNamesById[e.channel_type_id];
          });
          if (!hasPendingEntities(res.data) ) {
            stopRefresh();
            triesCount = 0;
          } else {
            startRefresh();
          }
        });
    }

    function fetchChannelTypes() {
      var deferred = $q.defer();
      _ChannelTypesRest.list().success(function(res) {
        _.each(res.data, function(e) {
          $scope.channelTypeNamesById[e.id] = e.name;
        })
        // $scope.channel_types = _.map(res.data, function(type) {
        //   return _.pick(type, ['id', 'name', 'sync_status']);
        // });
      }).finally(function() {
        deferred.resolve();
      });
      return deferred.promise;
    }

    activateController();

    function activateController() {
      $scope.table = {
        sort: {
          predicate: 'created_at',
          reverse: false,
        }
      };
      $scope.selectedList = [];
      $scope.flags = {
        searchTerm: '',
        selectedAll: false,
      };

      fetchChannelTypes().then(function() {
        startRefresh();  
      });
    }

    function deleteEntity(name) {
      return _EventTypesRest.delete(name)
        .success(function() {
          fetchEntityList();
          SystemAlert.info('Deleted `' + name + '`');
        })
        .catch(function() {
          // SystemAlert.error('Failed to delete `' + entity.name + '`');
        });
    }

    function applySync(name) {
      return _EventTypesRest.applySchema(name)
        .success(function() {
          fetchEntityList();
          SystemAlert.info('Synced `' + name + '`');
        })
        .catch(function() {
          // SystemAlert.error('Failed to synchronize ' + name);
        });
    }

    $scope.select = function (entity) {
      if (!entity) { // global selection
        _.each($scope.entityList, function(e) {
          e.selected = !$scope.flags.selectedAll;
        });

        if ($scope.flags.selectedAll) {
          $scope.selectedList = [];
        } else {
          $scope.selectedList = _.clone($scope.entityList);
        }
        $scope.flags.selectedAll = !$scope.flags.selectedAll;

      } else {
        _.each($scope.entityList, function(item) {
          if (entity.id === item.id) {
            if (_.findWhere($scope.selectedList, { id: entity.id })) {
              _.remove($scope.selectedList, entity);
            } else {
              $scope.selectedList.push(entity)
            }
            item.selected = !entity.selected;
          }
        });

        $scope.flags.selectedAll = ($scope.selectedList.length === $scope.entityList.length);
      }
    };
  }
  EventTypesListCtrl.$inject = ["$scope", "$q", "$interval", "EventTypesRest", "ChannelTypesRest", "MetadataService", "SystemAlert"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('FileUploadCtrl', FileUploadCtrl);

  /** @ngInject */
  function FileUploadCtrl($scope, $modalInstance, _entityName, _uploadFunc, MetadataService, SystemAlert) {

    angular.extend($scope, {
      progress: 0,
      form: {
        separator: null,
        selectedFile: null,
      },
      uploadingFile: false,

      onImportFile: onImportFile,
      onUploadFile: onUploadFile,
      onCloseDialog: onCloseDialog,
      separtors: MetadataService.getCSVSeparators()
    });

    function onImportFile(files) {
      if(!files.length) return;
      $scope.form.selectedFile = files[0];
    }

    function onUploadFile() {
      $scope.uploadingFile = true;
      var params = {
        sep: $scope.form.separator,
        file: $scope.form.selectedFile,
        name: _entityName,
      };

      var updateProgressBar = setInterval(function increase() {
        $scope.progress += 1;
        if ($scope.progress > 100) {
          $scope.progress = 0;
        }
        $scope.$digest();
      }, 30);

      _uploadFunc(params)
        .success(function(res) {
          SystemAlert.info('Uploaded file successfully!');
        })
        .catch(function(err) {
          SystemAlert.error('Failed to upload file!');
        })
        .finally(function() {
          $scope.uploadingFile = false;
          clearInterval(updateProgressBar);
          $modalInstance.close();
        });
    }

    function onCloseDialog() {
      $modalInstance.dismiss('cancel');
    };
  }
  FileUploadCtrl.$inject = ["$scope", "$modalInstance", "_entityName", "_uploadFunc", "MetadataService", "SystemAlert"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/groups/', {
          templateUrl: '/partials/groups/list',
          controller: 'GroupsListCtrl',
          name: 'groups'
        })
        .when('/groups/edit/', {
          templateUrl: '/partials/groups/edit',
          controller: 'CreateUpdateGroupCtrl',
          name: 'groups'
        })
        .when('/groups/edit/:group_id/', {
          templateUrl: '/partials/groups/edit',
          controller: 'CreateUpdateGroupCtrl',
          name: 'groups'
        })
        .when('/groups/edit/:group_id/:tab/', {
          templateUrl: '/partials/groups/edit',
          controller: 'CreateUpdateGroupCtrl',
          name: 'groups'
        })
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateUpdateGroupCtrl', CreateUpdateGroupCtrl);

  /** @ngInject */
  function CreateUpdateGroupCtrl($scope,
                                 $location,
                                 $routeParams,
                                 $q,
                                 ChannelsService,
                                 UserRolesRest,
                                 UserService,
                                 SmartTags,
                                 GroupsRest,
                                 JourneyTagsRest,
                                 JourneyTypesRest,
                                 JourneyFunnelsRest,
                                 PredictorsRest) {
    var JourneyFunnels = new JourneyFunnelsRest(),
        JourneyTags = new JourneyTagsRest(),
        JourneyTypes = new JourneyTypesRest(),
        Predictors = new PredictorsRest(),
        Groups = new GroupsRest(),
        UserRoles = new UserRolesRest();
    $scope.group_id = $routeParams.group_id;
    $scope.chosen = {
      groupChannel: [],
      groupSmartTag: [],
      groupJourneyTypes: [],
      groupJourneyTags: [],
      groupFunnels: [],
      groupPredictors: [],
      groupRoles: [],
      groupUsers: []
    };

    $scope.initData = function (is_edit) {
      // Do all the required data initialization which we need.
      // Load full channel list for channel access
      ChannelsService.load(['inbound', 'dispatch'], false, true);
      /** ROLES */
      UserRoles.list().success(function (res) {
        $scope.fullGroupRoles = res.list;

        if (is_edit) { // edited user
          // data contains only roles accessible by current user
          // so all roles in group.roles might not be there in data
          // so filter out undefined values
          var arr = _.filter(_.map($scope.group.roles, function (roleId) {
            return _.find($scope.fullGroupRoles, {id: roleId});
          }));
          $scope.chosen.groupRoles = _.uniq(arr);
        } else {
          $scope.chosen.groupRoles = $scope.fullGroupRoles;
          $scope.group.roles = [];
        }
      });
      /** USERS */
      UserService.listAvailableUsers(function (data) {
        $scope.fullUserList = data['list'];
        var users = [];
        for (var i = 0, len = $scope.fullUserList.length; i < len; i++) {
          var current = $scope.fullUserList[i];
          if (current.email.indexOf("+") > 0) {
            users[i] = $scope.fullUserList[i];
          }
        }
        $scope.fullUserList = _.difference($scope.fullUserList, users);

        if (is_edit) {
          var arr = _.filter(_.map($scope.group.members, function (memberId) {
            return _.find($scope.fullUserList, {id: memberId});
          }));
          $scope.chosen.groupUsers = _.uniq(arr);
        } else {
          $scope.chosen.groupUsers = [];
          $scope.group.members = [];
        }
      });
      /** FUNNELS */
      JourneyFunnels.list().success(function (res) {
        $scope.fullFunnelsList = _.uniq(res.data);

        if (is_edit) {
          groupDeferred.promise.then(function () {
            var arr = _.map($scope.group.funnels, function (funnelId) {
              return _.find($scope.fullFunnelsList, {id: funnelId});
            });
            $scope.chosen.groupFunnels = _.uniq(arr);
          });
        } else {
          $scope.chosen.groupFunnels = [];
          $scope.group.funnels = [];
        }
      });
      /** JOURNEY TAGS & TYPES */
      JourneyTags.list().success(function (jTags) {
        $scope.fullJourneyTagsList = _.uniq(jTags.data);

        JourneyTypes.list().success(function (jTypes) {
          $scope.fullJourneyTypesList = _.uniq(jTypes.data);

          _.each(jTags.data, function (jTag) {
            var jType = _.find($scope.fullJourneyTypesList, {id: jTag.journey_type_id});
            jTag.journey_tag_full_name = jType.display_name + ' : ' + jTag.display_name;
          });

          if (is_edit) {
            groupDeferred.promise.then(function () {
              var arr = _.map($scope.group.journey_types, function (id) {
                return _.find($scope.fullJourneyTypesList, {id: id});
              });
              $scope.chosen.groupJourneyTypes = _.uniq(arr);

              arr = _.map($scope.group.journey_tags, function (id) {
                return _.find($scope.fullJourneyTagsList, {id: id});
              });
              $scope.chosen.groupJourneyTags = _.uniq(arr);
              updateAvailableJourneyTags();
            });
          } else {
            $scope.chosen.groupJourneyTypes = [];
            $scope.chosen.groupJourneyTags = [];
            $scope.group.journey_types = [];
            $scope.group.journey_tags = [];
          }
        });
      });

      /** PREDICTORS */
      Predictors.list().success(function (res) {
        $scope.fullPredictorsList = _.uniq(res.list);

        if (is_edit) {
          groupDeferred.promise.then(function () {
            var arr = _.map($scope.group.predictors, function (id) {
              return _.findWhere($scope.fullPredictorsList, {id: id});
            });
            $scope.chosen.groupPredictors = _.uniq(arr);
          });
        } else {
          $scope.chosen.groupPredictors = [];
          $scope.group.predictors = [];
        }
      });
    };

    if ($scope.group_id) {
      $scope.mode = 'edit';
      Groups.getOne($scope.group_id).success(function (res) {
        groupDeferred.resolve();
        $scope.group = res.group;
        if ($scope.group.perm == 'r' && $scope.mode == 'edit') {
          $scope.title = 'View Group';
        }
        $scope.initData(true);
      });
    } else {
      $scope.mode = 'create';
      $scope.group = {};
      $scope.initData(false);
    }

    $scope.objectIds = [$scope.group_id];
    var groupDeferred = $q.defer();

    $scope.title = {
      'create': 'New',
      'edit': 'Update'
    }[$scope.mode];

    $scope.$on(ChannelsService.ON_CHANNELS_LOADED, function () {
      $scope.fullChannelList = ChannelsService.getList();
      if ($scope.mode === 'edit') {
        var arr = _.map($scope.group.channels, function (roleId) {
          return _.find($scope.fullChannelList, {id: roleId});
        });
        $scope.chosen.groupChannel = _.uniq(arr);
      } else {
        $scope.chosen.groupChannel = $scope.fullChannelList;
        $scope.group.channels = [];
      }
      $scope.loadSmartTags();
    });

    $scope.addSelectTag = function (item, array) {
      array.indexOf(item) < 0 && array.push(item);
    };

    $scope.removeSelectTag = function (item, array) {
      _.remove(array, {id: item.id});
    };

    $scope.addJourneyType = function () {
      updateAvailableJourneyTags();
    };

    $scope.removeJourneyType = function (journeyType) {
      updateAvailableJourneyTags();
      _.remove($scope.chosen.groupJourneyTags, {journey_type_id: journeyType.id});
    };

    $scope.addChannelGroup = function (channel) {
      updateAvailableSmartTags();
    };
    $scope.removeChannelGroup = function (channel) {
      updateAvailableSmartTags();
      _.remove($scope.chosen.groupSmartTag, {channel: channel.id});
    };

    $scope.selectedJourneyTypeTags = [];

    function updateAvailableJourneyTags() {
      $scope.selectedJourneyTypeTags.length = 0;
      _.each($scope.chosen.groupJourneyTypes, function (journeyType) {
        Array.prototype.push.apply($scope.selectedJourneyTypeTags, _.filter($scope.fullJourneyTagsList, {journey_type_id: journeyType.id}));
      });
    }

    $scope.selectedChannelSmartTags = [];

    function updateAvailableSmartTags() {
      $scope.selectedChannelSmartTags.length = 0;
      _.each($scope.chosen.groupChannel, function (channel) {
        Array.prototype.push.apply($scope.selectedChannelSmartTags, _.filter($scope.fullSmartTags, {channel: channel.id}));
      });
    }

    /** SMART TAGS */
    $scope.loadSmartTags = function () {
      $scope.fullSmartTags = [];
      var loadedChannelCounter = 0;

      _.each($scope.fullChannelList, function (channel) {
        var params = {channel: channel.id};
        SmartTags.listAll(params).then(function (res) {
          Array.prototype.push.apply($scope.fullSmartTags, res.list);
          loadedChannelCounter += 1;

          if (loadedChannelCounter === $scope.fullChannelList.length) {
            updateAvailableSmartTags();

            if ($scope.mode === 'edit') {
              groupDeferred.promise.then(function () {
                var arr = _.map($scope.group.smart_tags, function (smartTagId) {
                  return _.findWhere($scope.selectedChannelSmartTags, {id: smartTagId});
                });
                $scope.chosen.groupSmartTag = _.uniq(arr);
              });
            } else { // new
              $scope.chosen.groupSmartTag = [];
              $scope.group.smart_tags = [];
            }
          }
        });
      });
    };

    $scope.saveButtonDisabled = function () {
      if (!$scope.group) {
        return true;
      }
      if (!$scope.group.name) {
        return true;
      }
      if (!$scope.chosen.groupChannel.length) {
        // Test that user roles are set for this user
        return true;
      }
      return false;
    };

    $scope.save = function () {
      $scope.group.channels = _.uniq(_.pluck($scope.chosen.groupChannel, 'id'));
      $scope.group.smart_tags = _.uniq(_.pluck($scope.chosen.groupSmartTag, 'id'));
      $scope.group.members = _.uniq(_.pluck($scope.chosen.groupUsers, 'id'));
      $scope.group.roles = _.uniq(_.pluck($scope.chosen.groupRoles, 'id'));
      $scope.group.journey_types = _.uniq(_.pluck($scope.chosen.groupJourneyTypes, 'id'));
      $scope.group.journey_tags = _.uniq(_.pluck($scope.chosen.groupJourneyTags, 'id'));
      $scope.group.funnels = _.uniq(_.pluck($scope.chosen.groupFunnels, 'id'));
      $scope.group.predictors = _.uniq(_.pluck($scope.chosen.groupPredictors, 'id'));
      Groups.save($scope.group).then(function () {
        $location.path('/groups/');
      });
    };
  }
  CreateUpdateGroupCtrl.$inject = ["$scope", "$location", "$routeParams", "$q", "ChannelsService", "UserRolesRest", "UserService", "SmartTags", "GroupsRest", "JourneyTagsRest", "JourneyTypesRest", "JourneyFunnelsRest", "PredictorsRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('GroupsListCtrl', GroupsListCtrl);

  /** @ngInject */
  function GroupsListCtrl($scope, $location, GroupsRest, DialogService) {
    var Groups = new GroupsRest();
    // Items Selection
    $scope.selected = [];
    $scope.filters = {
      name: ''
    };
    $scope.table = {
      sort: {
        predicate: 'name',
        reverse: false
      }
    };

    $scope.select = function (group) {
      if ($scope.selected.length) {
        var i = $scope.selected.indexOf(group);
        if (i === -1) {
          $scope.selected.push(group);
        } else {
          $scope.selected.splice(i, 1);
        }
      } else {
        $scope.selected.push(group);
      }
    };

    var getSelectedItems = function (list) {
      return _.filter(list, function (item) {
        return item['is_selected'];

      });
    };

    var findItems = function (list, item) {
      var items = [];
      if (item) {
        items = [item];
      } else {
        items = getSelectedItems(list);
      }
      return items;
    };

    var findItemIds = function (label) {
      var items = findItems($scope.groups, label);
      return _.pluck(items, 'id');
    };


    // CRUD actions
    $scope.load = function () {
      Groups.list().success(function (res) {
        $scope.groups = _.map(res.data, function (item) {
          item.is_selected = false;
          return item;
        });
      });
    };

    $scope.create = function () {
      $scope.edit();
    };

    $scope.edit = function (group) {

      var groupId = group && group.id || '';
      $location.path('/groups/edit/' + groupId);
    };

    $scope.share = function (group) {
      var ids = findItemIds(group);
      if (!ids.length) return;

      DialogService.openDialog({target: 'acl', objectType: 'group', objectIds: ids});
    };

    $scope.delete = function (group) {
      if (!group) {
        var ids = _.pluck($scope.selected, 'id');
        _.each(ids, function (id) {
          removeFromGroups(id);
        });
      } else {
        var id = group.id;
        removeFromGroups(id);
      }
    };

    function removeFromGroups(id) {
      Groups.remove(id).success(function () {
        var i = $scope.groups.indexOf(_.findWhere($scope.groups, {id: id}));
        $scope.groups.splice(i, 1);
      });
    }

    $scope.hasAnyPerm = function () {
      return _.any($scope.groups, function (item) {
        return item.perm != 'r'
      });
    };

    $scope.load();

    //Additional Actions
    $scope.showUsers = function (group) {
      $location.path('/groups/edit/' + group.id + '/users/');
    };


  }
  GroupsListCtrl.$inject = ["$scope", "$location", "GroupsRest", "DialogService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/funnels', {
          templateUrl: '/partials/funnels/list',
          controller: 'FunnelsListCtrl',
          name: 'funnels'
        })
        .when('/funnels/edit/:id?', {
          templateUrl: '/partials/funnels/edit',
          controller: 'CreateEditFunnelCtrl',
          name: 'funnels'
        })
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateEditFunnelCtrl', CreateEditFunnelCtrl);

  /** @ngInject */
  function CreateEditFunnelCtrl($routeParams,
                                $scope,
                                JourneyFunnelsRest,
                                JourneyTypesRest) {
    var JourneyFunnels = new JourneyFunnelsRest();
    var JourneyTypes = new JourneyTypesRest();
    var funnelId = $routeParams.id;
    $scope.title = funnelId ? 'Update' : 'Create';
    $scope.journeyTypes = {};
    $scope.journeyStages = {};
    $scope.item = {};
    $scope.formState = {};
    $scope.stepItems = [];

    JourneyTypes.list().success(function (types) {
      $scope.journeyTypes = types.data;
      if (!funnelId && $scope.item.journey_type == null && $scope.journeyTypes.length) {
        $scope.item.journey_type = $scope.journeyTypes[0].id;
      }

      var journeyStages = [];
      _.each($scope.journeyTypes, function(type) {
        JourneyTypes.getStages(type.id)
          .success(function(stage) {
            journeyStages.push(stage.data);
            if (journeyStages.length === $scope.journeyTypes.length) {
              $scope.journeyStages = _.flatten(journeyStages);
            }
          });
      });
    });

    $scope.filterByJourneyType = function(item) {
      return item.journey_type_id === $scope.item.journey_type
    };

    if (funnelId) {
      JourneyFunnels.getOne(funnelId).success(function (res) {
        $scope.item = res.data;
        $scope.loadStepItems();
      });
    } else {
      $scope.item = {
        name: '',
        journey_type: null,
        description: '',
        steps: []
      };
    }

    $scope.journeyTypeChanged = function () {
      $scope.stepItems.length = 0;
    };

    $scope.loadStepItems = function () {
      if ($scope.item) {
        $scope.stepItems.length = 0;
        $scope.stepItems = _.map($scope.item.steps, function (step) {
          return {'id': step}
        });
      }
    };

    $scope.addStepItem = function () {
      $scope.stepItems.push({'id': null});
    };

    $scope.removeStepItem = function (index) {
      $scope.stepItems.splice(index, 1);
    };

    $scope.save = function () {
      var isEditMode = !!funnelId;
      $scope.formState.isSaved = false;
      $scope.item.steps = _.remove(_.pluck($scope.stepItems, 'id'), undefined);
      JourneyFunnels.save($scope.item, isEditMode).success(function (res) {
        $scope.title = 'Update';
        $scope.item = res.data;
        $scope.loadStepItems($scope.item);
        $scope.formState.isSaved = true;
      });
    };

    $scope.openNewForm = function () {
      $scope.item = {
        name: '',
        journey_type: null,
        description: '',
        steps: []
      };
      $scope.title = 'Create';
      $scope.loadStepItems($scope.item);
      $scope.formState.isSaved = false;
      $scope.funnelForm.$setPristine();
    }
  }
  CreateEditFunnelCtrl.$inject = ["$routeParams", "$scope", "JourneyFunnelsRest", "JourneyTypesRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('FunnelsListCtrl', FunnelsListCtrl);

  /** @ngInject */
  function FunnelsListCtrl($scope, JourneyFunnelsRest, JourneyTypesRest) {
    var JourneyFunnels = new JourneyFunnelsRest();
    var JourneyTypes = new JourneyTypesRest();
    $scope.table = {
      sort: {
        predicate: 'name',
        reverse: false
      }
    };
    $scope.filters = {
      name: ''
    };
    $scope.selected = [];
    $scope.selectRow = function (selected) {
      var found = _.find($scope.selected, {id: selected.id});

      if (found) {
        _.remove($scope.selected, selected)
      } else {
        $scope.selected.push(selected)
      }
    };

    JourneyTypes.list().success(function (types) {
      $scope.journeyTypes = types.data;

      var journeyStages = [];
      _.each($scope.journeyTypes, function (type) {
        JourneyTypes.getStages(type.id)
          .success(function (stage) {
            journeyStages.push(stage.data);
            if (journeyStages.length === $scope.journeyTypes.length) {
              $scope.journeyStages = journeyStages;
            }
          });
      });
    });

    JourneyFunnels.list().success(function (res) {
      $scope.items = res.data;
      _.each($scope.items, function (item) {
        var journeyType = _.find($scope.journeyTypes, {'id': item.journey_type});
        if (journeyType) item.journeyTypeName = journeyType.display_name;
      });
    });

    $scope.remove = function () {
      _.each($scope.selected, function (item) {
        JourneyFunnels.remove(item.id).success(function () {
          _.remove($scope.items, {id: item.id});
        });
      });
    };
  }
  FunnelsListCtrl.$inject = ["$scope", "JourneyFunnelsRest", "JourneyTypesRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/journey_tags', {
          templateUrl: '/partials/journey/tag/list',
          controller: 'JourneyTagListCtrl',
          name: 'journey_tags'
        })
        .when('/journey_tags/edit/:id?', {
          templateUrl: '/partials/journey/tag/edit',
          controller: 'CreateEditJourneyTagCtrl',
          name: 'journey_tags'
        })
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateEditJourneyTagCtrl', CreateEditJourneyTagCtrl);

  /** @ngInject */
  function CreateEditJourneyTagCtrl($routeParams,
                                    $scope,
                                    $http,
                                    JourneyTagsRest,
                                    JourneyTypesRest,
                                    CustomerSegmentsRest) {
    var JourneyTags = new JourneyTagsRest();
    var JourneyTypes = new JourneyTypesRest();
    var CustomerSegments = new CustomerSegmentsRest();

    var id = $routeParams.id;
    $scope.title = id ? 'Update' : 'Create';
    $scope.journey_types = {};
    $scope.journey_stages = {};
    $scope.smart_tags = {
      list: []
    };
    $scope.customer_segments = [];
    $scope.item = {};
    $scope.formState = {};

    var resolveCtrl = function () {
      JourneyTypes.list().success(function (res) {
        $scope.journey_types = res.data;
        $scope.journey_stages = {};
        _.each($scope.journey_types, function (journey_type) {
          JourneyTypes.getStages(journey_type.id).success(function (stages) {
            $scope.journey_stages[journey_type.id] = stages.data.data;
          });
        });
      });

      CustomerSegments.list().success(function (res) {
        $scope.customer_segments = res.data;
      });

      $http.get('/smart_tags/json')
        .success(function (res) {
          $scope.smart_tags.list = _.map(res.list, function (item) {
            return {display_name: item.title, id: item.id, enabled: false}
          })
        })
    };

    $scope.filterSkipTags = function (tag) {
      return !_.contains($scope.item.skip_smart_tags, tag.id);
    };

    $scope.filterKeyTags = function (tag) {
      return !_.contains($scope.item.key_smart_tags, tag.id);
    };

    if (id) {
      JourneyTags.getOne(id).success(function (res) {
        $scope.item = res.data;
      });
    } else {
      $scope.item = newJourneyTag();
    }

    function newJourneyTag() {
      return {
        journey_type_id: null,
        display_name: "",
        description: "",
        tracked_stage_sequences: [],
        tracked_customer_segments: [],
        nps_range: [],
        csat_score_range: [],
        key_smart_tags: [],
        skip_smart_tags: []
      };
    }

    $scope.save = function () {
      $scope.formState.isSaved = false;
      JourneyTags.save($scope.item).success(function (res) {
        $scope.title = 'Update';
        $scope.item = res.data;
        $scope.formState.isSaved = true;
      });
    };

    $scope.openNewForm = function () {
      $scope.item = newJourneyTag();
      $scope.title = 'Create';
      $scope.formState.isSaved = false;
    };

    resolveCtrl();
  }
  CreateEditJourneyTagCtrl.$inject = ["$routeParams", "$scope", "$http", "JourneyTagsRest", "JourneyTypesRest", "CustomerSegmentsRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('JourneyTagListCtrl', JourneyTagListCtrl);

  /** @ngInject */
  function JourneyTagListCtrl($scope, JourneyTagsRest, JourneyTypesRest) {
    var JourneyTags = new JourneyTagsRest();
    var JourneyTypes = new JourneyTypesRest();
    $scope.table = {
      sort: {
        predicate: 'display_name',
        reverse: false
      }
    };

    $scope.filters = {
      display_name: ''
    };
    $scope.selected = [];
    $scope.selectRow = function (selected) {
      var found = _.find($scope.selected, {id: selected.id});

      if (found) {
        _.remove($scope.selected, selected)
      } else {
        $scope.selected.push(selected)
      }
    };

    var resolveCtrl = function () {
      var journey_type_id_maps_title = {};
      JourneyTypes.list().success(function (res) {
        _.each(res.data, function (jt) {
          journey_type_id_maps_title[jt.id] = jt.display_name;
        });

        JourneyTags.list().success(function (tags) {
          $scope.items = _.map(tags.data, function (d) {
            return _.extend(d, {selected: false});
          });
          _.each($scope.items, function (item) {
            item.journey_type = journey_type_id_maps_title[item.journey_type_id];
          });
        });
      });
    };

    $scope.remove = function () {
      _.each($scope.selected, function (item) {
        JourneyTags.remove(item.id).success(function () {
          _.remove($scope.items, {id: item.id});
        });
      });
    };

    resolveCtrl();
  }
  JourneyTagListCtrl.$inject = ["$scope", "JourneyTagsRest", "JourneyTypesRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/journey_types/', {
          templateUrl: '/partials/journey/type/list',
          controller: 'JourneyTypeListCtrl',
          name: 'journey_types'
        })
        .when('/journey_types/edit/:id?/', {
          templateUrl: '/partials/journey/type/edit',
          controller: 'CreateEditJourneyTypeCtrl',
          name: 'journey_types'
        })
        .when('/journey_types/edit/:jtId/stage/:id?/', {
          templateUrl: '/partials/journey/stage/edit',
          controller: 'CreateEditJourneyStageCtrl',
          name: 'journey_types'
        })
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('JourneyFacetConfig', JourneyFacetConfig);

  /** @ngInject */
  function JourneyFacetConfig($http, $q) {
    var _cachedOptions = null;
    var platforms = ['twitter', 'facebook', 'nps', 'chat', 'email', 'web', 'voice'];

    return {
      "getOptions": function (callback) {
        var result;
        if (_cachedOptions !== null) {
          result = $q.when(_cachedOptions);
        } else {
          result = $http.get('/journeys/facet_options').then(function (resp) {
            _cachedOptions = resp.data;
            return _cachedOptions;
          });
        }
        if (callback && angular.isFunction(callback)) {
          return result.then(callback);
        }
        return result;
      },
      "getEventTypes": function (callback) {
        var result;
        var promises = [];
        if (_cachedOptions && _cachedOptions.eventTypes !== null) {
          result = $q.when(_cachedOptions);
        } else {
          //fetch dynamic and static events {show_all:true}
          var event_type_promise = $http.get('/event_type/list', {
            params : { show_all : true }
          });
          promises = [event_type_promise];

          result = $q.all(promises).then(function (responses) {
            var types = [];
            _.each(responses, function (resp) {
              if (!resp.data) return;
              types = types.concat(_.map(resp.data.data, function (type) {
                return {
                  'id': type.id,
                  'name': type.name,
                  'platform' : type.platform,
                  'display_name' : type.name
                };
              }));
            });
            _cachedOptions.eventTypes = types;
            return _cachedOptions;
          });
        }
        if (callback && angular.isFunction(callback)) {
          return result.then(callback);
        }
        return result;
      },
      "makeFilter": function (scope) {
        var keys = _.keys(_.pick(scope, 'display_name', 'description', 'title'));
        return _.object(keys, ['', '', '']);
      }
    };
  }
  JourneyFacetConfig.$inject = ["$http", "$q"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateEditJourneyStageCtrl', CreateEditJourneyStageCtrl);

  /** @ngInject */
  function CreateEditJourneyStageCtrl($location,
                                      $routeParams,
                                      $scope,
                                      JourneyFacetConfig,
                                      SystemAlert,
                                      JourneyTypesRest) {
    var JourneyTypes = new JourneyTypesRest();
    var jtId = $routeParams.jtId,
      id = $routeParams.id;

    $scope.title = id ? 'Update' : 'Create';
    $scope.item = {};
    $scope.eventTypeItems = [];

    JourneyFacetConfig.getOptions(function (opts) {
      $scope.options = {stageStatuses: opts.journey_type.stageStatuses};
    });

    JourneyFacetConfig.getEventTypes(function (opts) {

      console.log("GET EVENT TYPES", opts);

      $scope.options = _.extend($scope.options, {eventTypes: opts.eventTypes});
    });

    function setJourneyType(item) {
      item = item || $scope.item;
      item.jtId = jtId;
      $scope.loadEventTypeItems();
    }

    function load() {
      if (!id) return;
      return JourneyTypes.getOneStage(jtId, id).success(function(res) {
        $scope.item = res.data;
        setJourneyType($scope.item);
      });
    }

    _.extend($scope,
      {
        redirectAll: function () {
          $location.path('/journey_types/edit/' + jtId);
        }
      },
      {
        "save": function () {
          $scope.item.event_types = [];
          $scope.item.must_have_rules = [];
          $scope.item.must_not_have_rules = [];
          _.each($scope.eventTypeItems, function (type) {
            if (type.id) {
              $scope.item.event_types.push(type.id);
              var obj1 = {}, obj2 = {};
              obj1[type.id] = type.must_have_rules;
              obj2[type.id] = type.must_not_have_rules;
              $scope.item.must_have_rules.push(obj1);
              $scope.item.must_not_have_rules.push(obj2);
            }
          });
          var params = {
            data: $scope.item,
            id: jtId
          };
          if (id) {
            _.extend(params, {stageId: id});
          }

          return JourneyTypes.saveStage(params).success(function () {
            SystemAlert.success('Journey Stage saved', 5000);
            $scope.redirectAll();
          });
        }
      });

    $scope.loadEventTypeItems = function () {
      if ($scope.item) {
        $scope.eventTypeItems.length = 0;
        _.each($scope.item.event_types, function (typeId) {
          var must_have_rules = _.find($scope.item.must_have_rules, function (obj) {
            return obj.hasOwnProperty(typeId)
          });
          var must_not_have_rules = _.find($scope.item.must_not_have_rules, function (obj) {
            return obj.hasOwnProperty(typeId)
          });
          $scope.eventTypeItems.push({
            'id': typeId,
            'must_have_rules': must_have_rules[typeId],
            'must_not_have_rules': must_not_have_rules[typeId]
          });
        });
      }
    };

    $scope.addEventTypeItem = function () {
      $scope.eventTypeItems.push({'id': null, 'must_have_rules': [], 'must_not_have_rules': []});
    };

    $scope.removeEventTypeItem = function (index) {
      $scope.eventTypeItems.splice(index, 1);
    };

    setJourneyType();
    load();
  }
  CreateEditJourneyStageCtrl.$inject = ["$location", "$routeParams", "$scope", "JourneyFacetConfig", "SystemAlert", "JourneyTypesRest"];
})();
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
        controller: ["$scope", function ($scope) {
          $scope.data = data;
          $scope.close = $scope.$close;
        }]
      });
    };

    $scope.showEventTypeModal = function (item) {
      openEventTypeModal(item);
    };

    $scope.load(id);
  }
  CreateEditJourneyTypeCtrl.$inject = ["$location", "$timeout", "$modal", "$q", "$routeParams", "$scope", "SystemAlert", "MetadataService", "JourneyFacetConfig", "JourneyTypesRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('JourneyTypeListCtrl', JourneyTypeListCtrl);

  /** @ngInject */
  function JourneyTypeListCtrl($location, $scope, SystemAlert, JourneyTypesRest, JourneyFacetConfig) {
    var JourneyTypes = new JourneyTypesRest();
    var init = function () {
      $scope.selected = [];
      $scope.flags = {
        search: '',
        selectedAll: false
      };
      $scope.table = {
        sort: {
          predicate: 'display_name',
          reverse: false
        }
      };
//      $scope.filterPredicate = JourneyFacetConfig.makeFilter($scope); // ???
      $scope.refresh();
    };

    $scope.select = function (selected) {
      if (!selected) {
        // for all selection
        _.each($scope.items, function(each, index) {
          $scope.items[index].selected = !$scope.flags.selectedAll;
        });

        if ($scope.flags.selectedAll) {
          $scope.selected = [];
        } else {
          $scope.selected = _.clone($scope.items);
        }
        $scope.flags.selectedAll = !$scope.flags.selectedAll;
      } else {
        _.each($scope.items, function(each, index) {
          if (selected.id === each.id) {
            var found = _.findWhere($scope.selected, {id: selected.id});
            if (found) {
              _.remove($scope.selected, selected);
            } else {
              $scope.selected.push(selected)
            }
            $scope.items[index].selected = !selected.selected;
          }
        });
        $scope.flags.selectedAll = ($scope.selected.length === $scope.items.length);
      }
    };

    $scope.create = function() {
      $location.path('/journey_types/edit/');
    };

    $scope.refresh = function() {
      JourneyTypes.list().success(function (types) {
        $scope.items = _.map(types.data, function(each) {
          return _.extend(each, {
            status: _.sample(['IN_SYNC', 'OUT_OF_SYNC']),
            selected: false
          });
        });
      });
    };

    $scope.remove = function() {
      _.each($scope.selected, function (item, index) {
        JourneyTypes.remove(item.id).success(function () {
          _.remove($scope.items, function (i) {
            return i.id === item.id
          });
          SystemAlert.info('Journey Type "' + item.display_name + '" removed', 3000);
          if (index === ($scope.selected.length - 1)) {
            $scope.refresh();
          }
        });
      });
    };

    init();
  }
  JourneyTypeListCtrl.$inject = ["$location", "$scope", "SystemAlert", "JourneyTypesRest", "JourneyFacetConfig"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/labels/all', {
          templateUrl: '/partials/labels/labels',
          controller: 'ContactLabelsCtrl',
          name: 'labels'
        })
        .when('/labels/edit', {
          templateUrl: '/partials/labels/edit',
          controller: 'CreateEditLabelCtrl',
          name: 'labels'
        })
        .when('/labels/edit/:label_id', {
          templateUrl: '/partials/labels/edit',
          controller: 'CreateEditLabelCtrl',
          name: 'labels'
        })
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('ContactLabel', ContactLabel);

  /** @ngInject */
  function ContactLabel($resource) {
    return $resource('/contact_label/:action/json', {}, {
      update: {method: 'POST', params: {action: 'update'}},
      add: {method: 'POST', params: {action: 'update'}},
      delete: {method: 'POST', params: {action: 'delete'}},
      activate: {method: 'POST', params: {action: 'activate'}},
      deactivate: {method: 'POST', params: {action: 'deactivate'}}
    });
  }
  ContactLabel.$inject = ["$resource"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('ContactLabelsCtrl', ContactLabelsCtrl);

  /** @ngInject */
  function ContactLabelsCtrl($scope, ContactLabelsRest, ContactLabel, DialogService) {
    var ContactLabels = new ContactLabelsRest();
    var getSelectedItems = function (list) {
      return _.filter(list, function (item) {
        return item['is_selected'];
      });
    };


    var findItems = function (list, item) {
      var items = [];
      if (item) {
        items = [item];
      } else {
        items = getSelectedItems(list);
      }
      return items;
    };

    var findItemIds = function (label) {
      var items = findItems($scope.labels, label);
      return _.pluck(_.filter(items, function (el) {
        return el.perm == 's' || el.perm == 'rw'
      }), 'id');
    };

    $scope.labels = [];
    $scope.noLabelsAlert = false;

    $scope.filters = {
      'status': '',
      'title': ''
    };

    $scope.filterPredicate = function (tag) {
      var result = true;
      if ($scope.filters.title) {
        var title = tag.title || '';
        var description = tag.description || '';
        result = result && (title.toLowerCase().indexOf($scope.filters.title.toLowerCase()) != -1 ||
          description.toLowerCase().indexOf($scope.filters.title.toLowerCase()) != -1);
      }
      if ($scope.filters.status) {
        result = result && tag.status == $scope.filters.status;
      }
      return result;
    };

    var loadLabels = function () {
      ContactLabels.list().success(
        function (d) {
          $scope.labels = d.list;
          $scope.noLabelsAlert = $scope.labels.length == 0;
        }
      ).error(function () {
        $scope.noLabelsAlert = true;
      });
    };
    loadLabels();

    $scope.loadLabels = function (dates) {
      loadLabels();
    };

    $scope.deleteLabel = function (items) {
      ContactLabel.delete({"labels": items}, loadLabels);
    };

    $scope.share = function (item) {
      var ids = findItemIds(item);
      if (!ids.length) return;

      DialogService.openDialog({target: 'acl', objectType: 'ContactLabel', objectIds: ids});

      $scope.$on(DialogService.CLOSE, function () {
        $scope.deselectAll();
      });
    };

    $scope.activateLabel = function (items) {
      ContactLabel.activate({"labels": items}, loadLabels);
    };

    $scope.suspendLabel = function (items) {
      ContactLabel.deactivate({"labels": items}, loadLabels);
    };
    // Items Selection
    $scope.selectAll = function () {
      _.forEach($scope.labels, function (item) {
        item.is_selected = $scope.all_selected;
      });
    };

    $scope.deselectAll = function () {
      $scope.all_selected = false;
      $scope.selectAll();
    };

  }
  ContactLabelsCtrl.$inject = ["$scope", "ContactLabelsRest", "ContactLabel", "DialogService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateEditLabelCtrl', CreateEditLabelCtrl);

  /** @ngInject */
  function CreateEditLabelCtrl($scope, $routeParams, ContactLabel) {
    $scope.params = {};

    $scope.item_id = $routeParams.label_id;
    var contactLabelDefaults = {};
    if ($scope.item_id) {
      $scope.mode = 'edit';
      ContactLabel.get({id: $scope.item_id}, function (res) {
        $scope.item = res.item;
      });
    } else {
      $scope.mode = 'create';
      $scope.item = new ContactLabel();
      $scope.item = angular.extend($scope.item, contactLabelDefaults);
      //console.log('new smart tag', $scope.item);
    }

    $scope.title = {
      'create': 'Create',
      'edit': 'Update'
    }[$scope.mode];


    $scope.formState = {
      isSaved: false,
      isError: false
    };

    $scope.save = function () {
      $scope.formState.isSaved = false;

      ContactLabel.update($scope.item, function (res) {
        $scope.formState.isSaved = true;
        $scope.item = res.item;
        //$location.path('/tags/all/')
      });
    };

  }
  CreateEditLabelCtrl.$inject = ["$scope", "$routeParams", "ContactLabel"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/messages/all', {
          templateUrl: '/partials/messages/messages',
          controller: 'AllMessagesCtrl',
          name: 'messages'
        })
        .when('/messages/all/:channel_id', {
          templateUrl: '/partials/messages/messages',
          controller: 'AllMessagesCtrl',
          name: 'messages'
        })
        .when('/messages/edit', {
          templateUrl: '/partials/messages/edit',
          controller: 'CreateEditMessageCtrl',
          name: 'messages'
        })
        .when('/messages/edit/:message_id', {
          templateUrl: '/partials/messages/edit',
          controller: 'CreateEditMessageCtrl',
          name: 'messages'
        })
        .when('/messages/edit/:form_mode/:source_channel_id', {
          templateUrl: '/partials/messages/edit',
          controller: 'CreateEditMessageCtrl',
          name: 'messages'
        })
        .when('/messages/edit/:form_mode/:message_id/:source_channel_id', {
          templateUrl: '/partials/messages/edit',
          controller: 'CreateEditMessageCtrl',
          name: 'messages'
        })
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('AppState', AppState);

  /** @ngInject */
  function AppState($rootScope) {
    //store filters
    $rootScope.$on('configure_messages_filters_changed', function (evnt) {
      amplify.store('configure_messages_filters', evnt.targetScope.filters);
    });
    return amplify;
  }
  AppState.$inject = ["$rootScope"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('Message', Message);

  /** @ngInject */
  function Message($resource) {
    return $resource('/message/:action/json', {}, {
      create: {method: 'POST', params: {action: 'create'}},
      update: {method: 'POST', params: {action: 'update'}},
      remove: {method: 'POST', params: {action: 'delete'}},
      activate: {method: 'POST', params: {action: 'activate'}},
      deactivate: {method: 'POST', params: {action: 'deactivate'}}
    });
  }
  Message.$inject = ["$resource"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('Messages', Messages);

  /** @ngInject */
  function Messages($resource) {
    return $resource('/messages/json', {}, {
      list: {method: 'GET', isArray: false}
    });
  }
  Messages.$inject = ["$resource"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .directive('messageTags', messageTags);

  /** @ngInject */
  function messageTags() {
    return {
      require: '?ngModel',
      link: function (scope, element, attrs, ctrl) {
        setTimeout(function () {
          var sel = element.select2({tags: []});

          scope.$watch('matchable.topics', function (newVal, oldVal) {
            sel.select2("val", newVal);
          });

          angular.element(sel).bind("change", function ($event, flag) {
            ctrl.$setViewValue(sel.select2("val"));
          });
        }, 0);
      }
    };
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('AllMessagesCtrl', AllMessagesCtrl);

  /** @ngInject */
  function AllMessagesCtrl($scope, $location, $routeParams, Messages, Message, ChannelsService, DialogService) {
    $scope.messages = [];
    $scope.form_mode = null;
    $scope.filters = {
      'channel': null,
      'status': '',
      'creative': '',
      'limit': 30,
      'offset': 0
    };

    $scope.selected = [];
    $scope.selectRow = function (selected) {
      var found = _.find($scope.selected, {id: selected.id});

      if (found) {
        _.remove($scope.selected, selected)
      } else {
        $scope.selected.push(selected)
      }
    };

    $scope.filterPredicate = function (message) {
      var result = true;
      if ($scope.filters.creative) {
        result = result && message.creative.toLowerCase().indexOf($scope.filters.creative.toLowerCase()) != -1;
      }
      if ($scope.filters.status) {
        result = result && message.status == $scope.filters.status;
      }
      if ($scope.filters.channel) {
        result = result && message.channels.indexOf($scope.filters.channel) != -1;
      }
      return result;
    };

    $scope.selectAll = function () {
      $scope.selected = $scope.messages;
    };

    $scope.activate = function () {
      var ids = _.pluck($scope.selected, 'id');
      Message.activate({'ids': ids}, function (res) {
        _.each($scope.selected, function (item) {
          item.status = 'active';
        });
      });
    };

    $scope.deactivate = function () {
      var ids = _.pluck($scope.selected, 'id');
      Message.deactivate({'ids': ids}, function (res) {
        _.each($scope.selected, function (item) {
          item.status = 'inactive';
        });
      });
    };

    $scope.createMessage = function () {
      //$location.path('/messages/edit/');
      $scope.form_mode = 'creation';
      $location.path('/messages/edit/' + $scope.form_mode + '/' + ($routeParams.channel_id || ''));
    };

    $scope.edit = function (message) {
      if (!message) return;
      //$location.path('/messages/edit/').search({message_id: message.id});
      $scope.form_mode = 'edition';
      $location.path('/messages/edit/' + $scope.form_mode + '/' + message.id + '/' + $scope.filters.channel);
    };

    $scope.share = function () {
      var ids = _.pluck($scope.selected, 'id');

      DialogService.openDialog({target: 'acl', objectType: 'matchable', objectIds: ids});

      $scope.$on(DialogService.CLOSE, function () {
        $scope.selectAll();
      });
    };

    $scope.remove = function () {
      var ids = _.pluck($scope.selected, 'id');
      Message.remove({'ids': ids}, function () {
        $scope.messages = _.filter($scope.messages, function (item) {
          return _.indexOf(ids, item.id) == -1;
        });
      });
    };

    $scope.refresh = function (options) {
      if (options && options.redirect) {
        $location.path('/messages/all/' + $scope.filters.channel);
      }
      $scope.loadMessages();
    };

    $scope.loadMessages = function () {
      if ($routeParams.channel_id) {
        $scope.filters.channel = $routeParams.channel_id;
        //$routeParams.channel_id = undefined;
      }
      var params = {
        'offset': $scope.filters.offset,
        'limit': $scope.filters.limit,
        'channel': $scope.filters.channel,
        'status': $scope.filters.status,
        'search_term': $scope.filters.creative
      };

      Messages.list(params, function (res) {
        $scope.messages = res.list;

        $scope.filters.offset = res.offset;
        $scope.filters.limit = res.limit;
        $scope.size = res.size;

        var pages = res.size / res.limit;
        $scope.pages = Math.ceil(pages);
      });
    };

    //Make the first filters.status to be -- All Statuses --
    $scope.filters.status = "";

    ChannelsService.load('inbound', false, true);
    $scope.$on(ChannelsService.ON_CHANNELS_LOADED, function (scope, bookmark) {
      $scope.channels = ChannelsService.getList();
      if ($scope.channels.length != 0) {
        $scope.filters.channel = ChannelsService.getSelected() ? ChannelsService.getSelectedId() : $scope.channels[0];
        $scope.loadMessages();
      }
    });


    $scope.filters.currentPage = 0;
    $scope.pages = 0;

    // like python's range fn
    $scope.range = function (start, end) {
      var ret = [];
      if (!end) {
        end = start;
        start = 0;
      }
      for (var i = start; i < end; i++) {
        ret.push(i);
      }
      return ret;
    };

    $scope.prevPage = function () {
      if ($scope.filters.currentPage > 0) {
        $scope.filters.currentPage--;
        $scope.filters.offset = parseInt($scope.filters.offset) - parseInt($scope.filters.limit);
      }
    };

    $scope.nextPage = function () {
      if ($scope.filters.currentPage < $scope.pages - 1) {
        $scope.filters.currentPage++;
        $scope.filters.offset = parseInt($scope.filters.offset) + parseInt($scope.filters.limit);
      }
    };

    $scope.setPage = function () {
      $scope.filters.currentPage = this.n;
      $scope.filters.offset = (parseInt($scope.filters.limit) * this.n);
    };

    $scope.$watch('filters.currentPage', function (nVal, oVal) {
      if (nVal !== oVal) {
        $scope.loadMessages();
      }
    });

    $scope.$watch('filters', function (newVal, oldVal) {
      if (newVal != oldVal)
        $scope.$emit('configure_messages_filters_changed');
    }, true);


  }
  AllMessagesCtrl.$inject = ["$scope", "$location", "$routeParams", "Messages", "Message", "ChannelsService", "DialogService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateEditMessageCtrl', CreateEditMessageCtrl);

  /** @ngInject */
  function CreateEditMessageCtrl($scope, $location, $routeParams, $q, Message, Messages, ChannelsService, FilterService, SystemAlert, LanguageUtils) {
    /** INIT */
    $scope.params = {};
    $scope.form_mode = null;
    $scope.form_mode = $routeParams.form_mode;
    $scope.message_id = $routeParams.message_id;
    $scope.source_channel_id = $routeParams.source_channel_id; // Keep track where the edit came from.
    $scope.changingChannelIds = [];
    $scope.matchable = newMatchable();
    $scope.fullIntentions = _.map(FilterService.getIntentions(), function (el) {
      return {
        display: el.display,
        label: el.label
      };
    });

    function newMatchable() {
      return {
        intentions: [],
        channels: [],
        creative: '',
        language: '',
        topics: []
      };
    }

    /** ALL LANGUAGES */
    var langPromise = LanguageUtils.fetchSupportedLanguages().then(function (result) {
      $scope.fullLanguages = result;
    });

    ChannelsService.load('inbound', false, true);

    /** ALL CHANNELS */
    var channelsDeferred = $q.defer();
    $scope.$on(ChannelsService.ON_CHANNELS_LOADED, function () {
      channelsDeferred.resolve();
      $scope.fullChannelList = ChannelsService.getList();
    });

    /** OPERATIONS BY MODE STATUS */
    if ($scope.message_id && $scope.form_mode === 'edition') {
      $scope.mode = 'edit';
      Messages.get({id: $scope.message_id}, function (res) {
        /* res.matchable contains only labels, Ids, so we need to operate with them as well */
        $scope.matchable = res.matchable;

        /** INTENTIONS */
        var intentions = [];
        _.each($scope.matchable.intentions, function (intentionLabel) {
          intentions.push(_.findWhere($scope.fullIntentions, {label: intentionLabel}));
        });
        $scope.chosenIntentions = _.uniq(intentions);
        $scope.changingIntentionLabels = _.pluck($scope.chosenIntentions, 'label');

        /** CHANNEL */
        channelsDeferred.promise.then(function () {
          /* $scope.matchable.channels[0] === CHANNEL_ID */
          $scope.chosenChannel = _.findWhere($scope.fullChannelList, {id: $scope.matchable.channels[0]});
          $scope.changingChannelIds = $scope.matchable.channels; // 1 ID
          $scope.channelsChanged();
        });

        /** LANGUAGE */
        langPromise.then(function () {
          $scope.chosenLang = _.findWhere($scope.fullLanguages, {code: $scope.matchable.language});
          $scope.changingLangCode = [$scope.chosenLang.code];
        });
      });
    } else {
      $scope.mode = 'create';
      $scope.chosenIntentions = null;
      $scope.changingIntentionLabels = [];

      $scope.chosenLang = null;
      $scope.changingLangCode = [];

      $scope.chosenChannel = null;
      $scope.changingChannelIds = [];

      $scope.matchable = newMatchable();

      if ($scope.source_channel_id) {
        channelsDeferred.promise.then(function () {
          $scope.matchable.channels = [$scope.source_channel_id];
          $scope.chosenChannel = _.findWhere($scope.fullChannelList, {id: $scope.matchable.channels[0]});
          $scope.changingChannelIds = $scope.matchable.channels;
          $scope.channelsChanged();
        });
      }
    }

    $scope.platform = null;
    $scope.title = {
      'create': 'Create',
      'edit': 'Update'
    }[$scope.mode];

    /** ACTIONS */
    $scope.addIntention = function (intention) {
      $scope.changingIntentionLabels.push(intention.label);
    };
    $scope.removeIntention = function (intention) {
      $scope.changingIntentionLabels.splice($scope.changingIntentionLabels.indexOf(intention.label), 1);
    };
    $scope.addChannel = function (channel) {
      $scope.changingChannelIds = [channel.id];
      $scope.channelsChanged();
    };
    $scope.addLang = function (lang) {
      $scope.changingLangCode = [lang.code];
    };

    $scope.channelsChanged = function () {
      // On each channel change, keep track if we need to track by platform or not
      if ($scope.matchable.channels.length) {
        var channel = null;
        if ($scope.form_mode === 'create') {
          channel = $scope.fullChannelList[0];
        } else {
          // We have a channel selected, filter by that platform.
          channel = _.findWhere($scope.fullChannelList, {id: $scope.matchable.channels[0]});
        }
        $scope.platform = channel.platform;
      } else {
        $scope.platform = null;
      }
    };

    $scope.redirectAllMessages = function (channel_id) {
      if (channel_id) {
        $location.path('/messages/all/' + channel_id);
      } else {
        $location.path('/messages/all');
      }
    };

    $scope.saveButtonDisabled = function () {
      if (!$scope.matchable.creative) {
        return true;
      }
      if (!$scope.changingChannelIds.length) {
        return true;
      }
      return false;
    };

    $scope.save = function () {
      var PostMethod;
      $scope.matchable.intentions = _.uniq($scope.changingIntentionLabels);
      $scope.matchable.channels = $scope.changingChannelIds;
      $scope.matchable.language = $scope.changingLangCode[0];

      if ($scope.mode == 'create') {
        PostMethod = Message.create;
      } else {
        PostMethod = Message.update;
      }

      PostMethod($scope.matchable, function () {
        $scope.redirectAllMessages($scope.changingChannelIds[0]);
      }, function onError(err) {
        SystemAlert.error(err);
      });
    };

  }
  CreateEditMessageCtrl.$inject = ["$scope", "$location", "$routeParams", "$q", "Message", "Messages", "ChannelsService", "FilterService", "SystemAlert", "LanguageUtils"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
    $routeProvider
      .when('/password/:email', {
        templateUrl: '/partials/users/profile',
        controller: 'PasswordCtrl',
        name: 'password'
      })
  }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('PasswordCtrl', PasswordCtrl);

  /** @ngInject */
  function PasswordCtrl($scope, $routeParams, $modal, DialogService, UserService, UserEditService, $timeout, toaster) {
    var off = [];
    var init = function () {
      $scope.errorMessages = [];
      $scope.messages = [];
      $scope.user = {};
      $scope.cached_user = {};
    };

    var destructor = function () {
      off.forEach(function (unbind) {
        unbind();
      });
      off = null;
    };

    var toResource = function (user) {
      var u = new UserEditService();
      for (var i in user) {
        u[i] = user[i];
      }
      u.password = "";
      u.passwordConfirm = "";
      return u;
    };

    if ($routeParams.hasOwnProperty('email')) {
      $scope.email = $routeParams.email;
    }

    if ($scope.email) {
      UserService.getUserByEmail($scope.email, function (res) {
        $scope.user = toResource(res.user);
        $scope.cached_user = $scope.user;
        $scope.user.password = "";
        $scope.userProfileForm.$setPristine();
      })
    }

    $scope.resetPassword = function () {
      //res is the promise object returned - code between 200 and 209 is considered a success...thus the callback function is called
      UserService.setPassword($scope.email, $scope.password, function (res) {
        $scope.messages = res.messages;
        //Close the dialog after 3 seconds
        $timeout(function () {
          DialogService.closeDialog({dialog: 'password_change', email: $scope.email});
          $scope.modalShown = false;
        });
      }, function onError(res) {
        $scope.errorMessages = res.messages;
      });
    };

    $scope.close = function () {
      DialogService.closeDialog({dialog: 'password_change', email: $scope.email});
      $scope.modalShown = false;
    };

    $scope.viewDetails = function () {
      var dialogueScope = $scope.$new();
      $modal.open({
        templateUrl: '/static/assets/js/app/configure/password/controllers/configure.password-policies.html',
        scope: dialogueScope
      });
    };

    $scope.saveProfile = function () {
      var usr = toResource($scope.user);
      $scope.user.$save(function () {
        $scope.user = usr;
        toaster.pop('success', 'Password has been changed');
      }, function () {
        $scope.user = usr;
      });
    };

    $scope.cancelEdition = function () {
      if (!$scope.userProfileForm.$pristine) {
        if ($scope.email) {
          UserService.getUserByEmail($scope.email, function (res) {
            $scope.user = toResource(res.user);
            $scope.cached_user = $scope.user;
            $scope.user.password = "";
          })
        }
        $scope.userProfileForm.$setPristine();
      }
    };

    off.push($scope.$on(DialogService.OPEN_DIALOG_EVENT, function (evt, data) {
      if (data.dialog == 'password_change') {
        //reset all fields
        $scope.errorMessages = [];
        $scope.messages = [];
        $scope.password = null;
        $scope.passwordConfirm = null;
        $scope.passwordResetForm.$setPristine();
        $scope.email = data.email;
        // modalShown is $watched by uiModal, only change of value would trigger showing of modal
        // if simply set to true here, when modal is dismissed by clicking on backdrop, modalShown's value would remain true
        // thereby not triggering any change in value
        // ++undefined === NaN ~ false
        $scope.modalShown = ++$scope.modalShown || true;
      }
    }));

    init();
    off.push($scope.$on('$destroy', destructor));
  }
  PasswordCtrl.$inject = ["$scope", "$routeParams", "$modal", "DialogService", "UserService", "UserEditService", "$timeout", "toaster"];
})();

(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/predictors', {
          templateUrl: '/partials/predictors/list',
          controller: 'PredictorsCtrl',
          name: 'predictors'
        })
        .when('/predictors/:new_or_id', {
          templateUrl: '/partials/predictors/new_predictor',
          controller: 'NewPredictorCtrl',
          name: 'predictors'
        })
        .when('/predictors_v2/:new_or_id', {
          templateUrl: '/partials/predictors/new_predictor_v2',
          controller: 'NewPredictorV2Ctrl',
          name: 'predictors'
        })
        .when('/predictors/:id/detail', {
          templateUrl: '/partials/predictors/view',
          controller: 'PredictorsViewCtrl',
          name: 'predictors'
        })
        .when('/predictors/:predictorId/models/', {
          templateUrl: '/partials/predictors/models/list',
          controller: 'PredictorModelListController',
          name: 'predictors'
        })
        .when('/predictors/:predictorId/models/edit/:id?/', {
          templateUrl: '/partials/predictors/models/edit',
          controller: 'CreateEditPredictorsModelCtrl',
          name: 'predictors'
        })
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory("selectedPredictorsService", selectedPredictorsService);

  /** @ngInject */
  function selectedPredictorsService() {
    var selected = [];
    return {
      setSelected: function (predictors) {
        selected = predictors;
      },
      getSelected: function () {
        return selected
      }
    };
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateEditPredictorsModelCtrl', CreateEditPredictorsModelCtrl);

  /** @ngInject */
  function CreateEditPredictorsModelCtrl($location, $routeParams, $scope, PredictorsRest, SystemAlert) {
    var Predictors = new PredictorsRest();
    var predictorId = $routeParams.predictorId,
        modelId = $routeParams.id;
    var viewModelBase = {
      title: modelId ? 'Update' : 'Create',
      item: {
        display_name: '',
        description: '',
        model_type: '',
        action_features: [],
        context_features: [],
        train_data_percentage: 50,
        min_samples_thresould: 1
      },
      redirectAllHref: function () {
        return '/predictors/' + predictorId + '/models/';
      },
      redirectAll: function () {
        $location.path(this.redirectAllHref());
      },
      save: function () {
        var _params = _.pick($scope.item, 'display_name', 'description', 'model_type', 'context_features', 'action_features', 'train_data_percentage', 'min_samples_thresould');

        console.log('SAVE', _params);
        if (modelId) {
          //update
          Predictors.updateModel(predictorId, modelId, _params)
            .success(function successCallback(response) {
              $scope.redirectAll();
            });
        } else {
          //create
          return Predictors.saveModel(predictorId, _params).success(function () {
            SystemAlert.success('Model saved', 5000);
            //$scope.form.$setPristine();
            $scope.redirectAll();
          });
        }
      }
    };

    angular.extend($scope, viewModelBase);

    function initialize() {
      if (modelId) {
        Predictors.getOneModel(predictorId, modelId)
          .success(function (item) {
            $scope.item = item.data;
          })
      }
      
      // load predictor template
      Predictors.getDefaultPredictor()
        .success(function (res) {
          $scope.template = res.template;
        });

      // load predictor
      Predictors.getOne(predictorId).success(function (res) {
        $scope.predictor = res.predictor;
      });
    }


/*
    $scope.updateSplit = function(val) {
      $scope.train_data_percentage = val;
    }
*/
    initialize();
  }
  CreateEditPredictorsModelCtrl.$inject = ["$location", "$routeParams", "$scope", "PredictorsRest", "SystemAlert"];
})();
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
  NewPredictorCtrl.$inject = ["$scope", "$http", "$location", "$routeParams", "$q", "PredictorService", "AccountsService", "FilterService"];
})();

(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('PredictorModelListController', PredictorModelListController);

  /** @ngInject */
  function PredictorModelListController($location,
                                        $timeout,
                                        $routeParams,
                                        $scope,
                                        PredictorsRest,
                                        SystemAlert) {
    var Predictors = new PredictorsRest();
    $scope.selectedModels = [];
    $scope.trainedModels = [];

    $scope.selectRow = function (selected) {
      var found = _.find($scope.selectedModels, {id: selected.id});

      if (found) {
        _.remove($scope.selectedModels, selected)
      } else {
        $scope.selectedModels.push(selected)
      }
    };

    $scope.getRetrainLabel = function (selectedModel) {
      var state = selectedModel ? selectedModel.state : null;
      var status = selectedModel ? selectedModel.status : null;
      if (state == 'NEW' && status == 'INACTIVE') {
        return "Train"
      } else if (state == 'TRAINED' && status == 'INACTIVE') {
        return "Retrain"
      } else if (state == 'LOCKED' && status == 'ACTIVE') {
        return "Copy"
      } else {
        return ""
      }
    };

    $scope.onChangeModelMix = function (model) {
      if (!model) {
        return;
      }
      model.weight_error = (model.weight < 0 || model.weight > 100000);
      if (!model.weight_error) {
        Predictors.updateModel(model.predictor, model.id, {'weight': model.weight});
      }
    };

    var predictorId = $routeParams.predictorId,
        viewModelBase = {
          filters: {
            display_name: '',
            state: '',
            status: '',
            predicate: function (item) {
              var f = viewModelBase.filters,
                match = true;
              if (f.display_name.trim()) {
                match = match && (
                  item.display_name +
                  item.id +
                  item.status +
                  item.state).toLowerCase().indexOf(f.display_name.trim().toLowerCase()) > -1;
              }
              _(['status', 'state']).each(function (attr) {
                if (f[attr]) {
                  match = match && item[attr] == f[attr];
                }
              });
              return match;
            }
          },
          table: {
            sort: {
              predicate: 'display_name',
              reverse: false
            }
          },

          "create": function () {
            $location.path('/predictors/' + predictorId + '/models/edit/');
          },
          "delete": function () {
            _.each($scope.selectedModels, function (item) {
              if (item.task_data !== null & item.task_data.progress < 100) {
                SystemAlert.error('Model "' + item.display_name + '" cannot be deleted because training is not done',
                    3000);
              } else {
                Predictors.removeModel(predictorId, item.id).success(function (res) {
                    loadModels();
                    SystemAlert.info('Model "' + item.display_name + '" removed from database', 3000);
                });
              }
            });
          },
          shouldActivate: function () {
            // enable when some selected are INACTIVE
            // TODO: this is dirty way to remove tooltip accessing DOM on every false boolean...
            // bind watcher as ng-disabled with such as iteration and return boolean - is not good idea
            var isEnabled = _.some($scope.selectedModels, function (model) {
              return model.status == 'INACTIVE' && model.state !== 'NEW'
            });

            if(!isEnabled) {
              angular.element('.tooltip').remove();
            }

            return isEnabled;
          },
          shouldDeactivate: function () {
            // status: NEW or TRAINED also might exist which is possible to deactivate
            // disable when all selected are INACTIVE
            var isDisabled = !_.all($scope.selectedModels, {status: 'INACTIVE'});

            if (!isDisabled) {
              angular.element('.tooltip').remove();
            }

            return isDisabled;
          },
          activate: function () {
            _.each($scope.selectedModels, function (item) {
              Predictors.doModelAction(predictorId, item.id, 'activate').success(function () {
                loadModels();
                SystemAlert.success("Model activated.", 3000);
              });
            });
          },
          deactivate: function (item) {
            _.each($scope.selectedModels, function (item) {
              Predictors.doModelAction(predictorId, item.id, 'deactivate').success(function () {
                loadModels();
                SystemAlert.success("Model deactivated.", 3000);
              });
            });
          },
          redirectAll: function () {
            $location.path('/predictors/' + predictorId + '/models/')
          },
          "editPath": function (item) {
            return '#/predictors/' + predictorId + '/models/edit/' + item.id;
          },
          "predictorEditPath": function () {
            return '#/predictors/' + predictorId;
          },
          resetClassifier: function (item) {
            Predictors.doModelAction(predictorId, item.id, 'reset').success(function () {
              loadModels();
              SystemAlert.success("Model " + item.display_name + " has been reset.", 5000);
            });
          },
          retrainClassifier: function (item) {
            var message = "Retrain task submitted for a model.";
            var task = 'retrain';
            if ($scope.getRetrainLabel(item) == "Copy") {
              message = "Copying a model...";
              task = 'copy'
            } else {
              message = "Retraining a model...";
              task = 'retrain'
            }
            item.predictorId = predictorId;
            var model = item;
            Predictors.doModelAction(predictorId, item.id, task).success(function (resp) {
              var updatedModels = resp.data.list;

              // refresh if new models returned
              for (var modelIdx in updatedModels) {
                if (_.pluck($scope.items, 'id').indexOf(updatedModels[modelIdx].id) < 0) {
                  loadModels();
                  break;
                }
              }

              console.log("Watching updated models " + updatedModels);
              watchModels(updatedModels);
              SystemAlert.success(message + ' ' + item.display_name, 5000);
            });
          },
          upsertFeedback: function (item) {
            var message = "Upsert feedback task submitted for a model.";
            if ($scope.getRetrainLabel(item) == "Copy") {
              message = "Copying and training a model.";
            }
            item.predictorId = predictorId;
            var model = item;
            Predictors.doModelAction(predictorId, item.model_id, 'upsertFeedback').success(function (resp) {
              var updatedModels = resp.data.list;

              // refresh if new models returned
              for (var modelIdx in updatedModels) {
                if (_.pluck($scope.items, 'id').indexOf(updatedModels[modelIdx].id) < 0) {
                  loadModels();
                  break;
                }
              }

              watchModels(updatedModels);
              SystemAlert.success(message + ' ' + item.display_name, 5000);
            });
          }
      };

    function watchModels (models, interval) {
      interval = interval || 1000;
      _(models).each(function (model) {
        (function tick() {
          Predictors.getOneModel(model.predictor, model.id)
            .success(function (res) {
              console.log("Trying to refresh the status of models.");
              res = res.data;
              var progress = res.task_data && res.task_data.progress;
              var isStuck = model.task_data && res.task_data && res.task_data.updated_at === model.task_data.updated_at;
              console.log(res);
              if (progress == null || angular.isNumber(progress) && progress < 100 && !isStuck) {
                $scope.being_retrained = true;
                _.each($scope.items, function (item, i) {
                  if (item.id == model.id) {
                    $scope.items[i].task_data = res.task_data;
                  }
                });
                $timeout(tick, interval);
              } else {
                $scope.being_retrained = false;
                loadModels();
              }
            });
        })();
      });
    }

    $scope.being_retrained = false;
    $scope.$watch('items.length', function (newVal) {
      if (newVal && newVal > 0) {
        var models = _.filter($scope.items, function (item) {
          return item.task_data && item.task_data.progress < 100
        });
        watchModels(models);
      }
    });

    angular.extend($scope, viewModelBase);

    function loadModels() {
      // load all models
      $scope.selectedModels.length = 0;
      Predictors.listModels(predictorId, true).success(function(res) {
        $scope.items = res.data;
        if (!$scope.items.length) return;
        if ($scope.items[0].quality.measure === 'AUC') {
          $scope.qualityDescr = 'The area under the Precision-Recall curve indicates the relationship between the precision of the model (is it correct when it reports a true value) vs. the recall (how many true positives does it pick up).'
        } else if ($scope.items[0].quality.measure === 'RMSE') {
          $scope.qualityDescr = 'The root mean square error is a standard measure of prediction accuracy capturing the difference between the predicted value and the actual value for a dataset.'
        }
      });
    }

    function initialize() {
      loadModels();
      // load predictor
      Predictors.getOne(predictorId).success(function (res) {
        $scope.predictor = res.predictor;
      });
    }

    initialize();
  }
  PredictorModelListController.$inject = ["$location", "$timeout", "$routeParams", "$scope", "PredictorsRest", "SystemAlert"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('PredictorsViewCtrl', PredictorsViewCtrl);

  /** @ngInject */
  function PredictorsViewCtrl($scope, $routeParams, PredictorsRest) {
    var Predictors = new PredictorsRest();

    $scope.contextTable = {
      sort: {
        predicate: 'feature',
        reverse: false
      }
    };
    $scope.actionTable = {
      sort: {
        predicate: 'feature',
        reverse: false
      }
    };

    Predictors.getPredictorDetails($routeParams.id).success(function (res) {
      function capitalizeFirstLetter(string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
      }

      $scope.predictor = res;

      // Capitalize the first letter of feature description
      _.each($scope.predictor.context_features, function (feature) {
        feature.description = capitalizeFirstLetter(feature.description);
      });
      _.each($scope.predictor.action_features, function (feature) {
        feature.description = capitalizeFirstLetter(feature.description);
      });
    });
  }
  PredictorsViewCtrl.$inject = ["$scope", "$routeParams", "PredictorsRest"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('PredictorsCtrl', PredictorsCtrl);

  /** @ngInject */
  function PredictorsCtrl($scope, $location, $q, PredictorsRest, selectedPredictorsService, PredictorService, FilterService, SystemAlert) {

    var Predictors = new PredictorsRest();

    $scope.newCompositePredictor = function() {
      var ids = _.pluck($scope.selected, 'id');
      $location.path('/predictors/new').search({'ids': ids});
    };

    $scope.shouldShowCreateComposite = function () {
      var selected_types = _.pluck($scope.selected, 'predictor_type');
      return $scope.selected.length > 1 && _.indexOf(selected_types, 'Composite Predictor') === -1
    };

    $scope.selectRow = function (selected) {
      var found = _.find($scope.selected, {id: selected.id});

      if (found) {
        _.remove($scope.selected, selected);
      } else {
        $scope.selected.push(selected);
      }
      selectedPredictorsService.setSelected($scope.selected);

      $scope.aggregatedPredictors = filterAggregatedPredictors($scope.selected);
      $scope.deleteAlertMessage = generateDeleteAlert($scope.aggregatedPredictors);
    };

    var loadPredictors = function() {
      var dateRange = FilterService.getDateRange({local: true});

      var params = {
          aggregate: true
      };

      PredictorService.listAllPredictors(params).then(
        function (res) {
          $scope.predictors = res;
          $scope.noPredictors = $scope.predictors.length === 0;
        },
        function () {
          $scope.noPredictors = true;
        }
      );
    };

    $scope.deletePredictor = function () {
      var promises = _.map($scope.selected, function(predictor) {
        return Predictors.removePredictor(predictor.id).then(function() {
          SystemAlert.success(predictor.name + ' has been deleted successfully');
        });
      });

      $q.all(promises).finally(function() {
        // This function also clears the $scope.selected variable.
        activateController();
      });
    };

    $scope.resetClassifier = function (predictor_id) {
      Predictors.doClassifier('reset', predictor_id);
    };

    $scope.retrainClassifier = function (predictor_id) {
      Predictors.doClassifier('retrain', predictor_id);
    };

    $scope.upsertFeedback = function (predictor_id) {
      Predictors.upsertFeedback('upsert_feedback', predictor_id);
    };

    function activateController() {
      $scope.table = {
        sort: {
          predicate: 'name',
          reverse: false
        }
      };
      $scope.filters = {
        name: ''
      };
      $scope.selected = [];
      $scope.aggregatedPredictors = []; // Predictors used by other composite predictors
      $scope.deleteAlertMessage = '';

      loadPredictors();
    }

    function filterAggregatedPredictors(predictors) {
      return _.filter(predictors, function(predictor) {
        return isUsedByCompositePredictor(predictor.id) === true
      });
    }

    // Check if a predictor (to be deleted ) is used by a composite predictor
    // It's not supposed to delete that predictor
    function isUsedByCompositePredictor(predictorId) {
      return _.some($scope.predictors, function(predictor) {
        var aggregatePredictorIds = _.keys(predictor.aggregate_predictors);
        return (aggregatePredictorIds.indexOf(predictorId) > -1);
      });
    }

    function generateDeleteAlert(predictors) {
      var message = [
        'You can not delete the following predictors. They are used by other composite predictors.',
        '<br/>',
        '<br/>',
        '<ul>',
        '</ul>'
      ];

      var names = '';
      _.each(predictors, function(predictor) {
        names += '<li>' + predictor.name + '</li>';
      });

      message.splice(3, 0, names);

      return message.join('');
    }

    activateController();
  }
  PredictorsCtrl.$inject = ["$scope", "$location", "$q", "PredictorsRest", "selectedPredictorsService", "PredictorService", "FilterService", "SystemAlert"];
    
})();

(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('NewPredictorV2Ctrl', NewPredictorV2Ctrl)
    .directive('animateOnChange', ["$animate", "$timeout", function($animate,$timeout) {
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
  }]);

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
  NewPredictorV2Ctrl.$inject = ["$scope", "$routeParams", "$q", "$timeout", "$location", "toaster", "DatasetsRest", "PredictorsRest", "MetadataService"];
})();

(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/schema_agent_profile', {
          templateUrl: '/partials/schema-profiles/index',
          controller: 'SchemaProfileCtrl',
          name: 'schema_agent_profile',
          resolve: {
            entityType: function() { return 'agent' }
          }
        })
        .when('/schema_customer_profile', {
          templateUrl: '/partials/schema-profiles/index',
          controller: 'SchemaProfileCtrl',
          name: 'schema_customer_profile',
          resolve: {
            entityType: function() { return 'customer' }
          }
        });
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateProfileCtrl', CreateProfileCtrl);

  /** @ngInject */

  /** @ngInject */
  function CreateProfileCtrl($scope, $modalInstance, toaster, _ProfileAccess, isAppending, MetadataService) {

    angular.extend($scope, {
      progress: 0,
      form: {
        separator: null,
        selectedFile: null,
      },
      uploadingFile: false,
      isAppending: isAppending,

      onImportFile: onImportFile,
      onUploadFile: onUploadFile,
      onCloseDialog: onCloseDialog,

      separtors: MetadataService.getCSVSeparators(),
    });

    function onImportFile(files) {
      if(!files.length) return;
      $scope.form.selectedFile = files[0];
    }

    function onUploadFile() {
      $scope.uploadingFile = true;
      var params = {
        'sep': $scope.form.separator,
        'csv_file': $scope.form.selectedFile,
        'type': isAppending? 'append': 'create'
      };

      var updateProgressBar = setInterval(function increase() {
        $scope.progress += 1;
        if ($scope.progress > 100) {
          $scope.progress = 0;
        }
        $scope.$digest();
      }, 30);

      _ProfileAccess.save(params)
        .then(function(res) {
          if (isAppending) {
            toaster.pop('info', 'Appended data successfully.');
          } else {
            toaster.pop('info', 'Created profile successfully.');
          }
        })
        .catch(function(err) {
          toaster.pop('error', 'Failed to create/append profile.');
        })
        .finally(function() {
          $scope.uploadingFile = false;
          clearInterval(updateProgressBar);
          $modalInstance.close();
        });
    }

    function onCloseDialog() {
      $modalInstance.dismiss('cancel');
    }
  }
  CreateProfileCtrl.$inject = ["$scope", "$modalInstance", "toaster", "_ProfileAccess", "isAppending", "MetadataService"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('SchemaProfileDiscoveryCtrl', SchemaProfileDiscoveryCtrl);

  /** @ngInject */
  function SchemaProfileDiscoveryCtrl($scope, $modal, $timeout, toaster, SchemaProfilesRest) {
    var self = this;
    var _SchemaProfilesRest = new SchemaProfilesRest();
    _SchemaProfilesRest.setType($scope.entityType);

    self.isRefreshing = false;

    angular.extend($scope, {
      isFetching: false,

      flags: { search: '', selectedAll: false },
      table: {
        sort: { predicate: 'is_id', reverse: false }
      },
      dataTypes: ['boolean', 'integer', 'label', 'list', 'string', 'timestamp'],
      selectedRows: [],

      showDetails       : onShowDetails,
      showData          : onShowData,
      showUploadDialog  : showUploadDialog,
      onAppendData      : onAppendData,
      onSelectRow       : onSelectRow
    });

    activateController();

    function activateController() {
      $scope.$on('LOAD_PROFILE_SUCESS', loadProfileSuccess);
      $scope.$emit('REQUEST_PROFILE');
    }

    function showUploadDialog(isAppending) {
      var modalInstance = $modal.open({
        templateUrl: 'partials/schema-profiles/upload_form',
        controller: 'CreateProfileCtrl',
        size: 'md',
        resolve: {
          _ProfileAccess: function() { return $scope.ProfileAccess },
          isAppending: function() { return isAppending },
        }
      });

      modalInstance.result.finally(function() {
        $timeout(function() {
          self.isRefreshing = true;
          $scope.$emit('START_REFRESH');
        });
      });
    }

    function loadProfileSuccess(evt) {
      if (!$scope.profile) {
        return;
      }

      $scope.isFetching = false;
      $scope.selectedRows = [];

      _.each($scope.profile.discovered_schema, function(each, index) {
        var cardinality = $scope.profile.cardinalities[each.name];
        each.cardinality = cardinality? cardinality.count: 0;
        $scope.profile.discovered_schema[index] = _.extend(each, { selected: false });
      });

      var status = $scope.profile.status;
      var sync_status = $scope.profile.sync_status;

      if (!self.isRefreshing) {
        return;
      }
      // Stop refresh when it finishes first-loading or appending data
      if (status === 'LOADED' && (sync_status === 'OUT_OF_SYNC' || sync_status === 'IN_SYNC') ) {
        self.isRefreshing = false;
        console.log("STOP REFRESH!!!");
        $scope.$emit('STOP_REFRESH');
      }
    }

    function onShowDetails(field, values) {
      var dialogScope = $scope.$new();

      dialogScope.data = {
        title: "Unique values in '" + field + "' column",
        field: field,
        values: values
      };

      var modalInstance = $modal.open({
        scope: dialogScope,
        size: 'lg',
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.column-values.html'
      });
    };

    function onShowData(field) {
      var dialogScope = $scope.$new();

      dialogScope.data = {
        title: "All values in '" + field + "' column",
        field: field
      };

      var pagination = {
        offset: 0,
        limit: 20,
        currentPage: 1,
        totalItems: 0,
        pages: 0,
        maxSize: 10,
        setPage: function () {
          pagination.offset = parseInt(pagination.limit) * (pagination.currentPage - 1);
          fetchData();
        }
      };

      dialogScope.pagination = pagination;

      var fetchData = function () {
        var params = {skip: pagination.offset, limit: pagination.limit};
        _SchemaProfilesRest.fetchFieldData(field, params)
          .then(function (res) {
            dialogScope.data.values = res.data.list;
            pagination.totalItems = res.data.total_items;
            pagination.pages = Math.ceil(pagination.totalItems/pagination.limit);
          });
      };
      fetchData();

      var modalInstance = $modal.open({
        scope: dialogScope,
        size: 'lg',
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.column-values.html'
      });
    };

    function onAppendData() {
      var params = {
        'csv_file': $scope.form.selectedFile,
        'type': 'update',
      };
      $scope.ProfileAccess.save(params)
        .then(function(res) {
          toaster.pop('info', 'Appended data successfully.');
          self.isRefreshing = true;
          $scope.$emit('START_REFRESH');
        });
    }

    function onSelectRow(selected) {
      if (!selected) {
        // for all selection
        _.each($scope.profile.discovered_schema, function(each, index) {
          $scope.profile.discovered_schema[index].selected = !$scope.flags.selectedAll;
        });

        if ($scope.flags.selectedAll) {
          $scope.selectedRows = [];
        } else {
          $scope.selectedRows = _.clone($scope.profile.discovered_schema);
        }
        $scope.flags.selectedAll = !$scope.flags.selectedAll;
      } else {
        _.each($scope.profile.discovered_schema, function(each, index) {
          if (selected.name === each.name) {
            var found = _.findWhere($scope.selectedRows, {name: selected.name});
            if (found) {
              _.remove($scope.selectedRows, selected);
            } else {
              $scope.selectedRows.push(selected)
            }
            $scope.profile.discovered_schema[index].selected = !selected.selected;
          }
        });
        $scope.flags.selectedAll = ($scope.selectedRows.length === $scope.profile.discovered_schema.length);
      }
    }

  }
  SchemaProfileDiscoveryCtrl.$inject = ["$scope", "$modal", "$timeout", "toaster", "SchemaProfilesRest"];
})();

(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('SchemaProfileEditCtrl', SchemaProfileEditCtrl);

  /** @ngInject */
  function SchemaProfileEditCtrl($scope, $modal, $timeout, toaster, MetadataService) {

    var schemaKey = 'schema';
    var isRefreshing = false;

    angular.extend($scope, {
      fieldTypes: MetadataService.getSchemaFieldTypes(),
      availableFields: [],
      hasSchema: false,
      hasErorr: false,
      wrapper: {
        id_field: null,
      },

      onSaveSchema: onSaveSchema,
      onApplySchema : onApplySchema,
      onAcceptSchema: onAcceptSchema,
      onCancelSchema: onCancelSchema,
      onAddField: onAddField,
      onRemoveField: onRemoveField,
      onFieldNameInput: onFieldNameInput,
      onShowErrors: onShowErrors,

      getTextRaw: function(item) { return item },
      searchExpressions: searchExpressions,
    });

    // $scope.$on('ON_UPDATE_PROFILE', onReceiveProfile);

    activateController(); 

    function activateController() {
      $scope.$on('LOAD_PROFILE_SUCESS', loadProfileSuccess);
      $scope.$emit('REQUEST_PROFILE');
    }

    function onSaveSchema() {
      // Validate profile
      var hasMissingExpr = _.some($scope.profile[schemaKey], function (field) {
        return (field.is_expression && !field.expression);
      });

      var hasMissingType = _.some($scope.profile[schemaKey], function (field) {
        return !field.type;
      });

      if (hasMissingExpr || hasMissingType) {
        toaster.pop('error', 'Some fields have missing type or expression.');
        $scope.hasError = true;
        return;
      }

      console.log('Saving profile schema... ', $scope.profile[schemaKey]);
      $scope.hasError = false;

      $scope.ProfileAccess
        .updateSchema(_.pick($scope.profile, 'schema'))
        .then(function(res) {
          toaster.pop('info', 'Updated schema successfully.');
          $timeout(
            refreshNotify,
            500
          )
        })
    }

    function onAddField(evt) {
      evt.preventDefault();
      $scope.profile[schemaKey].push({
        name: '',
        type: '',
        expression: '',
      });

      // Automatically open the label selector which saves a click.
      $timeout(function() {
        var count = $scope.profile.schema.length;
        var elementClass = '.field-' + (count - 1) + ' a';
        angular.element(elementClass).click();
      });
    }

    function onRemoveField(evt, index) {
      evt.preventDefault();
      if ($scope.profile[schemaKey][index].name === $scope.wrapper.id_field) {
        $scope.wrapper.id_field = null;
      }
      $scope.profile[schemaKey].splice(index, 1);

      resetAvailableFields();
    }

    function onFieldNameInput(index) {
      // Pre-populate `type` and `field/expression` fields
      // if a label is selected from the predictor's schema fields
      var fields = $scope.profile[schemaKey];
      if ($scope.availableFields.indexOf(fields[index].name) >= 0) {
        fields[index].type = getFieldTypeByLabel(fields[index].name);
        delete fields[index].is_expression;
      } else {
        fields[index].is_expression = true;
      }

      resetAvailableFields();
    }

    function resetAvailableFields() {
      $scope.availableFields = _.filter($scope.originalFields, function(fieldName) {
        var usedFields = _.pluck($scope.profile[schemaKey], 'name');
        return usedFields.indexOf(fieldName) < 0;
      });
    }
    
    function getFieldTypeByLabel(fieldName) {
      /* istanbul ignore if  */
      if (!$scope.profile) {
        return;
      }
      var field = _.find($scope.profile.discovered_schema, { name: fieldName });
      return field? field.type: null;
    }

    function searchSuggestions(term, suggestionsList, searchResultsList) {
      _.each(suggestionsList, function(item) {
        if (item.toUpperCase().indexOf(term.toUpperCase()) >= 0) {
          searchResultsList.push(item);
        }
      });
      return searchResultsList;
    };

    function searchExpressions(term) {
      var list = [];
      $scope._availableFields = searchSuggestions(term, $scope.originalFields, list);
    }

    $scope.$watch('wrapper.id_field', function(item) {
      if($scope.profile) {
        _.each($scope.profile[schemaKey], function(field) {
          if (field.name === $scope.wrapper.id_field) {
            field.is_id = true;
          } else {
            delete field.is_id;
          }
        });
      }
    });

    function loadProfileSuccess(evt) {
      if (!$scope.profile) {
        return;
      }

      $scope.isFetching = false;
      $scope.originalFields = _.pluck($scope.profile.discovered_schema, 'name');
      resetAvailableFields();

      $scope.wrapper.id_field = null;
      _.each($scope.profile[schemaKey], function(field) {
        if (!!field.expression) {
          field.is_expression = true;
        }
        if (field.is_id) {
          $scope.wrapper.id_field = field.name;
        }
      });

      $scope.rowsLost = 0;
      if ($scope.profile.items_synced !== null) {
        $scope.rowsLost = $scope.profile.rows - $scope.profile.items_synced;
      }

      /*
      if (!isRefreshing) {
        return;
      }
      */
      // Stop refresh when it finishes applying schema
      // Stop refresh when it finishes appending data

      /*
      if ($scope.profile.sync_status === 'SYNCED' || 
         ($scope.profile.sync_status === 'IN_SYNC') ||
         ($scope.profile.sync_status === 'OUT_OF_SYNC')
      ) {
      */
      if (_.indexOf(['SYNCING','IMPORTING'], $scope.profile.sync_status) == -1)
      {
        console.log("STOP REFRESH", $scope.profile.sync_status);
        isRefreshing = false;
        $scope.$emit('STOP_REFRESH');
      } else {
        console.log("KEEP SYNCING", $scope.profile.sync_status);
      }

      $scope.hasSchema = ($scope.profile.schema && $scope.profile.schema.length > 0);
    }

    function onApplySchema() {
      $scope.ProfileAccess.applySchema();
      $scope.profile.sync_status = 'SYNCING';
      toaster.pop('info', 'Synchronization started.');
      isRefreshing = true;
      console.log("wait before refreshing...");
      $timeout(
        refreshNotify,
        500
      );
    }

    function refreshNotify() {
      //console.log("NOTIFY REFRESH");
      $scope.$emit('START_REFRESH')
    }

    function onAcceptSchema() {
      $scope.ProfileAccess.acceptSchema()
        .then(function() {
          toaster.pop('info', 'Accepted schema successfully.');
          $scope.$emit('LOAD_PROFILE');
        });
    }

    function onCancelSchema() {
      $scope.ProfileAccess.cancelSchema()
        .then(function() {
          toaster.pop('info', 'Cancelled schema successfully.');
          $scope.$emit('LOAD_PROFILE');
        });
    }

    function onShowErrors() {
      var dialogScope = $scope.$new();

      dialogScope.data = {
        errors: $scope.profile.sync_errors,
        options: {
          name: "Fields resulted in errors",
          mode: "tree",
        }
      };

      dialogScope.title = $scope.entityType + " profile schema";

      var modalInstance = $modal.open({
        scope: dialogScope,
        backdrop: false,
        keyboard: true,
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.sync-errors.html'
      });
    }
  }
  SchemaProfileEditCtrl.$inject = ["$scope", "$modal", "$timeout", "toaster", "MetadataService"];
})();

(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('SchemaProfileCtrl', SchemaProfileCtrl);

  /** @ngInject */
  function SchemaProfileCtrl($scope, $interval, $http, entityType, SchemaProfilesRest, MetadataService) {

    var self = this;

    self.pageRefresher = undefined;

    angular.extend($scope, {
      entityType: entityType,
      pageTitle: (entityType === 'agent')? 'Agent Profile': 'Customer Profile',
      profileTabs: [
        { name: 'Discovered Fields',  active: false,  templateUrl: 'partials/schema-profiles/schema_discovery' },
        { name: 'Schema',             active: false,  templateUrl: 'partials/schema-profiles/schema_edit' }
      ],

      profile: null, // global scope variable
      ProfileAccess: new SchemaProfilesRest(),

      onSelectTab: onSelectTab,
      deleteProfile : deleteProfile

    });

    $scope.$on('REQUEST_PROFILE', onRequestProfile);
    $scope.$on('LOAD_PROFILE', onLoadProfile);
    $scope.$on('START_REFRESH', onStartRefresh);
    $scope.$on('STOP_REFRESH', onStopRefresh);

    activateController();

    function activateController() {
      $scope.ProfileAccess.setType(entityType);
      onLoadProfile();

      onSelectTab($scope.profileTabs[0]);
    }

    function onLoadProfile() {
      $scope.isFetching = true;
      $scope.ProfileAccess.getOne()
        .then(loadProfileSuccess)
        .catch(function(err) {
          $scope.isFetching = false;
        });
    }

    function onRequestProfile() {
      $scope.$broadcast('LOAD_PROFILE_SUCESS');
    }

    function loadProfileSuccess(res) {
      $scope.profile = res.data;
      $scope.profile.discovered_schema.forEach(function (field) {
        field.cardinality = $scope.profile.cardinalities[field.name].count;
      });

      $scope.schemaFields = _.map($scope.profile.schema, function (field) {
        return field.name;
      });

      if ($scope.profile) {
        $scope.profile.status_display = MetadataService.getBeautifiedStatus($scope.profile);
      }
      $scope.$broadcast('LOAD_PROFILE_SUCESS');
    }

    function onStartRefresh() {
      if ( angular.isDefined(self.pageRefresher) ) {
        return;
      }
      onLoadProfile();
      self.pageRefresher = $interval(onLoadProfile, 2000);
    }

    function onStopRefresh() {
      if ( angular.isDefined(self.pageRefresher) ) {
        $interval.cancel(self.pageRefresher);
        self.pageRefresher = undefined;
      }
    }

    function onSelectTab(tab) {
      if ($scope.currentTab) {
        $scope.currentTab.active = false;
      }
      $scope.currentTab = tab;
      $scope.currentTab.active = true;
    }

    function deleteProfile() {
      var profile = $scope.entityType == 'agent'  ? '/agent_profile/' : '/customer_profile/';
      $http.post(profile + "delete", {}).then(function(res) {
        onLoadProfile();
        onSelectTab($scope.profileTabs[0]);
      })
    }

  }
  SchemaProfileCtrl.$inject = ["$scope", "$interval", "$http", "entityType", "SchemaProfilesRest", "MetadataService"];
})();

(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/tags/all', {
          templateUrl: '/partials/tags/tags',
          controller: 'AllTagsCtrl',
          name: 'tags'
        })
        .when('/tags/edit', {
          templateUrl: '/partials/tags/edit',
          controller: 'CreateEditTagCtrl',
          name: 'tags'
        })
        .when('/tags/edit/:tag_id', {
          templateUrl: '/partials/tags/edit',
          controller: 'CreateEditTagCtrl',
          name: 'tags'
        })
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('SharedState', SharedState);

  /** @ngInject */
  function SharedState() {
    return {filters: {}};
  }
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('AllTagsCtrl', AllTagsCtrl);

  /** @ngInject */
  function AllTagsCtrl($scope, $location, FilterService, SmartTags, SmartTag, ChannelsService, DialogService, SharedState) {
    var getSelectedItems = function (list) {
      return _.filter(list, function (item) {
        return item['is_selected'];
      });
    };
    var findItems = function (list, item) {
      var items = [];
      if (item) {
        items = [item];
      } else {
        items = getSelectedItems(list);
      }
      return items;
    };

    $scope.selected = [];
    $scope.selectRow = function (selected) {
      var found = _.find($scope.selected, {id: selected.id});

      if (found) {
        _.remove($scope.selected, selected)
      } else {
        $scope.selected.push(selected)
      }
    };

    var findItemIds = function (label) {
      var items = findItems($scope.tags, label);
      return _.pluck(_.filter(items, function (el) {
        return el.perm == 's' || el.perm == 'rw'
      }), 'id');
    };
    $scope.tags = [];
    //$scope.filters = AppState.store("configure_smart_tags_filters") || {
    $scope.filters = angular.extend(SharedState.filters, {
      channel: null,
      status: '',
      title: '',
      limit: 30,
      offset: 0
    });
    $scope.table = {
      sort: {
        predicate: 'name',
        reverse: false
      }
    };
    $scope.filterPredicate = function (tag) {
      var result = true;
      if ($scope.filters.title) {
        var title = tag.title || '';
        var description = tag.description || '';
        result = result && (title.toLowerCase().indexOf($scope.filters.title.toLowerCase()) != -1 ||
          description.toLowerCase().indexOf($scope.filters.title.toLowerCase()) != -1);
      }
      if ($scope.filters.status) {
        result = result && tag.status == $scope.filters.status;
      }
      return result;
    };
    $scope.edit = function (tag) {
      $location.path('/tags/edit/' + (tag ? tag.id : ''));
    };

    $scope.createSmartTag = function () {
      $scope.edit();
      $scope.mode = 'create';
    };

    $scope.delete = function () {
      _.each($scope.selected, function (tag) {
        var ids = findItemIds(tag);
        SmartTag.delete({ids: ids}, $scope.refresh);
      });
    };

    $scope.activate = function () {
      _.each($scope.selected, function (tag) {
        var ids = findItemIds(tag);
        if (!ids.length) return;

        SmartTag.activate({'ids': ids}, function () {
          $scope.refresh();
        });
      });
    };

    $scope.deactivate = function () {
      _.each($scope.selected, function (tag) {
        var ids = findItemIds(tag);
        if (!ids.length) return;

        SmartTag.deactivate({'ids': ids}, function () {
          $scope.refresh();
        });
      });
    };

    $scope.share = function (item) {
      var ids = findItemIds(item);
      if (!ids.length) return;

      DialogService.openDialog({target: 'acl', objectType: 'SmartTag', objectIds: ids});
    };


    $scope.refresh = function () {
      $scope.filters.offset = 0;
      $scope.loadSmartTags();
    };

    ChannelsService.load('inbound', false, true);
    $scope.$on(ChannelsService.ON_CHANNELS_LOADED, function (scope, bookmark) {
      $scope.channels = ChannelsService.getList();
      if ($scope.channels.length != 0) {
        $scope.filters.channel = ChannelsService.getSelected() ? ChannelsService.getSelectedId() : $scope.channels[0];
        $scope.refresh();
      }
    });


    $scope.loadSmartTags = function (dates) {
      if ($scope.filters.channel != null) {
        $scope.dateRange = dates || FilterService.getDateRange();
        var params = {
          offset: $scope.filters.offset,
          limit: $scope.filters.limit,
          channel: $scope.filters.channel,
          from: $scope.dateRange.from,
          to: $scope.dateRange.to
        };
        SmartTags.listAll(params).then(function (res) {
          $scope.tags = res.list;
          $scope.filters.offset = res.offset;
          $scope.filters.limit = res.limit;
          $scope.size = res.size;
          var pages = res.size / res.limit;
          $scope.pages = Math.ceil(pages);
        });
      }
    };

    $scope.filters.currentPage = 0;
    $scope.pages = 0;
    //Make the first filters.status to be Active
    //$scope.filters.status = "Active";

    // like python's range fn
    $scope.range = function (start, end) {
      var ret = [];
      if (!end) {
        end = start;
        start = 0;
      }
      for (var i = start; i < end; i++) {
        ret.push(i);
      }
      return ret;
    };

    $scope.prevPage = function () {
      if ($scope.filters.currentPage > 0) {
        $scope.filters.currentPage--;
        $scope.filters.offset = parseInt($scope.filters.offset) - parseInt($scope.filters.limit);
      }
    };

    $scope.nextPage = function () {
      if ($scope.filters.currentPage < $scope.pages - 1) {
        $scope.filters.currentPage++;
        $scope.filters.offset = parseInt($scope.filters.offset) + parseInt($scope.filters.limit);
      }
    };

    $scope.setPage = function () {
      $scope.filters.currentPage = this.n;
      $scope.filters.offset = (parseInt($scope.filters.limit) * this.n);
    };

    $scope.$watch('filters.currentPage', function (nVal) {
      $scope.loadSmartTags();
    });

    $scope.$watch('filters', function (newVal, oldVal) {
      if (newVal != oldVal)
        $scope.$emit('configure_messages_filters_changed');
    }, true);


  }
  AllTagsCtrl.$inject = ["$scope", "$location", "FilterService", "SmartTags", "SmartTag", "ChannelsService", "DialogService", "SharedState"];
})();
(function() {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateEditTagCtrl', CreateEditTagCtrl);

  /** @ngInject */
  function CreateEditTagCtrl($scope, $location, $routeParams, $http, $q,
                                             SmartTag, SmartTags, SmartTagForm, GroupsRest, SharedState) {
    var Groups = new GroupsRest();
    $scope._is_modal = false;
    $scope.groupUsers = [];
    $scope.allGroupsUsers = [];
    $scope.usersEmails = [];
    $scope.alertCandidateEmails = [];
    $scope.selected_users = [];

    $http.get('/alert_user_candidates', {}).
      success(function (data) {
        $scope.alertCandidateEmails = data.list;
      });

    //A flag to know when we've just restored an existing smart tag and we don't need to query for group users, since we already have them
    //This should be needed only on the first time the tag is restored, it is meant to avoid the tagItem.groups watcher to empty the users form field
    $scope.smart_tag_restored = false;

    $scope.selectOptions = {
      intentions: SmartTagForm.getIntentions(),
      postCreationStatuses: SmartTagForm.getPostStatuses()
    };

    SmartTagForm.getChannels().then(function (data) {
      $scope.selectOptions.channels = data;
    });
    SmartTagForm.getContactLabels().then(function (data) {
      $scope.selectOptions.labels = data;
    });

    $scope.tagItem_id = $routeParams.tag_id;

    //Add a watcher for the fullGroups, need to search for the groups users every time there is a change
    $scope.chosenSTGroups = [];
    $scope.$watch('chosenSTGroups', function (nVal, oVal) {
      if (!_.isEqual(nVal, oVal)) {
        //Removed all groups?
        if (nVal.length == 0) {
          //Delete all users too
          $scope.tagItem.users = [];
          $scope.groupUsers = [];
          $scope.allGroupsUsers = [];
          $scope.usersEmails = [];
          $scope.selected_users = [];
        }
        else {
          $scope.groupUsers = [];
          if (!$scope.smart_tag_restored) {
            $scope.usersEmails = [];
          }
          for (var i = 0; i < $scope.chosenSTGroups.length; i++) {
            var group_id;
            if ($scope.mode == 'create') {
              group_id = $scope.chosenSTGroups[i];
            }
            else {
              if (typeof $scope.chosenSTGroups[i].id === "undefined") {
                group_id = $scope.chosenSTGroups[i];
              }
              else {
                group_id = $scope.chosenSTGroups[i].id;
              }
            }
            //Query the users for each group in the group list
            Groups.action('get_users', {id: group_id}).success(function (res) {
              //Check if the user does not exist already in users array
              for (var j = 0; j < res.users.length; j++) {
                var userEmail = res.users[j].email;
                var userID = res.users[j].id;
                var user = res.users[j];
                var userFound = false;
                if ($scope.allGroupsUsers.length == 0)
                  $scope.allGroupsUsers.push(user);
                //Check if the user has been inserted in the whole group users array, to avoid duplicates
                for (var i = 0; i < $scope.allGroupsUsers.length; i++) {
                  if ($scope.allGroupsUsers[i].id == userID) {
                    userFound = true;
                    break;
                  }
                }
                if (!userFound) {
                  $scope.allGroupsUsers.push(user);
                }
                //Check if the current user email is in the drop down list userEmeials
                var foundElement = _.find($scope.usersEmails, function (val) {
                  return _.isEqual(userEmail, val);
                });
                //If undefined, could not find a matching element
                if (typeof foundElement === "undefined") {
                  $scope.groupUsers.push(user);
                  if (!$scope.smart_tag_restored) {
                    $scope.usersEmails.push(userEmail);
                  }
                }
              }
            });
          }
        }
      }
      else {
        //Check if we are restoring an existing smart tag
        if ($scope.smart_tag_restored) {
          $scope.smart_tag_restored = false;
          //Check what users are in the selected groups list and the drop down list
          for (var i = 0; i < $scope.groupUsers.length; i++) {
            var userEmail = $scope.groupUsers[i].email;
            var foundElement = _.find($scope.usersEmails, function (val) {
              return _.isEqual(userEmail, val);
            });
            //If undefined, could not find a matching element
            if (typeof foundElement === "undefined") {
              $scope.usersEmails.push(userEmail);
            }
          }
          //Need to update the selected user too here
        }
      }
    });

    function getFullGroups() {
      var deferred = $q.defer();

      Groups.list().success(function (res) {
        $scope.fullGroups = _.map(res.data, function (item) {
          item.is_selected = false;
          return item;
        });
        deferred.resolve($scope.fullGroups);
      });

      return deferred.promise;
    }

    $scope.directions = [{ type: "inbound" }, { type: "outbound" }, { type: "any" }];

    //Add a watcher for the users, need to remove the user ID whenever a user is added/removed
    $scope.$watch('tagItem_id', function (nVal, oVal) {
      if (nVal) {
        $scope.mode = 'edit';
        SmartTags.getById($scope.tagItem_id).then(function (res) {
          //Don't need the groups with number:permissions
          var aux = res;
          var auxGroups = [];
          for (var i = 0; i < aux.groups.length; i++) {
            var currentGroupID = aux.groups[i];
            //If found
            if (currentGroupID.indexOf(":") == -1) {
              auxGroups.push(currentGroupID);
            }
          }
          aux.groups = auxGroups;
          $scope.tagItem = aux;

          /** INTENTIONS */
          var intentions = [];
          _.each($scope.tagItem.intentions, function (intentionLabel) {
            intentions.push(_.findWhere($scope.selectOptions.intentions, {label: intentionLabel}));
          });
          $scope.chosenSTIntenions = _.uniq(intentions);
          $scope.changingSTIntentionLabels = _.pluck($scope.chosenSTIntenions, 'label');

          /** GROUPS */
          getFullGroups().then(function (fullGroups) {
            var groups = [];
            _.each($scope.tagItem.groups, function (groupId) {
              groups.push(_.findWhere(fullGroups, {id: groupId}));
            });
            $scope.chosenSTGroups = _.uniq(groups);
            $scope.changingSTGroupsIds = _.pluck($scope.chosenSTGroups, 'id');
          });

          //Need to restore the userIDs for the restored emails too
          $scope.selected_users_IDs = $scope.tagItem.alert.users;
          $scope.usersEmails = $scope.tagItem.alert.emails;
          $scope.smart_tag_restored = true;
          $scope.tagItemDefaults = SmartTagForm.getSmartTagDefaults();
        });
      } else {
        $scope.mode = 'create';
        $scope.tagItem = new SmartTag();
        $scope.tagItem.title = '';
        $scope.tagItem.direction = 'any';
        $scope.tagItem.description = '';
        $scope.tagItem = angular.extend($scope.tagItem, SmartTagForm.getSmartTagDefaults(), {channel: SharedState.filters.channel});
        $scope.chosenSTIntenions = [];
        $scope.changingSTIntentionLabels = [];
        $scope.changingSTGroupsIds = [];
        getFullGroups().then(function (fullGroups) {
          $scope.chosenSTGroups = fullGroups;
          $scope.changingSTGroupsIds = _.pluck($scope.chosenSTGroups, 'id');
        });
      }
      $scope.title = SmartTagForm.getFormTitle($scope.mode);
    });

    $scope.addSTIntenion = function (intention) {
      $scope.changingSTIntentionLabels.push(intention.label);
    };
    $scope.removeSTIntenion = function (intention) {
      $scope.changingSTIntentionLabels.splice($scope.changingSTIntentionLabels.indexOf(intention.label), 1);
    };
    $scope.addSTGroup = function (group) {
      $scope.changingSTGroupsIds.push(group.id);
    };
    $scope.removeSTGroup = function (group) {
      $scope.changingSTGroupsIds.splice($scope.changingSTGroupsIds.indexOf(group.id), 1);
    };

    $scope.newTag = function () {
      $location.path('/tags/edit/');
    };

    $scope.formState = {
      isSaved: false,
      isError: false
    };

    $scope.save = function () {
      $scope.formState.isSaved = false;
      //Get the array of userIDs from the selected users Array
      var usersIDs = [];
      for (var i = 0; i < $scope.selected_users.length; i++) {
        usersIDs.push($scope.selected_users[i].id);
      }
      $scope.tagItem.alert.users = usersIDs;
      //Don't need the groups with number:permissions
      var groups = _.uniq($scope.changingSTGroupsIds);
      var auxGroups = [];
      for (var i = 0; i < groups.length; i++) {
        var currentGroupID = groups[i];
        //If found
        if (currentGroupID.indexOf(":") == -1) {
          auxGroups.push(currentGroupID);
        }
      }
      $scope.tagItem.groups = auxGroups;
      $scope.tagItem.intentions = _.uniq($scope.changingSTIntentionLabels);
      SmartTag.update($scope.tagItem, function (res) {
        //Need to set this to edit, since after creating a tag we move to "edit" mode
        $scope.mode = 'edit';
        $scope.formState.isSaved = true;
      });
    };


    $scope.isAdvancedState = false;

    $scope.evaluate = function () {
      return $scope.isAdvancedState;
    };
    $scope.evaluateIcon = function () {
      if ($scope.isAdvancedState) {
        return "icon-chevron-down";
      }
      else {
        return "icon-chevron-right";
      }
    };

    $scope.evaluate = function () {
      return $scope.isAdvancedState;
    };
    $scope.evaluateIcon = function () {
      if ($scope.isAdvancedState) {
        return "icon-expand-down";
      }
      else {
        return "icon-expand-right";
      }
    };
    $scope.changeStatus = function () {
      $scope.isAdvancedState = !$scope.isAdvancedState;
    }
  }
  CreateEditTagCtrl.$inject = ["$scope", "$location", "$routeParams", "$http", "$q", "SmartTag", "SmartTags", "SmartTagForm", "GroupsRest", "SharedState"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/trials/', {
          templateUrl: '/partials/trials/list',
          controller: 'TrialsListCtrl',
          name: 'trials'
        })
        .when('/trials/edit/:id?/', {
          templateUrl: '/partials/trials/edit',
          controller: 'CreateUpdateTrialCtrl',
          name: 'trials.edit'
        })
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('Trial', Trial);

  /** @ngInject */
  function Trial($resource) {
    return {
      create: function (params) {
        var defaults = {
          account_name: "",
          first_name: "",
          last_name: "",
          // full_name: "",
          email: "",
          start_date: new Date().format('mm/dd/yyyy'),
          end_date: ""
        };
        var res = new this.resource(params || defaults);
        return res;
      },

      resource: $resource('/trials/:id/json', {id: '@id'})
    };
  }
  Trial.$inject = ["$resource"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateUpdateTrialCtrl', CreateUpdateTrialCtrl);

  /** @ngInject */
  function CreateUpdateTrialCtrl($location, $log, $scope, SystemAlert, Trial) {
    var clear = function () {
      $scope.item = Trial.create();
    };
    clear();

    $scope.pattern = {
      EMAIL_REGEXP: /^[a-z0-9!#$%&'*+/=?^_`{|}~.-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$/i,
      ACCOUNT_REGEXP: /^[a-zA-Z0-9-_()]+$/  // sync with db.account.ACCOUNT_NAME_RE
    };

    $scope.options = {
      start_date: {dateFormat: 'mm/dd/yy', minDate: new Date()},
      end_date: {dateFormat: 'mm/dd/yy', minDate: new Date(+new Date() + 24 * 60 * 60 * 1000)}
    };

    $scope["get"] = function (id) {
      return Trial.resource.get({id: id}).$promise.then(function (item) {
        $scope.item = Trial.create(item);
        return item;
      });
    };

    $scope.save = function () {
      Trial.resource.save($scope.item, function () {
        SystemAlert.success("Trial invitation was sent successfully!", 5000);
        clear();
        $scope.trialForm.$setPristine();
        $scope.redirectAll();
      });
    };


    $scope.redirectAll = function () {
      $location.path('/trials/');
    };
  }
  CreateUpdateTrialCtrl.$inject = ["$location", "$log", "$scope", "SystemAlert", "Trial"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('TrialsListCtrl', TrialsListCtrl);

  /** @ngInject */
  function TrialsListCtrl($scope, $location, SystemAlert, Trial) {
    $scope.filters = {
      status: ''
    };

    $scope.table = {
      sort: {
        predicate: 'start_date',
        reverse: true
      }
    };

    $scope.filterPredicate = function (item) {
      var result = true;
      if ($scope.filters.status) {
        result = result && item.status.toLowerCase() == $scope.filters.status.toLowerCase();
      }
      return result;
    };

    $scope.volClass = function (vol) {
      var colorClass = {
        'green': 'text-success',
        'orange': 'text-warning',
        'red': 'text-important'
      };
      if (vol >= 20000 && vol < 25000) {
        return colorClass.orange;
      }
      if (vol >= 25000) {
        return colorClass.red;
      }
      return colorClass.green;
    };

    $scope.create = function () {
      $location.path('/trials/edit/');
    };

    $scope.openAccountView = function (item) {
      $location.path('/accounts/' + item.account_id);
    };

    $scope.refresh = function () {
      Trial.resource.get({}, function (res) {
        $scope.items = res.items;
      }, function onError() {
        SystemAlert.error("Failed to fetch trials");
      });
    };

    $scope.refresh();
  }
  TrialsListCtrl.$inject = ["$scope", "$location", "SystemAlert", "Trial"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
    $routeProvider
      .when('/user/:email', {
        templateUrl: '/partials/configure/user',
        controller: 'UserEditCtrl',
        name: 'user'
      })
      .when('/users/:acct_id', {
        templateUrl: '/partials/configure/list_users',
        controller: 'UsersListCtrl',
        name: 'account_users'
      })
      .when('/users/edit/:acct_id/', {
        templateUrl: '/partials/users/edit',
        controller: 'CreateUpdateUserCtrl',
        name: 'account_users'
      })
      .when('/users/edit/:acct_id/:user_email', {
        templateUrl: '/partials/users/edit',
        controller: 'CreateUpdateUserCtrl',
        name: 'account_users'
      })
      .when('/users/add/:acct_id/', {
        templateUrl: '/partials/users/add',
        controller: 'AddUserCtrl',
        name: 'account_users'
      })
  }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('UserEditService', UserEditService);

  /** @ngInject */
  function UserEditService($resource) {
    return $resource('/users/edit/json', {}, {
      query: {method: 'GET', isArray: false},
      update: {method: 'PUT'}
    });
  }
  UserEditService.$inject = ["$resource"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('UserService', UserService);

  /** @ngInject */
  function UserService($http) {
    var sharedService = {};

    sharedService.setPassword = function (email, password, callback) {
      return $http.post('/users/' + email + '/password',
        $.param({password: password}),
        {headers: {'Content-Type': 'application/x-www-form-urlencoded'}}).success(callback);
    };
    sharedService.listAvailableUsers = function (callback) {
      return $http.get('/users/json',
        {headers: {'Content-Type': 'application/x-www-form-urlencoded'}}).success(callback);
    };
    sharedService.getUserByEmail = function (email, callback) {
      return $http.get('/users/edit/json?email=' + email,
        {headers: {'Content-Type': 'application/x-www-form-urlencoded'}}).success(callback);
    };
    sharedService.setCurrentAccount = function () {
    };

    return sharedService;
  }
  UserService.$inject = ["$http"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('AddUserCtrl', AddUserCtrl);

  /** @ngInject */
  function AddUserCtrl($scope, $location, $routeParams, $http, SystemAlert) {
    $scope.accountId = $routeParams.acct_id;

    $scope.title = 'Add existing user';

    $scope.save = function () {
      $http({
        method: 'POST',
        url: '/users/add_to_account/json',
        data: {user: $scope.user}
      }).success(function () {
        $location.path('/users/' + $scope.accountId);
        SystemAlert.success("User was added to account!", 4000);
      }).error(function onError(res) {
        SystemAlert.error(res.message);
      });
    };

    $scope.list = function () {
      $location.path('/users/' + $scope.accountId);
    };

  }
  AddUserCtrl.$inject = ["$scope", "$location", "$routeParams", "$http", "SystemAlert"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateUpdateUserCtrl', CreateUpdateUserCtrl);

  /** @ngInject */
  function CreateUpdateUserCtrl($scope, $location, $modal, $routeParams, UserRolesRest, GroupsService, UserEditService, $http, SystemAlert) {
    $scope.accountId = $routeParams.acct_id;
    $scope.userEmail = $routeParams.user_email;
    $scope.EMAIL_REGEXP = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}$/; //Same regex that angular uses
    $scope.changingRolesIds = [];
    var changingGroupsIds = [];
    var initial_role_ids = [];
    var initial_group_ids = [];
    
    var UserRoles = new UserRolesRest();

    var toResource = function (user) {
      var u = new UserEditService();
      for (var i in user) {
        u[i] = user[i];
      }
      return u;
    };

    $scope.initData = function (is_edit) {
      // Load possible user roles and populate field with all of them as default
      UserRoles.list().success(function (data) {
        $scope.fullRoles = data.list;

        if (is_edit) { // edited user
          var arr = [];
          _.each($scope.user.roles, function (roleId) {
            var found = _.findWhere(data.list, {id: roleId});
            if (found) {
              arr.push(found);
            } else {
              initial_role_ids.push(roleId);
            }
          });
          $scope.chosenRoles = _.uniq(arr);
        } else {
          $scope.chosenRoles = data.list;
        }
        $scope.changingRolesIds = initArray($scope.chosenRoles);
      });
      GroupsService.query({}, function (res) {
        $scope.fullGroups = _.map(res.data, function (item) {
          item.is_selected = false;
          return item;
        });

        if (is_edit) { // edited group
          var arr = [];
          _.each($scope.user.groups, function (groupId) {
            var found = _.findWhere($scope.fullGroups, {id: groupId});
            if (found) {
              arr.push(found);
            } else {
              initial_group_ids.push(found);
            }
          });
          $scope.chosenGroup = _.uniq(arr);
        } else {
          $scope.chosenGroup = $scope.fullGroups;
        }
        changingGroupsIds = initArray($scope.chosenGroup);
      });
      $scope.user.email = $scope.userEmail;
    };

    function initArray(array) {
      return array.length ? _.pluck(array, 'id') : [];
    }

    $scope.addRole = function (item) {
      $scope.changingRolesIds.push(item.id);
    };
    $scope.removeRole = function (item) {
      $scope.changingRolesIds.splice($scope.changingRolesIds.indexOf(item.id), 1);
    };
    $scope.addGroup = function (item) {
      changingGroupsIds.push(item.id);
    };
    $scope.removeGroup = function (item) {
      changingGroupsIds.splice(changingGroupsIds.indexOf(item.id), 1);
    };

    if ($scope.userEmail) {
      $scope.mode = 'edit';
      UserEditService.get({email: $scope.userEmail}, function (res) {
        $scope.user = toResource(res.user);
        $scope.initData(true);
      });
    } else {
      $scope.mode = 'create';
      $scope.user = new UserEditService();
      $scope.initData(false);
    }

    $scope.title = {
      'create': 'Create',
      'edit': 'Update'
    }[$scope.mode];

    $scope.isCreationMode = function () {
      return ($scope.mode == 'create');
    };

    $scope.save = function () {
      // Backup in case of error
      if (initial_group_ids.length) {
        changingGroupsIds = changingGroupsIds.concat(initial_group_ids);
      }
      if (initial_role_ids.length) {
        $scope.changingRolesIds = $scope.changingRolesIds.concat(initial_role_ids);
      }
      $scope.user.roles = _.uniq($scope.changingRolesIds);
      $scope.user.groups = _.uniq(changingGroupsIds);
      var usr = toResource($scope.user);
      var onSuccess = function () {
        $location.path('/users/' + $scope.accountId);
        SystemAlert.success("Congratulations, user was created successfully!", 4000);
      };

      if ($scope.mode == 'create') {
        $http({
          method: 'POST',
          url: '/users/check_user_archived/json',
          data: {user: $scope.user}
        }).success(onSuccess).error(function () {
          // if not archived
          $scope.user.$save(onSuccess).finally(function () {
            $scope.user = usr;
          });
        })
      } else {
        $scope.user.$save(function () {
          $location.path('/users/' + $scope.accountId)
        }).finally(function () {
          $scope.user = usr;
        });
      }
    };


    $scope.saveButtonDisabled = function () {
      if (!$scope.user) return false;
      if (!$scope.user.first_name || !$scope.user.last_name) {
        // Firstname + Lastname should be required
        return true;
      }
      if (!$scope.user.email || !$scope.EMAIL_REGEXP.test($scope.user.email)) {
        // Test that email is present and that it's valid
        return true;
      }
      if ($scope.changingRolesIds.length === 0) {
        // Test that user roles are set for this user
        return true;
      }
      return false;
    };

    $scope.deleteButtonDisabled = function () {
      if ($scope.mode == 'edit') {
        return true;
      }
      else {
        return false;
      }
    };

    $scope.deleteUser = function () {
      var postData = {id: $scope.user.id};
      $http({
        method: 'POST',
        url: '/users/delete/json',
        data: postData
      }).success(function () {
        $location.path('/users/' + $scope.accountId)
      })
    };

    $scope.list = function () {
      $location.path('/users/' + $scope.accountId);
    };

    $scope.add = function () {
      $location.path('/users/add/' + $scope.accountId);
    };

    $scope.openDialog = function (rootScope, http) {
      var d = $modal.open({
        backdrop: true,
        keyboard: true,
        backdropClick: true,
        templateUrl: '/partials/users/confirmDialog',
        controller: ["$scope", function ($scope) {
          $scope.user = rootScope.user;
          $scope.accountId = rootScope.accountId;
          $scope.modal_title = 'Warning'
          //$rootScope.$broadcast(SmartTags.ON_POST_TAGS_REMOVED, response_id, post_id, tag_removed, true);
          $scope.close = function (result) {
            $http({
              method: 'POST',
              url: '/users/reactivate_user/json',
              data: {user: $scope.user}
            }).success(function () {
              $location.path('/users/' + $scope.accountId);
            }).finally(function () {
              $scope.$close(result);
            });
          };
          $scope.dismiss = function (reason) {
            rootScope.user.email = '';
            $scope.$dismiss(reason);
          }

        }]
      });
    };

  }
  CreateUpdateUserCtrl.$inject = ["$scope", "$location", "$modal", "$routeParams", "UserRolesRest", "GroupsService", "UserEditService", "$http", "SystemAlert"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('UserEditCtrl', UserEditCtrl);

  /** @ngInject */
  function UserEditCtrl($scope, $resource, $route, DialogService, toaster) {
    var User = $resource('/user/json');

    var init = function () {
      $scope.user = null;
      $scope.flags = {
        isChanged: false
      };
    };

    $scope.close = function () {
      DialogService.closeDialog({target: 'user_edit'});
      $scope.userEditModalShown = false;
    };

    $scope.load = function (email) {
      User.get({email: email}, function (res) {
        $scope.user = res.user;
        $scope.userEditModalShown = true;
      });
    };

    $scope.save = function () {
      User.save($scope.user, function () {
          $scope.close();
          toaster.pop('success', 'User details have been changed');
          $scope.flags.isChanged = false;
        },
        function onError(res) {
          $scope.errorMessage = res.error;
        });
    };

    $scope.$on(DialogService.OPEN_DIALOG_EVENT, function (event, data) {
      //console.log(event, data);
      if (data.target == 'user_edit') {
        $scope.errorMessage = '';
        $scope.load(data.email);
      }
    });

    $scope.$watch('user', function (nVal) {
       if (nVal) {
         $scope.flags.isChanged = true;
       }
    }, true);

    if ($route.current.params.email) {
      $scope.load($route.current.params.email);
    }

    init();
  }
  UserEditCtrl.$inject = ["$scope", "$resource", "$route", "DialogService", "toaster"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('UsersListCtrl', UsersListCtrl);

  /** @ngInject */
  function UsersListCtrl($scope, $location, $http, $resource, $routeParams, $timeout, $window,
                         AccountsService, ACLService, ConfigureAccount, DialogService, SystemAlert, UserRolesRest) {

    var _UserRoles = new UserRolesRest();

    $scope.pagination = {
      offset: 0,
      limit: 20,
      currentPage: 1,
      totalItems: 0,
      pages: 0,
      maxSize: 10,
      setPage: setPage
    };

    $scope.filters = {
      searchQuery: ''
    };

    var debouncedFetchUsers = _.debounce(function () {
      $scope.fetchUsers();
    }, 500);

    $scope.$watch('filters.searchQuery', function (n, o) {
      if (!n && !o) {
        return;
      }
      debouncedFetchUsers();
    });

    function setPage() {
      $scope.pagination.offset = parseInt($scope.pagination.limit) * ($scope.pagination.currentPage - 1);
      $scope.fetchUsers();
    }

    $scope.users = [];
    $scope.selectedAccount = '';
    $scope.accountsList = []; // All accounts available to this user.
    $scope.editableAccountsList = []; // The accounts that this user has edit rights to.

    $scope.editPermsList = [{id: 'r', name: 'Can view'}, {id: 'rw', name: 'Can edit'}, {id: 'd', name: 'Delete'}];
    $scope.permsList = [{id: 'r', name: 'Can view'}, {id: 'rw', name: 'Can edit'}];
    $scope.newUserPermission = 'r';

    $scope.accountId = $routeParams.acct_id;
    $scope.NOAccount = null;

    $scope.fetchUsers = function() {
        _UserRoles.list().then(function(data) {
            $scope.fullRoles = data.data.list;
        });

        $scope.users = [];
//        angular.forEach($scope.accountsList, function(acc) {
//            if ($scope.NOAccount == null || acc.id != $scope.NOAccount.id) {
//                $scope.fetchUsersForAccount(acc);
//            }
//        });
        console.log('fetch users for account', $scope.currentAccount.name);
        $scope.usersResolved = false;
        $scope.fetchUsersForAccount($scope.currentAccount).$promise.then(function () {
            $scope.usersResolved = true;
        });
//        if ($scope.NOAccount !== null) {
//        	$scope.fetchOrphanedUsers();
//        }
    };
    //$scope.fetchUsers = function () {
    //  $scope.users = [];
    //  $scope.usersResolved = false;
    //  $scope.fetchUsersForAccount($scope.currentAccount).$promise.then(function () {
    //    $scope.usersResolved = true;
    //  });
    //};

    $scope.fetchAccounts = function () {
      return AccountsService.query({}, applyAccounts).$promise;
    };
    function applyAccounts() {
      $scope.accounts = AccountsService.getList();
      $scope.currentAccount = AccountsService.getCurrent();
      if ($scope.currentAccount && $scope.accountId !== $scope.currentAccount.id) {
        AccountsService.switchAccountId($scope.accountId);
      }
    }

    $scope.switchCurrentAccount = function () {
      AccountsService.switchAccount($scope.currentAccount, function () {
        //$scope.currentAccount = $scope.selectedAccount;
        //reload configure page since the current account was changed
        $window.location.href = '/configure#/users/' + $scope.currentAccount.id;
//            $scope.fetchUsers();
      });
    };

    $scope.fetchUsersForAccount = function (account) {
      var params = {
        offset: $scope.pagination.offset,
        limit: $scope.pagination.limit,
        account: account.id
      };

      if ($scope.filters.searchQuery) {
        params.searchQuery = $scope.filters.searchQuery;
      }

      return ConfigureAccount.getUsers(params, function (result) {
        $scope.pagination.totalItems = result.total_items;
        $scope.pagination.pages = result.pages;

        $scope.errorMessages = [];
        angular.forEach(result.users, function (u) {
          //console.log("User " + u.name);
          u.origPerm = u.perm;
          u.action = 'change';
          if (account.is_admin) {
            // This user will be editable, so make sure he can only be moved to account with permission
            u.currentAccount = _.find($scope.editableAccountsList, function (item) {
              return item.id == u.currentAccount.id;
            });
          } else {
            // This user will only be viewable, pick account from entire account list
            u.currentAccount = _.find($scope.accountsList, function (item) {
              return item.id == u.currentAccount.id;
            });
          }
          $scope.users.push(u);
        });
      }, function onError() {
        // no permission or other error
        $scope.accountsList = _.filter($scope.accountsList, function (acc) {
          return acc.id != account.id;
        });
      });
    };

    $scope.fetchOrphanedUsers = function () {
      $resource("/configure/users/json", {}).get({orphaned: true}, function (res) {
        angular.forEach(res.result, function (orphan) {
          orphan.origPerm = -1;
          orphan.perm = -1;
          orphan.action = 'change';
          var NO_ACCOUNT = orphan.accounts[0];
          orphan.currentAccount = _.find($scope.accountsList, function (item) {
            return item.id == NO_ACCOUNT.id;
          });
          $scope.users.push(orphan);
        });
      });
    };

    $scope.loadAccountsList = function () {
      $scope.fetchAccounts().then(function (res) {
        $scope.accountsList = angular.copy(res.data);
        $scope.editableAccountsList = _.filter($scope.accountsList, function (item) {
          return item.is_admin;
        });
      }).finally(function () {
        $scope.selectedAccount = _.find($scope.accountsList, function (item) {
          return item.id == $scope.accountId;
        });
        $scope.fetchUsers();

//            AccountsService.noAccount({}, function(res) {
//                $scope.accountsList.push(res.account);
//                $scope.editableAccountsList.push(res.account);
//                $scope.NOAccount = res.account;
//            }).$promise.finally(function(){
//	            $scope.selectedAccount = _.find($scope.accountsList, function(item){return item.id == $scope.accountId;});
//	        	$scope.fetchUsers();
//	        });
      });
    };

    $scope.EMAIL_REGEXP = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}$/; //Same regex that angular uses

    $scope.addUsers = function (emails) {
      if (!$scope.newUsers) return;
      if (!$scope.selectedAccount) return;
      var emails = _.uniq($scope.newUsers.split(/[,;:\s\n\t]+/));
      var existEmails = _.pluck($scope.users, 'email');
      var usersInfo = [];
      _.each(emails, function (email) {
        if ($scope.EMAIL_REGEXP.test(email)) {
          if (email && $scope.newUserPermission && !_.include(existEmails, email)) {  // if email is valid and permission set
            usersInfo.push(email + ':' + $scope.newUserPermission + ':' + 'add');
          } else if (_.include(existEmails, email)) {
            angular.forEach($scope.users, function (u) {
              if (u.email == email) {
                if (u.action == 'change') {
                  $scope.setUserAccount(u, $scope.selectedAccount);
                  usersInfo.push(email + ':' + $scope.newUserPermission + ':' + 'change');
                } else {
                  // u.currentAccount = $scope.selectedAccount;
                  usersInfo.push(email + ':' + $scope.newUserPermission + ':' + 'add');
                }
              }
            });
          }
        } else {
          SystemAlert.info("Invalid email " + email + " will be ignored.");
        }

      });
      ACLService.shareAndSave({
        up: usersInfo,
        id: [$scope.selectedAccount.id],
        ot: 'account'
      }, function (result) {
        $scope.fetchUsers();
      });
      $scope.newUsers = "";
    };

    /* deprecated
    $scope.filterAccount = function (user) {
      return (user.currentAccount != undefined && $scope.selectedAccount.id == user.currentAccount.id);
    };
    */

    /*$scope.removeUser = function(user) {
     //alert("Should be removing user " + user);
     var postData = {id: user.id,
     account_id: user.currentAccount.id};
     $http({
     method : 'POST',
     url    : '/users/remove/json',
     data: { user_id : user.id,
     account_id: user.currentAccount.id }

     }).success(function(res) {
     $scope.fetchUsers();
     })
     }*/

    $scope.saveButtonDisabled = function () {
      var changedUsersList = _.filter($scope.users, function (u) {
        return u.perm != u.origPerm
      });
      return !(changedUsersList && changedUsersList.length);
    };

    $scope.isEditDisabled = function (isCurrentSuper, currentUserEmail, targetUser) {
      if (targetUser.perm == 's' && currentUserEmail != targetUser.email) {
        // One super user should not be able to reset the password of another
        return true;
      }
      if (!isCurrentSuper && targetUser.perm == 's') {
        // A regular user should not be able to reset password of superuser
        return true;
      }
      return false;
    };

    $scope.resetPassword = function (email) {
      DialogService.openDialog({dialog: 'password_change', email: email});
    };

    $scope.close = function (result) {
      $scope.$close(result);
    };

    /*
     * Do a sync in database, setting the currently selected user account as users current account.
     * Called on any change in the 'Account select' entry from the collections table.
     */
    $scope.setCurrentAccount = function (user) {
      $scope.setUserAccount(user, user.currentAccount);
    };

    /*
     * Change the permissions for this given user, on his current account.
     */
    $scope.changePermissions = function (user) {
      var userInfo = user.email + ':' + user.perm + ':' + user.action;
      ACLService.shareAndSave({
        up: [userInfo],
        id: [user.currentAccount.id],
        ot: 'account'
      }, function (result) {
        $scope.fetchUsers();
      });
    };

    /*
     * For a give user, set account as the current one.
     */
    $scope.setUserAccount = function (user, account) {
      if (!(account.is_admin || account.is_super)) {
        SystemAlert.error("You only have view permissions in account " + account.name + "!");
      }
      if (user.action == 'change') {
        if ($scope.NOAccount == null || account.id != $scope.NOAccount.id) {
          // Switch from one account to another. Either keep the permissions
          // or in case we brough a user from NO_ACCOUNT'land give him the
          // permissions that are currently set for new users.
          var perm = user.perm;
          if (user.perm == -1) perm = $scope.newUserPermission; // Switched from NO_ACCOUNT land
          ConfigureAccount.save({
            account_id: account.id,
            email: user.email,
            perms: perm
          }, function () {
            user.origPerm = $scope.newUserPermission;
            user.perm = $scope.newUserPermission;
            user.currentAccount = account;
          });
        } else {
          // We just switched a user to NO_ACCOUNT land. Remove his current account.
          ConfigureAccount.removeUser({email: user.email},
            function () {
              user.perm = -1;
              user.origPerm = -1;
            });
        }
      }
    };

    $scope.editUser = function (user) {
      DialogService.openDialog({target: 'user_edit', email: user.email});
    };

    $scope.$on(DialogService.CLOSE, function (event, data) {
      if (data.target == 'user_edit') {
        $scope.fetchUsers();
      }
    });

    $scope.edit = function (email) {
      $location.path('/users/edit/' + $scope.accountId + '/' + email);
    };

    $scope.loadAccountsList();

  }
  UsersListCtrl.$inject = ["$scope", "$location", "$http", "$resource", "$routeParams", "$timeout", "$window", "AccountsService", "ACLService", "ConfigureAccount", "DialogService", "SystemAlert", "UserRolesRest"];
})();

(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/gallery', {
          templateUrl: '/partials/widget_gallery/list',
          controller: 'GalleriesCtrl',
          name: 'gallery'
        })
        .when('/gallery/:id', {
          templateUrl: '/partials/widget_gallery/widget_model_list',
          controller: 'WidgetsGalleryCtrl',
          name: 'gallery'
        })
        .when('/gallery/:gallery_id/widget_model/:id?', {
          templateUrl: '/partials/widget_gallery/widget_model_edit',
          controller: 'WidgetModelCRUDCtrl',
          name: 'widget_models'
        })
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('GalleriesCtrl', GalleriesCtrl);

  /** @ngInject */
  function GalleriesCtrl($scope, $http) {
    var init = function () {
      $http.get('/gallery')
        .success(function (galleries) {
          $scope.galleries = galleries.data;
        });

      $scope.filters = {display_name: ''};
    };

    init();
  }
  GalleriesCtrl.$inject = ["$scope", "$http"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('WidgetsGalleryCtrl', WidgetsGalleryCtrl);

  /** @ngInject */
  function WidgetsGalleryCtrl($scope, $http, $routeParams) {
    var init = function () {
      $http.get('/gallery/' + $routeParams.id)
        .success(function (res) {
          $scope.gallery = res.data;
        });
      $scope.filters = {title: ''};
      $scope.selected = [];
      $scope.table = {
        sort: {
          predicate: 'title',
          reverse: false
        }
      };
    };

    $scope.selectModel = function (model) {
      if ($scope.selected.length) {
        var i = $scope.selected.indexOf(model);
        if (i === -1) {
          $scope.selected.push(model);
        } else {
          $scope.selected.splice(i, 1);
        }
      } else {
        $scope.selected.push(model);
      }
    };

    $scope.remove = function () {
      _.each($scope.selected, function (model) {
        $http.delete('/gallery/' + $routeParams.id + '/widget_models/' + model.id)
          .success(function () {
            _.remove($scope.gallery.widget_models, {'id': model.id});
          });
      });
    };

    init();
  }
  WidgetsGalleryCtrl.$inject = ["$scope", "$http", "$routeParams"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('WidgetModelCRUDCtrl', WidgetModelCRUDCtrl);

  /** @ngInject */
  function WidgetModelCRUDCtrl($scope, $http, $location, $routeParams) {

    var id = $routeParams.id;
    $scope.title = id ? 'Update' : 'Create';
    $scope.gallery_id = $routeParams.gallery_id;
    $scope.model = {};
    $scope.formState = {};
    var url = '/gallery/' + $scope.gallery_id + '/widget_models';

    if (id) {
      $http.get(url + '/' + id)
        .then(function (resp) {
          $scope.model = resp.data.data;
          $scope.model.settings = JSON.stringify($scope.model.settings, null, 4);
        })
    } else {
      $scope.model = {
        title: "",
        description: "",
        settings: ""
      };
    }

    $scope.save = function () {
      function modelSaved(resp) {
        $scope.model = resp.data;
        $scope.model.settings = JSON.stringify($scope.model.settings, null, 4);
        $scope.formState.isSaved = true;
        $scope.formState.hasError = false;
        $scope.title = 'Update';
        if (!id) {
          $location.path('/gallery/' + $scope.gallery_id);  
        }
      }

      function modelNotSaved() {
        $scope.formState.hasError = true;
        $scope.model.settings = JSON.stringify($scope.model.settings, null, 4);
      }

      $scope.formState.isSaved = false;

      try {
        $scope.model.settings = JSON.parse($scope.model.settings);
        if (id) {
          $http.put(url + '/' + id, $scope.model)
            .success(modelSaved)
            .error(modelNotSaved);
        } else {
          $http.post(url, $scope.model)
            .success(modelSaved)
            .error(modelNotSaved);
        }
      } catch (e) {
        $scope.formState.hasError = true;
        console.log('Invalid JSON');
      }
    };
  }
  WidgetModelCRUDCtrl.$inject = ["$scope", "$http", "$location", "$routeParams"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/schema-predictors', {
          templateUrl: '/partials/schema-predictors/list',
          controller: 'SchemaPredictorsCtrl',
          name: 'schema-predictors'
        })
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('SchemaPredictorsCtrl', SchemaPredictorsCtrl);

  /** @ngInject */
  function SchemaPredictorsCtrl($scope, $http, toaster, AccountsService, Utils, $modal) {

    var init = function () {
      $scope.account = AccountsService.getCurrent();

      $http.get("/account/predictor-configuration/" + $scope.account.id)
        .success(function (response) {
          $scope.schemaList = response.data;
        })
        .error(function (data) {
          toaster.pop('error', data);
        });
    };

    $scope.showPredictorConfiguration = function (name, schema) {
      if (!$scope.schemaList) return;
      var dialogScope = $scope.$new();
      dialogScope.account = $scope.account;

      dialogScope.predictorObj = {
        data: schema,
        options: {
          name: name,
          mode: 'tree',
          // sort objects alphabetically because python dictionary doesn't preserve the order
          // for some reason, this is causing problem, and showing empty Object
          //sortObjectKeys: true
        }
      };

      var oldConfiguration = angular.copy(dialogScope.predictorObj.data);
      dialogScope.predictorConfigurationError = false;

      var modalInstance = $modal.open({
        scope: dialogScope,
        backdrop: true,
        keyboard: true,
        templateUrl: '/partials/schema-predictors/predictor-configuration'
      });

      // detect invalid json and disable 'save' button
      dialogScope.editorLoaded = function (jsonEditor) {
        // onChange and onError couldn't be configured in predictorObj.options configuration
        // so define them here
        // but it's overriding some default behavior, thereby not working at all
        //jsonEditor.options.onChange = function () {
        //  $timeout(function () {
        //    $scope.predictorConfigurationError = false;  // reset flag
        //    console.log('onChange');
        //  }, 10);
        //};
        //jsonEditor.options.onError = function (err) {
        //  $timeout(function () {
        //    $scope.predictorConfigurationError = true;
        //    console.log('onError', err);
        //  }, 20);
        //};
      };

      dialogScope.canPredictorConfigurationBeSaved = function () {
        if (angular.equals(oldConfiguration, dialogScope.predictorObj.data)) {
          return false;
        }
        return !dialogScope.predictorConfigurationError;
      };

      dialogScope.savePredictorConfiguration = function () {
        oldConfiguration = angular.copy(dialogScope.predictorObj.data);

        $scope.schemaList[name] = oldConfiguration;

        $http.post("/account/predictor-configuration/" + dialogScope.account.id, $scope.schemaList)
          .success(function () {
            toaster.pop('success', "Default predictor configuration for this account saved.");
            modalInstance.close();
          });
      };

    };

    init();
  }
  SchemaPredictorsCtrl.$inject = ["$scope", "$http", "toaster", "AccountsService", "Utils", "$modal"];
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(["$routeProvider", function ($routeProvider) {
      $routeProvider
        .when('/channel_types', {
          templateUrl: '/partials/channel-types/list',
          controller: 'ChannelTypesListCtrl',
          name: 'channel_types'
        })
        .when('/channel_types/edit/:name', {
          templateUrl: '/partials/channel-types/edit',
          controller: 'EditChannelTypeCtrl',
          name: 'channel_types'
        })
    }])
})();
(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('EditChannelTypeCtrl', EditChannelTypeCtrl)

  /** @ngInject */
  function EditChannelTypeCtrl($scope, $routeParams, $q, $timeout, $location, ChannelTypesRest, MetadataService, toaster) {

    var _ChannelTypesRest = new ChannelTypesRest();

    $scope.entityName = null;
    $scope.entity = null;
    $scope.hasError = false;

    $scope.attributeTypes = MetadataService.getSchemaFieldTypes();

    $scope.onSaveEntity = onSaveEntity;
    $scope.onAddAttribute = onAddAttribute;
    $scope.onRemoveAttribute = onRemoveAttribute;

    activateController();

    function onSaveEntity() {
      // Validate channel type
      var hasMissingField =
        _.some($scope.entity.schema, function (e) {
          return (!e.type || (e.type && !e.name));
        })

      if (hasMissingField) {
        toaster.pop('error', 'Some attributes have missing name or type');
        $scope.hasError = true;
        return;
      }

      $scope.hasError = false;

      // SnakeCase or CamelCase field names so that they can be bound to models.
      // _.each($scope.entity.schema, function(field) {
      //   field.key = field.name.replace(/(?!^)([A-Z])/g, ' $1')
      //       .replace(/[_\s]+(?=[a-zA-Z])/g, '_').toLowerCase();
      // });

      var saveFn;
      if ($scope.entityName) {
        saveFn = _ChannelTypesRest.update($scope.entityName, _.pick($scope.entity, ['name', 'description', 'schema']));
      } else {
        saveFn = _ChannelTypesRest.create($scope.entity);
      }

      saveFn.success(function(res) {
        toaster.pop('info', 'Saved successfully!');

        if(!$scope.entityName) {
          $location.path('/channel_types');
        }

      }).catch(function(err) {
        console.log(err);
        // toaster.pop('error', 'Failed to save!');
      })
    }

    function onAddAttribute(evt) {
      evt.preventDefault();

      $scope.entity.schema.push({
        name: '',
        type: '',
      });
    }

    function onRemoveAttribute(evt, index) {
      evt.preventDefault();

      $scope.entity.schema.splice(index, 1);
    }

    function loadEntity() {
      if ($routeParams.name === 'new') {
        $scope.entity = {
          name: '',
          description: '',
          schema: [],
        };
        return $q.when();
      } else {
        $scope.entityName = $routeParams.name;
        return _ChannelTypesRest.getOne($scope.entityName)
          .success(function(res) {
            $scope.entity = res.data;
          });
      }
    }

    function activateController() {
      loadEntity();
    }
  }
  EditChannelTypeCtrl.$inject = ["$scope", "$routeParams", "$q", "$timeout", "$location", "ChannelTypesRest", "MetadataService", "toaster"];
})();

(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('ChannelTypesListCtrl', ChannelTypesListCtrl);

  /** @ngInject */

  function ChannelTypesListCtrl($scope, $q, $interval, $modal, ChannelTypesRest, FilterService, MetadataService, SystemAlert) {

    var _ChannelTypesRest = new ChannelTypesRest();
    var pageRefresher;
    var debouncedFetch = _.debounce(fetchChannelTypes, 100);
    
    $scope.$on(FilterService.DATE_RANGE_CHANGED, debouncedFetch);

    $scope.delete = function() {
      stopRefresh();

      var promises = [];
      _.each($scope.selectedList, function(e) {
        promises.push(deleteEntity(e.name));
      });

      $q.all(promises)
        .then(function() {
          fetchChannelTypes();
        });
    };

    $scope.applySync = function() {
      stopRefresh();

      var promises = [];
      _.each($scope.selectedList, function(e) {
        promises.push(applySync(e.name));
      });

      $q.all(promises)
        .then(function() {
          fetchChannelTypes();
        });
    }

    //TODO: Why `ark-switch` dispatches action twice?
    $scope.toggleLock = _.debounce(toggleLock, 100);

    $scope.$on('$destroy', function() {
      stopRefresh();
    });

    function startRefresh() {
      if ( angular.isDefined(pageRefresher) ) return;
      fetchChannelTypes();
      pageRefresher = $interval(fetchChannelTypes, 2000);
    }

    function stopRefresh() {
      if ( angular.isDefined(pageRefresher) ) {
        $interval.cancel(pageRefresher);
        pageRefresher = undefined;
      }
    }

    function hasPendingEntities(entities) {
      return _.some(entities, function(e) {
        return e.status === 'LOADING' || e.sync_status === 'SYNCING';
      });
    }

    function fetchChannelTypes() {
      var dateRange = FilterService.getDateRange({ local: true });

      _ChannelTypesRest.list()
        .success(function(res) {
          $scope.entityList = res.data;
          _.each($scope.entityList, function(e) {
            e.status_display = MetadataService.getBeautifiedStatus(e, 'channel');
            e.has_error = !!e.sync_errors;
          });
          if (!hasPendingEntities(res.data) ) {
            stopRefresh();
          }
        });
    }

    activateController();

    function activateController() {
      $scope.table = {
        sort: {
          predicate: 'created_at',
          reverse: false,
        }
      };
      $scope.selectedList = [];
      $scope.flags = {
        searchTerm: '',
        selectedAll: false,
      }
      startRefresh();
    }

    function deleteEntity(name) {
      return _ChannelTypesRest.delete(name)
        .success(function() {
          fetchChannelTypes();
          SystemAlert.info('Deleted `' + name + '`');
        })
        .catch(function() {
          // SystemAlert.error('Failed to delete `' + name + '`');
        });
    }

    function applySync(name) {
      return _ChannelTypesRest.applySync(name)
        .success(function() {
          fetchChannelTypes();
          SystemAlert.info('Synced `' + name + '`');
        })
        .catch(function() {
          // SystemAlert.error('Failed to synchronize ' + name);
        });
    }

    function toggleLock(entity) {
      _ChannelTypesRest.update(entity.name, _.pick(entity, ['is_locked']))
        .success(function() {
          if (entity.is_locked) {
            SystemAlert.info('Locked `' + entity.name + '`');
          } else {
            SystemAlert.info('Unlocked `' + entity.name + '`');
          }
        })
        .catch(function() {
          SystemAlert.error('Failed to lock `' + entity.name + '`');
        });
    }

    $scope.onShowErrors = function(entity) {
      var dialogScope = $scope.$new();

      dialogScope.data = {
        errors: entity.sync_errors,
        options: {
          name: "Fields resulted in errors",
          mode: "tree",
        }
      };

      dialogScope.title = entity.name;

      var modalInstance = $modal.open({
        scope: dialogScope,
        backdrop: true,
        keyboard: true,
        templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.sync-errors.html'
      });
    }

    $scope.select = function (entity) {
      if (!entity) { // global selection
        _.each($scope.entityList, function(e) {
          e.selected = !$scope.flags.selectedAll;
        });

        if ($scope.flags.selectedAll) {
          $scope.selectedList = [];
        } else {
          $scope.selectedList = _.clone($scope.entityList);
        }
        $scope.flags.selectedAll = !$scope.flags.selectedAll;

      } else {
        _.each($scope.entityList, function(item) {
          if (entity.id === item.id) {
            if (_.findWhere($scope.selectedList, { id: entity.id })) {
              _.remove($scope.selectedList, entity);
            } else {
              $scope.selectedList.push(entity)
            }
            item.selected = !entity.selected;
          }
        });

        $scope.flags.selectedAll = ($scope.selectedList.length === $scope.entityList.length);
      }
    };

  }
  ChannelTypesListCtrl.$inject = ["$scope", "$q", "$interval", "$modal", "ChannelTypesRest", "FilterService", "MetadataService", "SystemAlert"];
})();

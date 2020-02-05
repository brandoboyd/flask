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
          controller: function ($scope) {
            $scope.modal_title = ("Confirm removing {lang} keywords").replace('{lang}', e.removed.text);
            $scope.language = e.removed.text;
            $scope.close = function () {
              $scope.$close(e.removed);
            };
            $scope.dismiss = function () {
              $scope.$dismiss('cancel');
            };
          }
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
})();
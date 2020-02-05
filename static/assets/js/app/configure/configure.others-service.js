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
    .factory('TagsMessages', function ($timeout) {
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
    })
    .service('fbUserDataProvider', function ($http) {
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

    })
    .factory('LanguageUtils', function ($http, TrackingChannel) {
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
    })
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
(function () {
  'use strict';

  angular
    .module('slr.utils')
    .service('Utils', Utils);

  /** @ngInject*/
  function Utils() {
    this.toTitleCase = function (str) {
      return str.replace(/\w\S*/g, function (txt) {
        return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
      });
    };

    this.roundUpTo2precision = function (num) {
      if (!num) return 0;
      var res;
      if (num.length) {
        res = _.map(num, function (n) {
          return Math.round(n * 100) / 100;
        });
      } else {
        res = Math.round(num * 100) / 100;
      }
      return res;
    };

    this.mean = function (list) {
      return list.reduce(function (p, c) {
          return parseFloat(p) + parseFloat(c);
        }) / list.length;
    };

    this.objToArray = function (obj, objkeys) {
      var keys = _.keys(obj);
      var values = _.values(obj);
      var arr = [];

      if (!objkeys) {
        objkeys = ['key', 'value'];
      }

      _.each(keys, function (k, i) {
        if (values[i] !== null) {
          arr.push(_.object(objkeys, [k, values[i]]));
        }
      });
      return arr;
    };

    this.compareArrays = function (a1, a2) {
      return (a1.length == a2.length) && a1.every(function (el, i) {
          return el === a2[i];
        });
    };

    this.noDataMessageHtml = function (params) {
      var noDataMessage = function (params) {
        var defaultNoDataMessage = null,
          noDataMessage = params.hasOwnProperty('noDataMessage') ? (params.noDataMessage() || defaultNoDataMessage) : defaultNoDataMessage;
        return noDataMessage;
      };

      var noDataMessageHeader = function (params) {
        var defaultNoDataHeader = " No Data Available",
          noDataMessageHeader = params.hasOwnProperty('noDataMessageHeader') ? (params.noDataMessageHeader() || defaultNoDataHeader) : defaultNoDataHeader;
        return noDataMessageHeader;
      };

      var header = "<i class='icon-alert-triangle'></i> header".replace('header', noDataMessageHeader(params));
      var message = !noDataMessage(params) ? '' : "<p>message</p>".replace('message', noDataMessage(params));
      return "<div class='alert alert-info text-center'>" + header + message + "</div>";
    };

    this.generateTicks = function (opts, tickSize) {
      var ticks = [],
        start = opts.min,
        i = 0,
        v = Number.NaN,
        prev;

      do {
        prev = v;
        v = start + i * tickSize;
        ticks.push(v);
        ++i;
      } while (v < opts.max && v != prev);
      return ticks;
    };

    this.formatSeconds = function (seconds) {
      function makeLabel(v, mode) {
        mode = mode || 'minutes';
        if (isNaN(v)) {
          return "";
        }
        var res;
        if (v >= 3600) {
          res = "" + Math.floor(v / 3600) + 'h';
          v = v % 3600;
        } else if (v >= 60) {
          var round = mode == 'seconds' ? Math.floor : Math.ceil;
          res = "" + round(v / 60) + 'm';
          v = v % 60;
        } else {
          if (mode == 'minutes') {
            return "";
          } else if (mode == 'seconds') {
            return Math.ceil(v) + 's';
          }
        }
        return res + " " + makeLabel(v, mode);
      }

      return seconds ? makeLabel(seconds, seconds < 60 ? "seconds" : "minutes") : "0";
    };
  }
})();
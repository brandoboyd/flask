/*!
 * Ark Graphs v1.0.0-0 (2015-08-27)
 * http://ark.genesys.com
 * Copyright (c) 2015 Ark Team at Genesys; License: MIT
 */

'use strict';

// TODO: This Angular module should be use from external package
// Probably included into underscore.js Nexus package
angular.module('underscore', []).factory('_', function() {
  return window._;
});

angular.module('ark.graphs', [
    'underscore',
    'ark.graphs.common',
    'ark.graphs.bar',
    'ark.graphs.spark-line',
    'ark.graphs.line-graph',
    'ark.graphs.gauge',
    'ark.graphs.donut',
    // 'ark.graphs.pie',
    // 'ark.graphs.multi-widget',
    'ark.graphs.multi-line-graph'
  ])
  .run(['$rootScope', function($rootScope) {
    $rootScope.safeApply = function(fn) {
      var phase = this.$root.$$phase;
      if (phase === '$apply' || phase === '$digest') {
        if (fn && (typeof(fn) === 'function')) {
          fn();
        }
      } else {
        this.$apply(fn);
      }
    };
    angular.element(window).on('resize', function() {
      $rootScope.safeApply();
    });
  }]);


'use strict';

angular.module('ark.graphs.common', []);

'use strict';

angular.module('ark.graphs.bar', ['ark.graphs.common']);

'use strict';

angular.module('ark.graphs.donut', ['ark.graphs.common']);

'use strict';

angular.module('ark.graphs.gauge', ['ark.graphs.common']);

'use strict';

angular.module('ark.graphs.line-graph', ['ark.graphs.common']);

'use strict';

angular.module('ark.graphs.multi-line-graph', ['ark.graphs.common']);

'use strict';

angular.module('ark.graphs.spark-line', ['ark.graphs.common']);

'use strict';

angular.module('ark.graphs.common')
  .service('ark.graphs.arc-service', ['ark.graphs.d3',
    function(d3) {
      var ArcService = function() {};

      ArcService.prototype.polarToCartesian = function(centerX, centerY, radius, angleInDegrees) {
        var angleInRadians = (angleInDegrees - 90) * Math.PI / 180.0;
        return {
          x: centerX + (radius * Math.cos(angleInRadians)),
          y: centerY + (radius * Math.sin(angleInRadians))
        };
      };

      ArcService.prototype.toRadians = function(degrees) {
        return (degrees / 180) * Math.PI;
      };

      ArcService.prototype.toDegrees = function(radians) {
        return (radians * 180) / Math.PI;
      };

      ArcService.prototype.describeArc = function(x, y, radius, startAngle, endAngle) {
        var start = this.polarToCartesian(x, y, radius, endAngle);
        var end = this.polarToCartesian(x, y, radius, startAngle);
        var arcSweep = ((endAngle - startAngle) <= 180) ? 0 : 1;
        return [
          'M', start.x, start.y,
          'A', radius, radius, 0, arcSweep, 0, end.x, end.y
        ].join(' ');
      };

      ArcService.prototype.computeArc = function(startAngle, endAngle, value, max, width, height, radius) {
        return this.describeArc(
          width / 2,
          height / 2,
          radius,
          startAngle,
          endAngle * (value / max)
        );
      };

      ArcService.prototype.computeRotation = function(angle, width, height) {
        return 'rotate(' + angle + ',' + width / 2 + ',' + height / 2 + ')';
      };

      ArcService.prototype.translate = function(width, height) {
        return 'translate(' + width / 2 + ',' + height / 2 + ')';
      };

      ArcService.prototype.d3Arc = function(radius, strokeWidth) {
        return d3.svg.arc()
          .outerRadius(radius)
          .innerRadius(radius - strokeWidth);
      };

      ArcService.prototype.d3Pie = function(amplitude, padAngle, sorting) {
        var sort = null;
        if (sorting === 'ascending') {
          sort = d3.ascending;
        } else if (sorting === 'descending') {
          sort = d3.descending;
        }
        return d3.layout.pie()
          .sort(sort)
          .padAngle(this.toRadians(padAngle))
          .startAngle(0)
          .endAngle(this.toRadians(amplitude))
          .value(function(d) {
            return d + Math.random() / 100000;
          });
      };

      return new ArcService();
    }
  ]);

'use strict';

angular.module('ark.graphs.common')
  .service('ark.graphs.color-service', function() {
    var RED = '#EA4F6B';
    var YELLOW = '#F8A740';
    var BLUE = '#203B73';
    var GREEN = '#4AC764';

    var THRESHOLDS_4 = [RED, YELLOW, BLUE, GREEN];
    var THRESHOLDS_3 = [RED, YELLOW, GREEN];
    var THRESHOLDS_2 = [RED, GREEN];
    var THRESHOLDS_1 = [GREEN];

    var PALETTE = ['#203B73', '#2E69DB', '#5E99FF', '#9BBCE0', '#5A6B8C', '#75A8FF', '#0F6A51', '#569180', '#14819C', '#7EC0C2', '#AFD6D2', '#584FB3', '#7272E0', '#B9B9F0', '#575746', '#827C75', '#C9C4B7', '#8C6542', '#8A4D67', '#C48C88', '#EBC8BE', '#724787', '#B07EC2', '#D1B4D9'];

    var ColorService = function() {};

    ColorService.prototype.getStatusColors = function(n) { // supports for up to four status colors
      switch (n) {
        case 4:
          return THRESHOLDS_4;
        case 3:
          return THRESHOLDS_3;
        case 2:
          return THRESHOLDS_2;
        default: // n == 1
          return THRESHOLDS_1;
      }
    };

    ColorService.prototype.arkPalette = function() {
      return PALETTE;
    };

    ColorService.prototype.arkBlueColors = function() {
      return this.arkPalette().slice(0, 5); //return the first 5 items of the palette which are blue colors
    };

    ColorService.prototype.arkThresholdIcon = function() {
      return RED;
    };

    return new ColorService();
  });

'use strict';

angular.module('ark.graphs.common')
  .service('ark.graphs.config-service', ['ark.graphs.color-service',
    function(ColorService) {
      var ConfigService = function() {};

      ConfigService.prototype.getData = function(index, arr) {
        return (arr[index]) ? arr[index] : arr[0];
      };

      ConfigService.prototype.getStatusColors = function(obj) {
        if ((obj.data.thresholds.values.length + 1) !== obj.data.thresholds.statusColors.length) {
          obj.data.thresholds.statusColors = ColorService.getStatusColors(obj.data.thresholds.values.length + 1);
        }
      };

      ConfigService.prototype.updateColors = function(obj) {
        var colors = obj.data.thresholds ? obj.data.thresholds.statusColors : obj.data.colors;
        if (colors.length !== obj.numberOfData) {
          colors = ColorService.arkPalette().slice(obj.numberOfData - 1);
        }
      };

      ConfigService.prototype.updateInitialValues = function(obj) {
        if (obj.initialValues.length === 0) {
          obj.initialValues = Array.apply(null, new Array(obj.numberOfData)).map(function() {
            return 0;
          });
        }
      };

      ConfigService.prototype.updateLegendLabels = function(obj) {
        if (obj.numberOfData !== obj.legend.title.length) {
          obj.legend.title = Array.apply(null, new Array(obj.numberOfData)).map(function(x, i) {
            return 'Label ' + String.fromCharCode(i + 65);
          });
        }
      };

      ConfigService.prototype.updateTooltipLabels = function(obj) {
        if (obj.numberOfData !== obj.data.labels.length) {
          obj.data.labels = Array.apply(null, new Array(obj.numberOfData)).map(function(x, i) {
            return 'data ' + i.toString();
          });
        }
      };

      return new ConfigService();
    }
  ]);

'use strict';

angular.module('ark.graphs.common')
  .service('ark.graphs.d3', function() {
    return d3;
  });

'use strict';

angular.module('ark.graphs.common')
  .service('ark.graphs.line-service', ['ark.graphs.d3',
    function(d3) {
      var LineService = function() {};

      LineService.prototype.createLine = function(rangeX, rangeY, fieldX, fieldY) {
        return d3.svg.area()
          .x(function(d) {
            return rangeX(d[fieldX] || 0);
          })
          .y(function(d) {
            return rangeY(d[fieldY] || 0);
          });
      };

      LineService.prototype.createRange = function(start, end) {
        return d3.time.scale().range([start, end]);
      };

      LineService.prototype.createLinearRange = function(start, end) {
        return d3.scale.linear().range([start, end]);
      };

      LineService.prototype.createAxis = function(d3range, ticks, orient) {
        return d3.svg.axis().scale(d3range).orient(orient ? orient : 'left').ticks(ticks);
      };

      LineService.prototype.scaleFromDomain = function(axis, domain) {
        return axis.domain(domain);
      };

      LineService.prototype.scaleFromData = function(axis, data, field, offset) {
        var min = d3.min(data, function(d) {
          return (d[field] !== undefined) ? d[field] : d3.min(d, function(c) {
            return c[field] || 0;
          });
        });
        var max = d3.max(data, function(d) {
          return (d[field] !== undefined) ? d[field] : d3.max(d, function(c) {
            return c[field] || min + 1;
          });
        });

        if (offset !== undefined) {
          max += offset * (max - min);
        }
        return axis.domain([min, max]);
      };

      LineService.prototype.scaleFrom0ToMax = function(axis, data, field) {
        return axis.domain([
          0,
          d3.max(data, function(d) {
            return (d.constructor !== Array) ? d[field] : d3.max(d, function(c) {
              return c[field];
            });
          })
        ]);
      };

      LineService.prototype.scale = function(axis, range) {
        return axis.domain(range);
      };

      LineService.prototype.computeLine = function(x1, y1, x2, y2) {
        return ['M', x1, y1, 'L', x2, y2, 'Z'].join(' ');
      };

      return new LineService();
    }
  ]);

'use strict';

angular.module('ark.graphs.common')
  .service('ark.graphs.pie-service', ['ark.graphs.arc-service',
    function(ArcService) {
      var PieService = function() {};
      var that = new PieService();

      PieService.prototype.getLabelTranslation = function(d, config) {
        var size;
        if (config.slice.label.position === 'out') {
          size = config.radius + config.slice.hover.growBy + config.slice.label.line.size;
        } else if (config.slice.label.position === 'in') {
          //If it is a pie chart

          if (config.radius === config.strokeWidth) {
            size = config.radius - config.slice.label.value.fontsize * 3;
          } else {
            size = config.radius - config.strokeWidth / 2 - config.slice.label.value.fontsize;
          }
        }
        return 'translate(' +
          Math.cos(((d.startAngle + d.endAngle + d.padAngle * 2 - Math.PI) / 2)) * (size) + ',' +
          Math.sin((d.startAngle + d.endAngle + d.padAngle * 2 - Math.PI) / 2) * (size) + ')';
      };

      PieService.prototype.getTextAnchor = function(d) {
        return (that.getMiddle(d) < Math.PI) ? 'beginning' : 'end';
      };

      PieService.prototype.getMiddle = function(d) {
        return (d.startAngle + d.endAngle) / 2 + d.padAngle * 4;
      };

      PieService.prototype.getLabelValueDY = function(d) {
        var middle = that.getMiddle(d);
        if (middle <= Math.PI / 2) {
          return 0;
        } else if (middle > Math.PI / 2 && middle <= Math.PI * 1.5) {
          return 10;
        } else {
          return 0;
        }
      };

      PieService.prototype.getLabelNameDY = function(d) {
        var middle = that.getMiddle(d);
        if (middle <= Math.PI / 2) {
          return 0;
        } else if (middle > Math.PI / 2 && middle <= Math.PI * 1.5) {
          return 10;
        } else {
          return 0;
        }
      };

      PieService.prototype.getLabelRotation = function(d) {
        return ArcService.computeRotation(
          ArcService.toDegrees(that.getMiddle(d)),
          0,
          0
        );
      };

      PieService.prototype.drawLabels = function(widget, pieData, config) {
        if (config.slice.label.position === 'out' && config.slice.label.line.display) {
          var lines = widget.select('.ark-graphs-label-group').selectAll('line');

          lines.data(pieData)
            .enter()
            .append('line')
            .attr('class', config.slice.label.line.class)
            .attr('x1', 0)
            .attr('x2', 0)
            .attr('y1', -config.radius - config.slice.hover.growBy)
            .attr('y2', -config.radius - config.slice.hover.growBy - config.slice.label.line.size)
            .attr('stroke', config.slice.label.line.color)
            .attr('transform', function(d) {
              return that.getLabelRotation(d);
            });

          lines = widget.select('.ark-graphs-label-group').selectAll('line');
          lines.transition()
            .duration(config.transitions.arc)
            .attr('transform', function(d) {
              return that.getLabelRotation(d);
            });
        }

        if (config.slice.label.value.display) {
          var valueLabels = widget.select('.ark-graphs-label-group').selectAll('text.' + config.slice.label.value.class);
          valueLabels.data(pieData)
            .enter()
            .append('text')
            .attr('fill', config.slice.label.value.color)
            .attr('font-size', config.slice.label.value.fontsize + 'px')
            .attr('class', config.slice.label.value.class + ' ' + config.slice.label.position)
            .attr('transform', function(d) {
              return that.getLabelTranslation(d, config);
            })
            .attr('dy', that.getLabelValueDY)
            .attr('text-anchor', that.getTextAnchor);

          valueLabels = widget.select('.ark-graphs-label-group').selectAll('text.' + config.slice.label.value.class);
          valueLabels.transition()
            .duration(config.transitions.arc)
            .text(config.slice.label.value.format)
            .attr('dy', that.getLabelValueDY)
            .attr('text-anchor', that.getTextAnchor)
            .attr('transform', function(d) {
              return that.getLabelTranslation(d, config);
            });
        }

        var nameLabels = widget.select('.ark-graphs-label-group').selectAll('text.' + config.slice.label.name.class);

        nameLabels.data(pieData)
          .enter()
          .append('text')
          .attr('fill', config.slice.label.name.color)
          .attr('font-size', config.slice.label.name.fontsize + 'px')
          .attr('class', config.slice.label.name.class + ' ' + config.slice.label.position)
          .attr('transform', function(d) {
            return that.getLabelTranslation(d, config);
          })
          .attr('dy', that.getLabelNameDY)
          .attr('text-anchor', that.getTextAnchor)
          .text(function(d, i) {
            return config.slice.label.name.format(d, i);
          });

        nameLabels = widget.select('.ark-graphs-label-group').selectAll('text.' + config.slice.label.name.class);
        nameLabels
          .transition()
          .duration(config.transitions.arc)
          .attr('dy', that.getLabelNameDY)
          .attr('text-anchor', that.getTextAnchor)
          .text(function(d, i) {
            return config.slice.label.name.format(d, i);
          })
          .attr('transform', function(d) {
            return that.getLabelTranslation(d, config);
          });
      };
      return that;
    }
  ]);

'use strict';

angular.module('ark.graphs.common')
  .service('ark.graphs.text-service', ['ark.graphs.color-service', 'ark.graphs.threshold-service',
    function(ColorService, ThresholdService) {
      var TextService = function() {};

      TextService.prototype.showText = function(configuration, widget, data) {
        if (!configuration.legend.display) {
          return;
        }

        var legend = widget.select('.ark-graphs-' + configuration.type + '-div')
          .append('div')
          .attr('class', 'ark-graphs-' + configuration.type + '-legend')
          .style('width', configuration.legend.width.toString() + 'px');

        if (configuration.legend.padding.top) {
          legend
            .style('padding-top', configuration.legend.padding.top + 'px');
        }

        legend.selectAll('div').data(data)
          .enter()
          .append('div')
          .attr('class', function(d, i) {
            return 'ark-graphs-' + configuration.type + '-legend-text ark-graphs-' + configuration.type + '-legend-text-' + i;
          });

        var legendLines = legend.selectAll('div');
        legendLines
          .append('span')
          .attr('class', 'metric-name')
          .style('left', function() {
            if (typeof configuration.legend.letters !== 'undefined' && configuration.legend.letters.display) {
              return '20px';
            }
            return '0px';
          })
          .append('text')
          .text(function(d, i) {
            return configuration.legend.title[i];
          })
          .style('font-size', configuration.legend.fontsize + 'px');

        if (typeof configuration.legend.letters !== 'undefined' && configuration.legend.letters.display) {
          legendLines
            .append('span')
            .attr('class', 'letters')
            .text(function(d, i) {
              return String.fromCharCode(i + 65);
            })
            .style('font-size', configuration.legend.fontsize + 'px');
        }

        legendLines
          .append('span')
          .attr('class', 'data')
          .text(function(d, i) {
            return configuration.legend.format(data[i], i);
          })
          .style('font-size', configuration.legend.fontsize + 'px');

        legendLines
          .append('span')
          .attr('class', function(d) {
            var icon = 'font-icon ';
            if (typeof configuration.data.thresholds !== 'undefined' && configuration.data.thresholds.display === true) {
              icon += configuration.legend.icon.display ? ThresholdService.getFontIcon(d, configuration) : '';
            } else {
              if (configuration.legend.icon.display && d < configuration.legend.icon.minValue) {
                icon += 'icon-alert-circle';
              }
            }
            return icon;
          })
          .style('color', function(d) {
            if (typeof configuration.data.thresholds !== 'undefined' && configuration.data.thresholds.display === true) {
              return ThresholdService.getDataColor(d, configuration);
            } else {
              return ColorService.arkThresholdIcon();
            }
          });
      };

      TextService.prototype.showTextUpdate = function(configuration, widget, data) {
        var legend = widget.select('.ark-graphs-' + configuration.type + '-legend');
        var legendLines = legend.selectAll('div');
        legendLines.select('.font-icon').data(data)
          .attr('class', function(d) {
            var icon = 'font-icon ';
            if (typeof configuration.data.thresholds !== 'undefined' && configuration.data.thresholds.display === true) {
              icon += configuration.legend.icon.display ? ThresholdService.getFontIcon(d, configuration) : '';
            } else {
              if (configuration.legend.icon.display && d < configuration.legend.icon.minValue) {
                icon += 'icon-alert-circle';
              }
            }
            return icon;
          })
          .style('font-size', '16px')
          .style('top', function() {
            var base = 16;
            var current = configuration.legend.fontsize;
            var top = (current / base * 4);

            return configuration.type === 'spark-line' ? -top / 2 + 'px' : -top + 'px';
          })
          .style('color', function(d) {
            if (typeof configuration.data.thresholds !== 'undefined' && configuration.data.thresholds.display === true) {
              return ThresholdService.getDataColor(d, configuration);
            } else {
              return ColorService.arkThresholdIcon();
            }
          });
        legendLines.select('.data')
          .text(function(d, i) {
            return configuration.legend.format(data[i], i);
          });
      };

      TextService.prototype.showTextChart = function(configuration, widget, data) {
        if (!configuration.legend.display) {
          return;
        }

        var legend = widget.select('.ark-graphs-' + configuration.type + '-div')
          .append('div')
          .attr('class', 'ark-graphs-' + configuration.type + '-legend')
          .style('width', configuration.legend.width.toString() + 'px');

        legend.selectAll('div').data(data)
          .enter()
          .append('div')
          .attr('class', function(d, i) {
            return 'ark-graphs-' + configuration.type + '-legend-text ark-graphs-' + configuration.type + '-legend-text-' + i;
          })
          .style('display', 'inline-block');

        var legendLines = legend.selectAll('div');
        legendLines
          .append('div')
          .attr('class', 'color')
          .style('background-color', function(d, i) {
            return configuration.data.colors[i];
          });

        legendLines
          .append('text')
          .style('padding-left', '8px')
          .style('padding-right', '8px')
          .text(function(d, i) {
            return configuration.legend.title[i];
          });

      };

      return new TextService();
    }
  ]);

'use strict';

angular.module('ark.graphs.common')
  .service('ark.graphs.threshold-service', ['ark.graphs.d3',
    function(d3) {
      var ThresholdService = function() {};

      ThresholdService.prototype.isBelowThreshold = function(data, configuration) {
        var i = this.findRegion(data, configuration);
        if (i === configuration.data.thresholds.values.length) {
          return false;
        }
        return true;
      };

      ThresholdService.prototype.findRegion = function(data, configuration) {
        var comparator = configuration.data.thresholds.comparator;
        var i = 0;
        for (i = 0; i < configuration.data.thresholds.values.length; i++) {
          if (comparator(data, configuration.data.thresholds.values[i])) {
            return i;
          }
        }
        return i;
      };

      ThresholdService.prototype.getDataColor = function(data, configuration) {
        var i = this.findRegion(data, configuration);
        return configuration.data.thresholds.statusColors[i];
      };

      ThresholdService.prototype.getFontIcon = function(data, configuration) {
        var i = this.findRegion(data, configuration);
        return configuration.fontIcons[i];
      };

      ThresholdService.prototype.getMiddleIcon = function(configuration, data) {
        d3.select('#' + configuration.id).select('.ark-graphs-' + configuration.type + '-span')
          .attr('class', (this.getFontIcon(data, configuration) === '') ? 'ark-graphs-' + configuration.type + '-span icon-alert-circle' : 'ark-graphs-' + configuration.type + '-span ' + this.getFontIcon(data, configuration))
          .style('opacity', (this.getFontIcon(data, configuration) === '') ? '0' : '1')
          .style('color', this.getDataColor(data, configuration));
      };

      ThresholdService.prototype.drawThresholds = function(configuration, arrangedData) {
        angular.forEach(arrangedData, function(value, key) {
          var thresholds = d3.select('#' + configuration.id).select('.ark-graphs-' + configuration.type + '-threshold').selectAll('.path-' + key.toString());
          thresholds.data(configuration.data.thresholds.values, function(d) {
              return d + Math.random() / 1000;
            })
            .enter()
            .append('path')
            .attr('class', 'path-' + key.toString() + ' ark-graphs-' + configuration.type + '-threshold-path-' + key.toString())
            .attr('opacity', configuration.data.thresholds.opacity)
            .attr('stroke-width', configuration.data.thresholds.strokeWidth)
            .transition()
            .attrTween('stroke', function(d, i) {
              var color;
              if (d < arrangedData[key]) {
                color = configuration.data.thresholds.barColorOver;
              } else {
                color = configuration.data.thresholds.barColor;
              }
              var interpolate = d3.interpolate(configuration.currentThresholdColors[key][i], color);
              configuration.currentThresholdColors[key][i] = color;
              return function(t) {
                return interpolate(t);
              };
            })
            .duration(configuration.transitions.thresholds);
          thresholds.remove();
        });
      };

      ThresholdService.prototype.initThresholdValues = function(configuration) {
        configuration.fontIcons = ['icon-alert-circle', 'icon-alert-triangle', '', 'icon-alert-checkmark'];
        configuration.fontIcons = configuration.fontIcons.slice(0, configuration.data.thresholds.values.length);
        configuration.fontIcons.push('icon-alert-checkmark');
        configuration.currentThresholdColors = [];

        var length = configuration.numberOfData ? configuration.numberOfData : 1;

        for (var i = 0; i < length; i++) {
          var tmp = [];
          for (var j = 0; j < configuration.data.thresholds.values.length; j++) {
            tmp.push(configuration.data.thresholds.color);
          }
          configuration.currentThresholdColors.push(tmp);
        }
      };

      return new ThresholdService();

    }
  ]);

'use strict';

angular.module('ark.graphs.common')
  .service('ark.graphs.tooltip-service', ['ark.graphs.d3',
    function(d3) {
      var TooltipService = function() {};

      TooltipService.prototype.initTooltip = function(scope, type) {
        if (scope.tooltip) {
          d3.select('#tooltip-' + scope.internalConfiguration.id)
            .remove();
        }
        scope.tooltip = d3.tip(scope.internalConfiguration.id)
          .attr('id', 'tooltip-' + scope.internalConfiguration.id)
          .attr('class', 'ark-graphs-' + type + '-tooltip ark-graphs-tooltip')
          .offset([10, 10])
          .html(scope.internalConfiguration.tooltip.format);
        scope.widget.select('.ark-graphs-' + type + '-svg').call(scope.tooltip);

      };

      TooltipService.prototype.showTooltip = function(tooltip) {
        tooltip.show.apply(this, Array.prototype.slice.call(arguments, 1));
      };

      TooltipService.prototype.setCoordinates = function(tooltip, pageX, pageY) {
        tooltip.coordinate({
          x: pageX,
          y: pageY
        });
      };

      TooltipService.prototype.hideTooltip = function(tooltip) {
        tooltip.hide();
      };

      return new TooltipService();
    }
  ]);

'use strict';

angular.module('ark.graphs.common')
  .service('ark.graphs.utils', function() {
    var Utils = function() {};

    Utils.prototype.prepareData = function(data, previousData, configuration) {
      var tmp;
      if (previousData.length > configuration.numberOfData) {
        previousData = previousData.slice(0, configuration.numberOfData);
      }
      if (typeof data === 'object') {
        if (data.length === configuration.numberOfData) {
          return data;
        } else {
          tmp = angular.copy(previousData);
          for (var i = 0; i < data.length; i++) {
            tmp.unshift(data);
          }
          tmp = tmp.slice(0, configuration.numberOfData);
          return tmp;
        }
      } else {
        tmp = angular.copy(previousData);
        tmp.unshift(data);
        tmp = tmp.slice(0, configuration.numberOfData);
        return tmp;
      }
    };

    Utils.prototype.generateID = function(type) {
      var id = '';
      var possible = 'abcdef0123456789';

      for (var i = 0; i < 16; i++) {
        id += possible.charAt(Math.floor(Math.random() * possible.length));
      }

      return type + '-' + id;
    };

    Utils.prototype.mergeRecursive = function(obj1, obj2) {
      for (var p in obj2) {
        try {
          obj1[p] = (obj2[p].constructor === Object) ? this.mergeRecursive(obj1[p], obj2[p]) : obj2[p];
        } catch (e) {
          obj1[p] = obj2[p];
        }
      }
      return obj1;
    };

    Utils.prototype.getTrueWidth = function(element) {
      var computedStyles = getComputedStyle(element);
      var width = parseInt(computedStyles.width, 10);
      var paddingLeft = parseInt(computedStyles.paddingLeft, 10);
      var paddingRight = parseInt(computedStyles.paddingRight, 10);

      return width - paddingLeft - paddingRight;
    };

    Utils.prototype.resize = function(configuration, element) {
      var e = angular.element(element[0].parentElement);
      var trueWidth = this.getTrueWidth(e[0]);

      if (configuration.autosnap.enabled) {
        var tmpConfiguration;
        if (trueWidth < configuration.autosnap.threshold) {
          tmpConfiguration = configuration.autosnap.smallConfig;
        } else {
          tmpConfiguration = configuration.autosnap.largeConfig;
        }
        configuration = this.mergeRecursive(configuration, tmpConfiguration);
      } else {
        if (configuration.type !== 'spark-line') {
          configuration.svg.width = trueWidth;
        } else {
          configuration.div.width = trueWidth;
        }
      }
      configuration.update(configuration);
    };

    return new Utils();
  });

'use strict';

angular.module('ark.graphs.bar')
  .directive('arkBar', ['ark.graphs.bar-config', 'ark.graphs.line-service',
    'ark.graphs.text-service', 'ark.graphs.d3', 'ark.graphs.utils', 'ark.graphs.tooltip-service',
    'ark.graphs.threshold-service', 'ark.graphs.config-service',
    function(BarConfiguration, LineService, TextService, d3, Utils, TooltipService, ThresholdService, ConfigService) {
      return {
        restrict: 'E',
        scope: {
          configuration: '=',
          data: '='
        },
        link: function($scope, element) {
          $scope.internalConfiguration = new BarConfiguration($scope.configuration);
          $scope.previousData = $scope.internalConfiguration.initialValues;

          $scope.draw = function(data) {
            //Prepare data, adds in previous values of data if required
            $scope.arrangedData = Utils.prepareData(angular.copy(data), $scope.previousData, $scope.internalConfiguration);

            //Draw bars
            var paths = $scope.widget.select('.ark-graphs-bar-container').selectAll('path');
            paths.data($scope.arrangedData, function(d) {
                return d + Math.random() / 1000;
              })
              .enter()
              .append('path')
              .attr('class', 'path')
              .attr('stroke', function(d) {
                return ThresholdService.getDataColor(d, $scope.internalConfiguration);
              })
              .attr('transform', function(d, i) {
                return ['translate(', 0, $scope.internalConfiguration.svg.height * i, ')'].join(' ');
              })
              .attr('stroke-width', $scope.internalConfiguration.strokeWidth)
              .attr('height', $scope.internalConfiguration.strokeWidth / 2)
              .attr('width', $scope.internalConfiguration.svg.width)
              .attr('opacity', 1)
              .transition()
              .attrTween('d', function(d, i) {
                var interpolate = d3.interpolate($scope.previousData[i], $scope.arrangedData[i]);
                if ($scope.internalConfiguration.tooltip.display) {
                  TooltipService.hideTooltip($scope.tooltip);
                }
                return function(t) {
                  var y = (0 + $scope.internalConfiguration.strokeWidth) / 2;
                  var x = (interpolate(t) / $scope.internalConfiguration.max) * $scope.internalConfiguration.svg.width;
                  return LineService.computeLine(0, y, x, y);
                };
              })
              .duration($scope.internalConfiguration.transitions.bar)
              .each('end', function() {
                $scope.allowUpdate($scope.arrangedData);
              });
            paths.remove();

            //Draw thesholds and gauge fonticon
            if ($scope.internalConfiguration.data.thresholds.display) {
              ThresholdService.drawThresholds($scope.internalConfiguration, $scope.arrangedData);
              angular.forEach($scope.arrangedData, function(value, key) {
                var thresholds = $scope.widget.select('.ark-graphs-bar-threshold').selectAll('.path-' + key.toString());
                thresholds.attr('d', function(d) {
                    var x = (d / $scope.internalConfiguration.max) * $scope.internalConfiguration.svg.width;
                    return LineService.computeLine(x, 0, x, $scope.internalConfiguration.strokeWidth);
                  })
                  .attr('transform', ['translate(', 0, $scope.internalConfiguration.svg.height * key, ')'].join(' '));
              });
            }

            //Draw legend
            if ($scope.internalConfiguration.legend.display) {
              TextService.showTextUpdate($scope.internalConfiguration, $scope.widget, $scope.arrangedData);
            }
          };

          //When bar stops transitioning, allow mouse events
          $scope.allowUpdate = function(data) {
            var selection = $scope.widget.select('.ark-graphs-bar-container').selectAll('path');
            selection
              .on('mousemove', function(d, i) {
                $scope.coordinate = d3.mouse($scope.widget.select('.ark-graphs-bar-container')[0][0]);
                $scope.mousemovePath(d, i, this);
              })
              .on('mouseout', function(d, i) {
                $scope.mouseoutPath(i, this);
              });
            $scope.previousData = angular.copy(data);
          };

          $scope.mousemovePath = function(d, i, elem) {
            if ($scope.internalConfiguration.hover.apply) {
              d3.select(elem).transition()
                .duration(200)
                .attr('stroke-width', $scope.internalConfiguration.hover.growBy + $scope.internalConfiguration.strokeWidth);
              if ($scope.internalConfiguration.data.thresholds.display) {
                $scope.widget.select('.ark-graphs-bar-threshold').selectAll('.ark-graphs-bar-threshold-path-' + i.toString())
                  .attr('d', function(d) {
                    var x = (d / $scope.internalConfiguration.max) * $scope.internalConfiguration.svg.width;
                    return LineService.computeLine(x, -($scope.internalConfiguration.hover.growBy / 2), x, $scope.internalConfiguration.strokeWidth + $scope.internalConfiguration.hover.growBy / 2);
                  });
              }
            }
            if ($scope.internalConfiguration.tooltip.display) {
              TooltipService.setCoordinates($scope.tooltip, $scope.coordinate[0], $scope.coordinate[1]);
              TooltipService.showTooltip($scope.tooltip, d, i, ThresholdService.getDataColor(d, $scope.internalConfiguration), ConfigService.getData(i, $scope.internalConfiguration.data.labels));
            }
          };

          $scope.mouseoutPath = function(i, elem) {
            if ($scope.internalConfiguration.hover.apply) {
              d3.select(elem).transition()
                .duration(200)
                .attr('stroke-width', $scope.internalConfiguration.strokeWidth);
              if ($scope.internalConfiguration.data.thresholds.display) {
                $scope.widget.select('.ark-graphs-bar-threshold').selectAll('.ark-graphs-bar-threshold-path-' + i.toString())
                  .attr('d', function(d) {
                    var x = (d / $scope.internalConfiguration.max) * $scope.internalConfiguration.svg.width;
                    return LineService.computeLine(x, 0, x, $scope.internalConfiguration.strokeWidth);
                  });
              }
            }
            if ($scope.internalConfiguration.tooltip.display) {
              TooltipService.hideTooltip($scope.tooltip);
            }
          };

          $scope.init = function() {
            $scope.widget = d3.select(element[0]);
            $scope.widget.selectAll('*').remove();

            //Prepare data, adds in previous values of data if required
            $scope.arrangedData = Utils.prepareData(angular.copy($scope.data), $scope.previousData, $scope.internalConfiguration);

            //Main bar widget container
            $scope.widget.append('div')
              .attr('class', 'ark-graphs-bar-div')
              .attr('id', $scope.internalConfiguration.id)
              .style('position', 'relative')
              .style('white-space', 'nowrap')
              .style('width', $scope.internalConfiguration.div.width.toString() + 'px')
              .style('height', ($scope.internalConfiguration.div.height.toString()) + 'px');

            //SVG portion of widget
            $scope.widget.select('.ark-graphs-bar-div')
              .append('svg')
              .attr('class', 'ark-graphs-bar-svg')
              .attr('width', $scope.internalConfiguration.svg.width)
              .attr('height', $scope.internalConfiguration.svg.height * $scope.internalConfiguration.numberOfData);

            $scope.widget.select('.ark-graphs-bar-svg')
              .append('g')
              .attr('class', 'ark-graphs-bar-svg-inner')
              .attr('transform', ['translate(', 0, ',', $scope.internalConfiguration.div.padding.top, ')'].join(' '));

            //Draw background bar/line
            if ($scope.internalConfiguration.background.display) {
              var y = ($scope.internalConfiguration.strokeWidth) / 2;
              angular.forEach($scope.arrangedData, function(value, key) {
                $scope.widget.select('.ark-graphs-bar-svg-inner')
                  .append('g')
                  .attr('class', 'ark-graphs-bar-line')
                  .append('path')
                  .attr('stroke', $scope.internalConfiguration.background.color.toString())
                  .attr('transform', ['translate(', 0, $scope.internalConfiguration.svg.height * key, ')'].join(' '))
                  .attr('stroke-width', $scope.internalConfiguration.background.strokeWidth.toString())
                  .attr('d', LineService.computeLine(0, y, $scope.internalConfiguration.svg.width, y));
              });
            }

            //Bar container for drawing/updating bars
            $scope.widget.select('.ark-graphs-bar-svg-inner')
              .append('g')
              .attr('class', 'ark-graphs-bar-container');

            //Threshold container for drawing/updating thresholds
            if ($scope.internalConfiguration.data.thresholds.display) {
              $scope.widget.select('.ark-graphs-bar-svg-inner')
                .append('g')
                .attr('class', 'ark-graphs-bar-threshold');
              ThresholdService.initThresholdValues($scope.internalConfiguration);
            }

            //Draw initial legend
            if ($scope.internalConfiguration.legend.display) {
              //TextService.showText($scope.internalConfiguration, $scope.widget, $scope.arrangedData);
            }

            if ($scope.internalConfiguration.legend.display) {
              TextService.showText($scope.internalConfiguration, $scope.widget, $scope.arrangedData);
            }

            //Initalizes tooltip
            if ($scope.internalConfiguration.tooltip.display) {
              TooltipService.initTooltip($scope, 'bar');
            }
          };

          if ($scope.internalConfiguration.autoresize) {
            Utils.resize($scope.internalConfiguration, element);
          }

          $scope.init();

          //Check for resizing
          $scope.$watch(function() {
            var e = angular.element(element[0].parentElement);
            return Utils.getTrueWidth(e[0]);
          }, function() {
            if ($scope.internalConfiguration.autoresize) {
              Utils.resize($scope.internalConfiguration, element);
              $scope.init();
              $scope.draw($scope.data);
            }
          }, true);

          //Check for changes in internalConfiguration
          $scope.$watch('configuration', function() {
            $scope.internalConfiguration.update($scope.configuration);
            $scope.init();
            $scope.draw($scope.data);
          }, true);

          //Check for changes in data
          $scope.$watch('data', function(newVals) {
            if (newVals !== undefined) {
              return $scope.draw(newVals);
            }
          });
        }
      };
    }
  ]);

'use strict';

angular.module('ark.graphs.bar')
  .factory('ark.graphs.bar-config', ['ark.graphs.color-service', 'ark.graphs.utils', 'ark.graphs.config-service',
    function(ColorService, Utils, ConfigService) {
      var BarConfiguration = function(configuration) {
        this.type = 'bar';
        this.id = Utils.generateID(this.type);
        this.initialValues = [];
        this.max = 100;
        this.strokeWidth = 7;
        this.numberOfDataSet = 1;
        this.numberOfData = this.numberOfDataSet;
        this.autoresize = false; //If set to true, given divWidth will not be taken into account

        this.svg = {
          height: 14,
          width: 208,
          padding: {
            top: 2
          },
          dataGap: 5
        };

        this.legend = {
          display: true,
          fontsize: 12,
          height: 26,
          width: this.svg.width,
          title: ['Metric name'],
          format: function(d, i) {
            return d;
          },
          letters: {
            display: true
          },
          padding: {
            top: -6,
            left: 0,
            right: 20
          },
          icon: {
            display: true,
            minValue: 40
          }
        };

        this.data = {
          labels: ['data 0'],
          thresholds: {
            display: true,
            values: [75],
            strokeWidth: 1,
            opacity: 1,
            statusColors: ColorService.getStatusColors(2),
            barColorOver: '#FFFFFF',
            barColor: '#C4CDD6',
            comparator: function(value, threshold) {
              return value < threshold;
            }
          }
        };

        this.tooltip = {
          display: true,
          format: function(value, index, color, name) {
            return '<table class="ark-graphs-bar-tooltip"><tbody><tr class="ark-graphs-bar-tooltip-name-data"><td class="name"><span class="ark-graphs-bar-tooltip-square" style="background-color: ' + color + ';"></span><text class="name-container">' + name + '</text></td><td class="value">' + value + '</td></tr></tbody></table>';
          }
        };

        this.background = {
          display: true,
          color: '#E3E9EF',
          strokeWidth: 1
        };

        this.hover = {
          apply: true,
          growBy: 2
        };

        this.transitions = {
          bar: 1000,
          thresholds: 1000
        };

        this.autosnap = {
          enabled: false,
          threshold: 516,
          smallConfig: {
            svg: {
              width: 208
            }
          },
          largeConfig: {
            svg: {
              width: 516
            }
          }
        };

        this.update(configuration);
      };

      BarConfiguration.prototype.update = function(configuration) {
        Utils.mergeRecursive(this, configuration);

        this.legend.width = this.svg.width;
        this.div = {
          width: this.svg.width,
          height: (this.svg.height + (this.legend.display ? this.legend.height : 0)) * this.numberOfData,
          padding: {
            top: this.svg.padding.top
          }
        };
        this.dataGap = (this.svg.height - this.strokeWidth * this.numberOfData) / this.numberOfData;

        ConfigService.getStatusColors(this);
        ConfigService.updateInitialValues(this);
        ConfigService.updateLegendLabels(this);
        ConfigService.updateTooltipLabels(this);
      };

      return BarConfiguration;
    }
  ]);

'use strict';

angular.module('ark.graphs.donut')
  .directive('arkDonut', ['ark.graphs.donut-chart-config', 'ark.graphs.arc-service',
    'ark.graphs.pie-service', 'ark.graphs.text-service', 'ark.graphs.d3', 'ark.graphs.utils',
    'ark.graphs.tooltip-service', 'ark.graphs.config-service',
    function(DonutConfiguration, ArcService, PieService, TextService, d3, Utils, TooltipService, ConfigService) {
      return {
        restrict: 'E',
        scope: {
          configuration: '=',
          data: '='
        },
        link: function($scope, element) {
          $scope.internalConfiguration = new DonutConfiguration($scope.configuration, $scope.data);
          $scope.previousData = $scope.internalConfiguration.initialValues;

          angular.forEach($scope.data, function() {
            $scope.previousData.push(0);
          });
          $scope.draw = function(data) {
            var paths = $scope.widget.select('.ark-graphs-donut-container').selectAll('path');

            var arc = ArcService.d3Arc($scope.internalConfiguration.radius, $scope.internalConfiguration.strokeWidth);
            var arcOver = ArcService.d3Arc($scope.internalConfiguration.radius + $scope.internalConfiguration.slice.hover.growBy, $scope.internalConfiguration.strokeWidth + $scope.internalConfiguration.slice.hover.growBy);

            var pie = ArcService.d3Pie($scope.internalConfiguration.amplitude, $scope.internalConfiguration.padAngle, $scope.internalConfiguration.sort);

            var previousPie = pie($scope.previousData);

            if ($scope.internalConfiguration.slice.label.display) {
              PieService.drawLabels($scope.widget, pie(data), $scope.internalConfiguration);
            }

            paths.data(pie(data), function(d) {
                return d + Math.random() / 10000;
              })
              .enter()
              .append('path')
              .attr('class', 'path')
              .attr('fill', function(d, i) {
                return $scope.internalConfiguration.data.colors[i];
              })
              .attr('stroke', $scope.internalConfiguration.slice.border.color)
              .attr('stroke-width', ($scope.internalConfiguration.slice.border.display ? $scope.internalConfiguration.slice.border.width : 0))
              .attr('opacity', $scope.internalConfiguration.opacity)
              .attr('transform',
                ArcService.computeRotation(
                  $scope.internalConfiguration.startAngle,
                  $scope.internalConfiguration.svg.width,
                  $scope.internalConfiguration.svg.height
                ) + ' ' +
                ArcService.translate(
                  $scope.internalConfiguration.svg.width,
                  $scope.internalConfiguration.svg.height
                ))
              .on('click', $scope.internalConfiguration.slice.click)
              .transition()
              .attrTween('d', function(d, i) {
                TooltipService.hideTooltip($scope.tooltip);
                var previous = previousPie[i] || {
                  startAngle: 0,
                  endAngle: 0
                };
                var interpolate = d3.interpolate(previous, d);
                return function(t) {
                  return arc(interpolate(t));
                };
              })
              .duration($scope.internalConfiguration.transitions.arc)
              .each('end', function() {
                $scope.allowUpdate(data, arc, arcOver);
              });
            paths.remove();
            $scope._updateLabels(data);
            TextService.showTextUpdate($scope.internalConfiguration, $scope.widget, $scope.data);
          };

          $scope.allowUpdate = function(data, arc, arcOver) {
            var selection = $scope.widget.select('.ark-graphs-donut-container').selectAll('path');
            selection
              .on('mousemove', function(d, i) {
                $scope.coordinate = d3.mouse($scope.widget.select('.ark-graphs-donut-container')[0][0]);
                $scope.mousemovePath(d, i, this, arcOver);
              })
              .on('mouseout', function() {
                $scope.mouseoutPath(this, arc);
              });
            $scope.previousData = angular.copy(data);
          };

          $scope.setMiddleLabelFont = function(fontsize) {
            $scope.internalConfiguration.label.fontsize = fontsize;
          };

          $scope.setMiddleLabel = function() {
            //Middle label
            $scope.widget.select('.ark-graphs-donut-svg').select('g').select('text')
              .attr('font-size', $scope.internalConfiguration.label.fontsize + 'px');
          };

          $scope._updateLabels = function(data) {
            if ($scope.internalConfiguration.label.display) {
              $scope.widget.select('.ark-graphs-donut-middle-label').select('text')
                .attr('opacity', 0.2)
                .transition()
                .duration($scope.internalConfiguration.transitions.label)
                .attr('opacity', 1)
                .text($scope.internalConfiguration.label.format(data));
              if ($scope.internalConfiguration.label.symbol.display) {
                $scope.widget.select('.ark-graphs-donut-middle-label-symbol').select('text')
                  .attr('opacity', 0.2)
                  .transition()
                  .duration($scope.internalConfiguration.transitions.label)
                  .attr('opacity', 1)
                  .text($scope.internalConfiguration.label.symbol.format(data));
              }
            }
          };

          $scope.mousemovePath = function(d, i, elem, arcOver) {
            if ($scope.internalConfiguration.slice.hover.apply) {
              d3.select(elem).transition()
                .duration(50)
                .attr('d', arcOver);
            }
            if ($scope.internalConfiguration.tooltip.display) {
              TooltipService.setCoordinates($scope.tooltip, $scope.coordinate[0], $scope.coordinate[1]);
              TooltipService.showTooltip($scope.tooltip, d, i, ConfigService.getData(i, $scope.internalConfiguration.data.colors), ConfigService.getData(i, $scope.internalConfiguration.data.labels));
            }
          };

          $scope.mouseoutPath = function(elem, arc) {
            if ($scope.internalConfiguration.slice.hover.apply) {
              d3.select(elem).transition()
                .duration(50)
                .attr('d', arc);
            }
            if ($scope.internalConfiguration.tooltip.display) {
              TooltipService.hideTooltip($scope.tooltip);
            }
          };

          $scope.init = function() {
            $scope.widget = d3.select(element[0]);
            $scope.widget.selectAll('*').remove();

            $scope.widget.append('div')
              .attr('class', 'ark-graphs-donut-div')
              .attr('id', $scope.internalConfiguration.id)
              .style('position', 'relative')
              .style('white-space', 'nowrap')
              .style('width', $scope.internalConfiguration.div.width.toString() + 'px')
              .style('height', $scope.internalConfiguration.div.height.toString() + 'px')
              .style('padding-top', $scope.internalConfiguration.div.padding.top.toString() + 'px');

            $scope.widget.select('.ark-graphs-donut-div').append('svg')
              .attr('class', 'ark-graphs-donut-svg')
              .attr('width', $scope.internalConfiguration.svg.width)
              .attr('height', $scope.internalConfiguration.svg.height);

            if ($scope.internalConfiguration.label.display) {
              //Middle label
              $scope.widget.select('.ark-graphs-donut-svg').append('g')
                .attr('class', 'ark-graphs-donut-middle-label')
                .append('text')
                .text($scope.internalConfiguration.label.format(0))
                .attr('x', $scope.internalConfiguration.svg.width / 2)
                .attr('y', $scope.internalConfiguration.svg.height / 2)
                .attr('opacity', $scope.internalConfiguration.label.opacity)
                .attr('font-size', $scope.internalConfiguration.label.fontsize + 'px')
                .attr('fill', $scope.internalConfiguration.label.color)
                .style('dominant-baseline', 'middle')
                .style('text-anchor', 'middle');
              if ($scope.internalConfiguration.label.symbol.display) {
                $scope.widget.select('.ark-graphs-donut-svg').append('g')
                  .attr('class', 'ark-graphs-donut-middle-label-symbol')
                  .append('text')
                  .text($scope.internalConfiguration.label.symbol.format(0))
                  .attr('x', $scope.internalConfiguration.svg.width / 2)
                  .attr('y', $scope.internalConfiguration.svg.height / 2 + $scope.internalConfiguration.label.fontsize)
                  .attr('opacity', $scope.internalConfiguration.label.symbol.opacity)
                  .attr('font-size', $scope.internalConfiguration.label.symbol.fontsize + 'px')
                  .attr('fill', $scope.internalConfiguration.label.symbol.color)
                  .style('text-anchor', 'middle');
              }
            }

            //Main widget content
            $scope.widget.select('.ark-graphs-donut-svg').append('g')
              .attr('class', 'ark-graphs-donut-container');

            $scope.widget.select('.ark-graphs-donut-svg').append('g')
              .attr('class', 'ark-graphs-label-group')
              .attr('transform', ArcService.translate(
                $scope.internalConfiguration.svg.width,
                $scope.internalConfiguration.svg.height
              ));

            TextService.showText($scope.internalConfiguration, $scope.widget, $scope.data);

            TooltipService.initTooltip($scope, 'donut');
          };

          $scope.resize = function() {
            Utils.resize($scope.internalConfiguration, element);
            $scope.init();
            $scope.draw($scope.data);
          };

          if ($scope.internalConfiguration.autoresize) {
            Utils.resize($scope.internalConfiguration, element);
          }

          $scope.init();

          //Check for resizing
          $scope.$watch(function() {
            var e = angular.element(element[0].parentElement);
            return Utils.getTrueWidth(e[0]);
          }, function() {
            if ($scope.internalConfiguration.autoresize) {
              Utils.resize($scope.internalConfiguration, element);
              $scope.init();
              $scope.previousData = angular.copy($scope.data);
              $scope.draw($scope.data);
            }
          }, true);

          //Check for text overflow
          $scope.$watch(function() {
            var a = element[0].querySelector('.ark-graphs-donut-middle-label text');
            if (a === null) {
              return $scope.internalConfiguration.radius * 2;
            }
            return a.getBoundingClientRect().width;
          }, function(newVal) {
            if (newVal > $scope.internalConfiguration.radius * 2 * 0.7) { // text is greater than 0.7 of donut diameter
              $scope.setMiddleLabelFont($scope.internalConfiguration.label.fontsize / 2);
              $scope.setMiddleLabel();
            }

            if ($scope.internalConfiguration.label.maxFontsize > $scope.internalConfiguration.label.fontsize) {
              if (newVal < $scope.internalConfiguration.radius * 2 * 0.6) { // text is less than 0.6 of donut diameter
                $scope.setMiddleLabelFont($scope.internalConfiguration.label.fontsize * 1.5);
                $scope.setMiddleLabel();
              }
            }
          });

          //Check for changes in internalConfiguration
          $scope.$watch('configuration', function() {
            $scope.internalConfiguration.update($scope.configuration);
            $scope.init();
            $scope.draw($scope.data);
          }, true);

          $scope.$watch('data', function(newVals) {
            return $scope.draw(newVals);
          });
        }
      };
    }
  ]);

'use strict';

angular.module('ark.graphs.donut')
  .factory('ark.graphs.donut-chart-config', ['ark.graphs.d3', 'ark.graphs.color-service',
    'ark.graphs.utils', 'ark.graphs.config-service',
    function(d3, ColorService, Utils, ConfigService) {
      var DonutConfiguration = function(configuration, data) {
        this.type = 'donut';
        this.id = Utils.generateID(this.type);
        this.startAngle = 0;
        this.strokeWidth = 8;
        this.amplitude = 360;
        this.padAngle = 0.75;
        this.radius = 69;
        this.opacity = 1;
        this.initialValues = [];
        this.sort = null;
        this.autoresize = false;
        this.numberOfDataSet = data.length;
        this.numberOfData = this.numberOfDataSet;

        this.svg = {
          height: this.radius * 2 + this.strokeWidth / 2 + 26,
          width: 208,
          padding: {
            top: 0
          }
        };

        this.legend = {
          display: true,
          fontsize: 12,
          height: 72,
          width: this.svg.width,
          title: ['Metric name'],
          format: function(d, i) {
            return d;
          },
          letters: {
            display: true
          },
          padding: {
            top: 0,
            left: 20,
            right: 20
          },
          icon: {
            display: true,
            minValue: 3
          }
        };

        this.data = {
          colors: ColorService.arkBlueColors(),
          labels: ['data 0']
        };

        this.tooltip = {
          display: true,
          format: function(value, index, color, name) {
            return '<table class="ark-graphs-donut-tooltip"><tbody><tr class="ark-graphs-donut-tooltip-name-data"><td class="name"><span class="ark-graphs-donut-tooltip-square" style="background-color: ' + color + ';"></span><text class="name-container">' + name + '</text></td><td class="value">' + value.data + '</td></tr></tbody></table>';
          }
        };

        this.slice = {
          border: {
            display: true,
            color: '#FFFFFF',
            width: 1
          },
          label: {
            position: 'out',
            display: true,
            line: {
              display: false,
              size: 0,
              color: 'gray',
              class: 'ark-graphs-donut-label-line'
            },
            value: {
              display: false,
              fontsize: 12,
              color: 'gray',
              class: 'ark-graphs-donut-label-value',
              format: function(value) {

                return value.data;
              }
            },
            name: {
              topOffset: 2,
              fontsize: 11,
              color: '#444A52',
              class: 'ark-graphs-donut-label-name',
              format: function(d, i) {
                var chr = String.fromCharCode(i + 65);
                return chr;
              }
            }
          },
          hover: {
            apply: false,
            callback: function() {},
            growBy: 4
          },
          click: function() {}
        };
        this.label = {
          display: true,
          fontsize: 32,
          maxFontsize: 32,
          color: 'black',
          format: function(values) {
            return d3.sum(values);
          },
          opacity: 1,
          symbol: {
            display: true,
            fontsize: 20,
            color: 'black',
            format: function() {
              return '';
            },
            opacity: 1
          }
        };
        this.transitions = {
          arc: 1000,
          label: 500
        };

        this.autosnap = {
          enabled: false,
          threshold: 516,
          smallConfig: {
            radius: 69,
            svg: {
              width: 208
            },
            strokeWidth: 8,
            slice: {
              label: {
                name: {
                  fontsize: 12
                }
              }
            },
            label: {
              fontsize: 32,
              maxFontsize: 32
            },
            legend: {
              fontsize: 12,
              height: 72,
              width: 208,
              padding: {
                top: 0,
                left: 20,
                right: 20
              }
            }
          },
          largeConfig: {
            radius: 124,
            svg: {
              width: 516
            },
            strokeWidth: 12,
            slice: {
              label: {
                name: {
                  fontsize: 14
                }
              }
            },
            label: {
              fontsize: 48,
              maxFontsize: 48
            },
            legend: {
              fontsize: 14,
              height: 160,
              width: 260,
              padding: {
                top: 20,
                left: 24,
                right: 24
              }
            }
          }
        };

        this.update(configuration);
      };

      DonutConfiguration.prototype.update = function(configuration) {
        Utils.mergeRecursive(this, configuration);

        this.svg.height = this.radius * 2 + this.strokeWidth / 2 + 26;
        this.div = {
          width: this.svg.width,
          height: this.svg.height + (this.legend.display ? this.legend.height : 0),
          padding: {
            top: this.svg.padding.top
          }
        };

        ConfigService.updateColors(this);
        ConfigService.updateInitialValues(this);
        ConfigService.updateLegendLabels(this);
        ConfigService.updateTooltipLabels(this);
      };

      return DonutConfiguration;
    }
  ]);

'use strict';

angular.module('ark.graphs.gauge')
  .directive('arkCircularGauge', ['ark.graphs.gauge-config', 'ark.graphs.arc-service',
    'ark.graphs.text-service', 'ark.graphs.d3', 'ark.graphs.utils',
    'ark.graphs.tooltip-service', 'ark.graphs.threshold-service', 'ark.graphs.config-service',
    function(GaugeConfiguration, ArcService, TextService, d3, Utils, TooltipService, ThresholdService, ConfigService) {
      return {
        restrict: 'E',
        scope: {
          configuration: '=',
          data: '='
        },
        link: function($scope, element) {
          $scope.internalConfiguration = new GaugeConfiguration($scope.configuration);
          $scope.previousData = $scope.internalConfiguration.initialValues;

          var toggle = false;
          $scope.draw = function(data) {
            toggle = false;
            $scope.arrangedData = Utils.prepareData(angular.copy(data), $scope.previousData, $scope.internalConfiguration);
            var paths = $scope.widget.select('.ark-graphs-gauge-container').selectAll('path');
            paths.data($scope.arrangedData, function(d) {
                return d + Math.random() / 1000;
              })
              .enter()
              .append('path')
              .attr('class', 'path')
              .attr('fill', 'none')
              .attr('transform', ArcService.computeRotation(
                $scope.internalConfiguration.startAngle,
                $scope.internalConfiguration.svg.width,
                $scope.internalConfiguration.svg.height
              ))
              .attr('stroke', function(d) {
                return ThresholdService.getDataColor(d, $scope.internalConfiguration);
              })
              .attr('stroke-width', $scope.internalConfiguration.strokeWidth)
              .attr('opacity', 1)
              .transition()
              .attrTween('d', function(d, i) {
                toggle = true;
                TooltipService.hideTooltip($scope.tooltip);
                var interpolate = d3.interpolate($scope.previousData[i], $scope.arrangedData[i]);
                return function(t) {
                  return ArcService.computeArc(
                    0,
                    $scope.internalConfiguration.amplitude,
                    interpolate(t),
                    $scope.internalConfiguration.max,
                    $scope.internalConfiguration.svg.width,
                    $scope.internalConfiguration.svg.height, $scope.internalConfiguration.computeGaugeWidth(d, i)
                  );
                };
              })
              .duration($scope.internalConfiguration.transitions.arc)
              .each('end', function() {
                $scope.allowUpdate($scope.arrangedData);
              });
            paths.remove();

            // display thesholds and middle fonticon
            if ($scope.internalConfiguration.data.thresholds.display) {
              ThresholdService.getMiddleIcon($scope.internalConfiguration, data);
              ThresholdService.drawThresholds($scope.internalConfiguration, $scope.arrangedData);
              angular.forEach($scope.arrangedData, function(value, key) {
                var thresholds = $scope.widget.select('.ark-graphs-gauge-threshold').selectAll('.path-' + key.toString());
                thresholds.attr('d', function(d) {
                    return ArcService.computeArc(
                      ($scope.internalConfiguration.amplitude * (d / $scope.internalConfiguration.max)) - $scope.internalConfiguration.data.thresholds.amplitude / 2, ($scope.internalConfiguration.amplitude * (d / $scope.internalConfiguration.max)) + $scope.internalConfiguration.data.thresholds.amplitude / 2,
                      $scope.internalConfiguration.max,
                      $scope.internalConfiguration.max,
                      $scope.internalConfiguration.svg.width,
                      $scope.internalConfiguration.svg.height, $scope.internalConfiguration.computeGaugeWidth(d, key)
                    );
                  })
                  .attr('transform', ArcService.computeRotation(
                    $scope.internalConfiguration.startAngle,
                    $scope.internalConfiguration.svg.width,
                    $scope.internalConfiguration.svg.height
                  ));
              });
            }

            $scope._updateLabels($scope.arrangedData[0]);
            TextService.showTextUpdate($scope.internalConfiguration, $scope.widget, $scope.arrangedData);
          };

          $scope.allowUpdate = function(data) {

            var selection = $scope.widget.select('.ark-graphs-gauge-container').selectAll('path').data(data);
            toggle = false;
            selection
              .on('mousemove', function(d, i) {
                if (!toggle) {
                  toggle = true;
                  $scope.mouseoverPath(this, $scope.internalConfiguration.computeGaugeWidth(d, i), d, i);
                }
                $scope.coordinate = d3.mouse($scope.widget.select('.ark-graphs-gauge-container')[0][0]);
                $scope.mousemovePath(d, i);
              })
              .on('mouseout', function(d, i) {
                toggle = false;
                $scope.mouseoutPath(this, $scope.internalConfiguration.computeGaugeWidth(d, i), d, i);
              });
            $scope.previousData = angular.copy(data);
          };

          $scope.setMiddleLabelFont = function(fontsize) {
            $scope.internalConfiguration.label.fontsize = fontsize;
          };

          $scope.setMiddleLabel = function() {
            //Middle label
            $scope.widget.select('.ark-graphs-gauge-middle-label').select('text')
              .attr('font-size', $scope.internalConfiguration.label.fontsize + 'px');
          };

          $scope._updateLabels = function(data) {
            if ($scope.internalConfiguration.label.display) {
              $scope.widget.select('.ark-graphs-gauge-middle-label').select('text')
                .attr('opacity', 0.2)
                .transition()
                .duration($scope.internalConfiguration.transitions.label)
                .attr('opacity', 1)
                .text($scope.internalConfiguration.label.format(data));

              if ($scope.internalConfiguration.label.symbol.display) {
                $scope.widget.select('.ark-graphs-gauge-middle-label-symbol')
                  .text(data);
              }
              if ($scope.internalConfiguration.svg.icon.display) {
                $scope.widget.select('.ark-graphs-gauge-span')
                  .style('top', ($scope.internalConfiguration.svg.height / 1.55).toString() + 'px')
                  .style('font-size', ($scope.internalConfiguration.label.fontsize / 2).toString() + 'px')
                  .style('display', 'inline-block');
              }
            }
          };

          $scope.mouseoverPath = function(elem, gaugeWidth, d, i) {
            if ($scope.internalConfiguration.hover.apply) {
              var interpolateGaugeMiddle = d3.interpolate(gaugeWidth, gaugeWidth + $scope.internalConfiguration.hover.growBy / 2);
              var interpolateGaugeWidth = d3.interpolate($scope.internalConfiguration.strokeWidth, $scope.internalConfiguration.strokeWidth + $scope.internalConfiguration.hover.growBy);
              d3.select(elem).transition()
                .duration(200)
                .attrTween('d', function() {
                  return function(t) {
                    return ArcService.computeArc(
                      0,
                      $scope.internalConfiguration.amplitude,
                      d,
                      $scope.internalConfiguration.max,
                      $scope.internalConfiguration.svg.width,
                      $scope.internalConfiguration.svg.height,
                      interpolateGaugeMiddle(t)
                    );
                  };
                })
                .duration(200)
                .attrTween('stroke-width', function() {
                  return function(t) {
                    return interpolateGaugeWidth(t);
                  };
                });

              if ($scope.internalConfiguration.data.thresholds.display) {
                var thresholds = $scope.widget.select('.ark-graphs-gauge-threshold').selectAll('.ark-graphs-gauge-threshold-path-' + i.toString());
                thresholds
                  .transition()
                  .duration(200)
                  .attr('d', function(d) {
                    return ArcService.computeArc(
                      $scope.internalConfiguration.amplitude * (d / $scope.internalConfiguration.max) - $scope.internalConfiguration.data.thresholds.amplitude / 2,
                      $scope.internalConfiguration.amplitude * (d / $scope.internalConfiguration.max) + $scope.internalConfiguration.data.thresholds.amplitude / 2,
                      $scope.internalConfiguration.max,
                      $scope.internalConfiguration.max,
                      $scope.internalConfiguration.svg.width,
                      $scope.internalConfiguration.svg.height,
                      gaugeWidth + (($scope.arrangedData[i] > d) ? $scope.internalConfiguration.hover.growBy / 2 : 0)
                    );
                  })
                  .attrTween('stroke-width', function(d) {
                    var interpolateStrokeWidth = d3.interpolate($scope.internalConfiguration.strokeWidth, $scope.internalConfiguration.strokeWidth + $scope.internalConfiguration.hover.growBy);
                    return function(t) {
                      return ($scope.arrangedData[i] > d ? interpolateStrokeWidth(t) : $scope.internalConfiguration.strokeWidth);
                    };
                  });
              }
            }
          };

          $scope.mousemovePath = function(d, i) {
            if ($scope.internalConfiguration.tooltip.display) {
              TooltipService.setCoordinates($scope.tooltip, $scope.coordinate[0], $scope.coordinate[1]);
              TooltipService.showTooltip($scope.tooltip, d, i, ThresholdService.getDataColor(d, $scope.internalConfiguration), ConfigService.getData(i, $scope.internalConfiguration.data.labels));
            }
          };

          $scope.mouseoutPath = function(elem, gaugeWidth, d, i) {
            var interpolateGaugeMiddle = d3.interpolate(gaugeWidth + $scope.internalConfiguration.hover.growBy / 2, gaugeWidth);
            var interpolateGaugeWidth = d3.interpolate($scope.internalConfiguration.strokeWidth + $scope.internalConfiguration.hover.growBy, $scope.internalConfiguration.strokeWidth);
            if ($scope.internalConfiguration.hover.apply) {
              d3.select(elem).transition()
                .duration(200)
                .attrTween('d', function() {
                  return function(t) {
                    return ArcService.computeArc(
                      0,
                      $scope.internalConfiguration.amplitude,
                      d,
                      $scope.internalConfiguration.max,
                      $scope.internalConfiguration.svg.width,
                      $scope.internalConfiguration.svg.height,
                      interpolateGaugeMiddle(t)
                    );
                  };
                })
                .attrTween('stroke-width', function() {
                  return function(t) {
                    return interpolateGaugeWidth(t);
                  };
                });

              if ($scope.internalConfiguration.data.thresholds.display) {
                var thresholds = $scope.widget.select('.ark-graphs-gauge-threshold').selectAll('.ark-graphs-gauge-threshold-path-' + i.toString());
                thresholds
                  .transition()
                  .duration(200)
                  .attr('d', function(d) {
                    return ArcService.computeArc(
                      ($scope.internalConfiguration.amplitude * (d / $scope.internalConfiguration.max)) - $scope.internalConfiguration.data.thresholds.amplitude / 2, ($scope.internalConfiguration.amplitude * (d / $scope.internalConfiguration.max)) + $scope.internalConfiguration.data.thresholds.amplitude / 2,
                      $scope.internalConfiguration.max,
                      $scope.internalConfiguration.max,
                      $scope.internalConfiguration.svg.width,
                      $scope.internalConfiguration.svg.height,
                      gaugeWidth
                    );
                  })
                  .attr('stroke-width', $scope.internalConfiguration.strokeWidth);
              }

            }
            if ($scope.internalConfiguration.tooltip.display) {
              TooltipService.hideTooltip($scope.tooltip);
            }
          };

          $scope.init = function() {
            $scope.widget = d3.select(element[0]);
            $scope.widget.selectAll('*').remove();

            $scope.widget.append('div')
              .attr('class', 'ark-graphs-gauge-div')
              .attr('id', $scope.internalConfiguration.id)
              .style('width', $scope.internalConfiguration.div.width.toString() + 'px')
              .style('height', $scope.internalConfiguration.div.height.toString() + 'px')
              .style('padding-top', $scope.internalConfiguration.div.padding.top.toString() + 'px')
              .style('white-space', 'nowrap')
              .style('position', 'relative');

            if ($scope.internalConfiguration.svg.icon.display) {
              $scope.widget.select('.ark-graphs-gauge-div')
                .append('span')
                .attr('class', 'ark-graphs-gauge-span')
                .style('position', 'absolute')
                .style('text-align', 'center')
                .style('width', '100%');
            }

            $scope.widget.select('.ark-graphs-gauge-div')
              .append('svg')
              .attr('class', 'ark-graphs-gauge-svg')
              .attr('width', $scope.internalConfiguration.div.width)
              .attr('height', $scope.internalConfiguration.svg.height);

            if ($scope.internalConfiguration.background.display) {
              //Setting background
              $scope.widget.select('.ark-graphs-gauge-svg')
                .append('g')
                .attr('class', 'ark-graphs-gauge-background').selectAll('path').data($scope.internalConfiguration.maxData)
                .enter()
                .append('path')
                .attr('d', function(d, i) {
                  return ArcService.computeArc(
                    0,
                    $scope.internalConfiguration.amplitude,
                    $scope.internalConfiguration.max,
                    $scope.internalConfiguration.max,
                    $scope.internalConfiguration.svg.width,
                    $scope.internalConfiguration.svg.height, $scope.internalConfiguration.computeGaugeWidth(d, i) + $scope.internalConfiguration.background.offset
                  );
                })
                .attr('opacity', $scope.internalConfiguration.background.opacity)
                .attr('fill', 'none')
                .attr('transform', ArcService.computeRotation(
                  $scope.internalConfiguration.startAngle,
                  $scope.internalConfiguration.svg.width,
                  $scope.internalConfiguration.svg.height
                ))
                .attr('stroke', $scope.internalConfiguration.background.color)
                .attr('stroke-width', $scope.internalConfiguration.background.strokeWidth);
            }

            if ($scope.internalConfiguration.label.display) {
              //Middle label
              $scope.widget.select('.ark-graphs-gauge-svg')
                .append('g')
                .attr('class', 'ark-graphs-gauge-middle-label')
                .append('text')
                .text($scope.internalConfiguration.label.format(0))
                .attr('x', $scope.internalConfiguration.svg.width / 2)
                .attr('y', $scope.internalConfiguration.svg.height / 2)
                .attr('opacity', $scope.internalConfiguration.label.opacity)
                .attr('font-size', $scope.internalConfiguration.label.fontsize + 'px')
                .attr('fill', $scope.internalConfiguration.label.color)
                .style('dominant-baseline', 'middle')
                .style('text-anchor', 'middle');
              if ($scope.internalConfiguration.label.symbol.display) {
                $scope.widget.select('.ark-graphs-gauge-svg')
                  .append('g')
                  .attr('class', 'ark-graphs-gauge-middle-label-symbol')
                  .append('text')
                  .text($scope.internalConfiguration.label.symbol.format(0))
                  .attr('x', $scope.internalConfiguration.svg.width / 2)
                  .attr('y', $scope.internalConfiguration.svg.height / 2 + $scope.internalConfiguration.label.fontsize)
                  .attr('opacity', $scope.internalConfiguration.label.symbol.opacity)
                  .attr('font-size', $scope.internalConfiguration.label.symbol.fontsize + 'px')
                  .attr('fill', $scope.internalConfiguration.label.symbol.color)
                  .style('text-anchor', 'middle');
              }
            }

            //Main widget content
            $scope.widget.select('.ark-graphs-gauge-svg')
              .append('g')
              .attr('class', 'ark-graphs-gauge-container');

            if ($scope.internalConfiguration.data.thresholds.display) {
              //Display thresholds
              $scope.widget.select('.ark-graphs-gauge-svg')
                .append('g')
                .attr('class', 'ark-graphs-gauge-threshold');
              ThresholdService.initThresholdValues($scope.internalConfiguration);
            }

            TextService.showText($scope.internalConfiguration, $scope.widget, $scope.previousData);

            TooltipService.initTooltip($scope, 'gauge');
          };

          if ($scope.internalConfiguration.autoresize) {
            Utils.resize($scope.internalConfiguration, element);
          }

          $scope.init();

          //Check for resizing
          $scope.$watch(function() {
            var e = angular.element(element[0].parentElement);
            return Utils.getTrueWidth(e[0]);
          }, function() {
            if ($scope.internalConfiguration.autoresize) {
              Utils.resize($scope.internalConfiguration, element);
              $scope.init();
              $scope.draw($scope.data);
            }
          }, true);

          //Check for text overflow
          $scope.$watch(function() {
            var a = element[0].querySelector('.ark-graphs-gauge-middle-label text');
            if (a === null) {
              return $scope.internalConfiguration.radius * 2;
            }
            return a.getBoundingClientRect().width;
          }, function(newVal) {
            if (newVal > $scope.internalConfiguration.radius * 2 * (0.9 - 0.1 * $scope.internalConfiguration.numberOfData)) {
              $scope.setMiddleLabelFont($scope.internalConfiguration.label.fontsize / 2);
              $scope.setMiddleLabel();
            }

            if ($scope.internalConfiguration.label.maxFontsize > $scope.internalConfiguration.label.fontsize) {
              if (newVal < $scope.internalConfiguration.radius * 2 * (0.7 - 0.1 * $scope.internalConfiguration.numberOfData)) {
                $scope.setMiddleLabelFont($scope.internalConfiguration.label.fontsize * 1.5);
                $scope.setMiddleLabel();
              }
            }
          });

          //Check for changes in internalConfiguration
          $scope.$watch('configuration', function() {
            $scope.internalConfiguration.update($scope.configuration);
            $scope.init();
            $scope.draw($scope.data);
          }, true);

          $scope.$watch('data', function(newVals) {
            if (newVals !== undefined) {
              return $scope.draw(newVals);
            }
          });
        }
      };
    }
  ]);

'use strict';

angular.module('ark.graphs.gauge')
  .factory('ark.graphs.gauge-config', ['ark.graphs.color-service', 'ark.graphs.utils',
    'ark.graphs.config-service',
    function(ColorService, Utils, ConfigService) {
      var GaugeConfiguration = function(configuration) {
        this.type = 'gauge';
        this.id = Utils.generateID(this.type);
        this.initialValues = [];
        this.max = 100;
        this.startAngle = -150;
        this.amplitude = 300;
        this.strokeWidth = 8;
        this.radius = 69;
        this.numberOfDataSet = 1;
        this.numberOfData = this.numberOfDataSet;
        this.autoresize = false;

        this.radiusRule = {
          apply: true,
          rule: function(value, index, initialRadius, initialWidth) {
            return initialRadius - index * initialWidth * 1.5;
          }
        };

        this.svg = {
          height: this.radius * 2 + this.strokeWidth / 2 + 26,
          width: 208,
          padding: {
            top: 9
          },
          icon: {
            display: true
          }
        };

        this.legend = {
          display: true,
          fontsize: 12,
          height: 72,
          width: this.svg.width,
          title: ['Metric name'],
          format: function(d, i) {
            return d;
          },
          letters: {
            display: false
          },
          padding: {
            top: 10,
            left: 20,
            right: 20
          },
          icon: {
            display: true,
            minValue: 50
          }
        };

        this.data = {
          labels: ['data 0'],
          thresholds: {
            display: true,
            values: [75],
            strokeWidth: 8,
            amplitude: 1,
            opacity: 1,
            statusColors: ColorService.getStatusColors(2),
            barColor: '#C4CDD6',
            barColorOver: '#FFF',
            aboveGauge: false,
            comparator: function(value, threshold) {
              return value < threshold;
            }
          }
        };

        this.tooltip = {
          display: true,
          format: function(value, index, color, name) {
            return '<table class="ark-graphs-gauge-tooltip"><tbody><tr class="ark-graphs-gauge-tooltip-name-data"><td class="name"><span class="ark-graphs-gauge-tooltip-square" style="background-color: ' + color + ';"></span><text class="name-container">' + name + '</text></td><td class="value">' + value + '</td></tr></tbody></table>';
          }
        };

        this.hover = {
          apply: true,
          growBy: 2
        };

        this.background = {
          display: true,
          color: '#E3E9EF',
          strokeWidth: 2,
          opacity: 1,
          offset: this.strokeWidth / 2
        };

        this.label = {
          display: true,
          fontsize: 32,
          maxFontsize: 32,
          color: 'black',
          format: function(value) {
            return value + '%';
          },
          opacity: 1,
          symbol: {
            display: true,
            fontsize: 20,
            color: 'black',
            format: function() {
              return '';
            },
            opacity: 1
          }
        };

        this.transitions = {
          arc: 1000,
          label: 500,
          thresholds: 1000
        };

        this.autosnap = {
          enabled: false,
          threshold: 516,
          smallConfig: {
            radius: 69,
            svg: {
              width: 208
            },
            strokeWidth: 8,
            label: {
              fontsize: 32,
              maxFontsize: 32
            },
            legend: {
              fontsize: 12,
              height: 72,
              width: 208,
              padding: {
                top: 10,
                left: 20,
                right: 20
              }
            },
            data: {
              thresholds: {
                strokeWidth: 8
              }
            }
          },
          largeConfig: {
            radius: 124,
            svg: {
              width: 516
            },
            strokeWidth: 12,
            label: {
              fontsize: 48,
              maxFontsize: 48
            },
            thresholds: {
              strokeWidth: 12
            },
            legend: {
              fontsize: 14,
              height: 160,
              width: 260,
              padding: {
                top: 20,
                left: 24,
                right: 24
              }
            },
            data: {
              thresholds: {
                strokeWidth: 12
              }
            }
          }
        };

        this.update(configuration);
      };

      GaugeConfiguration.prototype.update = function(configuration) {
        Utils.mergeRecursive(this, configuration);

        this.maxData = [];
        this.multiThreshold = [];
        this.svg.height = this.radius * 2 + this.strokeWidth / 2 + 26;
        this.div = {
          width: this.svg.width,
          height: this.svg.height + (this.legend.display ? this.legend.height : 0),
          padding: {
            top: this.svg.padding.top
          }
        };

        var i = 0;
        for (i = 0; i < this.numberOfData; i++) {
          this.maxData.push(this.max);
        }

        ConfigService.getStatusColors(this);
        ConfigService.updateInitialValues(this);
        ConfigService.updateLegendLabels(this);
        ConfigService.updateTooltipLabels(this);
      };

      GaugeConfiguration.prototype.computeGaugeWidth = function(d, i) {
        if (this.radiusRule.apply) {
          return this.radiusRule.rule(d, i, this.radius - this.strokeWidth / 2, this.strokeWidth);
        } else {
          return (this.radius - this.strokeWidth / 2);
        }
      };

      return GaugeConfiguration;
    }
  ]);

'use strict';

angular.module('ark.graphs.line-graph')
  .directive('arkLineGraph', ['ark.graphs.line-graph-config', 'ark.graphs.text-service',
    'ark.graphs.line-service', 'ark.graphs.d3', 'ark.graphs.utils', 'ark.graphs.tooltip-service',
    function(LineGraphConfiguration, TextService, LineService, d3, Utils, TooltipService) {
      return {
        restrict: 'E',
        scope: {
          configuration: '=',
          data: '='
        },
        link: function($scope, element) {
          $scope.internalConfiguration = new LineGraphConfiguration($scope.configuration, $scope.data);

          $scope.init = function() {

            $scope.widget = d3.select(element[0]);
            $scope.widget.selectAll('*').remove();

            $scope.widget.append('div')
              .attr('class', 'ark-graphs-line-graph-div')
              .attr('id', $scope.internalConfiguration.id)
              .style('width', $scope.internalConfiguration.div.width.toString() + 'px')
              .style('height', $scope.internalConfiguration.div.height.toString() + 'px')
              .style('position', 'relative')
              .style('white-space', 'nowrap');

            $scope.widget.select('.ark-graphs-line-graph-div')
              .append('svg')
              .attr('class', 'ark-graphs-line-graph-svg')
              .attr('width', $scope.internalConfiguration.svg.width)
              .attr('height', $scope.internalConfiguration.svg.height);

            $scope.widget.select('.ark-graphs-line-graph-svg')
              .append('g')
              .attr('class', 'ark-graphs-line-graph-svg-inner')
              .attr('transform', ['translate(', 0, ',', $scope.internalConfiguration.padding.top, ')'].join(' '));

            // clip path to crops graph
            $scope.widget.select('.ark-graphs-line-graph-svg-inner')
              .append('defs')
              .append('clipPath')
              .attr('id', 'ark-graphs-line-graph-clipPath-' + $scope.internalConfiguration.id)
              .append('rect')
              .attr('x', 0)
              .attr('y', -$scope.internalConfiguration.padding.top)
              .attr('width', $scope.internalConfiguration.graphWidth)
              .attr('height', $scope.internalConfiguration.graphHeight + $scope.internalConfiguration.padding.top + $scope.internalConfiguration.svg.xAxis.tickUnitHeight + $scope.internalConfiguration.svg.xAxis.labelUnitHeight);

            if ($scope.internalConfiguration.brush.activated) {
              $scope.widget.select('.ark-graphs-line-graph-svg-inner')
                .append('g')
                .attr('transform', ['translate(', $scope.internalConfiguration.marginLeft, 0, ')'].join(' '))
                .attr('id', 'ark-graphs-line-graph-brush-' + $scope.internalConfiguration.id)
                .attr('class', 'ark-graphs-line-graph-brush');
            }

            $scope.widget.select('.ark-graphs-line-graph-svg-inner')
              .append('g')
              .attr('class', 'ark-graphs-line-graph-container')
              .attr('transform', ['translate(', $scope.internalConfiguration.marginLeft, 0, ')'].join(' '));

            $scope.container = $scope.widget.select('.ark-graphs-line-graph-svg-inner').select('.ark-graphs-line-graph-container');

            if ($scope.internalConfiguration.svg.yAxis.guidelines.display) {
              $scope.container
                .append('g')
                .attr('class', 'ark-graphs-line-graph-y-axis-guidelines');
            }

            if ($scope.internalConfiguration.svg.xAxis.guidelines.display) {
              $scope.container
                .append('g')
                .attr('class', 'ark-graphs-line-graph-x-axis-guidelines')
                .style('clip-path', 'url(#ark-graphs-line-graph-clipPath-' + $scope.internalConfiguration.id + ')');
            }

            $scope.container
              .append('g')
              .attr('class', 'ark-graphs-line-graph-y-axis');

            $scope.container
              .append('g')
              .attr('class', 'ark-graphs-line-graph-x-axis')
              .style('clip-path', 'url(#ark-graphs-line-graph-clipPath-' + $scope.internalConfiguration.id + ')');

            $scope.container
              .append('g')
              .attr('class', 'ark-graphs-line-graph-data')
              .style('clip-path', 'url(#ark-graphs-line-graph-clipPath-' + $scope.internalConfiguration.id + ')')
              .append('g')
              .attr('class', 'ark-graphs-line-graph-dataLines');

            $scope.container.select('.ark-graphs-line-graph-data')
              .append('g')
              .attr('class', 'ark-graphs-line-graph-circles');

            $scope.container.select('.ark-graphs-line-graph-data')
              .append('g')
              .attr('class', 'ark-graphs-line-graph-text');

            // START generating stuff

            // display guidelines on y axis
            if ($scope.internalConfiguration.svg.yAxis.guidelines.display) {
              $scope.container.select('.ark-graphs-line-graph-y-axis-guidelines').selectAll('path').data($scope.internalConfiguration.graphYLocation)
                .enter()
                .append('path')
                .attr('d', function(d) {
                  return LineService.computeLine(0, d, $scope.internalConfiguration.graphWidth, d);
                })
                .attr('stroke', $scope.internalConfiguration.svg.yAxis.guidelines.color)
                .attr('opacity', $scope.internalConfiguration.svg.yAxis.guidelines.opacity)
                .attr('stroke-width', $scope.internalConfiguration.svg.yAxis.guidelines.strokeWidth);
            }

            // display y axis
            $scope.container.select('.ark-graphs-line-graph-y-axis').selectAll('path').data($scope.internalConfiguration.graphYLocation)
              .enter()
              .append('path')
              .attr('class', 'ark-graphs-line-graph-y-guidelines-all')
              .attr('d', function(d) {
                return LineService.computeLine(0, d, -$scope.internalConfiguration.svg.yAxis.axisLine.tickLineSize, d);
              })
              .attr('stroke', $scope.internalConfiguration.svg.yAxis.axisLine.color)
              .attr('stroke-width', $scope.internalConfiguration.svg.yAxis.axisLine.strokeWidth);

            $scope.container.select('.ark-graphs-line-graph-y-axis')
              .append('path')
              .attr('class', 'ark-graphs-line-graph-y-guidelines-all')
              .attr('d', LineService.computeLine(0, 0, 0, $scope.internalConfiguration.graphHeight))
              .attr('stroke', $scope.internalConfiguration.svg.yAxis.axisLine.color)
              .attr('stroke-width', $scope.internalConfiguration.svg.yAxis.axisLine.strokeWidth);

            // display y axis ticks
            if ($scope.internalConfiguration.svg.yAxis.tick.show) {
              $scope.widget.select('.ark-graphs-line-graph-svg-inner')
                .append('g')
                .attr('class', 'ark-graphs-line-graph-y-tick-group').selectAll('g').data($scope.internalConfiguration.graphYLocation)
                .enter()
                .append('g')
                .attr('class', 'ark-graphs-line-graph-y-tick')
                .attr('transform', ['translate(', $scope.internalConfiguration.svg.yAxis.tick.fontsize - $scope.internalConfiguration.svg.yAxis.axisLine.tickLineSize, -$scope.internalConfiguration.svg.yAxis.tick.fontsize / 6, ')'].join(' '))
                .append('text')
                .attr('text-anchor', 'end')
                .text(function(d, i) {
                  return $scope.internalConfiguration.svg.yAxis.tick.ticks[i];
                })
                .attr('x', $scope.internalConfiguration.svg.yAxis.labelUnitHeight + $scope.internalConfiguration.svg.yAxis.tickUnitHeight / 2)
                .attr('y', function(d) {
                  return d + $scope.internalConfiguration.svg.yAxis.tick.fontsize / 2;
                });
            }

            // display guidelines on x axis
            if ($scope.internalConfiguration.svg.xAxis.guidelines.display) {
              $scope.widget.select('.ark-graphs-line-graph-x-axis-guidelines').selectAll('path').data($scope.internalConfiguration.graphXLocation)
                .enter()
                .append('path')
                .attr('id', function(d, i) {
                  return 'ark-graphs-line-graph-x-guidelines-' + i.toString();
                })
                .attr('class', 'ark-graphs-line-graph-x-guidelines-all')
                .attr('d', function(d) {
                  return LineService.computeLine(d, 0, d, $scope.internalConfiguration.graphHeight);
                })
                .attr('stroke', $scope.internalConfiguration.svg.xAxis.guidelines.unselectedColor)
                .attr('opacity', $scope.internalConfiguration.svg.xAxis.guidelines.opacity)
                .attr('stroke-width', $scope.internalConfiguration.svg.xAxis.guidelines.strokeWidth);
            }

            // display x axis
            $scope.container.select('.ark-graphs-line-graph-x-axis').selectAll('path').data($scope.internalConfiguration.graphXLocation)
              .enter()
              .append('path')
              .attr('id', function(d, i) {
                return 'ark-graphs-line-graph-x-lines-' + i.toString();
              })
              .attr('class', 'ark-graphs-line-graph-x-lines')
              .attr('d', function(d) {
                return LineService.computeLine(d, $scope.internalConfiguration.graphHeight, d, $scope.internalConfiguration.graphHeight + $scope.internalConfiguration.svg.xAxis.axisLine.tickLineSize);
              })
              .attr('stroke', $scope.internalConfiguration.svg.xAxis.axisLine.color)
              .attr('stroke-width', $scope.internalConfiguration.svg.xAxis.axisLine.strokeWidth);

            $scope.container.select('.ark-graphs-line-graph-x-axis')
              .append('path')
              .attr('d', LineService.computeLine(0, $scope.internalConfiguration.graphHeight, $scope.internalConfiguration.graphWidth, $scope.internalConfiguration.graphHeight))
              .attr('stroke', $scope.internalConfiguration.svg.xAxis.axisLine.color)
              .attr('stroke-width', $scope.internalConfiguration.svg.xAxis.axisLine.strokeWidth);

            // display x axis ticks
            if ($scope.internalConfiguration.svg.xAxis.tick.show) {
              $scope.widget.select('.ark-graphs-line-graph-svg-inner')
                .append('g')
                .attr('class', 'ark-graphs-line-graph-x-tick-group')
                .attr('transform', ['translate(', $scope.internalConfiguration.marginLeft, 0, ')'].join(' '))
                .style('clip-path', 'url(#ark-graphs-line-graph-clipPath-' + $scope.internalConfiguration.id + ')')
                .selectAll('g').data($scope.internalConfiguration.graphXLocation)
                .enter()
                .append('g')
                .attr('class', 'ark-graphs-line-graph-x-tick')
                .append('text')
                .attr('text-anchor', 'middle')
                .text(function(d, i) {
                  return $scope.internalConfiguration.svg.xAxis.tick.ticks[i];
                })
                .attr('x', function(d) {
                  return d;
                })
                .attr('y', $scope.internalConfiguration.graphHeight + $scope.internalConfiguration.svg.xAxis.axisLine.tickLineSize + $scope.internalConfiguration.svg.xAxis.tickUnitHeight / 2);
            }

            // generate data
            angular.forEach($scope.data, function(value, key) {

              //generate CIRCLES
              $scope.container.select('.ark-graphs-line-graph-circles').selectAll('.ark-graphs-line-graph-node-dataset-' + key.toString()).data($scope.internalConfiguration.graphXLocation)
                .enter()
                .append('circle')
                .attr('class', function(d, i) {
                  return 'ark-graphs-line-graph-nodes ark-graphs-line-graph-node-dataset-' + key.toString() + ' ark-graphs-line-graph-node-' + i.toString();
                })
                .attr('id', function(d, i) {
                  return 'ark-graphs-line-graph-node-' + key.toString() + '-' + i.toString();
                })
                .attr('fill', $scope.internalConfiguration.data.colors[key])
                .attr('r', $scope.internalConfiguration.data.circles.rUnselected)
                .attr('cx', function(d) {
                  return d;
                })
                .attr('cy', function(d, i) {
                  return $scope.internalConfiguration.getY($scope.data[key][i]);
                });

              //generate TEXT
              if ($scope.internalConfiguration.data.showValue) {
                $scope.container.select('.ark-graphs-line-graph-text').selectAll('#ark-graphs-line-graph-text-' + key.toString()).data($scope.internalConfiguration.graphXLocation)
                  .enter()
                  .append('g')
                  .attr('class', function(d, i) {
                    return 'ark-graphs-line-graph-text-dataset-' + key.toString() + ' ark-graphs-line-graph-text-' + i.toString();
                  })
                  .attr('id', function(d, i) {
                    return 'ark-graphs-line-graph-text-' + key.toString() + '-' + i.toString();
                  })
                  .append('text')
                  .text(function(d, i) {
                    return $scope.data[key][i];
                  })
                  .attr('text-anchor', $scope.internalConfiguration.data.text.textAnchor)
                  .attr('x', function(d) {
                    return d;
                  })
                  .attr('y', function(d, i) {
                    return $scope.internalConfiguration.getY($scope.data[key][i]) - $scope.internalConfiguration.svg.fontsize / 2;
                  });
              }

              //generate LINES
              $scope.widget.select('.ark-graphs-line-graph-dataLines').selectAll('.ark-graphs-line-graph-node-dataLine-' + key.toString()).data($scope.internalConfiguration.graphXLocationSlice)
                .enter()
                .append('path')
                .attr('class', function(d, i) {
                  return 'ark-graphs-line-graph-node-dataLine-dataset-' + key.toString() + ' ark-graphs-line-graph-node-dataLine-' + i.toString() + '-' + (i + 1).toString();
                })
                .attr('id', function(d, i) {
                  return 'ark-graphs-line-graph-node-dataLine' + key.toString() + '-' + i.toString() + '-' + (i + 1).toString();
                })
                .attr('stroke', $scope.internalConfiguration.data.colors[key])
                .attr('stroke-width', $scope.internalConfiguration.data.lines.strokeWidth)
                .attr('d', function(d, i) {
                  var yPrev = $scope.internalConfiguration.getY($scope.data[key][i]);
                  var y = $scope.internalConfiguration.getY($scope.data[key][i + 1]);
                  if (i === 0) {
                    return LineService.computeLine($scope.internalConfiguration.graphXLocation[0], yPrev, d, y);
                  } else {
                    return LineService.computeLine($scope.internalConfiguration.graphXLocation[i], yPrev, d, y);
                  }
                });
            });

            // show y axis label
            $scope.widget.select('.ark-graphs-line-graph-svg-inner')
              .append('g')
              .attr('class', '.ark-graphs-line-graph-y-label')
              .append('text')
              .attr('text-anchor', 'middle')
              .attr('transform', ['translate(', $scope.internalConfiguration.svg.fontsize, 0, ')', 'rotate(', -90, 0, $scope.internalConfiguration.graphHeight / 2, ')'].join(' '))
              .attr('x', 0)
              .attr('y', $scope.internalConfiguration.graphHeight / 2)
              .text($scope.internalConfiguration.svg.yAxis.label)
              .style('font-weight', 'bold');

            // show x axis label
            $scope.widget.select('.ark-graphs-line-graph-svg-inner')
              .append('g')
              .attr('class', '.ark-graphs-line-graph-x-label')
              .append('text')
              .attr('text-anchor', 'middle')
              .attr('transform', ['translate(', $scope.internalConfiguration.marginLeft, -$scope.internalConfiguration.svg.fontsize, ')'].join(' '))
              .attr('x', $scope.internalConfiguration.graphWidth / 2)
              .attr('y', $scope.internalConfiguration.graphHeight + $scope.internalConfiguration.svg.xAxis.tickUnitHeight + $scope.internalConfiguration.svg.xAxis.labelUnitHeight / 2 + $scope.internalConfiguration.svg.fontsize / 2)
              .text($scope.internalConfiguration.svg.xAxis.label)
              .style('font-weight', 'bold');

            // show legend
            TextService.showTextChart($scope.internalConfiguration, $scope.widget, $scope.data);

            // show tooltip
            TooltipService.initTooltip($scope, 'line-graph');

            // brush initilization
            $scope.x = d3.scale.linear().range([0, $scope.internalConfiguration.graphWidth]).domain([0, $scope.internalConfiguration.graphWidth]);

            if ($scope.internalConfiguration.brush.activated) {
              $scope.brush = d3.svg.brush()
                .x($scope.x)
                .on('brush', $scope.brushmove)
                .on('brushend', $scope.brushend);

              $scope.widget.select('#ark-graphs-line-graph-brush-' + $scope.internalConfiguration.id)
                .call($scope.brush)
                .selectAll('rect')
                .attr('height', $scope.internalConfiguration.graphHeight);
            }

            $scope.transitioning = false;
          };

          $scope.brushmove = function() {
            if ($scope.internalConfiguration.tooltip.display) {
              TooltipService.hideTooltip($scope.tooltip);
            }

            var extent = $scope.brush.extent();

            angular.forEach($scope.data, function(value, key) {
              $scope.widget.selectAll('.ark-graphs-line-graph-node-dataset-' + key.toString()).data($scope.internalConfiguration.graphXLocation)
                .classed('selected', function(d) {
                  return extent[0] <= d && d <= extent[1];
                });

              $scope.widget.selectAll('.ark-graphs-line-graph-text-dataset-' + key.toString()).data($scope.internalConfiguration.graphXLocation)
                .classed('selected', function(d) {
                  return extent[0] <= d && d <= extent[1];
                });

              $scope.widget.selectAll('.ark-graphs-line-graph-node-dataLine-dataset-' + key.toString()).data($scope.internalConfiguration.graphXLocationSlice)
                .classed('selected', function(d, i) {
                  return extent[0] <= $scope.internalConfiguration.graphXLocation[i] && d <= extent[1];
                });

            });

            $scope.widget.select('.ark-graphs-line-graph-x-tick-group').selectAll('.ark-graphs-line-graph-x-tick').data($scope.internalConfiguration.graphXLocation)
              .classed('selected', function(d) {
                return extent[0] <= d && d <= extent[1];
              });
            $scope.widget.selectAll('.ark-graphs-line-graph-x-lines').data($scope.internalConfiguration.graphXLocation)
              .classed('selected', function(d) {
                return extent[0] <= d && d <= extent[1];
              });
            $scope.widget.select('.ark-graphs-line-graph-x-axis-guidelines').selectAll('path').data($scope.internalConfiguration.graphXLocation)
              .classed('selected', function(d) {
                return extent[0] <= d && d <= extent[1];
              });
          };

          $scope.brushend = function() {
            if (Math.abs($scope.brush.extent()[0] - $scope.brush.extent()[1]) <= $scope.internalConfiguration.brush.brushMinExtent) {
              $scope.brush.extent([0, $scope.internalConfiguration.graphWidth]);
            }
            $scope.x.domain($scope.brush.extent());
            $scope.transitionData($scope.internalConfiguration.brush.brushTransition.duration);
            $scope.unselectSelected();
            d3.select('#ark-graphs-line-graph-brush-' + $scope.internalConfiguration.id).call($scope.brush.clear());
          };

          $scope.unselectSelected = function() {
            d3.select('#' + $scope.internalConfiguration.id).selectAll('.selected').classed('selected', false);
          };

          $scope.transitionData = function(duration) {
            $scope.mouseoutPath($scope.internalConfiguration.xLoc);
            $scope.transitioning = true;
            angular.forEach($scope.data, function(value, key) {

              //CIRCLESS
              $scope.widget.selectAll('.ark-graphs-line-graph-node-dataset-' + key.toString())
                .transition().duration(duration)
                .attrTween('cy', function(d, i) {
                  var selection = $scope.widget.select('#ark-graphs-line-graph-node-' + key.toString() + '-' + i.toString());
                  var interpolateY1 = d3.interpolate(selection.attr('cy'), $scope.internalConfiguration.getY($scope.data[key][i]));
                  return function(t) {
                    return interpolateY1(t);
                  };
                })
                .attrTween('cx', function(d, i) {
                  var selection = $scope.widget.select('#ark-graphs-line-graph-node-' + key.toString() + '-' + i.toString());
                  var interpolateX1 = d3.interpolate(selection.attr('cx'), $scope.x($scope.internalConfiguration.graphXLocation[i]));
                  return function(t) {
                    return interpolateX1(t);
                  };
                });

              //TEXTS
              $scope.widget.selectAll('.ark-graphs-line-graph-text-dataset-' + key.toString()).select('text')
                .transition().duration(duration)
                .text(function(d, i) {
                  return $scope.data[key][i];
                })
                .attrTween('y', function(d, i) {
                  var selection = $scope.widget.select('#ark-graphs-line-graph-text-' + key.toString() + '-' + i.toString()).select('text');
                  var interpolate = d3.interpolate(selection.attr('y'), $scope.internalConfiguration.getY($scope.data[key][i]) - $scope.internalConfiguration.svg.fontsize / 2);
                  return function(t) {
                    return interpolate(t);
                  };
                })
                .attrTween('x', function(d, i) {
                  var selection = $scope.widget.select('#ark-graphs-line-graph-text-' + key.toString() + '-' + i.toString()).select('text');
                  var interpolate = d3.interpolate(selection.attr('x'), $scope.x($scope.internalConfiguration.graphXLocation[i]));
                  return function(t) {
                    return interpolate(t);
                  };
                });

              //LINES
              $scope.widget.selectAll('.ark-graphs-line-graph-node-dataLine-dataset-' + key.toString())
                .transition().duration(duration)
                .attrTween('d', function(d, i) {
                  var selection = $scope.widget.select('#ark-graphs-line-graph-node-dataLine' + key.toString() + '-' + i.toString() + '-' + (i + 1).toString());
                  var interpolateY1 = d3.interpolate(selection.attr('d').split(' ')[2], $scope.internalConfiguration.getY($scope.data[key][i]));
                  var interpolateY2 = d3.interpolate(selection.attr('d').split(' ')[5], $scope.internalConfiguration.getY($scope.data[key][i + 1]));
                  var interpolateX1 = d3.interpolate(selection.attr('d').split(' ')[1], $scope.x($scope.internalConfiguration.graphXLocation[i]));
                  var interpolateX2 = d3.interpolate(selection.attr('d').split(' ')[4], $scope.x($scope.internalConfiguration.graphXLocation[i + 1]));
                  return function(t) {
                    return LineService.computeLine(interpolateX1(t), interpolateY1(t), interpolateX2(t), interpolateY2(t));
                  };
                });

            });

            $scope.widget.select('.ark-graphs-line-graph-x-tick-group').selectAll('.ark-graphs-line-graph-x-tick').select('text')
              .transition().duration(duration)
              .attr('x', function(d) {
                return $scope.x(d);
              });

            $scope.widget.selectAll('.ark-graphs-line-graph-x-lines')
              .transition().duration(duration)
              .attr('d', function(d) {
                return LineService.computeLine($scope.x(d), $scope.internalConfiguration.graphHeight, $scope.x(d), $scope.internalConfiguration.graphHeight + $scope.internalConfiguration.svg.yAxis.axisLine.tickLineSize);
              });

            $scope.widget.select('.ark-graphs-line-graph-x-axis-guidelines').selectAll('path')
              .transition().duration(duration)
              .attr('d', function(d) {
                return LineService.computeLine($scope.x(d), $scope.internalConfiguration.graphHeight, $scope.x(d), 0);
              })
              .each('end', function() {
                $scope.transitioning = false;
                $scope.updateToolTip();
              });
          };

          $scope.draw = function() {
            $scope.transitionData($scope.internalConfiguration.data.transitions);
          };

          $scope.updateToolTip = function() {
            $scope.widget.select('.ark-graphs-line-graph-svg')
              .on('mousemove', function() {
                var coordinate = d3.mouse(this);
                $scope.mousemovePath('.ark-graphs-line-graph-svg', coordinate);
              })
              .on('mouseout', function() {
                $scope.internalConfiguration.xLoc = d3.event.pageX;
                $scope.mouseoutPath(d3.event.pageX);
              });
          };

          $scope.computeClosestX = function(x) {
            var difference = ($scope.x($scope.internalConfiguration.graphXLocation[1]) - $scope.x($scope.internalConfiguration.graphXLocation[0])) / 2; // assume always greater than one data
            var key = 0;
            var value = '';
            var i = 0;
            for (i = 0; i < $scope.data[0].length; i++) {
              if (Math.abs(Math.round(x) - $scope.x($scope.internalConfiguration.graphXLocation[i])) <= Math.round(difference)) {
                if ($scope.x($scope.internalConfiguration.graphXLocation[i]) <= $scope.internalConfiguration.graphWidth) {
                  value = $scope.x($scope.internalConfiguration.graphXLocation[i]);
                } else {
                  value = '';
                }
                key = i;
              }
            }
            return {
              i: key,
              x: value
            };
          };

          $scope.mousemovePath = function(id, coordinate) {
            $scope.tooltipBox = d3.select('#tooltip-' + $scope.internalConfiguration.id).node().getBoundingClientRect();

            //position of mouse relative to svg
            $scope.keyVal = $scope.computeClosestX(coordinate[0] - $scope.internalConfiguration.marginLeft);
            var x = parseFloat($scope.widget.select('#ark-graphs-line-graph-x-guidelines-' + $scope.keyVal.i).attr('d').split(' ')[1], 10) + $scope.internalConfiguration.marginLeft;
            var y = coordinate[1];

            if ($scope.tooltipBox.width + x > $scope.internalConfiguration.svg.width) {
              x -= $scope.tooltipBox.width + $scope.internalConfiguration.marginLeft - 20;
            }
            if ($scope.tooltipBox.height + y > $scope.internalConfiguration.svg.height) {
              y -= $scope.tooltipBox.height + $scope.internalConfiguration.marginLeft - 20;
            }

            TooltipService.setCoordinates($scope.tooltip, x, y);

            if (typeof $scope.keyVal.x !== 'string' && !$scope.transitioning) {
              TooltipService.showTooltip($scope.tooltip, $scope.data, $scope.keyVal.i, $scope.internalConfiguration.data.colors, $scope.internalConfiguration.data.labels);
            }

            // change node data size based on mouse position
            $scope.widget.selectAll('.ark-graphs-line-graph-nodes')
              .attr('r', 3.5);

            $scope.widget.selectAll('.ark-graphs-line-graph-node-' + $scope.keyVal.i.toString())
              .attr('r', 4);

            // change guideline color based on mouse position
            $scope.widget.selectAll('.ark-graphs-line-graph-x-guidelines-all')
              .attr('stroke', $scope.internalConfiguration.svg.xAxis.guidelines.unselectedColor);

            $scope.widget.select('#ark-graphs-line-graph-x-guidelines-' + $scope.keyVal.i.toString())
              .attr('stroke', $scope.internalConfiguration.svg.xAxis.guidelines.selectedColor);
          };

          $scope.mouseoutPath = function(pageX) {
            if ($scope.internalConfiguration.tooltip.display) {
              TooltipService.hideTooltip($scope.tooltip);
            }
            $scope.keyVal = $scope.computeClosestX(pageX);

            $scope.widget.selectAll('.ark-graphs-line-graph-x-guidelines-all')
              .attr('stroke', $scope.internalConfiguration.svg.xAxis.guidelines.unselectedColor);

            $scope.widget.selectAll('.ark-graphs-line-graph-node-' + $scope.keyVal.i.toString())
              .attr('r', 3.5);
          };

          if ($scope.internalConfiguration.autoresize) {
            Utils.resize($scope.internalConfiguration, element);
          }

          //Check for resizing
          $scope.$watch(function() {
            var e = angular.element(element[0].parentElement);
            return Utils.getTrueWidth(e[0]);
          }, function() {
            if ($scope.internalConfiguration.autoresize) {
              Utils.resize($scope.internalConfiguration, element);
              $scope.init();
              $scope.draw($scope.data);
            }
          }, true);

          $scope.init();

          $scope.$watch('configuration', function() {
            $scope.internalConfiguration.update($scope.configuration);
            $scope.init();
          }, true);

          $scope.$watch('data', function(newVals) {
            if (newVals !== undefined) {
              $scope.draw(newVals);
            }
          });
        }
      };
    }
  ]);

'use strict';

angular.module('ark.graphs.line-graph')
  .factory('ark.graphs.line-graph-config', ['ark.graphs.color-service', 'ark.graphs.utils', 'ark.graphs.config-service', 'ark.graphs.d3',
    function(ColorService, Utils, ConfigService, d3) {
      var LineGraphConfiguration = function(configuration, data) {
        this.type = 'line-graph';
        this.id = Utils.generateID(this.type);
        this.autoresize = false;
        this.numberOfDataSet = data.length;
        this.numberOfData = data.length;

        this.svg = {
          height: 216,
          width: 335,
          fontsize: 12,
          yAxis: {
            label: 'y-axis label (unit)',
            labelUnitHeight: 24,
            tickUnitHeight: 24,
            axisLine: {
              color: 'black',
              tickLineSize: 5,
              strokeWidth: 1
            },
            guidelines: {
              display: true,
              color: '#E3E9EF',
              opacity: 1,
              strokeWidth: 1
            },
            tick: {
              show: true,
              fontsize: 12,
              numOfTicks: 6,
              ticks: []
            }
          },
          xAxis: {
            label: 'x-axis label (unit)',
            labelUnitHeight: 24,
            tickUnitHeight: 24,
            axisLine: {
              color: 'black',
              tickLineSize: 5,
              strokeWidth: 1
            },
            guidelines: {
              display: true,
              unselectedColor: '#E3E9EF',
              selectedColor: '#3F4142',
              opacity: 1,
              strokeWidth: 1
            },
            tick: {
              show: true,
              fontsize: 12,
              ticks: []
            }
          }
        };

        this.padding = {
          top: 0,
          right: 20,
          left: 20
        };

        this.brush = {
          activated: false,
          brushTransition: {
            duration: 1000
          },
          brushMinExtent: 15 // used to zoom out (if extent size is less than this, it will zoom all the way out
        };

        this.data = {
          transitions: 1000,
          colors: ColorService.arkBlueColors(),
          labels: ['data 0'],
          circles: {
            rUnselected: 3.5,
            rSelected: 4.5
          },
          lines: {
            strokeWidth: 1
          },
          text: {
            textAnchor: 'middle'
          },
          showValue: false,
          dataSetLength: data.length,
          dataLength: data[0].length
        };

        this.tooltip = {
          display: true,
          format: function(data, index, colors, names) {
            var tableData = '';

            for (var i = 0; i < data.length; i++) {
              tableData += '<tr class="ark-graphs-line-graph-tooltip-name-data"><td class="name"><span class="ark-graphs-line-graph-tooltip-square" style="background-color: ' + colors[i] + ';"></span><text class="name-container">' + names[i] + '</text></td><td class="value">' + data[i][index] + '</td></tr>';
            }

            return '<table class="ark-graphs-line-graph-tooltip"><tbody><tr><th class="header" colspan="2">' + index + '</th></tr>' + tableData + '</tbody></table>';
          }
        };

        this.legend = {
          display: true,
          height: 20,
          title: ['Key if needed'],
          format: function(d, i) {
            return d;
          }
        };

        this.autosnap = {
          enabled: false,
          threshold: 464,
          smallConfig: {
            svg: {
              width: 335,
              height: 216
            }
          },
          largeConfig: {
            svg: {
              height: 216,
              width: 464
            }
          }
        };

        this.updateMaxMinData(data);

        this.update(configuration, data);
      };

      LineGraphConfiguration.prototype.update = function(configuration) {
        Utils.mergeRecursive(this, configuration);

        this.marginLeft = this.svg.yAxis.labelUnitHeight + this.svg.yAxis.tickUnitHeight;
        this.marginBottom = this.svg.xAxis.labelUnitHeight + this.svg.xAxis.tickUnitHeight;

        this.graphWidth = this.svg.width - this.marginLeft;
        this.graphHeight = this.svg.height - this.marginBottom;

        this.div = {
          height: this.svg.height + (this.legend.display ? this.legend.height : 0),
          width: this.svg.width
        };

        this.legend.width = this.svg.width;

        this.padding.top = 4 + this.svg.fontsize;

        ConfigService.updateLegendLabels(this);
        ConfigService.updateTooltipLabels(this);

        this.generateDataColor(this.data.dataSetLength);
        this.updateTickX(this.data.dataLength);
        this.updateTickY();

      };

      LineGraphConfiguration.prototype.generateDataColor = function(n) {
        if (n !== this.data.colors.length) {
          for (var i = this.data.colors.length; i < n; i++) {
            this.data.colors.push('#' + (Math.random() * 0xFFFFFF).toString(16));
          }
        }
      };

      LineGraphConfiguration.prototype.updateTickX = function(n) {
        if (n !== this.svg.xAxis.tick.ticks.length) {
          this.svg.xAxis.tick.ticks = [];
          for (var i = 0; i < n; i++) {
            this.svg.xAxis.tick.ticks.push(i);
          }
        }
        var interval = this.graphWidth / n;
        var start = 0;
        var offset = interval / 2;
        this.graphXLocation = [];
        this.graphXLocationSlice = [];
        for (var j = 0; j < n; j++) {
          if (j !== 0) {
            this.graphXLocationSlice.push(start + offset);
          }
          this.graphXLocation.push(start + offset);
          start += interval;
        }
      };

      LineGraphConfiguration.prototype.updateMaxMinData = function(data) {
        if (!this.updated) {
          this.minData = d3.min([].concat.apply([], data));
          this.maxData = d3.max([].concat.apply([], data));
        }
        this.updated = true;
      };

      LineGraphConfiguration.prototype.updateTickY = function() {
        if (this.svg.yAxis.tick.numOfTicks !== this.svg.yAxis.tick.ticks.length) {
          var minData = this.minData;
          var maxData = this.maxData;
          var data = minData;
          var interval = Math.ceil(((maxData - minData) / (this.svg.yAxis.tick.numOfTicks - 1)) / 10) * 10;
          this.svg.yAxis.tick.ticks = [];
          for (var i = 0; i < this.svg.yAxis.tick.numOfTicks; i++) {
            this.svg.yAxis.tick.ticks.push(data);
            data += interval;
          }
          this.maxData = data - interval;
        }
        this.graphYLocation = [];
        for (var j = 0; j < this.svg.yAxis.tick.ticks.length; j++) {
          var y = this.getY(this.svg.yAxis.tick.ticks[j]);
          this.graphYLocation.push(y);
        }
      };

      LineGraphConfiguration.prototype.getY = function(y) {
        return this.graphHeight - (y / this.maxData) * this.graphHeight;
      };

      return LineGraphConfiguration;
    }
  ]);

'use strict';

angular.module('ark.graphs.multi-line-graph')
  .directive('arkMultiLineGraph', ['ark.graphs.multi-line-graph-config', 'ark.graphs.text-service',
    'ark.graphs.line-service', 'ark.graphs.d3', 'ark.graphs.utils', 'ark.graphs.tooltip-service',
    function(MultiLineGraphConfiguration, TextService, LineService, d3, Utils, TooltipService) {
      return {
        restrict: 'E',
        scope: {
          configuration: '=',
          data: '='
        },
        link: function($scope, element) {

          $scope.internalConfiguration = new MultiLineGraphConfiguration($scope.configuration);
          $scope.initialized = false;
          $scope.previousData = angular.copy($scope.data);

          $scope.selectedDataSetIndex = 0;
          $scope.tooltipDisplayed = false;
          $scope.previouslyEmpty = false;

          $scope.noDataAvailable = function() {
            $scope.widget = d3.select(element[0]);

            $scope.widget.selectAll('*').remove();
            $scope.widget.append('div')
              .attr('class', 'ark-graphs-multi-line-graph-no-data-container')
              .style('text-align', 'center')
              .style('display', 'table')
              .style('width', $scope.internalConfiguration.width + 'px')
              .style('height', $scope.internalConfiguration.height + 'px');

            $scope.widget.select('.ark-graphs-multi-line-graph-no-data-container')
              .append('span')
              .attr('class', 'ark-graphs-multi-line-graph-no-data-message')
              .style('display', 'table-cell')
              .style('vertical-align', 'middle')
              .html($scope.internalConfiguration.data.noDataAvailable);
          };

          $scope.isDataEmpty = function() {
            var allEmpty = true;
            angular.forEach($scope.data, function(line) {
              allEmpty = allEmpty && Boolean(!line.length);
            });
            return allEmpty;
          };

          $scope.draw = function() {
            if ($scope.isDataEmpty()) {
              $scope.previouslyEmpty = true;
              return $scope.init();
            } else if ($scope.previouslyEmpty) {
              $scope.previouslyEmpty = false;
              return $scope.init();
            }
            if (!$scope.data[$scope.selectedDataSetIndex].length) {
              angular.forEach($scope.data, function(data, index) {
                if (data.length) {
                  $scope.selectedDataSetIndex = index;
                }
              });
            }

            $scope.createOrUpdateGraphElements();
            $scope.drawAxis();
            $scope.drawThresholds();

            var paths = $scope.widget.select('.ark-graphs-multi-line-graph-data-lines').selectAll('path');

            paths.transition()
              .attrTween('d', function(d, i) {
                var line = $scope.internalConfiguration.data.binding[i];
                var interpolate = d3.interpolate($scope.previousData[i] || {}, $scope.data[i] || {});
                return function(t) {
                  return $scope.data[i].length ? $scope.lines[line](interpolate(t)) : '';
                };
              })
              .duration($scope.internalConfiguration.transition.duration)
              .each('end', function() {
                $scope.previousData = angular.copy($scope.data);
              });

            angular.forEach($scope.data, function(dataset, lineIndex) {
              var circles = $scope.widget.select('.ark-graphs-multi-line-graph-data-circle-line-' + lineIndex.toString()).selectAll('circle');
              circles.transition()
                .attrTween('cx', function(d, i) {
                  var interpolate = d3.interpolate(
                    $scope.ranges.x($scope.previousData[lineIndex].length ? $scope.previousData[lineIndex][i][$scope.internalConfiguration.xAxis.field] : 0),
                    $scope.ranges.x($scope.data[lineIndex].length ? $scope.data[lineIndex][i][$scope.internalConfiguration.xAxis.field] : 0)
                  );
                  return function(t) {
                    return interpolate(t);
                  };
                })
                .attrTween('cy', function(d, i) {
                  var range = $scope.internalConfiguration.data.binding[lineIndex];
                  var interpolate = d3.interpolate(
                    $scope.ranges.y[range]($scope.previousData[lineIndex].length ? $scope.previousData[lineIndex][i][$scope.internalConfiguration.yAxis[range].field] : 0),
                    $scope.ranges.y[range]($scope.data[lineIndex].length ? $scope.data[lineIndex][i][$scope.internalConfiguration.yAxis[range].field] : 0)
                  );
                  return function(t) {
                    return interpolate(t);
                  };
                })
                .duration($scope.internalConfiguration.transition.duration);
            });
            $scope.drawLegend();
            if ($scope.tooltipDisplayed) {
              TooltipService.showTooltip($scope.tooltip, $scope.data, $scope.closest.index, $scope.selectedDataSetIndex, $scope.internalConfiguration.data.colors, $scope.internalConfiguration.data.labels, $scope.internalConfiguration.data.thresholds.values[$scope.selectedDataSetIndex], $scope.internalConfiguration.data.thresholds.icons[$scope.selectedDataSetIndex], $scope.internalConfiguration.data.thresholds.colors[$scope.selectedDataSetIndex]);
            }
          };

          $scope.drawAxis = function() {
            if ($scope.internalConfiguration.xAxis.display) {
              $scope.widget.select('.ark-graphs-multi-line-graph-x-axis')
                .attr('transform', 'translate(0, ' + ($scope.internalConfiguration.height - $scope.internalConfiguration.margin.top - $scope.internalConfiguration.margin.bottom) + ')')
                .call($scope.axis.x);
            }
            if ($scope.internalConfiguration.yAxis.left.display) {
              $scope.widget.select('.ark-graphs-multi-line-graph-y-left-axis')
                .call($scope.axis.y.left);
            }
            if ($scope.internalConfiguration.yAxis.right.display) {
              $scope.widget.select('.ark-graphs-multi-line-graph-y-right-axis')
                .attr('transform', 'translate(' + ($scope.internalConfiguration.width - $scope.internalConfiguration.margin.left - $scope.internalConfiguration.margin.right) + ', 0)')
                .call($scope.axis.y.right);
            }
          };

          $scope.drawLegend = function() {
            var container = $scope.widget.select('.ark-graphs-multi-line-graph-legend-container');
            container.html('');
            angular.forEach($scope.data, function(dataset, index) {
              var legendItem = container.append('a')
                .attr('class', 'ark-graphs-multi-line-graph-legend-' + index + (($scope.selectedDataSetIndex === index) ? ' selected' : ''))
                .on('click', function() {
                  if ($scope.data[index].length) {
                    $scope.selectedDataSetIndex = index;
                    $scope.drawLegend();
                    $scope.updateThresholds();
                    $scope.createOrUpdateGraphElements();
                  }
                });

              var data = $scope.data[index];
              var side = $scope.internalConfiguration.data.binding[index];

              legendItem.append('span')
                .attr('class', 'color')
                .style('background-color', $scope.internalConfiguration.data.colors[index]);
              legendItem.append('span')
                .attr('class', 'value')
                .html((data.length) ? data[data.length - 1][$scope.internalConfiguration.yAxis[side].field] : '');
              legendItem.append('span')
                .attr('class', 'label')
                .html($scope.internalConfiguration.data.labels[index]);
            });
          };

          $scope.drawThresholds = function() {
            $scope.widget.select('.ark-graphs-multi-line-graph-threshold-lines').selectAll('line').remove();
            $scope.widget.select('.ark-graphs-multi-line-graph-threshold-lines').selectAll('line')
              .data($scope.internalConfiguration.data.thresholds.values[$scope.selectedDataSetIndex])
              .enter()
              .append('line')
              .attr('x1', 0)
              .attr('x2', ($scope.internalConfiguration.width - $scope.internalConfiguration.margin.left - $scope.internalConfiguration.margin.right))
              .attr('y1', function(d) {
                var side = $scope.internalConfiguration.data.binding[$scope.selectedDataSetIndex];
                return $scope.ranges.y[side](d);
              })
              .attr('y2', function(d) {
                var side = $scope.internalConfiguration.data.binding[$scope.selectedDataSetIndex];
                return $scope.ranges.y[side](d);
              })
              .attr('stroke', function(d, i) {
                return $scope.internalConfiguration.data.thresholds.colors[$scope.selectedDataSetIndex][i];
              })
              .attr('stroke-linecap', 'square')
              .attr('stroke-dasharray', $scope.internalConfiguration.data.thresholds.dash);
          };

          $scope.updateThresholds = function() {
            var thresholds = $scope.widget.select('.ark-graphs-multi-line-graph-threshold-lines').selectAll('line');
            thresholds.transition()
              .attr('x1', 0)
              .attr('x2', ($scope.internalConfiguration.width - $scope.internalConfiguration.margin.left - $scope.internalConfiguration.margin.right))
              .attrTween('y1', function(d, i) {
                var side = $scope.internalConfiguration.data.binding[$scope.selectedDataSetIndex];
                var interpolate = d3.interpolate(d, $scope.internalConfiguration.data.thresholds.values[$scope.selectedDataSetIndex][i]);
                return function(t) {
                  return $scope.ranges.y[side](interpolate(t));
                };
              })
              .attrTween('y2', function(d, i) {
                var side = $scope.internalConfiguration.data.binding[$scope.selectedDataSetIndex];
                var interpolate = d3.interpolate(d, $scope.internalConfiguration.data.thresholds.values[$scope.selectedDataSetIndex][i]);
                return function(t) {
                  return $scope.ranges.y[side](interpolate(t));
                };
              })
              .attr('stroke', function(d, i) {
                return $scope.internalConfiguration.data.thresholds.colors[$scope.selectedDataSetIndex][i];
              })
              .duration(500);
          };

          $scope.drawThresholdIcon = function() {
            var side = $scope.internalConfiguration.data.binding[$scope.selectedDataSetIndex];
            var value = $scope.data[$scope.selectedDataSetIndex].length ? $scope.data[$scope.selectedDataSetIndex][$scope.closest.index][$scope.internalConfiguration.yAxis[side].field] : undefined;
            var icon = null;
            var color = null;

            if (value) {
              angular.forEach($scope.internalConfiguration.data.thresholds.values[$scope.selectedDataSetIndex], function(threshold, index) {
                if (value > threshold) {
                  icon = $scope.internalConfiguration.data.thresholds.icons[$scope.selectedDataSetIndex][index];
                  color = $scope.internalConfiguration.data.thresholds.colors[$scope.selectedDataSetIndex][index];
                }
              });
            }

            var container = $scope.widget.select('.ark-graphs-multi-line-graph-threshold-icon-container');
            container.html('');
            container.append('span')
              .attr('class', 'ark-graphs-multi-line-graph-threshold-top-icon fonticon ' + icon)
              .style('color', color)
              .style('font-size', $scope.internalConfiguration.data.thresholds.iconFontsize + 'px')
              .style('left', ($scope.ranges.x($scope.closest.value[$scope.internalConfiguration.xAxis.field]) - $scope.internalConfiguration.data.thresholds.iconFontsize / 2) + 'px');
          };

          $scope.drawMouseEventOrInitial = function() {
            $scope.highlightCircles($scope.closest.index);
            var x = $scope.ranges.x($scope.closest.value[$scope.internalConfiguration.xAxis.field]) || 0;
            $scope.widget.select('.ark-graphs-multi-line-graph-hover-line')
              .attr('x1', x)
              .attr('x2', x);

            $scope.drawThresholdIcon();
          };

          $scope.mousemove = function() {
            var x = $scope.ranges.x.invert(d3.mouse(this)[0]);
            $scope.closest = $scope.findClosestIndexTo(x);
            TooltipService.showTooltip($scope.tooltip, $scope.data, $scope.closest.index, $scope.selectedDataSetIndex, $scope.internalConfiguration.data.colors, $scope.internalConfiguration.data.labels, $scope.internalConfiguration.data.thresholds.values[$scope.selectedDataSetIndex], $scope.internalConfiguration.data.thresholds.icons[$scope.selectedDataSetIndex], $scope.internalConfiguration.data.thresholds.colors[$scope.selectedDataSetIndex]);
            TooltipService.setCoordinates($scope.tooltip, $scope.ranges.x($scope.closest.value[$scope.internalConfiguration.xAxis.field]), d3.event.pageY + 10);
            $scope.tooltipDisplayed = true;
            $scope.drawMouseEventOrInitial();
          };

          $scope.rescaleLines = function() {
            if ($scope.internalConfiguration.xAxis.rangePredefined) {
              LineService.scale($scope.ranges.x, $scope.internalConfiguration.xAxis.range);
            } else {
              LineService.scaleFromData($scope.ranges.x, $scope.data, $scope.internalConfiguration.xAxis.field, $scope.internalConfiguration.data.offset);
            }
            if ($scope.internalConfiguration.yAxis.left.rangePredefined) {
              LineService.scale($scope.ranges.y.left, $scope.internalConfiguration.yAxis.left.range);
            } else {
              LineService.scaleFromData($scope.ranges.y.left, $scope.data, $scope.internalConfiguration.yAxis.left.field, $scope.internalConfiguration.yAxis.left.offset);
            }
            if ($scope.internalConfiguration.yAxis.right.rangePredefined) {
              LineService.scale($scope.ranges.y.right, $scope.internalConfiguration.yAxis.right.range);
            } else {
              LineService.scaleFromData($scope.ranges.y.right, $scope.data, $scope.internalConfiguration.yAxis.right.field, $scope.internalConfiguration.yAxis.right.offset);
            }
          };

          $scope.highlightCircles = function() {
            var circles = $scope.widget.select('.ark-graphs-multi-line-graph-data-circles').selectAll('circle');
            circles.attr('r', $scope.internalConfiguration.data.circles.radius);

            var selected = $scope.widget.select('.ark-graphs-multi-line-graph-data-circles').selectAll('[index="' + $scope.closest.index + '"]');
            selected.attr('r', $scope.internalConfiguration.data.circles.hover.radius);
          };

          $scope.findClosestIndexTo = function(value) {
            var bisector = d3.bisector(function(d) {
              return d ? d[$scope.internalConfiguration.xAxis.field] : 0;
            }).left;
            var found = 0;
            var index = 0;
            var tmp;
            var d = $scope.data[$scope.selectedDataSetIndex];
            //angular.forEach($scope.data, function(d) {
            if (d.length) {
              var i = bisector(d, value, 1);
              var d0 = d[i - 1];
              var d1 = d[i];
              if (!d1) {
                tmp = d0;
              } else {
                tmp = value - d0[$scope.internalConfiguration.xAxis.field] > d0[$scope.internalConfiguration.xAxis.field] - value ? d1 : d0;
              }
              if ((index === 0) || (value - found[$scope.internalConfiguration.xAxis.field] > tmp[$scope.internalConfiguration.xAxis.field] - value)) {
                found = tmp;
                index = (found === d0) ? (i - 1) : i;
              }
            }
            //});
            return {
              index: index,
              value: found
            };
          };

          $scope.createOrUpdateGraphElements = function() {
            $scope.ranges = {
              x: LineService.createRange(0, ($scope.internalConfiguration.width - $scope.internalConfiguration.margin.left - $scope.internalConfiguration.margin.right)),
              y: {
                left: LineService.createLinearRange(($scope.internalConfiguration.height - $scope.internalConfiguration.margin.top - $scope.internalConfiguration.margin.bottom), 0),
                right: LineService.createLinearRange(($scope.internalConfiguration.height - $scope.internalConfiguration.margin.top - $scope.internalConfiguration.margin.bottom), 0)
              }
            };

            $scope.axis = {
              x: LineService.createAxis($scope.ranges.x, $scope.internalConfiguration.xAxis.ticks, 'bottom'),
              y: {
                left: LineService.createAxis($scope.ranges.y.left, $scope.internalConfiguration.yAxis.left.ticks, 'left').tickFormat($scope.internalConfiguration.yAxis.left.tickFormat),
                right: LineService.createAxis($scope.ranges.y.right, $scope.internalConfiguration.yAxis.right.ticks, 'right').tickFormat($scope.internalConfiguration.yAxis.right.tickFormat)
              }
            };

            if ($scope.internalConfiguration.grid.display) {
              $scope.axis.x.innerTickSize(-($scope.internalConfiguration.height - $scope.internalConfiguration.margin.top - $scope.internalConfiguration.margin.bottom));
              if ($scope.internalConfiguration.data.binding[$scope.selectedDataSetIndex] === 'left') {
                $scope.axis.y.left.innerTickSize(-($scope.internalConfiguration.width - $scope.internalConfiguration.margin.left - $scope.internalConfiguration.margin.right));
                $scope.axis.y.right.innerTickSize(0);
              } else {
                $scope.axis.y.right.innerTickSize(-($scope.internalConfiguration.width - $scope.internalConfiguration.margin.left - $scope.internalConfiguration.margin.right));
                $scope.axis.y.left.innerTickSize(0);
              }
            }

            $scope.lines = {
              left: LineService.createLine($scope.ranges.x, $scope.ranges.y.left, $scope.internalConfiguration.xAxis.field, $scope.internalConfiguration.yAxis.left.field), //lines that refers to the left y axis
              right: LineService.createLine($scope.ranges.x, $scope.ranges.y.right, $scope.internalConfiguration.xAxis.field, $scope.internalConfiguration.yAxis.right.field) //lines that refers to the right y axis
            };

            $scope.rescaleLines();
          };

          $scope.getDefaultSelectedItem = function() {
            var maxIndex = 0;
            var currentValue = {};
            angular.forEach($scope.data, function(d) {
              if (maxIndex < d.length) {
                maxIndex = d.length - 1;
                currentValue = d[maxIndex];
              }
            });
            return {
              index: maxIndex,
              value: currentValue
            };
          };

          $scope.init = function() {
            if ($scope.isDataEmpty()) {
              return $scope.noDataAvailable();
            }
            $scope.createOrUpdateGraphElements();

            $scope.widget = d3.select(element[0]);

            $scope.widget.selectAll('*').remove();

            $scope.widget.append('div')
              .attr('class', 'ark-graphs-multi-line-graph-threshold-icon-container')
              .style('width', ($scope.internalConfiguration.width - $scope.internalConfiguration.margin.left - $scope.internalConfiguration.margin.right) + 'px')
              .style('height', $scope.internalConfiguration.data.thresholds.iconFontsize + 'px')
              .style('left', $scope.internalConfiguration.margin.left + 'px');

            $scope.widget.append('svg')
              .attr('class', 'ark-graphs-multi-line-graph-svg')
              .attr('width', $scope.internalConfiguration.width + 'px')
              .attr('height', $scope.internalConfiguration.height + 'px')
              .append('g')
              .attr('class', 'ark-graphs-multi-line-graph-container')
              .attr('transform', 'translate(' + $scope.internalConfiguration.margin.left + ', ' + $scope.internalConfiguration.margin.top + ')');

            $scope.widget.append('div')
              .attr('class', 'ark-graphs-multi-line-graph-legend-container')
              .attr('width', $scope.internalConfiguration.width + 'px');

            var svg = $scope.widget.select('.ark-graphs-multi-line-graph-container');

            svg.append('defs')
              .append('clipPath')
              .attr('id', 'ark-graphs-multi-line-graph-clipPath-' + $scope.internalConfiguration.id)
              .append('rect')
              .attr('x', 0)
              .attr('y', 0)
              .attr('width', ($scope.internalConfiguration.width - $scope.internalConfiguration.margin.left - $scope.internalConfiguration.margin.right) + 'px')
              .attr('height', ($scope.internalConfiguration.height - $scope.internalConfiguration.margin.top - $scope.internalConfiguration.margin.bottom) + 'px');

            if ($scope.internalConfiguration.xAxis.display) {
              svg.append('g')
                .attr('class', 'x axis ark-graphs-multi-line-graph-x-axis');
            }
            if ($scope.internalConfiguration.yAxis.left.display) {
              svg.append('g')
                .attr('class', 'y axis ark-graphs-multi-line-graph-y-left-axis');
            }
            if ($scope.internalConfiguration.yAxis.right.display) {
              svg.append('g')
                .attr('class', 'y axis ark-graphs-multi-line-graph-y-right-axis');
            }

            $scope.drawAxis();

            //Create main container for graph
            svg.append('g')
              .attr('class', 'ark-graphs-multi-line-graph-data')
              .style('clip-path', 'url(#ark-graphs-multi-line-graph-clipPath-' + $scope.internalConfiguration.id + ')');

            var graphContainer = svg.select('.ark-graphs-multi-line-graph-data');

            graphContainer.append('g')
              .attr('class', 'ark-graphs-multi-line-graph-data-lines');

            graphContainer.append('line')
              .attr('class', 'ark-graphs-multi-line-graph-hover-line');

            graphContainer.append('g')
              .attr('class', 'ark-graphs-multi-line-graph-threshold-lines');

            graphContainer.append('g')
              .attr('class', 'ark-graphs-multi-line-graph-data-circles');

            angular.forEach($scope.data, function(dataset, i) {
              graphContainer.select('.ark-graphs-multi-line-graph-data-circles')
                .append('g')
                .attr('class', 'ark-graphs-multi-line-graph-data-circle-line-' + i.toString());
            });

            graphContainer.select('.ark-graphs-multi-line-graph-hover-line')
              .attr('x1', 0)
              .attr('x2', 0)
              .attr('y1', 0)
              .attr('y2', $scope.internalConfiguration.height - $scope.internalConfiguration.margin.top - $scope.internalConfiguration.margin.bottom)
              .attr('stroke-linecap', 'square')
              .attr('stroke-dasharray', $scope.internalConfiguration.data.guideline.dash);

            if ($scope.isDataEmpty()) {
              return;
            }
            //Otherwise fill in widget with data
            graphContainer.select('.ark-graphs-multi-line-graph-data-lines').selectAll('path')
              .data($scope.data)
              .enter()
              .append('path')
              .attr('d', function(d, i) {
                var line = $scope.internalConfiguration.data.binding[i];
                return d ? $scope.lines[line](d) : '';
              })
              .attr('stroke', function(d, i) {
                return $scope.internalConfiguration.data.colors[i];
              });

            if ($scope.internalConfiguration.data.thresholds.display) {
              $scope.drawThresholds();
            }

            if ($scope.internalConfiguration.data.circles.display) {
              angular.forEach($scope.data, function(dataset, i) {
                graphContainer.select('.ark-graphs-multi-line-graph-data-circle-line-' + i.toString()).selectAll('circle')
                  .data(dataset)
                  .enter()
                  .append('circle')
                  .attr('fill', function() {
                    return $scope.internalConfiguration.data.colors[i];
                  })
                  .attr('r', $scope.internalConfiguration.data.circles.radius)
                  .attr('index', function(d, j) {
                    return j;
                  })
                  .attr('cx', function(d) {
                    return $scope.ranges.x(d[$scope.internalConfiguration.xAxis.field]);
                  })
                  .attr('cy', function(d) {
                    var range = $scope.internalConfiguration.data.binding[i];
                    return $scope.ranges.y[range](d[$scope.internalConfiguration.yAxis[range].field]);
                  });
              });
            }
            svg.append('rect')
              .attr('class', 'ark-graphs-multi-line-graph-overlay')
              .attr('width', $scope.internalConfiguration.width - $scope.internalConfiguration.margin.left - $scope.internalConfiguration.margin.right)
              .attr('height', $scope.internalConfiguration.height - $scope.internalConfiguration.margin.top - $scope.internalConfiguration.margin.bottom)
              .on('mousemove', $scope.mousemove)
              .on('mouseover', function() {
                $scope.widget.select('.ark-graphs-multi-line-graph-hover-line')
                  .style('display', 'block');
              })
              .on('mouseout', function() {
                TooltipService.hideTooltip($scope.tooltip);
                $scope.closest = $scope.getDefaultSelectedItem();
                $scope.drawMouseEventOrInitial();
                $scope.tooltipDisplayed = false;
              });

            TooltipService.initTooltip($scope, 'multi-line-graph', $scope.internalConfiguration.id, $scope.internalConfiguration.tooltip.format);
            $scope.closest = $scope.getDefaultSelectedItem();
            $scope.drawMouseEventOrInitial();
            $scope.drawLegend();
            $scope.initialized = true;
          };

          $scope.init();

          $scope.$watch('configuration', function() {
            $scope.initialized = false;
            $scope.internalConfiguration.update($scope.configuration);
            $scope.init();
          }, true);

          $scope.$watch(function() {
            var e = angular.element(element[0].parentElement);
            return Utils.getTrueWidth(e[0]);
          }, function(value) {
            if ($scope.internalConfiguration.autofit) {
              $scope.internalConfiguration.width = value;
              $scope.internalConfiguration.update($scope.internalConfiguration);
              $scope.initialized = false;
              $scope.init();
            }
          }, true);

          $scope.$watch('data', function() {
            if ($scope.initialized) {
              $scope.draw();
            }
          });
        }
      };
    }
  ]);

'use strict';

angular.module('ark.graphs.multi-line-graph')
  .factory('ark.graphs.multi-line-graph-config', ['ark.graphs.color-service', 'ark.graphs.utils', 'ark.graphs.config-service', 'ark.graphs.d3',
    function(ColorService, Utils, ConfigService, d3) {
      var MultiLineGraphConfiguration = function(configuration) {
        this.type = 'multi-line-graph';
        this.id = Utils.generateID(this.type);
        this.autoresize = false;

        this.width = 600;
        this.height = 280;

        this.autofit = true; //Widget will automatically fit to parent container's width

        this.fontsize = 12;
        this.yAxis = {
          left: {
            display: true,
            rangePredefined: false,
            range: [0, 100], //Only used if rangePredefined is true
            offset: 0.1,
            field: 'value',
            label: 'y-left-axis label (unit)',
            ticks: 4,
            tickFormat: function(d) {
              return d3.format(',.0f')(d);
            }
          },
          right: {
            display: true,
            rangePredefined: true,
            range: [0, 100], //Only used if rangePredefined is true
            offset: 0.1,
            field: 'value',
            label: 'y-right-axis label (unit)',
            ticks: 3,
            tickFormat: function(d) {
              return d + ' %';
            }
          }
        };
        this.xAxis = {
          display: true,
          rangePredefined: false,
          range: [0, 100], //Only used if rangePredefined is true
          label: 'x-axis label (unit)',
          field: 'time',
          ticks: 3
        };
        this.grid = {
          display: true
        };
        this.margin = {
          left: 40,
          top: 10,
          right: 40,
          bottom: 30
        };

        this.data = {
          offset: 0.1, //Space left between the end of lines end right axis here = 1/10 of total range
          binding: ['left', 'left', 'right'], //Ordered array to determine on which axis the data is bound
          noDataAvailable: 'No Data Available.',
          colors: ColorService.arkBlueColors(),
          thresholds: {
            display: true,
            values: [
              [1000, 3000, 4000],
              [100, 300, 500],
              [10, 30, 70]
            ],
            colors: [ColorService.getStatusColors(3), ColorService.getStatusColors(3), ColorService.getStatusColors(3)],
            icons: [
              ['icon-alert-circle', 'icon-alert-triangle', 'icon-alert-checkmark'],
              ['icon-alert-circle', 'icon-alert-triangle', 'icon-alert-checkmark'],
              ['icon-alert-circle', 'icon-alert-triangle', 'icon-alert-checkmark']
            ],
            iconFontsize: 16, // size in px
            dash: '4,3'
          },
          guideline: {
            dash: '7,5'
          },
          labels: ['Line A', 'Line B', 'Line C'],
          circles: {
            display: true,
            radius: 0,
            hover: {
              radius: 8
            }
          }
        };

        this.transition = {
          duration: 1000
        };

        this.tooltip = {
          display: true,
          format: function(data, indexSelected, lineIndexSelected, colors, labels, thresholds, icons, thresholdColors) {
            var tableData = '';
            var time = (data[lineIndexSelected].length) ? data[lineIndexSelected][indexSelected].time : 0;
            var date = new Date(parseInt(time));
            var hours = date.getHours();
            var minutes = '0' + date.getMinutes();
            var formattedTime = hours + ':' + minutes.substr(-2);
            var thresholdIndex = 0;
            var value = (data[lineIndexSelected].length) ? data[lineIndexSelected][indexSelected].value : 0;
            angular.forEach(thresholds, function(threshold, index) {
              if (value > threshold) {
                thresholdIndex = index;
              }
            });
            for (var i = 0; i < data.length; i++) {
              if (data[i].length && data[i][indexSelected]) {
                tableData += '<tr>' +
                  '<td class="color">' +
                  '<span style="background-color: ' + colors[i] + ';"></span>' +
                  '</td>' +
                  '<td class="value">' +
                  '<span>' + data[i][indexSelected].value + ((i === 2) ? '%' : '') + '</span>' +
                  '</td>' +
                  '<td class="label">' +
                  '<span>' + labels[i] + '</span>' +
                  '</td>' +
                  '<td class="icon">';
                if (i === lineIndexSelected) {
                  tableData += '<span ng-show="' + (i === lineIndexSelected) + '" class="fonticon ' + icons[thresholdIndex] + '" style="color:' + thresholdColors[thresholdIndex] + ';"></span>';
                }
                tableData += '</td></tr>';
              }
            }
            return '<table class="ark-graphs-multi-line-graph-tooltip"><thead><th class="header" colspan="4">' + formattedTime + '</th></thead><tbody>' + tableData + '</tbody></table>';
          }
        };

        this.legend = {
          display: true,
          format: function(d, i) {
            return d;
          }
        };

        this.update(configuration);
      };

      MultiLineGraphConfiguration.prototype.update = function(configuration) {
        Utils.mergeRecursive(this, configuration);
      };

      return MultiLineGraphConfiguration;
    }
  ]);

'use strict';

angular.module('ark.graphs.spark-line')
  .directive('arkSparkLine', ['ark.graphs.spark-line-config', 'ark.graphs.text-service',
    'ark.graphs.line-service', 'ark.graphs.d3', 'ark.graphs.utils', 'ark.graphs.tooltip-service',
    'ark.graphs.threshold-service',
    function(SparkLineConfiguration, TextService, LineService, d3, Utils, TooltipService, ThresholdService) {
      return {
        restrict: 'E',
        scope: {
          configuration: '=',
          data: '='
        },
        link: function($scope, element) {

          $scope.internalConfiguration = new SparkLineConfiguration($scope.configuration);
          $scope.originalStrokeWidth = $scope.internalConfiguration.data.strokeWidth;
          $scope.originalRadius = $scope.internalConfiguration.data.circle.r;
          $scope.svgWidth = $scope.internalConfiguration.svg.width;

          $scope.prepareLine = function() {
            var strokeWidth = $scope.internalConfiguration.data.strokeWidth - 1;
            var r = $scope.internalConfiguration.data.circle.r;
            $scope.x = d3.scale.ordinal()
              .domain($scope.data.map(function(d, i) {
                return i;
              }))
              .rangePoints([0, $scope.internalConfiguration.svg.width]);

            $scope.y = d3.scale.linear()
              .domain([0, $scope.max])
              .range([$scope.internalConfiguration.svg.height - strokeWidth - r, strokeWidth + r]);

            $scope.line = d3.svg.line()
              .interpolate('basis')
              .x(function(d, i) {
                return $scope.x(i);
              })
              .y(function(d) {
                return $scope.y(d);
              });
          };

          $scope.draw = function() {
            $scope.widget.select('.ark-graphs-spark-line-path')
              .attr('d', $scope.line($scope.data))
              .attr('stroke', function() {
                return ThresholdService.getDataColor(parseInt(($scope.data[$scope.data.length - 1] / $scope.max) * 100, 10), $scope.internalConfiguration);
              });

            $scope.widget.select('.ark-graphs-spark-line-tip')
              .attr({
                'cx': $scope.internalConfiguration.svg.width,
                'cy': $scope.y($scope.data[$scope.data.length - 1]),
                'r': $scope.internalConfiguration.data.circle.r,
                'fill': ThresholdService.getDataColor(parseInt(($scope.data[$scope.data.length - 1] / $scope.max) * 100, 10), $scope.internalConfiguration)
              });

            TextService.showTextUpdate($scope.internalConfiguration, $scope.widget, [parseInt(($scope.data[$scope.data.length - 1] / $scope.max) * 100, 10)]);
            $scope.widget.select('.ark-graphs-spark-line-legend-name')
              .style('width', $scope.internalConfiguration.objectName.width.toString() + 'px');
          };

          $scope.update = function() {
            $scope.internalConfiguration.data.strokeWidth = 0.6 * $scope.internalConfiguration.svg.width / $scope.svgWidth * $scope.originalStrokeWidth;
            $scope.internalConfiguration.data.circle.r = 0.6 * $scope.internalConfiguration.svg.width / $scope.svgWidth * $scope.originalRadius;
          };

          $scope.init = function() {
            $scope.widget = d3.select(element[0]);
            $scope.widget.selectAll('*').remove();

            $scope.max = d3.max($scope.data);

            var div = $scope.widget
              .append('div')
              .attr('class', 'ark-graphs-spark-line-div')
              .style('width', $scope.internalConfiguration.div.width.toString() + 'px')
              .style('height', $scope.internalConfiguration.div.height.toString() + 'px')
              .style('padding-top', ($scope.internalConfiguration.div.padding.top - $scope.internalConfiguration.div.border.top.width).toString() + 'px')
              .style('padding-bottom', $scope.internalConfiguration.div.padding.bottom.toString() + 'px')
              .style('border-top', 'solid')
              .style('border-top-width', $scope.internalConfiguration.div.border.top.width.toString() + 'px')
              .style('border-top-color', $scope.internalConfiguration.div.border.top.color)
              .style('position', 'relative');

            var svg = div
              .append('svg')
              .attr('class', 'ark-graphs-spark-line-svg')
              .attr('width', $scope.internalConfiguration.svg.width + $scope.internalConfiguration.data.circle.r)
              .attr('height', $scope.internalConfiguration.svg.height + $scope.internalConfiguration.data.circle.r * 2)
              .style('position', 'absolute')
              .style('left', $scope.internalConfiguration.svg.position.left + 'px')
              .append('g');

            $scope.prepareLine();

            svg.append('path')
              .attr('d', $scope.line($scope.data))
              .attr('class', 'ark-graphs-spark-line-path')
              .attr('fill', 'none')
              .attr('stroke', function() {
                return ThresholdService.getDataColor(parseInt(($scope.data[$scope.data.length - 1] / $scope.max) * 100, 10), $scope.internalConfiguration);
              })
              .attr('stroke-width', $scope.internalConfiguration.data.strokeWidth);

            svg.append('circle')
              .attr('class', 'ark-graphs-spark-line-tip');

            ThresholdService.initThresholdValues($scope.internalConfiguration);

            TextService.showText($scope.internalConfiguration, $scope.widget, [parseInt(($scope.data[$scope.data.length - 1] / $scope.max) * 100, 10)]);
            $scope.widget.select('.ark-graphs-spark-line-legend-text').select('.metric-name')
              .style('width', ($scope.internalConfiguration.autoresize ? $scope.internalConfiguration.objectName.width : $scope.internalConfiguration.legend.width).toString() + 'px');
          };

          if ($scope.internalConfiguration.autoresize) {
            Utils.resize($scope.internalConfiguration, element);
            if (!$scope.internalConfiguration.autosnap.enabled) {
              $scope.update();
            }
          }

          $scope.init();

          //Check for resizing
          $scope.$watch(function() {
            var e = angular.element(element[0].parentElement);
            return Utils.getTrueWidth(e[0]);
          }, function() {
            if ($scope.internalConfiguration.autoresize) {
              Utils.resize($scope.internalConfiguration, element);
              if (!$scope.internalConfiguration.autosnap.enabled) {
                $scope.update();
              }
              $scope.init();
              $scope.draw($scope.data);
            }
          }, true);

          //Check for changes in internalConfiguration
          $scope.$watch('configuration', function() {
            $scope.internalConfiguration.update($scope.configuration);
            $scope.init();
            $scope.draw();
          }, true);

          //Check for changes in data
          $scope.$watch('data', function() {
            return $scope.draw();
          }, true);
        }
      };
    }
  ]);

'use strict';

angular.module('ark.graphs.spark-line')
  .factory('ark.graphs.spark-line-config', ['ark.graphs.color-service',
    'ark.graphs.utils', 'ark.graphs.config-service',
    function(ColorService, Utils, ConfigService) {
      var SparkLineConfiguration = function(configuration, data) {

        this.type = 'spark-line';
        this.id = Utils.generateID(this.type);
        this.numerOfData = 1;
        this.autoresize = false;

        this.div = {
          width: 208,
          height: 40,
          border: {
            top: {
              width: 1,
              color: '#E3E9EF'
            }
          }
        };

        this.svg = {
          width: 72,
          height: 24,
          position: {
            left: 72
          }
        };

        this.objectName = {
          width: 64
        };

        this.initialRatio = {
          svgWidth: this.svg.width / this.div.width,
          svgPositionLeft: this.svg.position.left / this.div.width,
          objectNameWidth: this.objectName.width / this.div.width
        };

        this.legend = {
          display: true,
          fontsize: 12,
          title: ['Metric name'],
          format: function(d, i) {
            return d;
          },
          letters: {
            display: false
          },
          padding: {
            top: 0,
            left: 0,
            right: 20
          },
          icon: {
            display: true
          }
        };

        this.data = {
          circle: {
            r: 1.5
          },
          strokeWidth: 1.5,
          thresholds: {
            display: true,
            values: [25, 50, 75],
            statusColors: ColorService.getStatusColors(2),
            comparator: function(value, threshold) {
              return value < threshold;
            }
          }
        };

        this.autosnap = {
          enabled: false,
          threshold: 516,
          smallConfig: {
            div: {
              width: 208,
              height: 40
            },
            data: {
              strokeWidth: 1.5,
              circle: {
                r: 1.5
              }
            }
          },
          largeConfig: {
            div: {
              width: 516,
              height: 40
            },
            data: {
              strokeWidth: 2,
              circle: {
                r: 2
              }
            }
          }
        };

        this.update(configuration, data);
      };

      SparkLineConfiguration.prototype.update = function(configuration) {
        Utils.mergeRecursive(this, configuration);
        ConfigService.getStatusColors(this);

        if (this.autoresize) {
          this.svg.width = this.initialRatio.svgWidth * this.div.width;
          this.svg.position.left = this.initialRatio.svgPositionLeft * this.div.width;
          this.objectName.width = this.initialRatio.objectNameWidth * this.div.width;
        }

        var paddingHeight = this.div.height - this.svg.height;

        this.div.padding = {
          top: paddingHeight / 2,
          bottom: paddingHeight / 2,
        };

        this.legend.width = this.div.width;
        this.legend.height = this.svg.height;
        this.legend.lineHeight = this.svg.height;
      };

      return SparkLineConfiguration;
    }
  ]);

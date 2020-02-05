describe('Chart Factory', function () {
  var ChartFactory, data;

  beforeEach(angular.mock.module("slr.components"));
  beforeEach(angular.mock.module("slr.chart"));
  beforeEach(angular.mock.module("tests_js_factory"));

  beforeEach(angular.mock.inject(function (_ChartFactory_, _TestsFactory_) {
    ChartFactory = _ChartFactory_;
    data = _TestsFactory_.getAnalysisMockClassificationData();
  }));

  xit('getFilterValue', function () {

  });

  xit('setTimeTooltip', function () {

  });

  xit('setXAxisTimeFormat', function () {

  });

  xit('d3Call', function () {

  });

  xit('getDefinedColors', function () {

  });

  xit('getOrdinalColors', function () {

  });

  xit('getGenesysColors', function () {

  });

  xit('parseMetricsData', function () {

  });

  xit('parseTrendsData', function () {

  });

});
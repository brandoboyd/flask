describe('Analysis Regression Factory', function () {
  var AnalysisRegression;
  var data;
  var Utils;

  beforeEach(angular.mock.module("slr.components"));
  beforeEach(angular.mock.module("slr.analysis"));
  beforeEach(angular.mock.module("tests_js_factory"));

  beforeEach(angular.mock.inject(function (_AnalysisRegression_, _Utils_, _TestsFactory_) {
    AnalysisRegression = _AnalysisRegression_;
    Utils = _Utils_;
    data = _TestsFactory_.getAnalysisMockRegressionData();
  }));

  it('getSelectedFeatureData - Overall', function () {
    data.feature = 'Overall';
    AnalysisRegression.getSelectedFeatureData(data, function (res) {
      expect(res).toBeDefined();
      expect(res.charts.length).toBe(1);
      expect(res.charts[0].settings.chart_type).toBe('LINEBAR');
      expect(res.flags).toBeDefined();
      expect(res.flags.showMultichart).toBeTruthy();
    });
  });

  it('getSelectedFeatureData - Categorical Feature', function() {
    data.feature = _.findWhere(data.report.parsedResults, function (each) {
      return each.value.value_type === 'Label';
    }).key;

    AnalysisRegression.getSelectedFeatureData(data, function (res) {
      expect(res).toBeDefined();
      // expect(res.charts.length).toBe(2);  // currently scatter and pie charts are disabled
      expect(res.charts.length).toBe(1);

      var chartTypes = _.map(res.charts, function(r) {return r.settings.chart_type});

      // expect(chartTypes.sort()).toEqual(['BOXPLOT', 'PIE']);
      expect(chartTypes.sort()).toEqual(['BOXPLOT']);  // currently scatter and pie charts are disabled
      expect(res.flags).toBeDefined();
      expect(res.flags.showBoxChart).toBeTruthy();
      // expect(res.flags.showPie).toBeTruthy();
    });
  });

  it('getSelectedFeatureData - Numeric Feature', function() {
    data.feature = _.findWhere(data.report.parsedResults, function (each) {
      return each.value.value_type === 'Numeric';
    }).key;

    AnalysisRegression.getSelectedFeatureData(data, function (res) {
      expect(res).toBeDefined();
      // expect(res.charts.length).toBe(3);  // currently scatter and pie charts are disabled
      expect(res.charts.length).toBe(2);

      var chartTypes = _.map(res.charts, function(r) {return r.settings.chart_type});

      // expect(chartTypes.sort()).toEqual(['BAR', 'BOXPLOT', 'SCATTER']);  // currently scatter and pie charts are disabled
      expect(chartTypes.sort()).toEqual(['BAR', 'BOXPLOT']);
      expect(res.flags).toBeDefined();
      expect(res.flags.showBar).toBeFalsy(); // we generate barchart, but dont show it until user switch to it
      expect(res.flags.showBoxChart).toBeTruthy();
      // expect(res.flags.showScatter).toBeTruthy();
    });
  });

  xit('buildTable', function () {
  });

});
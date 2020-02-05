describe('Analysis Classification Factory', function () {
  var AnalysisClassification, data;

  beforeEach(angular.mock.module("slr.components"));
  beforeEach(angular.mock.module("slr.analysis"));
  beforeEach(angular.mock.module("tests_js_factory"));

  beforeEach(angular.mock.inject(function (_AnalysisClassification_, _TestsFactory_) {
    AnalysisClassification = _AnalysisClassification_;
    data = _TestsFactory_.getAnalysisMockClassificationData();
  }));

  // TODO: also check flags binary value

  it('getPositions', function () {
    var cr = {
      key: "CSAT",
      value: {
        "0": "20",
        "1": "40",
        "2": "40"
      }
    };
    var positions = AnalysisClassification.getPositions(cr, data.report.buckets);
    var metric = _.chain(positions)
      .pluck('key')
      .flatten()
      .value()[0];

    expect(metric).toBe('CSAT');
    expect(positions.length).toBeTruthy();
    expect(positions.length).toBe(3);
  });

  it('getPositions - with n/a, e.g. -1 bucket', function () {
    var cr = {
      key: "CSAT",
      value: {
        "0": "20",
        "1": "40",
        "2": "20",
        "-1": "20"
      }
    };
    var positions = AnalysisClassification.getPositions(cr, data.report.buckets);
    var notavailableBucket = _.find(positions, {bucket: 'N/A'});
    expect(positions.length).toBeTruthy();
    expect(positions.length).toBe(4);
    expect(notavailableBucket).toBeDefined();
  });

  it('getSelectedFeatureData - Overall', function () {
    data.feature = 'Overall';
    AnalysisClassification.getSelectedFeatureData(data, function (res) {
      expect(res).toBeDefined();
      // we are passing only 1 feature
      expect(res.charts.length).toBe(1);
      // in Overall, we render only Trendline which is 100% width LINE chart
      expect(res.charts[0].settings.chart_type).toBe('LINE');
      expect(res.flags).toBeDefined();
      expect(res.flags.showTrend).toBeTruthy();
      expect(res.charts[0].width).toBe(100);
    });
  });

  it('getTrendData', function () {
    var trendData = AnalysisClassification.getTrendData(data.report.timerange_results, data.report.buckets);
    expect(trendData.length).toBeTruthy();
    checkObjectKeys(trendData[0], ['label', 'data'])
  });

  xit('getSelectedFeatureData - Feature', function () {
    data.feature = data.report.parsedResults[0].key;
  });

  it('getDataForBar', function () {
    var filteredByFeature = data.report.parsedResults[0];
    var barData = AnalysisClassification.getDataForBar(filteredByFeature.value.crosstab_results, data.report.buckets);
    expect(barData.length).toBeTruthy();
    checkObjectKeys(barData[0], ['key', 'values'])
  });

  it('getDataForPie', function () {
    var metricData = data.report.parsedResults[0];
    var pieData = AnalysisClassification.getDataForPie(metricData.value.crosstab_results, data.report.buckets);
    expect(pieData.length).toBeTruthy();
    checkObjectKeys(pieData[0], ['label', 'value']);
  });

  xit('buildTable', function () {

  });

});
(function () {
  'use strict';

  angular
    .module('tests_js_factory', [])
    .factory('TestsFactory', function () {
      var F = {};

      var analysisMockClassificationData = {
        "report": {
          "account_id": "57ff4f0ae252a51582fd1776",
          "analysis_type": "classification",
          "analyzed_metric": "CSAT",
          "application": "Predictive Matching",
          "created_at": 1477111962596,
          "filters": {},
          "id": "580af09ae252a50facadd36b",
          "level": "day",
          "metric_type": "Numeric",
          "metric_values": [
            "CSAT(0:0)",
            "CSAT(0:5)",
            "CSAT(5:10)"
          ],
          "metric_values_range": [
            0,
            10
          ],
          "timerange_results": [
            {
              "class_key": 0,
              "timerange": [
                [
                  1472688000000,
                  0
                ]
              ]
            },
            {
              "class_key": 1,
              "timerange": [
                [
                  1472688000000,
                  0
                ]
              ]
            },
            {
              "class_key": 2,
              "timerange": [
                [
                  1472688000000,
                  0
                ]
              ]
            },
            {
              "class_key": -1,
              "timerange": [
                [
                  1472688000000,
                  0
                ]
              ]
            }
          ],
          "title": "CSAT_Report",
          "user": "57ff4f0ae252a51582fd1778",
          "parsedFilters": [],
          "parsedResults": [
            {
              "key": "action native id",
              "value": {
                "crosstab_results": [{
                  "key": "112-A3001",
                  "value": {
                    "0": "0",
                    "1": "3.147",
                    "2": "3.147",
                    "-1": "0"
                  }
                }],
                "discriminative_weight": 0.4453053525421948,
                "values": ["112-A3001"]
              }
            }
          ],
          "parsed_analyzed_metric": "CSAT",
          "width": 1420,
          "tabs": [
            {
              "name": "action native id",
              "active": false,
              "$$hashKey": "06S"
            }
          ],
          "metric_buckets": [
            "CSAT(0:0)",
            "CSAT(0:5)",
            "CSAT(5:10)"
          ],
          "buckets": [
            "CSAT(0:0)",
            "CSAT(0:5)",
            "CSAT(5:10)"
          ],
          "selected": true
        },
        "flags": {
          "showBar": false,
          "showPie": false,
          "showScatter": false,
          "showTrend": false,
          "showBoxPlot": false,
          "showSwitchBtns": false,
          "showTable": false,
          "showCharts": false,
          "showMultichart": false
        }
      };

      var analysisMockRegressionData = {
        "report": {
          "analysis_type": "regression",
          "analyzed_metric": "CSAT",
          "metric_type": "Numeric",
          "metric_values": ["0", "10"],
          "metric_values_range": [0, 10],
          "results": {
            "action:Bill_Payment": {
              "bar": [
                {
                  "key": "Bar",
                  "values": [
                    {
                      "avg_metric": 5.061728395061729,
                      "count": 162,
                      "label": "50.0"
                    },
                    {
                      "avg_metric": 5.764705882352941,
                      "count": 68,
                      "label": "100.0"
                    },
                    {
                      "avg_metric": 5.321428571428571,
                      "count": 56,
                      "label": "10.0"
                    }
                  ]
                }
              ],
              "boxplot": [
                {
                  "label": 10,
                  "values": {
                    "Q1": 3,
                    "Q2": 5,
                    "Q3": 7,
                    "mean": 5.321428571428571,
                    "mode": [
                      3,
                      10
                    ],
                    "outliers": [],
                    "whisker_high": 10,
                    "whisker_low": 0
                  }
                }
              ],
              "pie": [{
                "label": 50,
                "value": 162
              }],
              "rank": 8,
              "scatter": [
                {
                  "key": "Bubble",
                  "values": [50, 5]
                }
              ],
              "score": 0.14315518289625803,
              "value_type": "Numeric",
              "values": [1, 2, 3, 4, 5]
            }
          },
          "id": "580af09ae252a50facadd36b",
          "timerange_results": [
            {
              "data": [[1473811200000, 15]],
              "label": "Count"
            },
            {
              "data": [[1473811200000, 5.466666666666667]],
              "label": "CSAT"
            }
          ],
          "title": "CSAT_Report",
          "parsedFilters": {},
          "parsedResults": [
            {
              "key": "action Bill Payment",
              "value": {
                "bar": [
                  {
                    "key": "Bar",
                    "values": [
                      {
                        "avg_metric": 5.061728395061729,
                        "count": 162,
                        "label": "50.0"
                      },
                      {
                        "avg_metric": 5.764705882352941,
                        "count": 68,
                        "label": "100.0"
                      },
                      {
                        "avg_metric": 5.321428571428571,
                        "count": 56,
                        "label": "10.0"
                      }
                    ]
                  }
                ],
                "boxplot": [
                  {
                    "label": 10,
                    "values": {
                      "Q1": 3,
                      "Q2": 5,
                      "Q3": 7,
                      "mean": 5.321428571428571,
                      "mode": [
                        3,
                        10
                      ],
                      "outliers": [],
                      "whisker_high": 10,
                      "whisker_low": 0
                    }
                  },
                  {
                    "label": 50,
                    "values": {
                      "Q1": 3,
                      "Q2": 5,
                      "Q3": 7,
                      "mean": 5.061728395061729,
                      "mode": [
                        6,
                        29
                      ],
                      "outliers": [],
                      "whisker_high": 10,
                      "whisker_low": 0
                    }
                  },
                  {
                    "label": 100,
                    "values": {
                      "Q1": 4,
                      "Q2": 6,
                      "Q3": 8,
                      "mean": 5.764705882352941,
                      "mode": [
                        6,
                        12
                      ],
                      "outliers": [],
                      "whisker_high": 10,
                      "whisker_low": 0
                    }
                  }
                ],
                "pie": [
                  {
                    "label": 50,
                    "value": 162
                  },
                  {
                    "label": 100,
                    "value": 68
                  },
                  {
                    "label": 10,
                    "value": 56
                  }
                ],
                "rank": 8,
                "scatter": [
                  {
                    "key": "Bubble",
                    "values": [[
                      50,
                      5
                    ]]
                  }
                ],
                "score": 0.14315518289625803,
                "value_type": "Numeric",
                "values": [5]
              }
            },
            {
              "key": "context customer seniority",
              "value": {
                "bar": [
                  {
                    "key": "Bar",
                    "values": [
                      {
                        "avg_metric": 4.780487804878049,
                        "count": 41,
                        "label": "NEW"
                      }
                    ]
                  }
                ],
                "boxplot": [
                  {
                    "label": "NEW",
                    "values": {
                      "Q1": 2,
                      "Q2": 5,
                      "Q3": 7,
                      "mean": 4.780487804878049,
                      "mode": [
                        5,
                        7
                      ],
                      "outliers": [],
                      "whisker_high": 10,
                      "whisker_low": 0
                    }
                  }
                ],
                "pie": [
                  {
                    "label": "NEW",
                    "value": 41
                  }
                ],
                "rank": 3,
                "score": 0.7387046200771887,
                "value_type": "Label",
                "values": [5]
              }
            }
          ],
          "parsed_analyzed_metric": "CSAT",
          "width": 1420,
          "tabs": [
            {
              "name": "action Bill Payment",
              "active": false
            }
          ]
        },
        "filters": {
            "ab_testing": "true",
            "action_vector": {
              "Bill_Payment": [],
              "Closing_Account": [],
              "Technical_Support": [],
              "agent_gender": [],
              "agent_location": [],
              "agent_seniority": [],
              "selected_agent_skill": []
            },
            "context_vector": {
              "customer_age": [],
              "customer_gender": [],
              "customer_last_call_intent": [],
              "customer_location": [],
              "customer_num_calls": [],
              "customer_seniority": [],
              "customer_status": []
            },
            "from": "09/01/2016",
            "level": "day",
            "models": [],
            "plot_by": "all",
            "plot_type": "time",
            "predictor_id": "57ff4f14e252a51582fd17e4",
            "request_url": "/predictors/facets/json",
            "to": "10/01/2016"
          },
        "flags": {
          "showBar": false,
          "showPie": false,
          "showScatter": false,
          "showTrend": false,
          "showBoxPlot": false,
          "showSwitchBtns": false,
          "showTable": false,
          "showCharts": false,
          "showMultichart": false
        },
        "feature": "Overall"
      };

      F.getAnalysisMockClassificationData = function () {
        return analysisMockClassificationData;
      };

      F.getAnalysisMockRegressionData = function () {
        return analysisMockRegressionData;
      };

      return F;
    });
})();
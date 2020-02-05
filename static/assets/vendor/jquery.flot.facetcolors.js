(function ($) {

    var options = { facetColors: [] };
    function init(plot) {
        var colors = [];
        function checkFacetsColorsEnabled(plot, options) {
            if (options.facetColors) {
                colors = options.facetColors;
                plot.hooks.processDatapoints.push(processFacetColors);
            }
        }

        function processFacetColors(plot, series, datapoints) {
            if (colors.length > 0) {
                _.each(colors, function(el) {
                    if (series.label == el.label)
                        series.color = el.color;
                })
            }
        }
        //plot.hooks.processOptions.push(getOptions);
        plot.hooks.processOptions.push(checkFacetsColorsEnabled);
    }


    $.plot.plugins.push({
        init: init,
        options: options,
        name: 'facetcolors',
        version: '1.0'
    });
})(jQuery);
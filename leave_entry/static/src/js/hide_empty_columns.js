odoo.define('leave_entry.hide_empty_columns', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');

    ListRenderer.include({
        _renderView: function () {
            var self = this;
            // Call the original _renderView function
            return this._super.apply(this, arguments).then(function () {
                // After rendering the view, hide the column if all values are empty
                self._hideEmptyColumns();
            });
        },

        _hideEmptyColumns: function () {
            // Select the table rows and column headers
            var rows = this.$el.find('tbody tr');
            var columns = this.$el.find('thead th');

            // Loop through each column to check for empty values
            columns.each(function (index) {
                var hideColumn = true;  // Assume the column is empty
                // Loop through each row in this column
                rows.each(function () {
                    var $cell = $(this).find('td').eq(index);

                    // Check if the cell is visible and has a value (ignores invisible cells)
                    if ($cell.is(':visible') && $cell.text().trim()) {
                        hideColumn = false;  // Column has a value, don't hide it
                        return false;  // Break the loop
                    }
                });

                // If all cells in the column are empty and visible, hide the entire column
                if (hideColumn) {
                    // Hide the column header
                    $(this).hide();
                    // Hide all cells in this column
                    rows.each(function () {
                        $(this).find('td').eq(index).hide();
                    });
                }
            });
        }
    });
});

odoo.define('leave_entry.ColoredFieldWidget', function(require) {
    "use strict";

    var Field = require('web.basic_fields').FieldChar;  // Use FieldChar or Field depending on your field type

    var ColoredFieldWidget = Field.extend({
        // Render the value with color based on conditions
        _renderReadonly: function() {
            var value = this.value;
            var color;

            // Define colors based on the value
            if (value === 'AB') {
                color = 'red';  // Absent
            } else if (value === 'WK') {
                color = '#FFBF00';  // Working Day
            } else if (value === '✔') {
                color = 'green';  // Present
                
            } 
            else if (value === 'AV') {
                color = '#0000FF';  // Present
                
            }
            else if (value === 'HO') {
                color = 'green';  // Present
                
            }
            else if (value === 'T') {
                color = '#6E260E';  // Present
                
            }
            
            else {
                color = '#ff0000';  // Leave type code (default color)
            }

            // Set the HTML content with the defined color
            this.$el.html('<span style="color: ' + color + ';">' + value + '</span>');
        }
    });

    // Register the widget
    var registry = require('web.field_registry');
    registry.add('colored_field', ColoredFieldWidget);
});

/** @odoo-module **/
import { registry } from "@web/core/registry";
import { FloatTimeField,floatTimeField } from "@web/views/fields/float_time/float_time_field";
import { _t } from "@web/core/l10n/translation";
const { useRef } = owl;

export class EasyTimePickerWidget extends FloatTimeField {
    static template = 'easy_timepicker_widget.EasyTimePicker'
    static props = {
        ...FloatTimeField.props,
    };

    setup() {
        super.setup();
        this.time_field_ref = useRef('numpadDecimal')
        this.element_id = this.props.id
        this.timepicker_element = null
    }

    _hideTimePicker(event){
        if (this.timepicker_element){
            $(this.timepicker_element).remove()
            this.timepicker_element = null
        }
    }

    _parseInitialTime(){
        if(this.time_field_ref){
            var cur_time = this.time_field_ref.el.value.split(':')
            var hours =  cur_time[0]
            var minutes = cur_time[1]
            return [hours,minutes]
        }
        return ['00','00']

    }

    _showTimePicker(event){
        this._parseInitialTime()
        var self = this
        var element = this.time_field_ref.el.parentElement
        var time_field_pos = $(element).offset();

        $(element).after(self._getPickerElementHTML())
        var picker = $(element).next()
        var rect = event.target.getBoundingClientRect();
        // Calculate the position
        var top = time_field_pos.top + $(element)[0].offsetHeight;
        var left = time_field_pos.left;
        // If width position of widget exceeds the window width 
        if ((left+200)>window.innerWidth){
            left = window.innerWidth - 210
        }
        this.timepicker_element = picker[0]

        picker.on("blur", function(event) {
            if ($(event.relatedTarget).closest(picker[0]).length) {
              // Focus stayed within the parent, so don't perform blur logic
              return;
            }
            self._hideTimePicker();
        })

        picker.find('.hours_picker').on('change blur',()=>{
            setTimeout(()=>{
                picker.focus()
            },10)
        })
        picker.find('.minutes_picker').on('change blur',()=>{
            setTimeout(()=>{
                picker.focus()
            },10)
        })

        self._setHandlers()

        setTimeout(()=>{
            picker.focus()

        },10)

        picker[0].style.top = top + 'px';
        picker[0].style.left = left + 'px';

        // Show the popup div
        picker[0].style.display = 'block';


    }

    _setHandlers(){
        var self = this
        var timepicker_element = $(this.timepicker_element)
        if(timepicker_element){
            timepicker_element.find('.hour_up_button').click(()=>{
                self._setSelectValue(timepicker_element.find('.hours_picker'), 1, 24)
            })

            timepicker_element.find('.hour_down_button').click(()=>{
                self._setSelectValue(timepicker_element.find('.hours_picker'), -1, 24)
            })

            timepicker_element.find('.minute_up_button').click(()=>{
                self._setSelectValue(timepicker_element.find('.minutes_picker'), 1, 60)
            })

            timepicker_element.find('.minute_down_button').click(()=>{
                self._setSelectValue(timepicker_element.find('.minutes_picker'), -1, 60)
            })

            timepicker_element.find('.apply_btn').click(()=>{
                var hour_picker = timepicker_element.find('.hours_picker')
                var minute_picker = timepicker_element.find('.minutes_picker')
                self.time_field_ref.el.value = `${hour_picker.val()}:${minute_picker.val()}`
                setTimeout(()=>{
                    timepicker_element.focus()

                },20)
                setTimeout(()=>{
                    timepicker_element.blur()

                },20)
                self.time_field_ref.el.dispatchEvent(new Event('input', { bubbles: true }))
            })
        }
    }

    _setSelectValue(selection_element,offset,maxVal){
        var self = this
        var cur_val = selection_element.val()==0 ? maxVal : selection_element.val()
        var new_val = (Number(cur_val) + offset) % maxVal
        selection_element.val( new_val>=10? new_val : '0'+new_val)

        setTimeout(()=>{
            $(self.timepicker_element).focus()
        })
    }

    _getHoursSelectOptionsHTML(initialHours){
        var hour_options = ''
        for(let curHour=0; curHour<=23; curHour++){
            let hour = curHour<10 ? '0'+curHour : curHour 
            hour_options+= `<option value="${hour}" ${hour==initialHours ? 'selected': ''}>${hour}</option>\n`
        }
        return hour_options
    }

    _getMinutesSelectOptionsHTML(initialMinutes){
        var minutes_options = ''
        for(let curMinute=0; curMinute<=59; curMinute++){
            let minute = curMinute<10 ? '0'+curMinute : curMinute 
            minutes_options+= `<option value="${minute}" ${minute==initialMinutes ? 'selected': ''}>${minute}</option>\n`
        }
        return minutes_options
    }

    _getPickerElementHTML(){
        var self = this
        var [hours,minutes] = self._parseInitialTime()

        return `<div class="easy_timepicker" tabindex="0" style="display:none;">
                    <div class="row justify-content-center text-center gx-1">
                        <div class="col-4">
                            <button class="hour_up_button btn btn-sm btn-primary px-1 py-0 m-0 mb-1"><i class="fa fa-arrow-up"></i></button>
                            <select class="hours_picker text-center form-select">
                                ${self._getHoursSelectOptionsHTML(hours)}
                            </select>
                            <button class="hour_down_button btn btn-sm btn-primary px-1 py-0 m-0 mt-1"><i class="fa fa-arrow-down"></i></button>
                        </div>
                        <div class="col-1 text-center align-self-center"> : </div>
                        <div class="col-4">
                            <button class="minute_up_button btn btn-sm btn-primary px-1 py-0 m-0 mb-1"><i class="fa fa-arrow-up"></i></button>
                            <select class="minutes_picker text-center form-select">
                                ${self._getMinutesSelectOptionsHTML(minutes)}
                            </select>
                            <button class="minute_down_button btn btn-sm btn-primary px-1 py-0 m-0 mt-1"><i class="fa fa-arrow-down"></i></button>
                        </div>
                        <div class="col-3 text-center align-self-center"><button class="apply_btn btn btn-sm btn-primary px-1 py-0 m-0 mt-1 mb-1">Ok <i class="fa fa-check"></i></button></div>

                    </div>
                </div>`
    }
}

export const EasyTimePicker = {
    ...floatTimeField,
    component: EasyTimePickerWidget,

};
registry.category("fields").add("easy_timepicker", EasyTimePicker);
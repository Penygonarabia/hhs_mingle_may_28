/** @odoo-module **/
import {DomGanttCommonRenderer} from "@dom_gantt_view/js/common/domgantt_common_renderer.esm";
import {patch} from "@web/core/utils/patch";

patch(DomGanttCommonRenderer.prototype, {
    cleanOptions(options) {
        const opt = super.cleanOptions(options);
        if (this.props.model.meta.resourceWOEventField) {
            opt.filterResourcesWithEvents = false;
        }
        return opt;
    },
    _getExtraResourceId(columnFields, resourceWOEventField, item) {
        const uniqs = [];
        Object.keys(columnFields).forEach(function (fName) {
            if (fName === resourceWOEventField) {
                uniqs.push(item.id);
                // Uniqs.push([item.id, item.display_name].toString());
                // eslint-disable-next-line no-prototype-builtins
            } else if (item.hasOwnProperty(fName)) {
                uniqs.push(item[fName]);
            } else {
                uniqs.push(false);
            }
        });
        return uniqs.join("_");
    },
    extraResources() {
        const resources = super.extraResources();
        const self = this;
        if (this.props.model.data.woEventResources) {
            const columnFields = this.props.model.meta.columnFields;
            const resourceWOEventField = this.props.model.meta.resourceWOEventField;
            const fieldObject = columnFields[resourceWOEventField];
            const extraRes = [];
            this.props.model.data.woEventResources.forEach(function (item) {
                const resourceItem = {
                    // Id: "extra_resource_" + item.id,
                    id: self._getExtraResourceId(
                        columnFields,
                        resourceWOEventField,
                        item
                    ),
                    // Title: item.display_name,
                    recordId: null,
                    postRenderFields: [],
                    // Used to replace resource title
                    forceValues: {},
                    // Used to set default value for the case of extra resource
                    extraResourceValues: {},
                };
                if (fieldObject.widget !== undefined) {
                    // To post-render the value by its widget (by onResourceLabelDidMount)
                    resourceItem.postRenderFields = [resourceWOEventField];
                    if (fieldObject.type === "many2one") {
                        // [id, display_name]
                        // resourceItem.forceValues[resourceWOEventField] = [item.id, item.display_name];
                        resourceItem.forceValues[resourceWOEventField] = item.id;
                    } else {
                        // Case of many2many
                        resourceItem.forceValues[resourceWOEventField] = [item.id];
                    }
                }
                resourceItem[resourceWOEventField] = item.display_name;
                if (fieldObject.type === "many2one") {
                    // ResourceItem.extraResourceValues[resourceWOEventField] = [item.id, item.display_name];
                    resourceItem.extraResourceValues[resourceWOEventField] = item.id;
                } else {
                    resourceItem.extraResourceValues[resourceWOEventField] = [item.id];
                }
                if (fieldObject.options.fields !== undefined) {
                    // FieldName1: field of the model of the gantt
                    // fieldName2: field of the extra resource
                    // eslint-disable-next-line array-callback-return
                    Object.entries(fieldObject.options.fields).map(
                        // eslint-disable-next-line array-callback-return
                        ([fieldName1, fieldName2]) => {
                            if (Array.isArray(item[fieldName2])) {
                                resourceItem[fieldName1] =
                                    item[fieldName2][item[fieldName2].length - 1];
                            } else {
                                resourceItem[fieldName1] = item[fieldName2];
                            }
                        }
                    );
                }
                extraRes.push(resourceItem);
            });
            return [...resources, ...extraRes];
        }
        return resources;
    },
});

/** @odoo-module **/
import {DomGanttModel} from "@dom_gantt_view/js/domgantt_model.esm";
import {Domain} from "@web/core/domain";
import {evaluateExpr} from "@web/core/py_js/py";
import {patch} from "@web/core/utils/patch";

patch(DomGanttModel.prototype, {
    /**
     * @protected
     * @param {Object} data
     */
    async updateData(data) {
        await super.updateData(...arguments);
        if (this.meta.resourceWOEventField) {
            const domain = this.woEventResourcesDomain(data);
            data.woEventResources = await this._loadWOEventResource(domain);
        }
    },
    woEventResourcesDomain(data) {
        const self = this;
        const resp = [];
        Object.values(data.records).forEach(function (record) {
            const rawRecord = record.rawRecord[self.meta.resourceWOEventField];
            if (rawRecord !== undefined && Array.isArray(rawRecord)) {
                // M2O: [id, name] ==> get id
                // M2M: [id1, id2] ==> get both
                rawRecord.forEach(function (_id) {
                    if (Number.isInteger(_id)) {
                        resp.push(_id);
                    }
                });
            }
        });
        const resource_ids = Array.from(new Set(resp));
        if (resource_ids.length === 0) return [];
        return [["id", "not in", resource_ids]];
    },
    _getDomain(domain, context) {
        return typeof domain === "string"
            ? new Domain(evaluateExpr(domain, context)).toList()
            : domain || [];
    },
    async _loadWOEventResource(originDomain) {
        let domain = originDomain || [];
        const resp = [];
        const columnFieldObject =
            this.meta.columnFields[this.meta.resourceWOEventField];
        const fieldObject = this.meta.fields[this.meta.resourceWOEventField];
        if (columnFieldObject === undefined || fieldObject === undefined) {
            return [...resp];
        }
        if (
            !["many2one", "one2many", "many2many"].includes(fieldObject.type) ||
            fieldObject.relation === undefined
        ) {
            return [...resp];
        }
        let limit = 100;
        if (columnFieldObject.options.limit !== undefined) {
            limit = columnFieldObject.options.limit;
        }
        if (columnFieldObject.domain) {
            const domain2 = this._getDomain(
                columnFieldObject.domain,
                Object.assign(
                    {},
                    columnFieldObject.context,
                    this.env.searchModel.domainEvalContext
                )
            );
            domain = new Domain([...domain, ...domain2]).toList();
        }
        const kw = {
            limit: limit,
        };
        let readFields = ["id", "display_name"];
        if (columnFieldObject.options.fields !== undefined) {
            readFields = [
                ...readFields,
                ...Object.values(columnFieldObject.options.fields),
            ];
        }
        return this.orm.searchRead(fieldObject.relation, domain, readFields, kw);
    },
});
